"""Configuración local de FBM, sin cuentas ni credenciales externas."""
from homeassistant import config_entries
from homeassistant.core import callback
from .const import DOMAIN


class FBMConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Crear una única configuración FBM en Home Assistant."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Configurar en modo invitado, sin inventar credenciales."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        if user_input is not None:
            return self.async_create_entry(title="FBM (modo invitado)", data={})
        return self.async_show_form(step_id="user")

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Use Home Assistant's native Configure button."""
        return FBMCompetitionOptionsFlow()


class FBMCompetitionOptionsFlow(config_entries.OptionsFlow):
    """Select and manage whole competition groups, not just favorite teams."""

    def __init__(self):
        self._results = {}
        self._candidate = None
        self._remove_candidate = None
        self._refresh_candidate = None

    def _entry(self):
        record = self.hass.data.get(DOMAIN, {}).get(self.config_entry.entry_id)
        if type(record) is not dict:
            raise ValueError("La integración no está disponible")
        return record

    @staticmethod
    def _display_group(group, index=0):
        """Never render FBM's opaque phase/group IDs in options menus."""
        fields = [group.get("team_name"), group.get("season_id"),
                  group.get("phase_name"), group.get("group_name")]
        readable = [v for v in fields if type(v) is str and v.strip()]
        if len(readable) == 1:
            return f"Competición {index + 1} · {readable[0]}"
        if not group.get("phase_name") and not group.get("group_name"):
            return " · ".join(filter(None, [group.get("team_name"),
                                             group.get("season_id"),
                                             f"Competición {index + 1}"]))
        return " · ".join(readable)

    async def async_step_init(self, user_input=None):
        return self.async_show_menu(
            step_id="init", menu_options=["search", "manage", "refresh", "automatic"])

    async def async_step_automatic(self, user_input=None):
        """Explicit opt-in to scheduled sync; both switches default to off."""
        import probatio
        saved = self.config_entry.options
        if user_input is not None:
            groups = user_input.get("auto_groups") is True
            players = user_input.get("auto_players") is True
            # Individual player queries require active group syncing.
            if players and not groups:
                return self.async_show_form(
                    step_id="automatic", errors={"base": "auto_requires_groups"},
                    data_schema=probatio.Schema({
                        probatio.Required("auto_groups", default=False): bool,
                        probatio.Required("auto_players", default=False): bool,
                    }))
            return self.async_create_entry(
                title="", data={**saved, "auto_groups": groups,
                                "auto_players": players})
        return self.async_show_form(
            step_id="automatic",
            data_schema=probatio.Schema({
                probatio.Required("auto_groups",
                                  default=saved.get("auto_groups") is True): bool,
                probatio.Required("auto_players",
                                  default=saved.get("auto_players") is True): bool,
            }))

    async def async_step_search(self, user_input=None):
        import probatio
        errors = {}
        if user_input is not None:
            query = user_input["texto"].strip()
            if not 3 <= len(query) <= 80:
                errors["base"] = "invalid_search"
            else:
                try:
                    client = self._entry()["cliente_independiente"]
                    candidates = await client.async_search_teams(query, 0)
                    self._results = {
                        result["id"]: result for result in candidates[:40]
                        if type(result) is dict and
                        type(result.get("id")) is str and
                        type(result.get("nombre")) is str and
                        0 < len(result["id"]) <= 512
                    }
                    if self._results:
                        return await self.async_step_select()
                    errors["base"] = "no_teams"
                except Exception:
                    errors["base"] = "cannot_connect"
        return self.async_show_form(
            step_id="search",
            data_schema=probatio.Schema({probatio.Required("texto"): str}),
            errors=errors)

    async def async_step_select(self, user_input=None):
        import probatio
        if not self._results:
            return await self.async_step_search()
        choices = {
            team_id: " · ".join(filter(None, [
                item["nombre"], item.get("categoria"), item.get("temporada")]))
            for team_id, item in self._results.items()
        }
        if user_input is not None:
            team_id = user_input["equipo"]
            if team_id not in self._results:
                return self.async_show_form(
                    step_id="select",
                    data_schema=probatio.Schema({probatio.Required("equipo"): probatio.In(choices)}),
                    errors={"base": "invalid_selection"})
            self._candidate = {"team_id": team_id, "name": self._results[team_id]["nombre"],
                               "season": self._results[team_id].get("temporada"),
                               "category": self._results[team_id].get("categoria")}
            return await self.async_step_confirm()
        return self.async_show_form(
            step_id="select",
            data_schema=probatio.Schema({probatio.Required("equipo"): probatio.In(choices)}))

    async def async_step_confirm(self, user_input=None):
        import probatio
        from .competition_manager import identify_competition, group_selection
        candidate = self._candidate
        if not candidate:
            return await self.async_step_search()
        if user_input is None:
            try:
                client = self._entry()["cliente_independiente"]
                candidate["verified"] = await identify_competition(
                    client, candidate["team_id"], candidate["season"])
            except Exception:
                return self.async_show_form(
                    step_id="confirm", errors={"base": "cannot_verify"},
                    description_placeholders={"team": candidate["name"], "group": "No disponible"},
                    data_schema=probatio.Schema({probatio.Required("confirmar", default=False): bool}))
        data = candidate.get("verified", {})
        if data.get("status") != "verified":
            return self.async_show_form(
                step_id="confirm", errors={"base": "season_unverified"},
                description_placeholders={"team": candidate["name"], "group": "Temporada no verificada"},
                data_schema=probatio.Schema({probatio.Required("confirmar", default=False): bool}))
        errors = {}
        pending_rosters = ""
        if user_input is not None and user_input.get("confirmar") is True:
            from datetime import date, timedelta
            from homeassistant.helpers.dispatcher import async_dispatcher_send
            from .competition_sync import sync_group

            entry = self._entry()
            identity = group_selection(data)
            archive = await self.hass.async_add_executor_job(
                entry["competitions_archive_factory"],
                entry["competitions_sqlite_path"])
            await self.hass.async_add_executor_job(
                archive.follow, identity, candidate["team_id"],
                {"team_name": candidate["name"],
                 "competition_name": (candidate.get("category") or "")[:120],
                 "phase_name": data.get("phase_name", ""),
                 "group_name": data.get("group_name", "")})
            today = date.today()
            try:
                result = await sync_group(
                    entry["cliente_independiente"], archive, candidate["team_id"],
                    today - timedelta(days=45), today + timedelta(days=60),
                    fetch_rosters=True, expected_competition=identity)
                if result.get("saved") and not result.get("roster_errors"):
                    return self.async_create_entry(title="", data=dict(self.config_entry.options))
                if result.get("saved"):
                    pending_rosters = ", ".join(result.get("failed_roster_names", []))
                    errors["base"] = "rosters_pending_named" if pending_rosters else "rosters_pending"
                else:
                    errors["base"] = result.get("status", "cannot_refresh")
            except Exception:
                errors["base"] = "cannot_refresh"
            finally:
                async_dispatcher_send(
                    self.hass, f"fbm_competitions_refresh_{self.config_entry.entry_id}")

        return self.async_show_form(
            step_id="confirm", errors=errors,
            data_schema=probatio.Schema({probatio.Required("confirmar", default=False): bool}),
            description_placeholders={
                "team": candidate["name"],
                "pending_rosters": pending_rosters,
                "group": (
                    f'{data["season_id"]} · '
                    f'{data.get("phase_name", "Fase")} · '
                    f'{data.get("group_name", "Grupo")} · '
                    f'{data["team_count"]} equipos'
                ),
            })

    async def async_step_manage(self, user_input=None):
        import probatio
        entry = self._entry()
        # Do not create a SQLite archive merely to view the manager.
        from pathlib import Path
        archive_path = entry["competitions_sqlite_path"]
        if not await self.hass.async_add_executor_job(Path(archive_path).is_file):
            return self.async_abort(reason="none_followed")
        archive = await self.hass.async_add_executor_job(
            entry["competitions_archive_factory"], archive_path)
        groups = await self.hass.async_add_executor_job(archive.followed_with_anchor)
        if not groups:
            return self.async_abort(reason="none_followed")
        options = {
            str(i): self._display_group(group, i)
            for i, group in enumerate(groups)
        }
        if user_input is not None:
            selected = user_input["competicion"]
            if selected not in options:
                return self.async_show_form(
                    step_id="manage",
                    data_schema=probatio.Schema({probatio.Required("competicion"): probatio.In(options)}),
                    errors={"base": "invalid_selection"})
            self._remove_candidate = groups[int(selected)]
            return await self.async_step_unfollow()
        return self.async_show_form(
            step_id="manage",
            data_schema=probatio.Schema({probatio.Required("competicion"): probatio.In(options)}))

    async def async_step_refresh(self, user_input=None):
        """Choose a previously followed competition for a manual refresh."""
        from pathlib import Path
        import probatio

        entry = self._entry()
        archive_path = entry["competitions_sqlite_path"]
        if not await self.hass.async_add_executor_job(Path(archive_path).is_file):
            return self.async_abort(reason="none_followed")
        archive = await self.hass.async_add_executor_job(
            entry["competitions_archive_factory"], archive_path)
        groups = await self.hass.async_add_executor_job(archive.followed_with_anchor)
        # Old DEV archives may lack an anchor: require re-selection, do not
        # guess the team from a display label or arbitrary competition member.
        choices = {
            str(i): self._display_group(g, i)
            for i, g in enumerate(groups) if g.get("anchor_team_id")
        }
        if not choices:
            return self.async_abort(reason="no_refreshable_groups")
        if user_input is not None:
            selected = user_input.get("competicion")
            if selected in choices:
                self._refresh_candidate = groups[int(selected)]
                return await self.async_step_refresh_confirm()
            return self.async_show_form(
                step_id="refresh",
                data_schema=probatio.Schema({
                    probatio.Required("competicion"): probatio.In(choices)}),
                errors={"base": "invalid_selection"})
        return self.async_show_form(
            step_id="refresh",
            data_schema=probatio.Schema({
                probatio.Required("competicion"): probatio.In(choices)}))

    async def async_step_refresh_confirm(self, user_input=None):
        """Only a second explicit confirmation can fetch competition data."""
        from datetime import date, timedelta
        import probatio

        selected = self._refresh_candidate
        if not selected:
            return await self.async_step_refresh()
        errors = {}
        if user_input is not None and user_input.get("confirmar") is True:
            from .competition_sync import sync_group
            begin = date.today() - timedelta(days=45)
            end = date.today() + timedelta(days=60)
            entry = self._entry()
            try:
                archive = await self.hass.async_add_executor_job(
                    entry["competitions_archive_factory"],
                    entry["competitions_sqlite_path"])
                result = await sync_group(
                    entry["cliente_independiente"], archive,
                    selected["anchor_team_id"], begin, end,
                    fetch_rosters=user_input.get("incluir_plantillas") is True,
                    expected_competition={
                        key: selected[key] for key in
                        ("season_id", "phase_id", "group_id")
                    })
                if result.get("status") not in ("ok", "partial") or not result.get("saved"):
                    errors["base"] = result.get("status", "cannot_refresh")
                elif result.get("competition") != {
                    key: selected[key] for key in
                    ("season_id", "phase_id", "group_id")
                }:
                    errors["base"] = "competition_changed"
                else:
                    return self.async_create_entry(
                        title="", data=dict(self.config_entry.options))
            except Exception:
                errors["base"] = "cannot_refresh"
        return self.async_show_form(
            step_id="refresh_confirm",
            data_schema=probatio.Schema({
                probatio.Required("confirmar", default=False): bool,
                probatio.Required("incluir_plantillas", default=False): bool,
            }),
            description_placeholders={
                "group": self._display_group(selected)
            },
            errors=errors)

    async def async_step_unfollow(self, user_input=None):
        """Explicit confirmation prevents accidental un-following."""
        import probatio
        chosen = self._remove_candidate
        if chosen is None:
            return await self.async_step_manage()
        if user_input is not None and user_input.get("confirmar") is True:
            entry = self._entry()
            archive = await self.hass.async_add_executor_job(
                entry["competitions_archive_factory"],
                entry["competitions_sqlite_path"])
            await self.hass.async_add_executor_job(
                archive.unfollow, {**chosen, "season_verified": True})
            # Historical snapshots are retained after stopping updates.
            return self.async_create_entry(title="", data=dict(self.config_entry.options))
        return self.async_show_form(
            step_id="unfollow",
            data_schema=probatio.Schema({
                probatio.Required("confirmar", default=False): bool}),
            description_placeholders={
                "group": self._display_group(chosen)})
