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

    async def async_step_init(self, user_input=None):
        return self.async_show_menu(
            step_id="init", menu_options=["search", "manage", "refresh"])

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
                               "season": self._results[team_id].get("temporada")}
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
        if user_input is not None and user_input.get("confirmar") is True:
            entry = self._entry()
            archive = await self.hass.async_add_executor_job(
                entry["competitions_archive_factory"],
                entry["competitions_sqlite_path"])
            await self.hass.async_add_executor_job(
                archive.follow, group_selection(data), candidate["team_id"])
            # This selects a group. It does not automatically download rosters.
            return self.async_create_entry(title="", data=dict(self.config_entry.options))
        return self.async_show_form(
            step_id="confirm",
            data_schema=probatio.Schema({probatio.Required("confirmar", default=False): bool}),
            description_placeholders={
                "team": candidate["name"],
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
        groups = await self.hass.async_add_executor_job(archive.followed)
        if not groups:
            return self.async_abort(reason="none_followed")
        options = {
            str(i): " · ".join((group["season_id"], group["phase_id"], group["group_id"]))
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
            str(i): " · ".join((g["season_id"], g["phase_id"], g["group_id"]))
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
                "group": " / ".join(
                    selected[k] for k in ("season_id", "phase_id", "group_id"))
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
                "group": " / ".join((chosen["season_id"], chosen["phase_id"],
                                     chosen["group_id"]))})
