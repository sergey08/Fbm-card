const FBM_TEAM_CONTENT_STYLES = `
      .fbm-player-person{display:flex;align-items:center;gap:8px;min-width:0}
      .fbm-player-photo{width:38px;height:38px;flex:0 0 38px;border-radius:50%;object-fit:cover;background:var(--secondary-background-color,#eee)}
      .fbm-fixture-side{display:flex;align-items:center;gap:7px;min-width:0}
      .fbm-fixture-side.fbm-fixture-away{justify-content:flex-end}
      .fbm-fixture-side.fbm-fixture-away img{order:2}
      .fbm-fixture-logo{width:25px;height:25px;flex:0 0 25px;object-fit:contain}
      .fbm-fixture-side span{font-size:.82rem;font-weight:600;overflow-wrap:anywhere}
      .fbm-fixture-side.fbm-fixture-away span{text-align:right}
      .fbm-fixture-list{display:grid;gap:9px;margin-top:10px}
      .fbm-fixture{border:1px solid var(--divider-color,#ddd);border-radius:12px;padding:11px;background:var(--card-background-color,#fff)}
      .fbm-fixture-teams{display:grid;grid-template-columns:minmax(0,1fr) auto minmax(0,1fr);align-items:center;gap:9px}
      .fbm-fixture-teams span{min-width:0;overflow-wrap:anywhere;font-weight:600;font-size:.83rem}
      .fbm-fixture-teams span:last-child{text-align:right}
      .fbm-fixture-score{font-variant-numeric:tabular-nums;white-space:nowrap;color:var(--primary-color,#1976d2);font-size:1rem}
      .fbm-roster{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,290px),1fr));gap:12px;margin:12px 0}
      .fbm-player{min-width:0;border:1px solid var(--divider-color,#ddd);border-radius:14px;padding:14px;background:var(--card-background-color,#fff);box-shadow:0 2px 8px rgba(0,0,0,.04)}
      .fbm-player-open{grid-column:1/-1;border-color:var(--primary-color,#1976d2)}
      .fbm-player-header{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:12px}
      .fbm-player-identity{min-width:0;display:flex;flex-direction:column;gap:3px}
      .fbm-player-name{font-size:.93rem;line-height:1.35;overflow-wrap:anywhere}
      .fbm-player-caption{color:var(--secondary-text-color,#737373);font-size:.79rem;line-height:1.4}
      ha-card .fbm-action{flex-shrink:0;border:1px solid var(--divider-color,#ddd);border-radius:10px;padding:8px 12px;background:var(--secondary-background-color,#f5f5f5);color:var(--primary-text-color,#222);font-weight:600;font-size:.82rem;cursor:pointer}
      ha-card .fbm-action:hover{border-color:var(--primary-color,#1976d2)}
      ha-card .fbm-action-primary{margin:10px 0;background:var(--primary-color,#1976d2);color:var(--text-primary-color,#fff);border-color:transparent}
      ha-card .fbm-action:disabled{opacity:.5;cursor:wait}
      .fbm-stat-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(88px,1fr));gap:8px}
      .fbm-stat{min-width:0;display:flex;flex-direction:column;gap:4px;padding:9px;border-radius:10px;background:var(--secondary-background-color,#f5f5f5)}
      .fbm-stat-primary{background:color-mix(in srgb,var(--primary-color,#1976d2) 10%,var(--card-background-color,#fff))}
      .fbm-stat-label{color:var(--secondary-text-color,#666);font-size:.73rem;line-height:1.2}
      .fbm-stat-value{font-size:1.08rem;line-height:1.2;font-variant-numeric:tabular-nums}
      .fbm-player-detail{margin-top:14px;padding-top:12px;border-top:1px solid var(--divider-color,#ddd)}
      .fbm-subheading{font-size:.92rem;margin:14px 0 10px}
      .fbm-match{border:1px solid var(--divider-color,#ddd);border-radius:12px;padding:12px;margin:10px 0}
      .fbm-match-header{display:flex;flex-wrap:wrap;align-items:baseline;justify-content:space-between;gap:4px 10px;margin-bottom:10px}
      .fbm-match-header strong{font-size:.85rem;overflow-wrap:anywhere}
      .fbm-match-grid{grid-template-columns:repeat(auto-fit,minmax(80px,1fr))}
      @media(max-width:420px){.fbm-roster{grid-template-columns:minmax(0,1fr)}.fbm-player{padding:11px}.fbm-stat-grid{grid-template-columns:repeat(3,minmax(0,1fr))}.fbm-match-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.fbm-player-header{gap:8px}.fbm-player-name{font-size:.86rem}}
`;

function fbmFixtureDateKey(value) {
  if (typeof value !== "string") return "";
  const parts = value.match(/^(\d{2})\/(\d{2})\/(\d{4})$/);
  return parts ? `${parts[3]}-${parts[2]}-${parts[1]}` : value;
}

function renderFBMFixtures(view, card, matches, resolveTeam, crests) {
  const games = view._element("div", "", "fbm-fixture-list");
  const sorted = [...matches].sort((a, b) => (a.jornada ?? 999) - (b.jornada ?? 999) ||
    fbmFixtureDateKey(a.fecha).localeCompare(fbmFixtureDateKey(b.fecha)) ||
    String(a.hora || "").localeCompare(String(b.hora || "")));
  for (const match of sorted) {
    const box = view._element("article", "", "fbm-fixture");
    const top = view._element("div", "", "fbm-match-header");
    top.append(view._element("strong", Number.isInteger(match.jornada) ? "Jornada " + match.jornada : "Jornada sin indicar"));
    top.append(view._element("span", [match.fecha, match.hora].filter(Boolean).join(" · ") || "Fecha pendiente", "fbm-player-caption"));
    box.append(top);
    const teams = view._element("div", "", "fbm-fixture-teams");
    const teamLabel = (name, image, side) => {
      const team = resolveTeam?.(name);
      const box = view._element(team?.id ? "button" : "div", "", "fbm-fixture-side fbm-fixture-" + side);
      if (team?.id) {
        box.type = "button";
        box.addEventListener("click", () => view._openTeam(team));
      }
      image ||= (crests && Object.hasOwn(crests, name) ? crests[name] : null) || team?.escudo;
      if (typeof image === "string" && (/^data:image\/(png|jpeg|webp);base64,/.test(image) || view._officialLogoUrl(image))) {
        const img = document.createElement("img"); img.src = image;
        img.className = "fbm-fixture-logo"; img.alt = "Escudo de " + name;
        img.loading = "lazy"; img.addEventListener("error", () => img.remove(), { once: true });
        box.append(img);
      }
      box.append(view._element("span", name));
      return box;
    };
    teams.append(teamLabel(match.local || "Local sin indicar", match.img_local || view._apkCrestUrl(match.escudo_local), "local"));
    const score = match.marcador &&
      Number.isInteger(match.marcador.local) && Number.isInteger(match.marcador.visitante)
      ? match.marcador.local + " – " + match.marcador.visitante : "vs";
    teams.append(view._element("strong", score, "fbm-fixture-score"));
    teams.append(teamLabel(match.visitante || "Visitante sin indicar", match.img_visitante || view._apkCrestUrl(match.escudo_visitante), "away"));
    box.append(teams);
    if (match.campo) box.append(view._element("p", match.campo, "fbm-player-caption"));
    games.append(box);
  }
  card.append(games);
}

function renderFBMRoster(view, card, roster, pinned, state, toggleDetail, loadStats) {
  card.append(view._element("div", roster.length + " jugadores · Datos oficiales FBM", "fbm-section-subtitle"));
  const collection = view._element("div", "", "fbm-roster");
  const numeric = value => typeof value === "number" && Number.isFinite(value);
  const format = value => String(value);
  const chip = (label, value, emphasize = false) => {
    const el = view._element("div", "", emphasize ? "fbm-stat fbm-stat-primary" : "fbm-stat");
    el.append(view._element("span", label, "fbm-stat-label"));
    el.append(view._element("strong", format(value), "fbm-stat-value"));
    return el;
  };
  const matchColumns = [
    ["puntos", "Puntos"], ["asistencias", "Asist."],
    ["faltas_cometidas", "Faltas"], ["faltas_recibidas", "F. recib."],
    ["rebotes", "Rebotes"], ["rebotes_defensivos", "Reb. def."],
    ["rebotes_ofensivos", "Reb. of."], ["recuperaciones", "Recup."],
    ["perdidas", "Pérdidas"], ["valoracion", "Valoración"]
  ];
  for (const player of roster) {
    if (!player || typeof player.id !== "string" || typeof player.nombre !== "string") continue;
    const opened = state.playerDetailTeamId === pinned?.id &&
      state.playerDetailPlayerId === player.id ? state.playerDetail : null;
    const item = view._element("section", "", opened ? "fbm-player fbm-player-open" : "fbm-player");
    const header = view._element("div", "", "fbm-player-header");
    const person = view._element("div", "", "fbm-player-identity");
    const personRow = view._element("div", "", "fbm-player-person");
    const photo = player.foto || (opened && opened.foto) || "";
    if (typeof photo === "string" && (/^data:image\/(png|jpeg|webp);base64,/.test(photo) || /^https:\/\/appaficionfbm\.gesdeportiva\.es\/imagenes\.ashx\?tipo=jugador&id=[0-9a-fA-F]{16,4096}$/.test(photo))) {
      const img = document.createElement("img");
      img.className = "fbm-player-photo"; img.src = photo;
      img.alt = "Fotografía de " + player.nombre; img.loading = "lazy";
      img.addEventListener("error", () => img.remove(), { once: true });
      personRow.append(img);
    }
    personRow.append(view._element("strong", player.nombre, "fbm-player-name"));
    person.append(personRow);
    person.append(view._element("span", "Temporada " + (player.temporada || pinned.temporada || "FBM"), "fbm-player-caption"));
    const detailButton = view._element("button", opened ? "Cerrar ficha" : "Ver ficha", "fbm-action");
    detailButton.type = "button";
    detailButton.disabled = state.busy;
    detailButton.setAttribute("aria-expanded", String(!!opened));
    detailButton.addEventListener("click", () => toggleDetail(player.id));
    header.append(person, detailButton);
    item.append(header);
    const overview = view._element("div", "", "fbm-stat-grid");
    if (numeric(player.partidos_jugados)) overview.append(chip("Partidos", player.partidos_jugados));
    if (numeric(player.puntos_por_partido ?? player.media_puntos)) overview.append(chip("Puntos/partido", player.puntos_por_partido ?? player.media_puntos, true));
    if (numeric(player.minutos_por_partido)) overview.append(chip("Min/partido", player.minutos_por_partido));
    if (numeric(player.puntos_totales)) overview.append(chip("Puntos totales", player.puntos_totales));
    if ([player.partidos_jugados, player.puntos_por_partido ?? player.media_puntos, player.minutos_por_partido, player.puntos_totales].some(numeric)) item.append(overview);
    if (opened) {
      const details = view._element("div", "", "fbm-player-detail");
      const meta = [opened.equipo, opened.temporada, opened.categoria].filter(Boolean);
      if (meta.length) details.append(view._element("p", meta.join(" · "), "fbm-player-caption"));
      const statsButton = view._element("button", "Consultar estadísticas por partido", "fbm-action fbm-action-primary");
      statsButton.type = "button";
      statsButton.disabled = state.busy;
      statsButton.addEventListener("click", () => loadStats(player.id));
      details.append(statsButton);
      const stats = state.playerStatsTeamId === pinned?.id &&
        state.playerStatsEntryId === state.entry &&
        state.playerStatsPlayerId === player.id ? state.playerStats : null;
      if (stats) {
        const globals = stats.globales?.estadisticas || stats.globales || {};
        const available = [
          ["puntos_totales", "Puntos totales"], ["media_puntos", "Media puntos"],
          ["asistencias", "Asistencias"], ["faltas_cometidas", "Faltas"],
          ["faltas_recibidas", "F. recibidas"], ["rebotes", "Rebotes"],
          ["recuperaciones", "Recuperaciones"], ["perdidas", "Pérdidas"],
          ["valoracion", "Valoración"]
        ].filter(([key]) => numeric(globals[key]));
        if (available.length) {
          details.append(view._element("h4", "Estadísticas globales", "fbm-subheading"));
          const globalGrid = view._element("div", "", "fbm-stat-grid");
          for (const [key, label] of available) globalGrid.append(chip(label, globals[key]));
          details.append(globalGrid);
        }
        const games = Array.isArray(stats.partidos) ? stats.partidos : stats.partidos?.partidos || [];
        details.append(view._element("h4", "Partidos con estadísticas (" + games.length + ")", "fbm-subheading"));
        if (!games.length) details.append(view._element("p", "No hay partidos con estadísticas disponibles.", "fbm-player-caption"));
        for (const game of games) {
          const match = view._element("article", "", "fbm-match");
          const matchHeader = view._element("div", "", "fbm-match-header");
          matchHeader.append(view._element("strong", game.rival || "Rival sin indicar"));
          matchHeader.append(view._element("span", game.fecha || "Fecha pendiente", "fbm-player-caption"));
          match.append(matchHeader);
          const matchGrid = view._element("div", "", "fbm-stat-grid fbm-match-grid");
          for (const [key, label] of matchColumns) {
            if (numeric(game[key])) matchGrid.append(chip(label, game[key], key === "puntos"));
          }
          if (matchColumns.some(([key]) => numeric(game[key]))) match.append(matchGrid);
          details.append(match);
        }
      }
      item.append(details);
    }
    collection.append(item);
  }
  card.append(collection);
}

/* FBM Card DEV — presentación de datos; fuente oficial pendiente de validar. */
class FBMCard extends HTMLElement {
  static getConfigElement() { return document.createElement("fbm-card-editor"); }

  setConfig(config) {
    if (!config || typeof config !== "object") throw new Error("Configuración inválida");
    const priorTeam = this._config?.equipo_fijo?.id;
    const newTeam = config.equipo_fijo?.id;
    const changed = !!this._config && (this._config.modo_experimental !== config.modo_experimental ||
      this._config.id_tarjeta !== config.id_tarjeta || this._config.tipo_tarjeta !== config.tipo_tarjeta || priorTeam !== newTeam);
    if (changed) { this._experimental = null; this._fixedInit = false; this._searchInit = false; }
    if (config.tipo_tarjeta && !["busqueda", "equipo"].includes(config.tipo_tarjeta)) throw new Error("Tipo de tarjeta inválido");
    if (config.tipo_tarjeta === "equipo" && !config.equipo_fijo && !config.id_tarjeta) {
      throw new Error("Cada tarjeta de equipo necesita un id_tarjeta distinto para guardar su elección.");
    }
    this._config = { ...config };
    this._render();
    if (this._hass && config.modo_experimental === true) {
      if (config.tipo_tarjeta === "equipo" && (!this._fixedInit || changed))
        Promise.resolve().then(() => this._initializeFixed());
      else if (config.tipo_tarjeta !== "equipo" && (!this._searchInit || changed))
        Promise.resolve().then(() => this._initializeSearch());
    }
  }
  set hass(hass) {
    const hadHass = !!this._hass;
    const userChanged = hadHass && this._hass.user?.id !== hass?.user?.id;
    if (userChanged) this._experimental = null;
    this._hass = hass;
    if (this._config?.modo_experimental === true && (!hadHass || userChanged)) {
      if (this._config.tipo_tarjeta === "equipo") {
        this._fixedInit = false;
        Promise.resolve().then(() => this._initializeFixed());
      } else {
        this._searchInit = false;
        Promise.resolve().then(() => this._initializeSearch());
      }
    }
    // HA asigna hass con frecuencia. No reconstruir inputs activos en modo experimental:
    // reemplazar el DOM en cada actualización elimina el foco y bloquea la escritura.
    if (this._config?.modo_experimental === true && hadHass && !userChanged) return;
    this._render();
  }
  connectedCallback() {
    if (this._fbmRefreshTimer || typeof setInterval !== "function") return;
    this._fbmRefreshTimer = setInterval(() => { void this._autoRefresh(); }, 60000);
  }
  disconnectedCallback() {
    if (this._fbmRefreshTimer) clearInterval(this._fbmRefreshTimer);
    this._fbmRefreshTimer = null;
  }
  async _autoRefresh() {
    if (this._config?.modo_experimental !== true || this._config?.tipo_tarjeta !== "equipo" ||
        !this._hass?.callWS || (typeof document !== "undefined" && document.visibilityState === "hidden"))
      return;
    const state = this._experimentalState();
    if (state.busy || !state.entry || !state.selected || state.status?.sesion_vigente !== true) return;
    const selected = this._restoreExperimentalTeam(state.entry);
    if (!selected || selected.id !== state.selected) return;
    if (state.archivedData) {
      // Re-read the local archive; never fan out remote FBM calls per card.
      if (!state.lastArchiveCheck || Date.now() - state.lastArchiveCheck >= 5 * 60 * 1000)
        await this._loadArchivedFixed();
      return;
    }
    const stale = timestamp => timestamp > 0 && Date.now() - timestamp >= 15 * 60 * 1000;
    if (state.tab === "partidos" && this._fixedMatchesAvailable(state, selected.id) &&
        stale(state.lastScheduleUpdate)) {
      await this._experimentalAction("refresh_schedule");
    } else if (state.tab === "jugadores" && Array.isArray(state.players) &&
               state.playersTeamId === selected.id && state.playersEntryId === state.entry &&
               stale(state.lastPlayersUpdate)) {
      await this._experimentalAction("refresh_players");
    } else if ((state.tab === "clasificacion" || !state.tab) &&
               Array.isArray(state.standings) && stale(state.lastStandingsUpdate)) {
      await this._experimentalAction("standings");
    }
  }
  getCardSize() { return 5; }
  static getStubConfig() {
    return {
      type: "custom:fbm-card", title: "FBM Card", equipos: [],
      modo_experimental: true, tipo_tarjeta: "busqueda"
    };
  }

  _teams() {
    if (Array.isArray(this._config?.equipos) && this._config.equipos.length) return this._config.equipos.filter(x => x && typeof x.nombre === "string" && typeof x.entidad_datos === "string");
    if (this._config?.entidad_datos) return [{ nombre: String(this._config.equipo || "Equipo"), entidad_datos: this._config.entidad_datos }];
    return this._config?.descubrir_entidades === true ? this._availableOfficialEntities() : [];
  }

  _storageKey() {
    const userId = this._hass?.user?.id;
    if (!userId) return null;
    return "fbm-card:seleccion:v1:" + userId + ":" + String(this._config?.id_tarjeta || "predeterminada");
  }

  _favoriteKey() {
    const userId = this._hass?.user?.id;
    if (!userId) return null;
    return "fbm-card:favoritos:v1:" + userId + ":" + String(this._config?.id_tarjeta || "predeterminada");
  }

  _favorites() {
    const key = this._favoriteKey();
    if (!key) return [];
    try {
      const data = JSON.parse(window.localStorage?.getItem(key) || "[]");
      return Array.isArray(data) ? data.filter(id => typeof id === "string") : [];
    } catch (_) { return []; }
  }

  _toggleFavorite(entityId) {
    if (!this._teams().some(team => team.entidad_datos === entityId)) return;
    const key = this._favoriteKey();
    if (!key) return;
    const favorites = this._favorites();
    const updated = favorites.includes(entityId) ? favorites.filter(id => id !== entityId) : [...favorites, entityId];
    try { window.localStorage?.setItem(key, JSON.stringify(updated)); } catch (_) { return; }
    this._render();
  }

  _selectedTeam() {
    const teams = this._teams();
    const key = this._storageKey();
    let saved = null;
    try { if (key) saved = window.localStorage?.getItem(key); } catch (_) { /* almacenamiento deshabilitado */ }
    return teams.find(t => t.entidad_datos === saved) || teams[0] || null;
  }

  _selectTeam(entityId) {
    const team = this._teams().find(t => t.entidad_datos === entityId);
    if (!team) return;
    const key = this._storageKey();
    try { if (key) window.localStorage?.setItem(key, entityId); } catch (_) { /* almacenamiento deshabilitado */ }
    this._render();
  }

  _availableOfficialEntities() {
    return Object.entries(this._hass?.states || {})
      .filter(([id, state]) => id.startsWith("sensor.") && state && !["unknown", "unavailable"].includes(state.state) && (state.attributes?.fbm?.fuente === "FBM" || state.attributes?.fuente === "FBM"))
      .filter(([, state]) => {
        const data = state.attributes.fbm || state.attributes;
        return Array.isArray(data.partidos) && Array.isArray(data.clasificacion);
      })
      .map(([id, state]) => ({ nombre: String(state.attributes?.friendly_name || id), entidad_datos: id }));
  }

  _data() {
    const entityId = this._selectedTeam()?.entidad_datos;
    if (!entityId) return { error: "Pendiente de conectar una fuente de datos oficiales de FBM." };
    const state = this._hass?.states?.[entityId];
    if (!state) return { error: "La entidad de datos no está disponible: " + entityId };
    if (["unknown", "unavailable"].includes(state.state)) return { error: "La entidad de datos no está disponible." };
    const data = state.attributes?.fbm || state.attributes;
    if (!data || data.fuente !== "FBM") {
      return { error: "Datos rechazados: la entidad debe identificar a FBM como fuente oficial." };
    }
    if (!Array.isArray(data.partidos) || !Array.isArray(data.clasificacion)) {
      return { error: "La entidad no contiene partidos y clasificación en el formato esperado." };
    }
    return { data };
  }

  _element(tag, text, className) {
    const el = document.createElement(tag);
    el.textContent = String(text ?? "");
    if (className) el.className = className;
    return el;
  }

  _experimentalState() {
    return this._experimental ||= { entry: null, status: null, release: "16", query: "", teams: [],
      selected: "", rounds: null, round: "", phaseName: "", start: "", end: "", schedule: null, standings: null, players: null, playersTeamId: "", playersEntryId: "", playerDetail: null, playerDetailTeamId: "", playerDetailPlayerId: "", playerStats: null, playerStatsTeamId: "", playerStatsPlayerId: "", playerStatsEntryId: "", showGroup: false, tab: "clasificacion", partidosTab: "fases", scheduleTeamId: "", scheduleEntryId: "", matchRound: "all", matchStart: "", matchEnd: "", lastScheduleUpdate: 0, lastStandingsUpdate: 0, lastPlayersUpdate: 0, photoDiagnostic: null, message: "", busy: false };
  }

  _experimentalPreferenceKey(entryId) {
    const user = this._hass?.user?.id;
    if (typeof user !== "string" || !user || typeof entryId !== "string" || !entryId) return null;
    const cardId = this._config?.id_tarjeta;
    if (this._config?.tipo_tarjeta === "equipo" && (typeof cardId !== "string" || !cardId.trim())) return null;
    const key = [user, String(cardId || "predeterminada"), entryId];
    if (this._config?.tipo_tarjeta === "equipo" && this._config.equipo_fijo?.id)
      key.push(this._config.equipo_fijo.id);
    return "fbm-card:experimental-equipo:v1:" + JSON.stringify(key);
  }

  _experimentalTeamIsValid(team) {
    return !!team && ["id", "nombre", "club", "categoria", "temporada"].every(key =>
      typeof team[key] === "string" && team[key].trim() && team[key].length <= 512);
  }

  _saveExperimentalTeam(entryId, team) {
    const key = this._experimentalPreferenceKey(entryId);
    if (!key || !this._experimentalTeamIsValid(team)) return;
    const data = {};
    for (const field of ["id", "nombre", "club", "categoria", "temporada"]) data[field] = team[field];
    if (typeof team.escudo === "string" && team.escudo.length <= 1024) data.escudo = team.escudo;
    try { window.localStorage?.setItem(key, JSON.stringify(data)); } catch (_) { /* almacenamiento deshabilitado */ }
  }

  _clearExperimentalTeam(entryId) {
    const key = this._experimentalPreferenceKey(entryId);
    if (!key) return;
    try { window.localStorage?.removeItem(key); } catch (_) { /* almacenamiento deshabilitado */ }
  }

  _restoreExperimentalTeam(entryId) {
    const configured = this._config?.tipo_tarjeta === "equipo" ? this._config?.equipo_fijo : null;
    const fallback = this._experimentalTeamIsValid(configured) ? configured : null;
    const key = this._experimentalPreferenceKey(entryId);
    if (!key) return fallback;
    try {
      const team = JSON.parse(window.localStorage?.getItem(key) || "null");
      if (!this._experimentalTeamIsValid(team)) return fallback;
      const result = { id: team.id, nombre: team.nombre, club: team.club, categoria: team.categoria, temporada: team.temporada };
      if (typeof team.escudo === "string" && team.escudo.length <= 1024) result.escudo = team.escudo;
      return result;
    } catch (_) { return fallback; }
  }

  _experimentalFavoritesKey(entryId) {
    const user = this._hass?.user?.id;
    if (typeof user !== "string" || !user || typeof entryId !== "string" || !entryId) return null;
    return "fbm-card:experimental-favoritos:v1:" + JSON.stringify([user, entryId]);
  }

  _experimentalFavorites(entryId) {
    const key = this._experimentalFavoritesKey(entryId);
    if (!key) return [];
    try {
      const values = JSON.parse(window.localStorage?.getItem(key) || "[]");
      if (!Array.isArray(values)) return [];
      return values.filter(team => this._experimentalTeamIsValid(team)).slice(0, 30);
    } catch (_) { return []; }
  }

  _isExperimentalFavorite(entryId, teamId) {
    return this._experimentalFavorites(entryId).some(team => team.id === teamId);
  }

  _toggleExperimentalFavorite(entryId, team) {
    const key = this._experimentalFavoritesKey(entryId);
    if (!key || !this._experimentalTeamIsValid(team)) return false;
    const favorites = this._experimentalFavorites(entryId);
    const exists = favorites.some(saved => saved.id === team.id);
    const updated = exists ? favorites.filter(saved => saved.id !== team.id) : [
      ...favorites.filter(saved => saved.id !== team.id),
      Object.fromEntries(["id", "nombre", "club", "categoria", "temporada", "escudo"].filter(field => field !== "escudo" || (typeof team.escudo === "string" && team.escudo.length <= 1024)).map(field => [field, team[field]]))
    ];
    if (updated.length > 30) return false;
    try { window.localStorage?.setItem(key, JSON.stringify(updated)); return true; }
    catch (_) { return false; }
  }

  _recentTeamKey(entryId) {
    const user = this._hass?.user?.id;
    if (typeof user !== "string" || !user || !entryId) return null;
    return "fbm-card:ultimo-equipo:v1:" + JSON.stringify([user, entryId]);
  }

  _saveRecentTeam(entryId, team) {
    if (!this._experimentalTeamIsValid(team)) return;
    const key = this._recentTeamKey(entryId);
    if (!key) return;
    const data = {};
    for (const prop of ["id", "nombre", "club", "categoria", "temporada"]) data[prop] = team[prop];
    if (typeof team.escudo === "string" && team.escudo.length <= 1024) data.escudo = team.escudo;
    try { window.localStorage?.setItem(key, JSON.stringify(data)); } catch (_) {}
  }

  _restoreRecentTeam(entryId) {
    const key = this._recentTeamKey(entryId);
    if (!key) return null;
    try {
      const value = JSON.parse(window.localStorage?.getItem(key) || "null");
      return this._experimentalTeamIsValid(value) ? value : null;
    } catch (_) { return null; }
  }

  async _initializeSearch() {
    if (this._searchInit || !this._hass?.callWS ||
        this._config?.modo_experimental !== true ||
        this._config?.tipo_tarjeta === "equipo") return;
    this._searchInit = true;
    // Discover the existing FBM session without registering a new device.
    await this._experimentalAction("status");
  }

  async _loadArchivedFixed(selected = this._restoreExperimentalTeam(this._experimentalState().entry)) {
    const state = this._experimentalState();
    if (!state.entry || !selected?.id || !this._hass?.callWS) return false;
    const entryId = state.entry, teamId = selected.id;
    let data;
    try {
      data = await this._hass.callWS({
        type: "fbm/competition/team_snapshot", entry_id: entryId, equipo: teamId
      });
    } catch (_) { return false; }
    if (state.entry !== entryId || state.selected !== teamId ||
        data?.found !== true || !Array.isArray(data.standings?.clasificacion))
      return false;
    state.standings = data.standings.clasificacion;
    state.lastStandingsUpdate = Date.now();
    if (Array.isArray(data.fixtures?.partidos)) {
      state.schedule = data.fixtures;
      state.scheduleTeamId = teamId;
      state.scheduleEntryId = entryId;
      state.lastScheduleUpdate = Date.now();
      state.showGroup = true;
    }
    state.archivedData = true;
    state.lastArchiveCheck = Date.now();
    return true;
  }

  async _initializeFixed() {
    if (this._fixedInit || !this._hass?.callWS || this._config?.tipo_tarjeta !== "equipo") return;
    this._fixedInit = true;
    const state = this._experimentalState();
    if (state.busy) return;
    state.busy = true;
    try {
      const result = await this._hass.callWS({ type: "fbm/client/entries" });
      if (!Array.isArray(result.entries) || result.entries.length !== 1) throw new Error("Entrada FBM no disponible");
      state.entry = result.entries[0];
      state.status = await this._hass.callWS({ type: "fbm/client/status", entry_id: state.entry });
      const saved = this._restoreExperimentalTeam(state.entry);
      if (saved) {
        state.teams = [saved]; state.selected = saved.id;
        const archived = await this._loadArchivedFixed();
        if (!archived && state.status.sesion_vigente) {
          await this._loadStandings(state);
        }
      }
    } catch (_) {
      state.message = "No se pudo actualizar la clasificación. Comprueba la conexión.";
    } finally { state.busy = false; this._render(); }
  }

  _fixedCardYaml(team) {
    if (!this._experimentalTeamIsValid(team)) return "";
    const quote = value => JSON.stringify(value);
    return [
      "type: custom:fbm-card", "title: " + quote(team.nombre),
      "modo_experimental: true", "tipo_tarjeta: equipo",
      "id_tarjeta: " + quote("fbm-fijo-" + team.id + "-" + Math.random().toString(36).slice(2, 10)),
      "equipo_fijo:",
      ...["id", "nombre", "club", "categoria", "temporada"].map(field => "  " + field + ": " + quote(team[field]))
    ].join("\n");
  }

  _officialLogoUrl(value) {
    if (typeof value !== "string" || value.length > 1024) return "";
    try {
      const url = new URL(value);
      const host = url.hostname.toLowerCase();
      if (url.protocol !== "https:") return "";
      if (host === "fbm.es" || host.endsWith(".fbm.es") ||
          host === "appaficionfbm.gesdeportiva.es") return url.href;
    } catch (_) { /* no mostrar URLs no verificadas */ }
    return "";
  }

  _apkCrestUrl(value) {
    if (typeof value !== "string" || !value.trim() || value.length > 1024 || /[\x00-\x1f\x7f]/.test(value)) return "";
    try {
      return "https://appaficionfbm.gesdeportiva.es/imagenes.ashx?tipo=escudo&id=" + encodeURIComponent(value.trim());
    } catch (_) { return ""; }
  }

  _experimentalMatches() {
    const state = this._experimentalState();
    const matches = Array.isArray(state.schedule?.partidos) ? state.schedule.partidos : [];
    if (state.showGroup) return matches;
    const name = state.teams.find(team => team.id === state.selected)?.nombre;
    if (typeof name !== "string" || !name.trim()) return [];
    const target = name.trim().toLowerCase();
    return matches.filter(match => [match.local, match.visitante].some(value =>
      typeof value === "string" && value.trim().toLowerCase() === target));
  }

  _toggleExperimentalGroup() {
    const state = this._experimentalState();
    state.showGroup = !state.showGroup;
    this._render();
  }

  _roundDateLabel(matches) {
    const dates = [...new Set(matches.map(game => game?.fecha)
      .filter(value => typeof value === "string" && /^\d{2}\/\d{2}\/\d{4}$/.test(value)))];
    dates.sort((a, b) => fbmFixtureDateKey(a).localeCompare(fbmFixtureDateKey(b)));
    if (!dates.length) return "";
    if (dates.length === 1) return dates[0];
    return dates[0] + " – " + dates[dates.length - 1];
  }

  _fixedScheduleDates(state) {
    const today = new Date();
    const start = new Date(today);
    start.setDate(start.getDate() - 45);
    const end = new Date(today);
    end.setDate(end.getDate() + 75);
    const iso = date => [date.getFullYear(), String(date.getMonth() + 1).padStart(2, "0"),
      String(date.getDate()).padStart(2, "0")].join("-");
    return { desde: state.matchStart || iso(start), hasta: state.matchEnd || iso(end) };
  }

  _fixedMatchesAvailable(state, teamId) {
    return state.scheduleEntryId === state.entry && state.scheduleTeamId === teamId &&
      Array.isArray(state.schedule?.partidos);
  }

  async _experimentalPlayerDetail(playerId) {
    const state = this._experimentalState();
    if (state.busy || !state.entry || !state.selected || !this._hass?.callWS ||
        typeof playerId !== "string" || !playerId.trim()) return;
    const teamId = state.selected, entryId = state.entry;
    const roster = state.playersTeamId === teamId && state.playersEntryId === entryId
      ? state.players : null;
    if (!Array.isArray(roster) || !roster.some(player => player.id === playerId)) return;
    if (state.playerDetailTeamId === teamId && state.playerDetailPlayerId === playerId && state.playerDetail) {
      state.playerDetail = null; state.playerDetailTeamId = ""; state.playerDetailPlayerId = "";
      state.playerStats = null; state.playerStatsTeamId = ""; state.playerStatsPlayerId = ""; state.playerStatsEntryId = "";
      this._render();
      return;
    }
    state.busy = true; state.message = ""; state.playerDetail = null;
    state.playerDetailTeamId = ""; state.playerDetailPlayerId = "";
    state.playerStats = null; state.playerStatsTeamId = ""; state.playerStatsPlayerId = ""; state.playerStatsEntryId = "";
    this._render();
    try {
      const data = await this._hass.callWS({
        type: "fbm/player/detail", entry_id: entryId, jugador: playerId
      });
      if (!data?.jugador || data.jugador.id !== playerId) throw new Error("Ficha no válida");
      if (state.entry !== entryId || state.selected !== teamId) return;
      state.playerDetail = data.jugador;
      state.playerDetailTeamId = teamId;
      state.playerDetailPlayerId = playerId;
    } catch (_) {
      if (state.entry === entryId && state.selected === teamId)
        state.message = "No se pudo obtener la ficha de este jugador desde FBM.";
    } finally { state.busy = false; this._render(); }
  }

  async _experimentalPlayerStats(playerId) {
    const state = this._experimentalState();
    if (state.busy || !state.entry || !state.selected || !this._hass?.callWS ||
        typeof playerId !== "string" || !playerId.trim()) return;
    const entryId = state.entry, teamId = state.selected;
    const roster = state.playersTeamId === teamId && state.playersEntryId === entryId
      ? state.players : null;
    if (!Array.isArray(roster) || !roster.some(player => player.id === playerId)) return;
    state.busy = true; state.message = "";
    state.playerStats = null; state.playerStatsTeamId = ""; state.playerStatsPlayerId = ""; state.playerStatsEntryId = "";
    this._render();
    try {
      const data = await this._hass.callWS({
        type: "fbm/player/stats", entry_id: entryId, equipo: teamId, jugador: playerId
      });
      if (!data || data.jugador !== playerId || data.equipo !== teamId ||
          !Array.isArray(data.partidos?.partidos) || !data.globales?.estadisticas) {
        throw new Error("Estadísticas FBM no válidas");
      }
      if (state.entry !== entryId || state.selected !== teamId ||
          state.playersTeamId !== teamId || state.playersEntryId !== entryId) return;
      state.playerStats = data;
      state.playerStatsTeamId = teamId;
      state.playerStatsPlayerId = playerId;
      state.playerStatsEntryId = entryId;
    } catch (_) {
      if (state.entry === entryId && state.selected === teamId)
        state.message = "FBM no ha facilitado estadísticas avanzadas válidas para este jugador.";
    } finally { state.busy = false; this._render(); }
  }

  async _experimentalAction(action) {
    const state = this._experimentalState();
    if (state.busy || !this._hass?.callWS) return;
    state.busy = true; state.message = ""; this._render();
    let remoteAttempted = false;
    try {
      if (action === "status") {
        const data = await this._hass.callWS({ type: "fbm/client/entries" });
        if (!Array.isArray(data.entries) || data.entries.length !== 1) throw new Error("No hay una única integración FBM disponible.");
        if (state.entry && state.entry !== data.entries[0]) {
          state.teams = []; state.selected = ""; state.rounds = null; state.round = "";
          state.schedule = null; state.standings = null; state.showGroup = false;
        }
        state.entry = data.entries[0];
        state.status = await this._hass.callWS({ type: "fbm/client/status", entry_id: state.entry });
        if (!state.selected && !state.teams.length) {
          const saved = this._restoreExperimentalTeam(state.entry);
          if (saved) { state.teams = [saved]; state.selected = saved.id; }
        }
      } else {
        if (!state.entry) throw new Error("Comprueba primero el estado de la integración.");
        const common = { entry_id: state.entry };
        if (action === "create") {
          await this._hass.callWS({ type: "fbm/client/create_identity", ...common });
          state.status = await this._hass.callWS({ type: "fbm/client/status", ...common });
          state.message = "Identidad local creada.";
        } else if (action === "register" || action === "recover_registration" || action === "connect") {
          if (!state.release.trim()) throw new Error("Indica una versión para el perfil experimental.");
          if (action === "connect") { state.schedule = null; state.standings = null; state.rounds = null; state.round = ""; }
          remoteAttempted = true;
          await this._hass.callWS({ type: `fbm/client/${action}`, ...common, android_release: state.release.trim() });
          state.status = await this._hass.callWS({ type: "fbm/client/status", ...common });
          state.message = action === "connect" ? "Acceso solicitado; puedes probar la búsqueda." : "Candidato guardado; falta validar la conexión.";
        } else if (action === "search") {
          if (!state.query.trim()) throw new Error("Escribe el nombre de un equipo.");
          remoteAttempted = true;
          const data = await this._hass.callWS({ type: "fbm/team/search", ...common, texto: state.query.trim(), skip: 0 });
          state.teams = Array.isArray(data.equipos) ? data.equipos : [];
          state.selected = ""; this._resetTeamData(state);
          state.message = state.teams.length ? "Elige un equipo, categoría y temporada." : "No se han encontrado equipos.";
        } else if (action === "fix_team") {
          const selected = state.teams.find(team => team.id === state.selected);
          if (!selected) throw new Error("Elige un equipo.");
          this._saveExperimentalTeam(state.entry, selected);
          state.editFixed = false;
          state.message = "Equipo fijado en esta tarjeta.";
          this._resetTeamData(state);
          if (!await this._loadArchivedFixed() && state.status?.sesion_vigente) {
            remoteAttempted = true;
            await this._loadStandings(state);
          }
        } else if (action === "phases") {
          if (!state.selected) throw new Error("Elige un equipo.");
          remoteAttempted = true;
          const data = await this._hass.callWS({ type: "fbm/team/phases", ...common, equipo: state.selected });
          if (!Array.isArray(data.rondas)) throw new Error("Respuesta de fases no válida.");
          state.rounds = data.rondas; state.round = ""; state.phaseName = data.nombre_fase || ""; state.schedule = null;
          state.message = state.rounds.length ? "Elige una ronda." : "Fase sin rondas: se utilizará el grupo actual.";
        } else if (action === "schedule") {
          if (this._config.mostrar_horarios !== true) throw new Error("Horarios desactivados en esta versión.");
          if (!state.selected || !state.start || !state.end || !Array.isArray(state.rounds) || (state.rounds.length && !state.round)) throw new Error("Elige equipo, fase y fechas.");
          const request = { type: state.rounds.length ? "fbm/team/schedule_round" : "fbm/team/schedule", ...common,
            equipo: state.selected, desde: state.start, hasta: state.end };
          if (state.rounds.length) request.ronda = state.round;
          remoteAttempted = true;
          state.schedule = await this._hass.callWS(request);
        } else if (action === "fixed_schedule" || action === "refresh_schedule") {
          if (!state.selected || state.status?.sesion_vigente !== true) throw new Error("Equipo o sesión no disponible.");
          const range = this._fixedScheduleDates(state);
          const first = new Date(range.desde + "T12:00:00");
          const last = new Date(range.hasta + "T12:00:00");
          if (!Number.isFinite(first.getTime()) || !Number.isFinite(last.getTime()) ||
              first > last || (last.getTime() - first.getTime()) > 125 * 86400000)
            throw new Error("Selecciona un periodo válido de hasta 125 días.");
          const teamId = state.selected, entryId = state.entry;
          remoteAttempted = true;
          const data = await this._hass.callWS({
            type: "fbm/team/schedule", ...common, equipo: teamId,
            desde: range.desde, hasta: range.hasta
          });
          if (state.selected !== teamId || state.entry !== entryId) return;
          if (!data || !Array.isArray(data.partidos)) throw new Error("Calendario FBM no válido.");
          state.schedule = data; state.scheduleTeamId = teamId;
          state.scheduleEntryId = entryId;
          if (action !== "refresh_schedule") { state.matchRound = "all"; state.showGroup = true; }
          state.lastScheduleUpdate = Date.now();
        } else if (action === "players" || action === "refresh_players") {
          if (!state.selected) throw new Error("Elige un equipo.");
          if (action !== "refresh_players") { state.players = null; state.playersTeamId = ""; state.playersEntryId = ""; state.photoDiagnostic = null; }
          remoteAttempted = true;
          const selectedTeam = state.selected, selectedEntry = state.entry;
          const data = await this._hass.callWS({ type: "fbm/team/players", ...common, equipo: selectedTeam });
          // Reject responses arriving after a card changed team or entry.
          if (state.selected !== selectedTeam || state.entry !== selectedEntry) return;
          if (!data || !Array.isArray(data.jugadores)) throw new Error("Plantilla FBM no válida.");
          state.players = data.jugadores; state.playersTeamId = selectedTeam;
          state.playersEntryId = selectedEntry; state.lastPlayersUpdate = Date.now();
          if (action !== "refresh_players" || !data.jugadores.some(player => player.id === state.playerDetailPlayerId)) {
            state.playerDetail = null; state.playerDetailTeamId = ""; state.playerDetailPlayerId = "";
            state.playerStats = null; state.playerStatsTeamId = ""; state.playerStatsPlayerId = ""; state.playerStatsEntryId = "";
          }
          if (action !== "refresh_players")
            state.message = data.jugadores.length ? "Plantilla consultada desde FBM." : "FBM devolvió una plantilla vacía para este equipo.";
        } else if (action === "photo_diagnostic") {
          if (this._config?.tipo_tarjeta !== "equipo" || !state.selected ||
              state.status?.sesion_vigente !== true) throw new Error("Equipo o sesión no disponible.");
          const selectedTeam = state.selected, selectedEntry = state.entry;
          state.photoDiagnostic = null;
          remoteAttempted = true;
          const data = await this._hass.callWS({
            type: "fbm/team/diagnostic", ...common, equipo: selectedTeam,
            kind: "roster", desde: "", hasta: ""
          });
          if (state.selected !== selectedTeam || state.entry !== selectedEntry) return;
          // Never display raw responses or identifiers. Show only allowlisted
          // format metadata already sanitized by the backend diagnostic.
          const info = data?.shape?.player_photo_format || {};
          const allowed = {
            kind: ["null","other","empty","https_url","http_url","inline_data","relative_path","image_filename","opaque_reference"],
            length_band: ["0","1-64","65-256","257-1024","1025-16384","16385+"],
            text_form: ["json","xml","html","absolute_url","relative_url","hex","base64","other"],
            hex_decoded_kind: ["png","jpeg","webp","utf8_url","utf16le_url","json","utf16le_json","utf8_text","utf16le_text","binary_or_encoded","invalid"],
            base64_magic: ["png","jpeg","webp","gif","other","invalid"],
            decoded_text_form: ["xml","json","url","html","other"],
            utf16le_reference_form: ["absolute_url","embedded_url","inline_image","json_like","relative_path","base64_or_identifier","opaque_text","invalid"],
            utf16le_inner_magic: ["png","jpeg","webp","other","invalid_base64"]
          };
          const parts = Object.entries(allowed)
            .filter(([key, values]) => typeof info[key] === "string" && values.includes(info[key]))
            .map(([key]) => key + "=" + info[key]);
          if (info.official_fbm_host_present === true) parts.push("official_fbm_host_present=true");
          else if (info.official_fbm_host_present === false) parts.push("official_fbm_host_present=false");
          state.photoDiagnostic = data?.ok === true
            ? (parts.length ? parts.join(" · ") : "FBM no ha devuelto un formato de fotografía reconocible.")
            : "Diagnóstico no disponible: revisa la sesión y vuelve a consultar.";
        } else if (action === "standings") {
          if (!state.selected) throw new Error("Elige un equipo.");
          const team = state.teams.find(item => item.id === state.selected);
          if (this._config.tipo_tarjeta !== "equipo" && !state.standings && team &&
              await this._loadArchivedFixed(team)) return;
          remoteAttempted = true;
          await this._loadStandings(state);
        }
      }
    } catch (_) {
      if (remoteAttempted && ["register", "recover_registration", "connect", "search", "phases", "schedule", "fixed_schedule", "refresh_schedule", "standings", "players", "refresh_players"].includes(action) && state.entry) {
        try { state.status = await this._hass.callWS({ type: "fbm/client/status", entry_id: state.entry }); }
        catch (_) {
          state.status = { ...state.status, sesion_vigente: false };
          if (action === "register" || action === "recover_registration") state.status.registro_pendiente = true;
        }
      }
      state.message = action === "register" || action === "recover_registration"
        ? "No se pudo confirmar el registro. El servidor podría haberlo procesado; no se repetirá automáticamente."
        : "No se pudo completar la operación. Comprueba la integración, los datos y la conexión.";
    } finally { state.busy = false; this._render(); }
  }

  async _loadStandings(state) {
    const data = await this._hass.callWS({
      type: "fbm/team/standings", entry_id: state.entry, equipo: state.selected
    });
    if (!Array.isArray(data?.clasificacion)) throw new Error("Clasificación no válida.");
    state.standings = data.clasificacion;
    state.lastStandingsUpdate = Date.now();
  }

  _resetTeamData(state) {
    Object.assign(state, {
      archivedData: false, lastArchiveCheck: 0, schedule: null, standings: null,
      players: null, playerDetail: null, playerStats: null, photoDiagnostic: null,
      lastStandingsUpdate: 0, lastPlayersUpdate: 0, lastScheduleUpdate: 0,
      rounds: null, round: "", phaseName: "", matchRound: "all", showGroup: false,
      tab: "clasificacion", partidosTab: "fases", showTeamDetail: false
    });
  }

  _renderExperimental(card) {
    const state = this._experimentalState();
    card.append(this._element("h2", this._config.title || "🏀 FBM Card"));
    const button = (label, action, enabled = true) => {
      const el = this._element("button", label); el.type = "button"; el.disabled = state.busy || !enabled;
      el.addEventListener("click", () => this._experimentalAction(action)); card.append(el);
    };
    const input = (labelText, key, type = "text") => {
      const label = this._element("label", labelText + " ");
      const el = document.createElement("input"); el.type = type; el.value = state[key];
      el.addEventListener("input", event => { state[key] = event.target.value; });
      label.append(el); card.append(label);
    };
    // Session discovery is automatic; expose manual retry only when needed.
    if (!state.status || state.status.sesion_vigente !== true)
      button("Reintentar conexión", "status", !!this._hass?.callWS);
    if (state.status) {
      const connected = state.status.sesion_vigente === true;
      if (!connected && state.status.sesion_en_memoria)
        card.append(this._element("p", "La sesión de FBM necesita reconexión.", "muted"));
      if (state.status.registro_pendiente) card.append(this._element("p", "Hay un registro pendiente o incierto. No se reintentará hasta que se recupere de forma segura.", "muted"));
      if (!state.status.identidad_creada) button("Crear identidad local", "create", true);
      if (!connected && (state.status.candidato_guardado || state.status.identidad_creada)) input("Versión del perfil Android", "release");
      if (state.status.identidad_creada && !state.status.candidato_guardado && !state.status.registro_pendiente) button("Registrar dispositivo en FBM", "register");
      if (state.status.registro_pendiente) {
        card.append(this._element("p", "Recuperar envía una nueva solicitud de registro con la misma identidad.", "muted"));
        button("Recuperar registro pendiente", "recover_registration");
      }
      if (!connected) button("Conectar", "connect", state.status.candidato_guardado);
      const fixed = this._config.tipo_tarjeta === "equipo";
      const selected = state.teams.find(team => team.id === state.selected);
      const pinned = fixed ? this._restoreExperimentalTeam(state.entry) : selected;
      const editing = fixed && (!pinned || state.editFixed);
      const showDetails = fixed ? !!pinned && !editing : !!pinned && state.showTeamDetail;
      const favorites = this._experimentalFavorites(state.entry);
      if (fixed && editing && favorites.length) {
        const label = this._element("label", "Elegir entre mis favoritos:");
        const select = document.createElement("select");
        const empty = this._element("option", "Selecciona un favorito"); empty.value = ""; select.append(empty);
        for (const team of favorites) {
          const option = this._element("option", [team.nombre, team.categoria, team.temporada].join(" · "));
          option.value = team.id; select.append(option);
        }
        select.addEventListener("change", event => {
          const team = favorites.find(item => item.id === event.target.value);
          if (!team) return;
          state.teams = [team]; state.selected = team.id; this._resetTeamData(state);
          this._render();
        });
        label.append(select); card.append(label);
      }
      if (showDetails) {
        const header = this._element("div", "", "team-header");
        const configuredLogo = this._officialLogoUrl(this._config.logo_equipo);
        const standing = Array.isArray(state.standings) ? state.standings.find(item => item.id === pinned.id) : null;
        const logo = configuredLogo || this._apkCrestUrl(pinned.escudo || standing?.escudo);
        if (logo) {
          const img = document.createElement("img");
          img.src = logo; img.alt = "Escudo oficial de " + pinned.nombre;
          img.className = "team-logo"; img.loading = "lazy";
          img.addEventListener("error", () => img.replaceWith(this._element("span", "🏀", "team-logo-placeholder")), { once: true });
          header.append(img);
        } else header.append(this._element("span", "🏀", "team-logo-placeholder"));
        header.append(this._element("h3", pinned.nombre));
        card.append(header);
        card.append(this._element("p", [pinned.club, pinned.categoria, pinned.temporada].join(" · "), "muted"));
        const tabs = this._element("div", "", "fbm-tabs");
        for (const [name, title] of [["partidos", "Partidos"], ["clasificacion", "Clasificación"], ["jugadores", "Jugadores"]]) {
          const tab = this._element("button", title);
          tab.type = "button"; tab.className = "fbm-tab";
          tab.setAttribute("aria-pressed", String((state.tab || "clasificacion") === name));
          tab.addEventListener("click", () => {
            state.tab = name; this._render();
            if (!connected || !pinned?.id || state.busy) return;
            if (name === "clasificacion" && !Array.isArray(state.standings))
              void this._experimentalAction("standings");
            if (name === "partidos" && !this._fixedMatchesAvailable(state, pinned.id))
              void this._experimentalAction("fixed_schedule");
            if (name === "jugadores") {
              const cached = state.playersEntryId === state.entry &&
                state.playersTeamId === pinned.id && Array.isArray(state.players);
              const stale = !state.lastPlayersUpdate ||
                Date.now() - state.lastPlayersUpdate >= 15 * 60 * 1000;
              if (!cached || stale)
                void this._experimentalAction(cached ? "refresh_players" : "players");
            }
          });
          tabs.append(tab);
        }
        card.append(tabs);
        if (state.tab === "clasificacion" && !state.standings && state.busy)
          card.append(this._element("p", "Consultando clasificación…", "muted"));
        if (state.tab === "partidos") {
          const subtabs = this._element("div", "", "fbm-tabs");
          for (const [name, title] of [["fases", "Fases"], ["jornadas", "Jornadas"]]) {
            const sub = this._element("button", title);
            sub.type = "button"; sub.className = "fbm-tab";
            sub.setAttribute("aria-pressed", String((state.partidosTab || "fases") === name));
            sub.addEventListener("click", () => {
              state.partidosTab = name; this._render();
              if (connected && !this._fixedMatchesAvailable(state, pinned.id))
                this._experimentalAction("fixed_schedule");
            });
            subtabs.append(sub);
          }
          card.append(subtabs);
          const controls = this._element("div", "", "fbm-match-controls");
          const range = this._fixedScheduleDates(state);
          for (const [label, key, value] of [["Desde", "matchStart", range.desde], ["Hasta", "matchEnd", range.hasta]]) {
            const field = this._element("label", label);
            const picker = document.createElement("input"); picker.type = "date"; picker.value = value;
            picker.disabled = state.busy;
            picker.addEventListener("change", event => { state[key] = event.target.value; });
            field.append(picker); controls.append(field);
          }
          const load = this._element("button", "Actualizar partidos", "fbm-action fbm-action-primary");
          load.type = "button"; load.disabled = state.busy || !connected;
          load.addEventListener("click", () => this._experimentalAction("fixed_schedule"));
          controls.append(load); card.append(controls);
          const hasSchedule = this._fixedMatchesAvailable(state, pinned.id);
          if (!hasSchedule) {
            card.append(this._element("p", state.busy ? "Consultando los partidos oficiales..." :
              "Pulsa Actualizar partidos para consultar el calendario del grupo.", "fbm-player-caption"));
          } else {
            const all = state.schedule.partidos;
            const rounds = [...new Set(all.map(match => match.jornada)
              .filter(value => Number.isInteger(value)))].sort((a, b) => a - b);
            if (state.partidosTab === "fases") {
              const heading = this._element("h4", state.phaseName || "Fase y grupo actual", "fbm-subheading");
              card.append(heading);
              const phase = this._element("p", "Jornadas con partidos: " + rounds.length +
                " · Enfrentamientos oficiales: " + all.length, "fbm-player-caption");
              card.append(phase);
              if (Number.isInteger(state.schedule.jornada_actual))
                card.append(this._element("p", "Jornada actual: " + state.schedule.jornada_actual, "fbm-player-caption"));
              const jump = this._element("button", "Ver enfrentamientos por jornada", "fbm-action");
              jump.type = "button"; jump.addEventListener("click", () => {
                state.partidosTab = "jornadas"; this._render();
              }); card.append(jump);
            } else {
              const roundSelector = this._element("label", "Seleccionar jornada");
              const selector = document.createElement("select");
              const optAll = this._element("option", "Todas las jornadas"); optAll.value = "all";
              selector.append(optAll);
              for (const number of rounds) {
                const dateText = this._roundDateLabel(all.filter(game => game.jornada === number));
                const option = this._element("option", "Jornada " + number + (dateText ? " · " + dateText : ""));
                option.value = String(number); selector.append(option);
              }
              selector.value = rounds.some(n => String(n) === state.matchRound) ? state.matchRound : "all";
              selector.addEventListener("change", event => {
                state.matchRound = event.target.value; this._render();
              });
              roundSelector.append(selector); card.append(roundSelector);
              const roundMatches = state.matchRound === "all" ? all :
                all.filter(game => String(game.jornada) === state.matchRound);
              const toggle = this._element("button", state.showGroup ? "Ver solo mi equipo" : "Ver todo el grupo", "fbm-action");
              toggle.type = "button";
              toggle.setAttribute("aria-pressed", String(!state.showGroup));
              toggle.addEventListener("click", () => { state.showGroup = !state.showGroup; this._render(); });
              card.append(toggle);
              const teamName = pinned.nombre.trim().toLowerCase();
              const filtered = state.showGroup ? roundMatches : roundMatches.filter(game =>
                [game.local, game.visitante].some(value => typeof value === "string" &&
                  value.trim().toLowerCase() === teamName));
              card.append(this._element("p", filtered.length + (state.showGroup ?
                " enfrentamientos del grupo" : " partidos de tu equipo"), "fbm-section-subtitle"));
              if (!filtered.length) card.append(this._element("p", "FBM no devuelve partidos en esta jornada.", "fbm-player-caption"));
              renderFBMFixtures(this, card, filtered);
            }
          }
        }
        if (state.tab === "jugadores") {
          // Opening this tab refreshes stale/missing rosters automatically.
          // Keep an explicit retry only for failed or unavailable data.
          if (!Array.isArray(state.players) && !state.busy)
            button("Reintentar plantilla", "players", connected && !!pinned?.id);
          if (this._config.mostrar_diagnostico === true)
            button("Diagnosticar fotos", "photo_diagnostic", connected && !!pinned?.id);
          if (state.photoDiagnostic) card.append(this._element("p",
            "Formato de fotografía (sin datos personales): " + state.photoDiagnostic, "fbm-player-caption"));
          const roster = state.playersEntryId === state.entry && state.playersTeamId === pinned?.id
            ? state.players : null;
          if (!Array.isArray(roster)) {
            card.append(this._element("p", "Consulta la plantilla para ver nombres y estadísticas oficiales.", "muted"));
          } else if (!roster.length) {
            card.append(this._element("p", "FBM no ha devuelto jugadores para este equipo.", "muted"));
          } else {
            renderFBMRoster(this, card, roster, pinned, state,
              id => this._experimentalPlayerDetail(id), id => this._experimentalPlayerStats(id));
          }
        }
      } else {
        if (fixed && !pinned && connected) {
          const recent = this._restoreRecentTeam(state.entry);
          if (recent) {
            const use = this._element("button", "Fijar último equipo buscado: " + recent.nombre);
            use.type = "button"; use.disabled = state.busy;
            use.addEventListener("click", () => {
              state.teams = [recent]; state.selected = recent.id;
              this._experimentalAction("fix_team");
            });
            card.append(use);
          }
        }
        input("Buscar equipo", "query");
        button("Buscar", "search", connected);
      }
      if (!fixed && !showDetails && favorites.length) {
        const label = this._element("label", "Mis equipos favoritos:");
        const select = document.createElement("select");
        const empty = this._element("option", "Selecciona un favorito"); empty.value = ""; select.append(empty);
        for (const team of favorites) {
          const option = this._element("option", [team.nombre, team.categoria, team.temporada].join(" · "));
          option.value = team.id; select.append(option);
        }
        select.addEventListener("change", event => {
          const team = favorites.find(item => item.id === event.target.value);
          if (!team) return;
          state.teams = [team]; state.selected = team.id; this._resetTeamData(state);
          this._render();
        });
        label.append(select); card.append(label);
      }
      if (state.teams.length && !showDetails) {
        const label = this._element("label", "Equipo, categoría y temporada: ");
        const select = document.createElement("select");
        select.disabled = state.busy;
        const empty = this._element("option", "Selecciona un equipo"); empty.value = ""; select.append(empty);
        for (const team of state.teams) {
          const option = this._element("option", `${team.nombre} | ${team.club} | ${team.categoria} | ${team.temporada}`);
          option.value = team.id; select.append(option);
        }
        select.value = state.selected;
        select.addEventListener("change", event => {
          state.selected = event.target.value; this._resetTeamData(state);
          const selectedTeam = state.teams.find(team => team.id === state.selected);
          if (selectedTeam && this._config.tipo_tarjeta !== "equipo") this._saveExperimentalTeam(state.entry, selectedTeam);
          if (selectedTeam) this._saveRecentTeam(state.entry, selectedTeam);
          else if (!state.selected) this._clearExperimentalTeam(state.entry);
          this._render();
        });
        label.append(select); card.append(label);
        if (fixed) button("Fijar este equipo en la tarjeta", "fix_team", !!state.selected && connected);
        else {
          const consult = this._element("button", "Consultar equipo");
          consult.type = "button"; consult.disabled = state.busy || !state.selected || !connected;
          consult.addEventListener("click", () => {
            state.showTeamDetail = true;
            if (state.standings) this._render();
            else void this._experimentalAction("standings");
          });
          card.append(consult);
          const current = state.teams.find(team => team.id === state.selected);
          if (current) {
            const favorite = this._isExperimentalFavorite(state.entry, current.id);
            const toggle = this._element("button", favorite ? "★ Quitar de favoritos" : "☆ Añadir a favoritos");
            toggle.type = "button";
            toggle.disabled = state.busy;
            toggle.addEventListener("click", () => {
              const saved = this._toggleExperimentalFavorite(state.entry, current);
              state.message = saved ? "Favoritos actualizados. Puedes crear una tarjeta independiente para este equipo." : "No se pudieron guardar los favoritos en este navegador.";
              this._render();
            });
            card.append(toggle);
          }
          if (favorites.length) {
            const summary = this._element("p", "Mis favoritos: " + favorites.map(team => team.nombre + " (" + team.categoria + ")").join(", "), "muted");
            card.append(summary);
          }
          const copy = this._element("button", "Copiar tarjeta independiente de este equipo");
          copy.type = "button"; copy.disabled = state.busy || !state.selected;
          copy.addEventListener("click", async () => {
            const team = state.teams.find(t => t.id === state.selected);
            if (!team) return;
            try {
              await navigator.clipboard.writeText(this._fixedCardYaml(team));
              state.message = "Configuración copiada. Añade otra tarjeta manual y pega el YAML.";
            } catch (_) {
              state.message = "El navegador no permite copiar. Utiliza el editor de tarjetas de HA.";
            }
            this._render();
          });
          card.append(copy);
        }
        if (this._config.mostrar_horarios === true) button("Consultar fase y rondas", "phases", !!state.selected && connected);
        if (this._config.mostrar_horarios === true && Array.isArray(state.rounds)) {
          card.append(this._element("p", "Fase: " + state.phaseName, "muted"));
          if (state.rounds.length) {
            const roundLabel = this._element("label", "Ronda: ");
            const roundSelect = document.createElement("select");
            roundSelect.disabled = state.busy;
            const placeholder = this._element("option", "Selecciona una ronda"); placeholder.value = ""; roundSelect.append(placeholder);
            for (const round of state.rounds) {
              const option = this._element("option", round.nombre); option.value = round.id; roundSelect.append(option);
            }
            roundSelect.value = state.round;
            roundSelect.addEventListener("change", event => { state.round = event.target.value; state.schedule = null; this._render(); });
            roundLabel.append(roundSelect); card.append(roundLabel);
          }
        }
        if (this._config.mostrar_horarios === true) {
          input("Desde", "start", "date"); input("Hasta", "end", "date");
          button("Consultar horarios", "schedule", !!state.selected && connected && Array.isArray(state.rounds) && (!state.rounds.length || !!state.round));
        }
      }
      if (Array.isArray(state.standings) && showDetails && state.tab === "clasificacion") {
        card.append(this._element("h3", "Clasificación del grupo actual"));
        if (!state.standings.length) card.append(this._element("p", "No hay clasificación disponible.", "muted"));
        else {
          const scroll = this._element("div", "", "fbm-table-scroll");
          const table = document.createElement("table"); table.className = "standings";
          const head = document.createElement("tr");
          for (const [title, numeric] of [["Pos.", true], ["Equipo", false], ["PJ", true], ["G", true], ["P", true], ["Pts", true]]) {
            const cell = this._element("th", title, numeric ? "num" : "");
            cell.scope = "col"; head.append(cell);
          }
          const thead = document.createElement("thead"); thead.append(head); table.append(thead);
          const body = document.createElement("tbody");
          for (const team of state.standings) {
            const row = document.createElement("tr");
            if (pinned?.id && team.id === pinned.id) {
              row.className = "fbm-current-team";
              row.setAttribute("aria-label", "Tu equipo: " + (team.equipo || ""));
            }
            for (const [field, numeric] of [["posicion",true], ["equipo",false], ["jugados",true],
                                            ["ganados",true], ["perdidos",true], ["puntos",true]]) {
              const cell = this._element("td", team[field] ?? "—", numeric ? "num" : "");
              if (field === "equipo") cell.className = "fbm-standing-name";
              row.append(cell);
            }
            body.append(row);
          }
          table.append(body); scroll.append(table); card.append(scroll);
        }
      }
      if (this._config.mostrar_horarios === true && state.schedule && Array.isArray(state.schedule.partidos) && !showDetails && !fixed) {
        const visible = fixed ? state.schedule.partidos : this._experimentalMatches();
        card.append(this._element("h3", state.showGroup ? "Partidos del grupo" : "Partidos del equipo"));
        card.append(this._element("p", "La selección del equipo compara nombres; los homónimos pueden coincidir. FBM puede devolver fechas fuera del intervalo solicitado.", "muted"));
        const toggle = this._element("button", state.showGroup ? "Ver solo mi equipo" : "Ver todo el grupo");
        toggle.type = "button"; toggle.setAttribute("aria-pressed", String(state.showGroup));
        toggle.addEventListener("click", () => this._toggleExperimentalGroup()); card.append(toggle);
        card.append(this._element("p", `${visible.length} de ${state.schedule.partidos.length} partidos`, "muted"));
        if (!visible.length) card.append(this._element("p", "No hay partidos que coincidan con la selección.", "muted"));
        for (const match of visible) {
          const result = match.marcador ? `${match.marcador.local}–${match.marcador.visitante}` : (match.estado_oficial || "Resultado no disponible");
          const when = [match.fecha, match.hora].filter(Boolean).join(" ") || "Fecha pendiente";
          const row = this._element("div", "", "row");
          const details = this._element("div", `${match.local} – ${match.visitante}`, "teams");
          details.append(this._element("div", when, "muted"));
          row.append(details, this._element("span", result, "score"));
          card.append(row);
        }
      }
    }
    if (state.message) card.append(this._element("p", state.message, "muted"));
    const fixed = this._config.tipo_tarjeta === "equipo";
    const pinned = fixed && this._restoreExperimentalTeam(state.entry);
    if ((pinned && !state.editFixed && this._config.id_tarjeta) || (!fixed && state.showTeamDetail)) {
      const back = this._element("button", fixed ? "Cambiar equipo" : "Volver a la búsqueda", "fbm-action");
      back.type = "button"; back.disabled = state.busy;
      back.addEventListener("click", () => {
        if (fixed) {
          state.editFixed = true; state.teams = [pinned]; state.selected = pinned.id;
        } else state.showTeamDetail = false;
        this._render();
      });
      card.append(back);
    }
  }

  _render() {
    if (!this._config) return;
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });
    const style = document.createElement("style");
    style.textContent = `
      ha-card{padding:16px;line-height:1.5}
      h2{font-size:1.15rem;margin:0 0 4px}
      h3{font-size:1rem;margin:16px 0 8px}
      .muted{opacity:.7;font-size:.87rem}
      .row{display:flex;justify-content:space-between;gap:12px;padding:9px 0;border-bottom:1px solid var(--divider-color,#ddd)}
      .row:last-child{border-bottom:0}
      .teams{min-width:0;overflow-wrap:anywhere}
      .score{white-space:nowrap;font-weight:700}
      .standings{width:100%;border-collapse:collapse;font-size:.9rem}
      ha-card>button{display:block;margin:12px 0;padding:10px 16px;border:1px solid var(--divider-color,#ddd);border-radius:10px;background:var(--primary-color,#1976d2);color:var(--text-primary-color,#fff);cursor:pointer;font:inherit;font-weight:600}
      ha-card>button:disabled{opacity:.48;cursor:not-allowed}
      ha-card>label{display:flex;flex-direction:column;gap:6px;margin:14px 0;font-size:.9rem;font-weight:600}
      ha-card>label input,ha-card>label select{width:100%;min-width:0;box-sizing:border-box;min-height:42px;padding:8px 10px;border:1px solid var(--divider-color,#bbb);border-radius:9px;background:var(--card-background-color,#fff);color:var(--primary-text-color,#222);font:inherit}
      ha-card>p.muted{margin:8px 0 14px}
      .standings{display:block;overflow-x:auto}
      .standings th,.standings td{text-align:left;padding:9px 8px;border-bottom:1px solid var(--divider-color,#ddd)}
      .standings tbody tr:nth-child(even){background:var(--secondary-background-color,transparent)}
      .standings td.num,.standings th.num{text-align:right}
      .team-header{display:flex;align-items:center;gap:12px;margin:8px 0}
      .team-header h3{margin:0}
      .team-logo,.team-logo-placeholder{width:52px;height:52px;flex-shrink:0;object-fit:contain;border-radius:12px;background:var(--secondary-background-color,#eee)}
      .team-logo-placeholder{display:flex;align-items:center;justify-content:center;font-size:1.65rem}
      .fbm-tabs{display:flex;gap:4px;overflow-x:auto;margin:12px 0;max-width:100%}
      ha-card .fbm-tab{flex:1 0 auto;padding:8px 10px;border:0;border-radius:9px;background:var(--secondary-background-color,#eee);color:var(--primary-text-color,#222);cursor:pointer;font:inherit}
      ha-card .fbm-tab[aria-pressed="true"]{background:var(--primary-color,#1976d2);color:var(--text-primary-color,#fff);font-weight:700}
      :host{display:block;min-width:0}
      ha-card{box-sizing:border-box;min-width:0}
      ha-card button{font:inherit}
      .fbm-section-subtitle{margin:8px 0 12px;color:var(--secondary-text-color,#6b7280);font-size:.85rem;font-weight:600}
      .fbm-table-scroll{width:100%;max-width:100%;overflow-x:auto;border:1px solid var(--divider-color,#ddd);border-radius:12px;margin:10px 0}
      .fbm-table-scroll .standings{display:table;width:100%;min-width:340px;margin:0}
      .fbm-table-scroll .standings th{font-size:.74rem;text-transform:uppercase;letter-spacing:.025em;color:var(--secondary-text-color,#666);background:var(--secondary-background-color,#f6f6f6)}
      .fbm-table-scroll .standings td{font-variant-numeric:tabular-nums;font-size:.82rem}
      .fbm-table-scroll .standings td:first-child{font-weight:700;color:var(--primary-color,#1976d2)}
      .fbm-standing-name{font-weight:600;line-height:1.35;min-width:145px;overflow-wrap:anywhere}
      .fbm-table-scroll .fbm-current-team{background:color-mix(in srgb,var(--primary-color,#1976d2) 11%,var(--card-background-color,#fff));box-shadow:inset 3px 0 var(--primary-color,#1976d2)}
      ${FBM_TEAM_CONTENT_STYLES}
      .fbm-match-controls{display:flex;flex-wrap:wrap;align-items:end;gap:8px;margin:10px 0}
      .fbm-match-controls label{display:flex;flex:1 1 125px;flex-direction:column;gap:4px;font-size:.75rem;color:var(--secondary-text-color,#666)}
      .fbm-match-controls input{width:100%;box-sizing:border-box;min-height:36px;border:1px solid var(--divider-color,#ddd);border-radius:8px;padding:5px;background:var(--card-background-color,#fff);color:var(--primary-text-color,#222)}
      .fbm-match-controls button{align-self:end}

    `;
    const card = document.createElement("ha-card");
    if (this._config.modo_experimental === true) {
      this._renderExperimental(card);
      this.shadowRoot.replaceChildren(style, card);
      return;
    }
    const title = this._element("h2", this._config.title || "🏀 FBM Card");
    const selected = this._selectedTeam();
    const team = this._element("div", selected?.nombre || this._config.equipo || "Sin equipo seleccionado", "muted");
    card.append(title, team);
    if (selected && this._favoriteKey()) {
      const favorite = document.createElement("button");
      const active = this._favorites().includes(selected.entidad_datos);
      favorite.textContent = active ? "★ Quitar de favoritos" : "☆ Añadir a favoritos";
      favorite.type = "button";
      favorite.setAttribute("aria-pressed", String(active));
      favorite.addEventListener("click", () => this._toggleFavorite(selected.entidad_datos));
      card.append(favorite);
    }
    const teams = this._teams();
    if (!teams.length && this._config?.descubrir_entidades !== true) {
      const official = this._availableOfficialEntities();
      if (official.length) {
        const notice = this._element("p", "Hay entidades FBM disponibles en Home Assistant. Añádelas a la configuración de la tarjeta para seguir tus equipos.", "muted");
        card.append(notice);
        for (const entry of official.slice(0, 10)) card.append(this._element("div", entry.nombre + " (" + entry.entidad_datos + ")", "muted"));
      }
    }
    if (teams.length > 1 || (this._config?.descubrir_entidades === true && teams.length === 1)) {
      const label = this._element("label", "Seleccionar equipo: ", "muted");
      const select = document.createElement("select");
      select.setAttribute("aria-label", "Seleccionar equipo");
      const favorites = this._favorites();
      for (const entry of [...teams].sort((a, b) => Number(favorites.includes(b.entidad_datos)) - Number(favorites.includes(a.entidad_datos)))) {
        const option = document.createElement("option");
        option.value = entry.entidad_datos;
        option.textContent = (favorites.includes(entry.entidad_datos) ? "★ " : "") + entry.nombre;
        select.append(option);
      }
      select.value = selected?.entidad_datos || "";
      select.addEventListener("change", () => this._selectTeam(select.value));
      label.append(select);
      card.append(label);
    }
    if (this._config.url_oficial) {
      try {
        const url = new URL(String(this._config.url_oficial));
        if (url.protocol === "https:" && (url.hostname === "fbm.es" || url.hostname.endsWith(".fbm.es"))) {
          const link = document.createElement("a");
          link.href = url.href;
          link.target = "_blank";
          link.rel = "noopener noreferrer";
          link.textContent = "Consultar ficha oficial en FBM";
          card.append(link);
        }
      } catch (_) { /* URL no válida: no mostrar enlace */ }
    }
    const result = this._data();
    if (result.error) {
      card.append(this._element("p", result.error, "muted"));
    } else {
      const matches = result.data.partidos.slice(0, 12);
      card.append(this._element("h3", "Partidos"));
      if (!matches.length) card.append(this._element("p", "No hay partidos disponibles.", "muted"));
      for (const match of matches) {
        const row = this._element("div", "", "row");
        const teams = this._element("div", [match.local, match.visitante].filter(Boolean).join(" – "), "teams");
        const score = this._element("span", match.resultado || match.fecha || "Pendiente", "score");
        row.append(teams, score);
        card.append(row);
      }
      card.append(this._element("h3", "Clasificación"));
      const table = document.createElement("table");
      table.className = "standings";
      const thead = document.createElement("thead");
      const head = document.createElement("tr");
      for (const col of ["Pos.", "Equipo", "PJ", "Pts"]) {
        const th = this._element("th", col);
        if (col !== "Equipo") th.className = "num";
        head.append(th);
      }
      thead.append(head);
      table.append(thead);
      const tbody = document.createElement("tbody");
      for (const item of result.data.clasificacion.slice(0, 30)) {
        const tr = document.createElement("tr");
        for (const [key, numeric] of [["posicion",true],["equipo",false],["jugados",true],["puntos",true]]) {
          const td = this._element("td", item[key] ?? "—");
          if (numeric) td.className = "num";
          tr.append(td);
        }
        tbody.append(tr);
      }
      table.append(tbody);
      const scroll=this._el("div",undefined,"fbm-table-scroll");scroll.append(table);card.append(scroll);
      if (result.data.actualizado) card.append(this._element("p", "Actualizado: " + result.data.actualizado, "muted"));
    }
    this.shadowRoot.replaceChildren(style, card);
  }
}
// Independent league card: the HA sensor is the read-only source for group results.
// Individual player rosters are fetched only on explicit team selection, from
// an admin-only local SQLite archive endpoint, never from the remote FBM API.
class FBMCompetitionCard extends HTMLElement {
  static getConfigElement() { return document.createElement("fbm-competition-card-editor"); }

  setConfig(config) {
    if (!config || typeof config !== "object") throw new Error("Configuración inválida");
    this._config = { title: "Competición FBM", entity: "sensor.competiciones",
      group_index: 0, ...config };
    if (typeof this._config.entity !== "string" ||
        !this._config.entity.startsWith("sensor."))
      throw new Error("Selecciona un sensor de competiciones FBM");
    if (!Number.isInteger(this._config.group_index) ||
        this._config.group_index < 0 || this._config.group_index > 49)
      throw new Error("Índice de competición inválido");
    this._groupIndex = this._config.group_index;
    this._selectedGroup = null;
    this._pickerFocused = this._pickerRefreshPending = false;
    this._teamRequest = this._playerRequest = null;
    this._teamId = null; this._roster = null; this._matches = null;
    this._matchView = "jornadas"; this._matchRound = "all";
    this._playerId = null; this._playerStats = null; this._playerError = "";
    this._error = "";
    this._render();
  }
  set hass(hass) {
    const entity = this._config?.entity;
    const before = this._hass?.states?.[entity]?.attributes?.groups;
    this._hass = hass;
    const after = hass?.states?.[entity]?.attributes?.groups;
    if (before === after || JSON.stringify(before) === JSON.stringify(after)) return;
    if (this._pickerFocused) this._pickerRefreshPending = true;
    else this._render();
  }
  getCardSize() { return 5; }
  static getStubConfig() {
    return { type: "custom:fbm-competition-card", entity: "sensor.competiciones" };
  }
  _el(tag, value, className) {
    const el = document.createElement(tag);
    if (value !== undefined) el.textContent = String(value);
    if (className) el.className = className;
    return el;
  }
  _element(tag, value, className) { return this._el(tag, value, className); }
  _officialLogoUrl(value) { return this._verifiedCrest(value); }
  _apkCrestUrl(value) {
    return this._verifiedCrest(value) || FBMCard.prototype._apkCrestUrl(value);
  }

  _crestForTeam(team) {
    return this._fixtureCrests && Object.hasOwn(this._fixtureCrests, team.equipo)
      ? this._fixtureCrests[team.equipo] : this._verifiedCrest(team.escudo);
  }

  _verifiedCrest(value) {
    if (typeof value !== "string" || value.length > 4096) return "";
    try {
      const url=new URL(value);
      if (url.protocol !== "https:" || url.username || url.password ||
          url.port || url.hash) return "";
      const host=url.hostname.toLowerCase();
      if (host==="appaficionfbm.gesdeportiva.es") {
        if (url.pathname.toLowerCase()!=="/imagenes.ashx") return "";
        const params=url.searchParams;
        const id=params.get("id");
        if (params.size!==2 || params.get("tipo")!=="escudo" ||
            !FBMCard.prototype._apkCrestUrl(id)) return "";
        return url.href;
      }
      if ((host==="fbm.es" || host==="www.fbm.es") &&
          !url.search && /\.(?:png|jpe?g|webp)$/i.test(url.pathname)) return url.href;
    } catch (_) {}
    return "";
  }
  _group() {
    const sensor = this._hass?.states?.[this._config?.entity];
    const groups = Array.isArray(sensor?.attributes?.groups) ? sensor.attributes.groups : [];
    const selected = groups.findIndex(group => this._groupKey(group) === this._selectedGroup);
    const index = selected >= 0 ? selected : (groups[this._groupIndex] ? this._groupIndex : 0);
    return { groups, index, group: groups[index] || null };
  }

  _groupKey(group) {
    return JSON.stringify([group.season_id, group.phase_id, group.group_id]);
  }

  _groupLabel(group) {
    return group.competition_name || group.team_name || group.group_name || "Competición FBM";
  }
  _teamButton(team) {
    const button = this._el("button", undefined, "team");
    button.type = "button";
    const crest = this._verifiedCrest(team.escudo);
    if (crest) {
      const img = this._el("img");
      img.src = crest; img.alt = ""; img.className = "crest"; img.loading = "lazy";
      img.addEventListener("error", () => img.remove(), { once: true });
      button.append(img);
    }
    button.append(this._el("span", team.equipo));
    button.disabled = !team.id;
    button.addEventListener("click", () => { void this._openTeam(team); });
    return button;
  }

  _rankingTable(ranking) {
    const table = this._el("table"), head = this._el("tr");
    for (const [name, numeric] of [["Pos.", true], ["Equipo", false], ["PJ", true], ["G", true], ["P", true], ["Pts", true]]) {
      const th = this._el("th", name, numeric ? "num" : "");
      th.scope = "col"; head.append(th);
    }
    const thead = this._el("thead"), tbody = this._el("tbody");
    thead.append(head); table.append(thead, tbody);
    for (const team of ranking) {
      const row = this._el("tr"), name = this._el("td");
      name.append(this._teamButton(team));
      row.append(this._el("td", team.posicion ?? "", "num"), name,
        this._el("td", team.jugados ?? "", "num"), this._el("td", team.ganados ?? "", "num"),
        this._el("td", team.perdidos ?? "", "num"), this._el("td", team.puntos ?? "", "num"));
      tbody.append(row);
    }
    return table;
  }

  async _openTeam(team) {
    if (!team || typeof team.id !== "string" || !team.id ||
        typeof team.equipo !== "string") return;
    if (this._teamId === team.id) return;
    this._playerRequest = null;
    this._photoRequest = null;
    this._fixtureCrests = null;
    this._detailTab = "partidos";
    this._teamId = team.id; this._roster = null; this._matches = null;
    this._matchView = "jornadas"; this._matchRound = "all";
    this._playerId = null; this._playerStats = null; this._playerError = "";
    this._error = "";
    this._render();
    const { group } = this._group();
    if (!group || !this._hass?.callWS) return;
    const teamId = team.id;
    const request = this._teamRequest = {};
    try {
      const entries = await this._hass.callWS({type:"fbm/client/entries"});
      if (!Array.isArray(entries?.entries) || entries.entries.length !== 1)
        throw new Error("No se ha encontrado una integración FBM única");
      const data = await this._hass.callWS({
        type:"fbm/competition/team_roster", entry_id:entries.entries[0],
        season_id:group.season_id, phase_id:group.phase_id,
        group_id:group.group_id, equipo:teamId
      });
      if (this._teamRequest !== request) return;
      if (!Array.isArray(data?.jugadores)) throw new Error("Plantilla no disponible");
      this._entryId = entries.entries[0];
      this._roster = data.jugadores;
      this._matches = Array.isArray(data.partidos) ? data.partidos : [];
      this._fixtureCrests = data.escudos;
      if (this._detailTab === "jugadores") void this._loadPlayerPhotos();
      void this._loadFixtureCrests(request, group);
    } catch (_) {
      if (this._teamRequest === request)
        this._error = "No se ha podido leer la plantilla archivada; no se hará una descarga adicional.";
    }
    this._render();
  }
  async _loadFixtureCrests(request, group) {
    const ranking = Array.isArray(group.ranking) ? group.ranking : [];
    const known = new Map(ranking.map(team => [team.equipo, this._verifiedCrest(team.escudo)]));
    const names = new Set(this._matches.flatMap(match => [match.local, match.visitante]).filter(Boolean));
    if (![...names].some(name => !known.get(name) && !Object.hasOwn(this._fixtureCrests || {}, name))) return;
    const dates = this._matches.map(match => fbmFixtureDateKey(match.fecha))
      .filter(date => /^\d{4}-\d{2}-\d{2}$/.test(date)).sort();
    if (!dates.length) return;
    const desde = dates[0];
    const last = Date.parse(dates[dates.length - 1]);
    const limit = Date.parse(desde) + 125 * 86400000;
    if (!Number.isFinite(last) || !Number.isFinite(limit)) return;
    const hasta = new Date(Math.min(last, limit)).toISOString().slice(0, 10);
    try {
      const data = await this._hass.callWS({
        type: "fbm/team/schedule", entry_id: this._entryId, equipo: this._teamId, desde, hasta
      });
      if (this._teamRequest !== request || !Array.isArray(data?.partidos)) return;
      const crests = Object.assign(Object.create(null), this._fixtureCrests);
      for (const match of data.partidos) {
        for (const side of ["local", "visitante"]) {
          const officialName = match[side];
          const name = typeof officialName === "string" && [...names].find(candidate =>
            candidate.trim().toUpperCase() === officialName.trim().toUpperCase());
          if (!name || Object.hasOwn(crests, name)) continue;
          const image = match["img_" + side] || this._apkCrestUrl(match["escudo_" + side]);
          if (image) crests[name] = image;
        }
      }
      this._fixtureCrests = crests;
      this._render();
    } catch (_) { /* Archived matches remain available when FBM is offline. */ }
  }

  async _loadPlayerPhotos() {
    if (!this._roster || !this._entryId || !this._teamId || this._photoRequest) return;
    const request = this._photoRequest = this._teamRequest;
    try {
      const data = await this._hass.callWS({
        type: "fbm/team/players", entry_id: this._entryId, equipo: this._teamId
      });
      if (this._teamRequest !== request || !Array.isArray(data?.jugadores)) return;
      const live = new Map(data.jugadores.map(player => [player.id, player]));
      this._roster = this._roster.length ? this._roster.map(player => {
        const photo = live.get(player.id)?.foto;
        return photo ? { ...player, foto: photo } : player;
      }) : data.jugadores;
      this._render();
    } catch (_) {
      if (this._teamRequest === request) this._photoRequest = null;
    }
  }

  async _openPlayer(player) {
    if (!player || typeof player.id !== "string" || !player.id ||
        !Array.isArray(this._roster) || !this._roster.some(p => p.id === player.id))
      return;
    const {group} = this._group();
    if (!group || !this._teamId || !this._hass?.callWS) return;
    const teamId = this._teamId, playerId = player.id;
    const request = this._playerRequest = {};
    this._playerId = playerId; this._playerStats = null; this._playerError = "";
    this._render();
    try {
      if (!this._entryId) throw Error("Missing integration");
      const data = await this._hass.callWS({
        type:"fbm/competition/team_player_stats", entry_id:this._entryId,
        season_id:group.season_id, phase_id:group.phase_id,
        group_id:group.group_id, equipo:teamId, jugador:playerId
      });
      if (this._playerRequest !== request || this._teamId !== teamId ||
          this._playerId !== playerId) return;
      this._playerStats = data?.estadisticas || {};
    } catch (_) {
      if (this._playerRequest === request && this._teamId === teamId &&
          this._playerId === playerId)
        this._playerError = "No se pudieron leer las estadísticas archivadas.";
    }
    this._render();
  }
  _render() {
    if (this._pickerFocused) {
      this._pickerRefreshPending = true;
      return;
    }
    if (!this._config || typeof document === "undefined") return;
    if (!this.shadowRoot) this.attachShadow({mode:"open"});
    const style = this._el("style");
    style.textContent = `
      :host{display:block;min-width:0}
      ha-card{padding:16px;line-height:1.5;box-sizing:border-box;min-width:0;overflow:hidden}
      h2{font-size:1.15rem;margin:0 0 4px;font-weight:700}
      h3{font-size:1rem;margin:16px 0 8px}
      h4{font-size:.9rem;margin:12px 0 6px}
      .muted{color:var(--secondary-text-color,#777);font-size:.87rem;margin:8px 0 12px}
      .back{display:inline-flex;align-items:center;margin:12px 0;padding:8px 12px;border:1px solid var(--divider-color,#ddd);border-radius:9px;background:var(--secondary-background-color,#eee);color:var(--primary-text-color,#222);font-weight:600}
      button{font:inherit;cursor:pointer;border:0;background:transparent;color:var(--primary-text-color,#222);text-align:left}
      button:focus-visible,select:focus-visible{outline:2px solid var(--primary-color,#1976d2);outline-offset:2px}
      button:disabled{opacity:.55;cursor:default}
      table{width:100%;border-collapse:collapse;font-size:.82rem;min-width:340px}
      th,td{padding:9px 8px;border-bottom:1px solid var(--divider-color,#ddd);text-align:left}
      th{font-size:.74rem;text-transform:uppercase;letter-spacing:.025em;color:var(--secondary-text-color,#666);background:var(--secondary-background-color,#f6f6f6)}
      th.num,td.num{text-align:right;font-variant-numeric:tabular-nums}
      tbody tr:nth-child(even){background:var(--secondary-background-color,transparent)}
      td:first-child{font-weight:700;color:var(--primary-color,#1976d2)}
      .fbm-table-scroll{width:100%;max-width:100%;overflow-x:auto;border:1px solid var(--divider-color,#ddd);border-radius:12px;margin:10px 0}
      .team{display:inline-flex;align-items:center;gap:8px;min-width:0;font-weight:600;line-height:1.35;overflow-wrap:anywhere}
      .team:hover{color:var(--primary-color,#1976d2)}
      .crest{width:30px;height:30px;flex:0 0 30px;object-fit:contain;border-radius:8px}
      .team-header{display:flex;align-items:center;gap:12px;margin:10px 0}
      .team-header h3{margin:0}
      .team-logo,.team-logo-placeholder{width:52px;height:52px;flex:0 0 52px;object-fit:contain;border-radius:12px;background:var(--secondary-background-color,#eee)}
      .team-logo-placeholder{display:flex;align-items:center;justify-content:center;font-size:1.65rem}
      .fixture-group{margin-top:12px}
      .tabs{display:flex;gap:4px;overflow-x:auto;margin:12px 0;max-width:100%}
      .tabs button{flex:1 0 auto;padding:8px 10px;border:0;border-radius:9px;background:var(--secondary-background-color,#eee);color:var(--primary-text-color,#222)}
      .tabs button[aria-pressed="true"]{background:var(--primary-color,#1976d2);color:var(--text-primary-color,#fff);font-weight:700}
      ${FBM_TEAM_CONTENT_STYLES}
      select{width:100%;min-width:0;box-sizing:border-box;min-height:42px;padding:8px 10px;margin:10px 0 12px;border:1px solid var(--divider-color,#bbb);border-radius:9px;background:var(--card-background-color,#fff);color:var(--primary-text-color,#222);font:inherit}
    `;
    const card = this._el("ha-card");
    card.append(this._el("h2", this._config.title));
    const {groups,group,index} = this._group();
    if (!group) {
      card.append(this._el("p", "No hay competiciones archivadas disponibles.", "muted"));
      this.shadowRoot.replaceChildren(style,card);
      return;
    }
    if (groups.length > 1) {
      const select = this._el("select");
      select.setAttribute("aria-label", "Cambiar competición");
      select.addEventListener("focus", () => { this._pickerFocused = true; });
      select.addEventListener("blur", () => {
        this._pickerFocused = false;
        if (this._pickerRefreshPending) {
          this._pickerRefreshPending = false;
          this._render();
        }
      });
      for (let i=0;i<groups.length;i++) {
        const option = this._el("option", [...new Set([this._groupLabel(groups[i]), groups[i].group_name, groups[i].season_id].filter(Boolean))].join(" · "));
        option.value = String(i); select.append(option);
      }
      select.value = String(index);
      select.addEventListener("change", event => {
        this._pickerFocused = this._pickerRefreshPending = false;
        this._groupIndex = Number(event.target.value);
        this._selectedGroup = this._groupKey(groups[this._groupIndex]);
        this._teamRequest = this._playerRequest = null;
        this._teamId = null; this._roster = null; this._matches = null;
        this._playerId = null; this._playerStats = null; this._error = "";
        this._render();
      });
      card.append(select);
    }
    card.append(this._el("h3", this._groupLabel(group)));
    const ranking = Array.isArray(group.ranking) ? group.ranking : [];
    const team = ranking.find(item => item.id === this._teamId);
    if (this._teamId && team) {
      const back = this._el("button", "‹ Volver a la competición", "back");
      back.addEventListener("click", () => {
        this._teamRequest = this._playerRequest = null;
        this._teamId = null; this._roster = null; this._error = "";
        this._render();
      });
      const header=this._el("div",undefined,"team-header");
      const crest=this._crestForTeam(team);
      if (crest) {
        const img=this._el("img");img.src=crest;img.alt="Escudo de "+team.equipo;
        img.className="team-logo";img.loading="lazy";
        img.addEventListener("error",()=>img.replaceWith(this._el("span","🏀","team-logo-placeholder")),{once:true});
        header.append(img);
      } else header.append(this._el("span","🏀","team-logo-placeholder"));
      header.append(this._el("h3",team.equipo));
      card.append(back,header);
      const tabs = this._el("div", undefined, "tabs");
      for (const [name, label] of [["partidos", "Partidos"], ["clasificacion", "Clasificación"], ["jugadores", "Jugadores"]]) {
        const button = this._el("button", label);
        button.type = "button";
        button.setAttribute("aria-pressed", String(this._detailTab === name));
        button.addEventListener("click", () => {
          this._detailTab = name; this._render();
          if (name === "jugadores") void this._loadPlayerPhotos();
        });
        tabs.append(button);
      }
      card.append(tabs);
      if (this._detailTab === "clasificacion") {
        card.append(this._rankingTable(ranking));
      } else if (this._detailTab === "partidos") {
        if (!this._matches) card.append(this._el("p", this._error || "Consultando el calendario archivado…", "muted"));
        else if (!this._matches.length) card.append(this._el("p", "No hay partidos archivados identificados para este equipo.", "muted"));
        else {
          const rounds = [...new Set(this._matches.map(m => m.jornada)
            .filter(v => (typeof v === "number" && Number.isInteger(v)) ||
                         (typeof v === "string" && v.trim())))].map(String);
          rounds.sort((x,y) => x.localeCompare(y,"es",{numeric:true}));
          if (rounds.length) {
            const tabs=this._el("div",undefined,"tabs");
            for (const [view,label] of [["jornadas","Jornadas"],["fases","Fase completa"]]) {
              const btn=this._el("button",label);
              btn.setAttribute("aria-pressed",String(this._matchView===view));
              btn.addEventListener("click",()=>{this._matchView=view;this._render();});
              tabs.append(btn);
            }
            card.append(tabs);
          }
          if (this._matchView === "jornadas" && rounds.length) {
            const select=this._el("select");
            const all=this._el("option","Todas las jornadas");all.value="all";select.append(all);
            for (const round of rounds) {
              const option=this._el("option","Jornada "+round);
              option.value=round;select.append(option);
            }
            select.value=this._matchRound;
            select.addEventListener("change",event=>{
              this._matchRound=event.target.value;this._render();
            });
            card.append(select);
          }
          const matches=this._matchView==="jornadas" && this._matchRound!=="all"
            ? this._matches.filter(m=>String(m.jornada)===this._matchRound)
            : this._matches;
          renderFBMFixtures(this, card, matches, name => {
            if (typeof name !== "string") return null;
            const candidates = ranking.filter(item =>
              item.equipo?.trim().toLowerCase() === name.trim().toLowerCase());
            return candidates.length === 1 ? candidates[0] : null;
          }, this._fixtureCrests);
        }
      } else {
        if (this._error) card.append(this._el("p", this._error, "muted"));
        else if (!this._roster) card.append(this._el("p", "Consultando el archivo local…", "muted"));
        else if (!this._roster.length) card.append(this._el("p", "No hay plantilla archivada para este equipo.", "muted"));
        else {
          const active = this._roster.find(player => player.id === this._playerId);
          const pinned = { id: team.id, temporada: group.season_id };
          renderFBMRoster(this, card, this._roster, pinned, {
            entry: this._entryId, playerDetailTeamId: team.id, playerDetailPlayerId: active?.id,
            playerDetail: active, playerStatsTeamId: team.id, playerStatsPlayerId: active?.id,
            playerStatsEntryId: this._entryId, playerStats: this._playerStats,
            busy: !!this._playerRequest && !this._playerStats && !this._playerError
          }, id => {
            this._playerRequest = null;
            this._playerId = this._playerId === id ? null : id;
            this._playerStats = null;
            this._playerError = "";
            this._render();
          }, id => this._openPlayer(this._roster.find(player => player.id === id)));
          if (this._playerError) card.append(this._el("p", this._playerError, "muted"));
        }
      }
    } else {
      this._teamId = null;
      const summary = [group.season_id && "Temporada " + group.season_id, group.phase_name, group.group_name,
        ranking.length ? ranking.length + " equipos" : null,
        Number.isInteger(group.matches) ? group.matches + " partidos" : null];
      card.append(this._el("p", summary.filter(Boolean).join(" · "), "muted"));
      for (const [key, label] of [["current", "Jornada actual"], ["last_completed", "Última jornada disputada"], ["next", "Próxima jornada"]]) {
        const round = group.round_status?.[key];
        if (round != null) card.append(this._el("p", label + ": " + round, "muted"));
      }
      if (ranking.length) card.append(this._rankingTable(ranking));
      else card.append(this._el("p", "Clasificación pendiente de sincronizar.", "muted"));
      if (group.standings_at) card.append(this._el("p","Clasificación archivada: "+group.standings_at,"muted"));
    }
    this.shadowRoot.replaceChildren(style,card);
  }
}
class FBMCardEditor extends HTMLElement {
  setConfig(config) {
    if (JSON.stringify(config) === JSON.stringify(this._config)) return;
    this._config = { ...config };
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    const groups = this._groups();
    if (JSON.stringify(groups) !== this._groupsSignature) this._render();
  }

  _groups() {
    if (!this._config || !this._competition) return [];
    const groups = this._hass?.states?.[this._config.entity || "sensor.competiciones"]?.attributes?.groups;
    return Array.isArray(groups) ? groups : [];
  }

  _update(patch, redraw = false) {
    const config = { ...this._config, ...patch };
    for (const key of Object.keys(patch)) {
      if (patch[key] === undefined) delete config[key];
    }
    this._config = config;
    if (redraw) this._render();
    this.dispatchEvent(new CustomEvent("config-changed", {
      detail: { config }, bubbles: true, composed: true
    }));
  }

  _field(parent, label, value, onChange, { type = "text", options, min, max, placeholder, pattern, required } = {}) {
    const field = document.createElement("label");
    const caption = document.createElement("span");
    caption.textContent = label;
    field.append(caption);
    const control = document.createElement(options ? "select" : "input");
    if (options) {
      for (const [key, title] of options) {
        const option = document.createElement("option");
        option.value = key;
        option.textContent = title;
        control.append(option);
      }
    } else {
      control.type = type;
      if (min !== undefined) control.min = min;
      if (max !== undefined) control.max = max;
      if (placeholder) control.placeholder = placeholder;
      if (pattern) control.pattern = pattern;
      if (required) control.required = true;
    }
    if (type === "checkbox") {
      field.className = "toggle";
      control.checked = value === true;
    } else control.value = value ?? "";
    control.addEventListener("change", () => {
      if ((type === "number" && !control.value) || (control.checkValidity && !control.checkValidity())) {
        control.reportValidity?.();
        return;
      }
      onChange(type === "checkbox" ? control.checked : control.value);
    });
    field.append(control);
    parent.append(field);
  }

  _render() {
    const config = this._config;
    if (!config) return;
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });
    const advancedOpen = this.shadowRoot.querySelector?.("details")?.open;
    const style = document.createElement("style");
    style.textContent = `
      :host { display: block; color: var(--primary-text-color); }
      label { display: grid; gap: 6px; margin: 0 0 16px; font-weight: 500; }
      input:not([type=checkbox]), select {
        width: 100%; min-height: 40px; box-sizing: border-box; padding: 8px 10px;
        border: 1px solid var(--divider-color, #ccc); border-radius: 8px;
        background: var(--card-background-color, #fff); color: inherit; font: inherit;
      }
      input:focus-visible, select:focus-visible, summary:focus-visible, button:focus-visible {
        outline: 2px solid var(--primary-color); outline-offset: 2px;
      }
      input[type=checkbox] { accent-color: var(--primary-color); }
      .toggle { display: flex; align-items: center; justify-content: space-between; }
      details { margin-top: 12px; }
      summary { cursor: pointer; margin-bottom: 12px; font-weight: 600; }
      p { margin: 0 0 16px; color: var(--secondary-text-color); }
      fieldset { border: 1px solid var(--divider-color); border-radius: 8px; margin: 0 0 12px; }
      button { cursor: pointer; padding: 7px 10px; border: 1px solid var(--divider-color);
        border-radius: 6px; background: var(--card-background-color, #fff); color: inherit; font: inherit; }
    `;
    const form = document.createElement("div");
    const edit = (parent, label, key, options = {}) =>
      this._field(parent, label, config[key] ?? options.default, value =>
        this._update({ [key]: value === "" ? undefined : value }, options.redraw), options);
    edit(form, "Título", "title");
    const groups = this._groups();
    this._groupsSignature = JSON.stringify(groups);
    if (this._competition) {
      edit(form, "Sensor de competiciones", "entity", {
        default: "sensor.competiciones", redraw: true, pattern: "sensor\\.[a-z0-9_]+"
      });
      const index = config.group_index ?? 0;
      const options = groups.map((group, position) => [String(position),
        [group.competition_name || group.team_name || "Competición " + (position + 1),
          group.group_name, group.season_id].filter(Boolean).join(" · ")]);
      if (options.length && !options.some(([value]) => Number(value) === index))
        options.push([String(index), "Grupo " + (index + 1) + " (sin datos)"]);
      this._field(form, "Competición inicial", options.length ? String(index) : index + 1,
        value => this._update({ group_index: Number(value) - (options.length ? 0 : 1) }),
        options.length ? { options } : { type: "number", min: 1, max: 50 });
    } else {
      const mode = config.modo_experimental === true ? config.tipo_tarjeta || "busqueda" : "entidades";
      this._field(form, "Tipo de tarjeta", mode, value => {
        const patch = { modo_experimental: value !== "entidades" };
        if (value !== "entidades") patch.tipo_tarjeta = value;
        if (value !== mode) this._search = null;
        if (value === "equipo" && !config.id_tarjeta && !config.equipo_fijo) {
          const suffix = window.crypto?.randomUUID?.() || Math.random().toString(36).slice(2);
          patch.id_tarjeta = "fbm-equipo-" + suffix;
        }
        this._update(patch, true);
      }, { options: [...(mode === "entidades" ? [["entidades", "Selecciona un tipo"]] : []),
        ["busqueda", "Buscar equipos"], ["equipo", "Equipo fijo"]] });

      if (mode === "equipo") {
        const hint = document.createElement("p");
        hint.textContent = config.equipo_fijo?.nombre
          ? "Equipo configurado: " + config.equipo_fijo.nombre
          : "Después de guardar, elige el equipo desde la tarjeta.";
        form.append(hint);
        this._teamSearch(form);
      }
      const advanced = document.createElement("details");
      advanced.open = !!advancedOpen;
      const summary = document.createElement("summary");
      summary.textContent = "Opciones avanzadas";
      advanced.append(summary);
      if (mode === "busqueda") edit(advanced, "Mostrar consulta de horarios", "mostrar_horarios", { type: "checkbox" });
      if (mode === "equipo") {
        edit(advanced, "Mostrar diagnóstico de fotos", "mostrar_diagnostico", { type: "checkbox" });
        if (config.equipo_fijo) {
          for (const [key, label] of [["id", "ID oficial del equipo"], ["nombre", "Nombre del equipo"],
              ["club", "Club"], ["categoria", "Categoría"], ["temporada", "Temporada"]]) {
            this._field(advanced, label, config.equipo_fijo[key], value => {
              if (value.trim()) this._update({ equipo_fijo: { ...this._config.equipo_fijo, [key]: value.trim() } });
            });
          }
        }
      }
      form.append(advanced);
    }
    this.shadowRoot.replaceChildren(style, form);
  }

  _teamSearch(form) {
    const state = this._search ||= { query: "", teams: [], message: "", busy: false };
    const label = document.createElement("label");
    label.textContent = "Nombre del equipo";
    const input = document.createElement("input");
    input.type = "search";
    input.maxLength = 100;
    input.placeholder = "Por ejemplo, Pintobasket";
    input.value = state.query;
    input.addEventListener("input", () => { state.query = input.value; });
    label.append(input);
    const search = document.createElement("button");
    search.type = "button";
    search.textContent = "Buscar en FBM";
    search.disabled = state.busy;
    const results = document.createElement("div");
    results.setAttribute("aria-live", "polite");
    results.textContent = state.message;
    search.addEventListener("click", async () => {
      const texto = input.value.trim();
      if (state.busy) return;
      if (!texto) {
        results.textContent = "Escribe el nombre de un equipo para buscar.";
        input.focus?.();
        return;
      }
      state.query = texto;
      state.busy = true;
      state.teams = [];
      state.message = "Buscando equipos…";
      this._render();
      try {
        const entry = await this._hass?.callWS?.({ type: "fbm/client/entries" });
        if (entry?.entries?.length !== 1) throw new Error("FBM entry unavailable");
        const response = await this._hass.callWS({
          type: "fbm/team/search", entry_id: entry.entries[0], texto, skip: 0
        });
        state.teams = Array.isArray(response?.equipos)
          ? response.equipos.filter(team => FBMCard.prototype._experimentalTeamIsValid(team)) : [];
        state.message = state.teams.length ? "" : "No se han encontrado equipos.";
      } catch (_) {
        state.message = "No se pudo buscar. Comprueba que FBM está conectado.";
      } finally {
        state.busy = false;
        if (this._search === state) this._render();
      }
    });
    input.addEventListener("keydown", event => {
      if (event.key === "Enter") {
        event.preventDefault();
        search.click();
      }
    });
    if (state.teams.length) {
      this._field(results, "Equipo, categoría y temporada", "", index => {
        const team = index === "" ? null : state.teams[Number(index)];
        if (!team) return;
        const { id, nombre, club, categoria, temporada, escudo } = team;
        const equipo_fijo = { id, nombre, club, categoria, temporada };
        if (typeof escudo === "string") equipo_fijo.escudo = escudo;
        this._search = null;
        this._update({ equipo_fijo }, true);
      }, { options: [["", "Selecciona un equipo"], ...state.teams.map((team, index) =>
        [String(index), [team.nombre, team.categoria, team.temporada].join(" · ")])] });
    }
    form.append(label, search, results);
  }
}

class FBMCompetitionCardEditor extends FBMCardEditor {
  get _competition() { return true; }
}

if (!customElements.get("fbm-card-editor"))
  customElements.define("fbm-card-editor", FBMCardEditor);
if (!customElements.get("fbm-competition-card-editor"))
  customElements.define("fbm-competition-card-editor", FBMCompetitionCardEditor);

if (!customElements.get("fbm-competition-card"))
  customElements.define("fbm-competition-card", FBMCompetitionCard);
window.customCards = window.customCards || [];
if (!window.customCards.some(card => card.type === "fbm-competition-card"))
  window.customCards.push({
    type:"fbm-competition-card",name:"FBM Competition Card",
    description:"Clasificación y plantillas archivadas de una competición FBM"
  });

if (!customElements.get("fbm-card")) customElements.define("fbm-card", FBMCard);
window.customCards = window.customCards || [];
if (!window.customCards.some((card) => card.type === "fbm-card")) {
  window.customCards.push({ type: "fbm-card", name: "FBM Card", description: "Busca equipos FBM y consulta partidos, clasificación y jugadores", preview: true });
}




