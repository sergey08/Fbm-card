/* FBM Card DEV — presentación de datos; fuente oficial pendiente de validar. */
class FBMCard extends HTMLElement {
  setConfig(config) {
    if (!config || typeof config !== "object") throw new Error("Configuración inválida");
    const priorTeam = this._config?.equipo_fijo?.id;
    const newTeam = config.equipo_fijo?.id;
    const changed = !!this._config && (this._config.modo_experimental !== config.modo_experimental ||
      this._config.id_tarjeta !== config.id_tarjeta || this._config.tipo_tarjeta !== config.tipo_tarjeta || priorTeam !== newTeam);
    if (changed) { this._experimental = null; this._fixedInit = false; }
    if (config.tipo_tarjeta && !["busqueda", "equipo"].includes(config.tipo_tarjeta)) throw new Error("Tipo de tarjeta inválido");
    if (config.tipo_tarjeta === "equipo" && !config.equipo_fijo && !config.id_tarjeta) {
      throw new Error("Cada tarjeta de equipo necesita un id_tarjeta distinto para guardar su elección.");
    }
    this._config = { ...config };
    this._render();
    if (this._hass && config.modo_experimental === true && config.tipo_tarjeta === "equipo" && (!this._fixedInit || changed)) {
      Promise.resolve().then(() => this._initializeFixed());
    }
  }
  set hass(hass) {
    const hadHass = !!this._hass;
    const userChanged = hadHass && this._hass.user?.id !== hass?.user?.id;
    if (userChanged) this._experimental = null;
    this._hass = hass;
    if (this._config?.modo_experimental === true && this._config.tipo_tarjeta === "equipo" && (!hadHass || userChanged)) {
      this._fixedInit = false;
      Promise.resolve().then(() => this._initializeFixed());
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
  static getStubConfig() { return { title: "FBM Card", equipos: [] }; }

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
      selected: "", rounds: null, round: "", phaseName: "", start: "", end: "", schedule: null, standings: null, players: null, playersTeamId: "", playersEntryId: "", playerDetail: null, playerDetailTeamId: "", playerDetailPlayerId: "", playerStats: null, playerStatsTeamId: "", playerStatsPlayerId: "", playerStatsEntryId: "", showGroup: false, tab: "clasificacion", partidosTab: "fases", scheduleTeamId: "", scheduleEntryId: "", matchRound: "all", matchStart: "", matchEnd: "", lastScheduleUpdate: 0, lastStandingsUpdate: 0, lastPlayersUpdate: 0, message: "", busy: false };
  }

  _experimentalPreferenceKey(entryId) {
    const user = this._hass?.user?.id;
    if (typeof user !== "string" || !user || typeof entryId !== "string" || !entryId) return null;
    const cardId = this._config?.id_tarjeta;
    if (this._config?.tipo_tarjeta === "equipo" && (typeof cardId !== "string" || !cardId.trim())) return null;
    return "fbm-card:experimental-equipo:v1:" + JSON.stringify([user, String(cardId || "predeterminada"), entryId]);
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
    if (configured && this._experimentalTeamIsValid(configured)) return configured;
    const key = this._experimentalPreferenceKey(entryId);
    if (!key) return null;
    try {
      const team = JSON.parse(window.localStorage?.getItem(key) || "null");
      if (!this._experimentalTeamIsValid(team)) return null;
      const result = { id: team.id, nombre: team.nombre, club: team.club, categoria: team.categoria, temporada: team.temporada };
      if (typeof team.escudo === "string" && team.escudo.length <= 1024) result.escudo = team.escudo;
      return result;
    } catch (_) { return null; }
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
        if (state.status.sesion_vigente) {
          const data = await this._hass.callWS({ type: "fbm/team/standings", entry_id: state.entry, equipo: saved.id });
          if (Array.isArray(data.clasificacion)) { state.standings = data.clasificacion; state.lastStandingsUpdate = Date.now(); }
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

  _fixtureDateKey(value) {
    if (typeof value !== "string") return "";
    const match = /^(\d{2})\/(\d{2})\/(\d{4})$/.exec(value);
    return match ? match[3] + "-" + match[2] + "-" + match[1] : value;
  }

  _roundDateLabel(matches) {
    const dates = [...new Set(matches.map(game => game?.fecha)
      .filter(value => typeof value === "string" && /^\d{2}\/\d{2}\/\d{4}$/.test(value)))];
    dates.sort((a, b) => this._fixtureDateKey(a).localeCompare(this._fixtureDateKey(b)));
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
          state.selected = ""; state.rounds = null; state.round = ""; state.schedule = null; state.standings = null; state.showGroup = false;
          state.message = state.teams.length ? "Elige un equipo, categoría y temporada." : "No se han encontrado equipos.";
        } else if (action === "fix_team") {
          const selected = state.teams.find(team => team.id === state.selected);
          if (!selected) throw new Error("Elige un equipo.");
          this._saveExperimentalTeam(state.entry, selected);
          state.editFixed = false;
          state.message = "Equipo fijado en esta tarjeta.";
          if (state.status?.sesion_vigente) {
            remoteAttempted = true;
            const data = await this._hass.callWS({ type: "fbm/team/standings", ...common, equipo: selected.id });
            if (Array.isArray(data.clasificacion)) state.standings = data.clasificacion;
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
          if (this._config?.tipo_tarjeta !== "equipo" || !state.selected ||
              state.status?.sesion_vigente !== true) throw new Error("Equipo o sesión no disponible.");
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
          if (action !== "refresh_players") { state.players = null; state.playersTeamId = ""; state.playersEntryId = ""; }
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
        } else if (action === "standings") {
          if (!state.selected) throw new Error("Elige un equipo.");
          remoteAttempted = true;
          const data = await this._hass.callWS({ type: "fbm/team/standings", ...common, equipo: state.selected });
          if (!Array.isArray(data.clasificacion)) throw new Error("Clasificación no válida.");
          state.standings = data.clasificacion;
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

  _renderExperimental(card) {
    const state = this._experimentalState();
    card.append(this._element("h2", this._config.title || "🏀 FBM Card"));
    card.append(this._element("p", "Consulta equipos y clasificaciones oficiales de la Federación de Baloncesto de Madrid.", "muted"));
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
    button("Comprobar estado", "status", !!this._hass?.callWS);
    if (state.status) {
      const connected = state.status.sesion_vigente === true;
      const sessionText = connected ? "vigente en la última comprobación local" : (state.status.sesion_en_memoria ? "necesita reconexión" : "sin conectar");
      card.append(this._element("p", `Identidad: ${state.status.identidad_creada ? "creada" : "pendiente"} · Dispositivo: ${state.status.candidato_guardado ? "guardado" : "pendiente"} · Sesión: ${sessionText}`, "muted"));
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
      const pinned = fixed ? this._restoreExperimentalTeam(state.entry) : null;
      const editing = fixed && (!pinned || state.editFixed);
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
          state.teams = [team]; state.selected = team.id; state.standings = null;
          this._render();
        });
        label.append(select); card.append(label);
      }
      if (fixed && pinned && !editing) {
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
          tab.addEventListener("click", () => { state.tab = name; this._render(); if (name === "partidos" && connected && !this._fixedMatchesAvailable(state, pinned.id)) this._experimentalAction("fixed_schedule"); });
          tabs.append(tab);
        }
        card.append(tabs);
        if (state.tab === "clasificacion" || !state.tab) button("Actualizar clasificación", "standings", connected);
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
              const games = this._element("div", "", "fbm-fixture-list");
              const sorted = [...filtered].sort((a, b) => (a.jornada ?? 999) - (b.jornada ?? 999) ||
                this._fixtureDateKey(a.fecha).localeCompare(this._fixtureDateKey(b.fecha)) ||
                String(a.hora || "").localeCompare(String(b.hora || "")));
              for (const match of sorted) {
                const box = this._element("article", "", "fbm-fixture");
                const top = this._element("div", "", "fbm-match-header");
                top.append(this._element("strong", Number.isInteger(match.jornada) ? "Jornada " + match.jornada : "Jornada sin indicar"));
                top.append(this._element("span", [match.fecha, match.hora].filter(Boolean).join(" · ") || "Fecha pendiente", "fbm-player-caption"));
                box.append(top);
                const teams = this._element("div", "", "fbm-fixture-teams");
                const teamLabel = (name, image, side) => {
                  const box = this._element("div", "", "fbm-fixture-side fbm-fixture-" + side);
                  if (typeof image === "string" && /^data:image\/(png|jpeg|webp);base64,/.test(image)) {
                    const img = document.createElement("img"); img.src = image;
                    img.className = "fbm-fixture-logo"; img.alt = "Escudo de " + name;
                    img.loading = "lazy"; img.addEventListener("error", () => img.remove(), { once: true });
                    box.append(img);
                  }
                  box.append(this._element("span", name));
                  return box;
                };
                teams.append(teamLabel(match.local || "Local sin indicar", match.img_local, "local"));
                const score = match.marcador &&
                  Number.isInteger(match.marcador.local) && Number.isInteger(match.marcador.visitante)
                  ? match.marcador.local + " – " + match.marcador.visitante : "vs";
                teams.append(this._element("strong", score, "fbm-fixture-score"));
                teams.append(teamLabel(match.visitante || "Visitante sin indicar", match.img_visitante, "away"));
                box.append(teams);
                if (match.campo) box.append(this._element("p", match.campo, "fbm-player-caption"));
                games.append(box);
              }
              card.append(games);
            }
          }
        }
        if (state.tab === "jugadores") {
          button("Actualizar plantilla", "players", connected && !!pinned?.id);
          const roster = state.playersEntryId === state.entry && state.playersTeamId === pinned?.id
            ? state.players : null;
          if (!Array.isArray(roster)) {
            card.append(this._element("p", "Consulta la plantilla para ver nombres y estadísticas oficiales.", "muted"));
          } else if (!roster.length) {
            card.append(this._element("p", "FBM no ha devuelto jugadores para este equipo.", "muted"));
          } else {
            card.append(this._element("div", roster.length + " jugadores · Datos oficiales FBM", "fbm-section-subtitle"));
            const collection = this._element("div", "", "fbm-roster");
            const numeric = value => typeof value === "number" && Number.isFinite(value);
            const format = value => String(value);
            const chip = (label, value, emphasize = false) => {
              const el = this._element("div", "", emphasize ? "fbm-stat fbm-stat-primary" : "fbm-stat");
              el.append(this._element("span", label, "fbm-stat-label"));
              el.append(this._element("strong", format(value), "fbm-stat-value"));
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
              const item = this._element("section", "", opened ? "fbm-player fbm-player-open" : "fbm-player");
              const header = this._element("div", "", "fbm-player-header");
              const person = this._element("div", "", "fbm-player-identity");
              const personRow = this._element("div", "", "fbm-player-person");
              const photo = player.foto || (opened && opened.foto) || "";
              if (typeof photo === "string" && /^data:image\/(png|jpeg|webp);base64,/.test(photo)) {
                const img = document.createElement("img");
                img.className = "fbm-player-photo"; img.src = photo;
                img.alt = "Fotografía de " + player.nombre; img.loading = "lazy";
                img.addEventListener("error", () => img.remove(), { once: true });
                personRow.append(img);
              }
              personRow.append(this._element("strong", player.nombre, "fbm-player-name"));
              person.append(personRow);
              person.append(this._element("span", "Temporada " + (player.temporada || pinned.temporada || "FBM"), "fbm-player-caption"));
              const detailButton = this._element("button", opened ? "Cerrar ficha" : "Ver ficha", "fbm-action");
              detailButton.type = "button";
              detailButton.disabled = state.busy;
              detailButton.setAttribute("aria-expanded", String(!!opened));
              detailButton.addEventListener("click", () => this._experimentalPlayerDetail(player.id));
              header.append(person, detailButton);
              item.append(header);
              const overview = this._element("div", "", "fbm-stat-grid");
              if (numeric(player.partidos_jugados)) overview.append(chip("Partidos", player.partidos_jugados));
              if (numeric(player.puntos_por_partido)) overview.append(chip("Puntos/partido", player.puntos_por_partido, true));
              if (numeric(player.minutos_por_partido)) overview.append(chip("Min/partido", player.minutos_por_partido));
              if (numeric(player.puntos_totales)) overview.append(chip("Puntos totales", player.puntos_totales));
              if ([player.partidos_jugados, player.puntos_por_partido, player.minutos_por_partido, player.puntos_totales].some(numeric)) item.append(overview);
              if (opened) {
                const details = this._element("div", "", "fbm-player-detail");
                const meta = [opened.equipo, opened.temporada, opened.categoria].filter(Boolean);
                if (meta.length) details.append(this._element("p", meta.join(" · "), "fbm-player-caption"));
                const statsButton = this._element("button", "Consultar estadísticas por partido", "fbm-action fbm-action-primary");
                statsButton.type = "button";
                statsButton.disabled = state.busy;
                statsButton.addEventListener("click", () => this._experimentalPlayerStats(player.id));
                details.append(statsButton);
                const stats = state.playerStatsTeamId === pinned?.id &&
                  state.playerStatsEntryId === state.entry &&
                  state.playerStatsPlayerId === player.id ? state.playerStats : null;
                if (stats) {
                  const globals = stats.globales?.estadisticas || {};
                  const available = [
                    ["puntos_totales", "Puntos totales"], ["media_puntos", "Media puntos"],
                    ["asistencias", "Asistencias"], ["faltas_cometidas", "Faltas"],
                    ["faltas_recibidas", "F. recibidas"], ["rebotes", "Rebotes"],
                    ["recuperaciones", "Recuperaciones"], ["perdidas", "Pérdidas"],
                    ["valoracion", "Valoración"]
                  ].filter(([key]) => numeric(globals[key]));
                  if (available.length) {
                    details.append(this._element("h4", "Estadísticas globales", "fbm-subheading"));
                    const globalGrid = this._element("div", "", "fbm-stat-grid");
                    for (const [key, label] of available) globalGrid.append(chip(label, globals[key]));
                    details.append(globalGrid);
                  }
                  const games = Array.isArray(stats.partidos?.partidos) ? stats.partidos.partidos : [];
                  details.append(this._element("h4", "Partidos con estadísticas (" + games.length + ")", "fbm-subheading"));
                  if (!games.length) details.append(this._element("p", "No hay partidos con estadísticas disponibles.", "fbm-player-caption"));
                  for (const game of games) {
                    const match = this._element("article", "", "fbm-match");
                    const matchHeader = this._element("div", "", "fbm-match-header");
                    matchHeader.append(this._element("strong", game.rival || "Rival sin indicar"));
                    matchHeader.append(this._element("span", game.fecha || "Fecha pendiente", "fbm-player-caption"));
                    match.append(matchHeader);
                    const matchGrid = this._element("div", "", "fbm-stat-grid fbm-match-grid");
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
        }
        const changeTeam = this._element("button", "Cambiar equipo");
        changeTeam.type = "button";
        changeTeam.addEventListener("click", () => { state.editFixed = true; state.teams = [pinned]; state.selected = pinned.id; this._render(); });
        if (!this._config.equipo_fijo) card.append(changeTeam);
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
      if (!fixed && favorites.length) {
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
          state.teams = [team]; state.selected = team.id; state.standings = null;
          this._render();
        });
        label.append(select); card.append(label);
      }
      if (state.teams.length && (!fixed || editing)) {
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
          state.selected = event.target.value; state.rounds = null; state.round = ""; state.schedule = null; state.standings = null; state.showGroup = false;
          const selectedTeam = state.teams.find(team => team.id === state.selected);
          if (selectedTeam && this._config.tipo_tarjeta !== "equipo") this._saveExperimentalTeam(state.entry, selectedTeam);
          if (selectedTeam) this._saveRecentTeam(state.entry, selectedTeam);
          else if (!state.selected) this._clearExperimentalTeam(state.entry);
          this._render();
        });
        label.append(select); card.append(label);
        if (fixed) button("Fijar este equipo en la tarjeta", "fix_team", !!state.selected && connected);
        else {
          button("Consultar clasificación del grupo actual", "standings", !!state.selected && connected);
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
      if (Array.isArray(state.standings) && (!fixed || !pinned || editing || !state.tab || state.tab === "clasificacion")) {
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
      if (this._config.mostrar_horarios === true && state.schedule && Array.isArray(state.schedule.partidos) && (!fixed || state.tab === "partidos")) {
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
      .fbm-player-person{display:flex;align-items:center;gap:8px;min-width:0}
      .fbm-player-photo{width:38px;height:38px;flex:0 0 38px;border-radius:50%;object-fit:cover;background:var(--secondary-background-color,#eee)}
      .fbm-fixture-side{display:flex;align-items:center;gap:7px;min-width:0}
      .fbm-fixture-side.fbm-fixture-away{justify-content:flex-end}
      .fbm-fixture-side.fbm-fixture-away img{order:2}
      .fbm-fixture-logo{width:25px;height:25px;flex:0 0 25px;object-fit:contain}
      .fbm-fixture-side span{font-size:.82rem;font-weight:600;overflow-wrap:anywhere}
      .fbm-fixture-side.fbm-fixture-away span{text-align:right}
      .fbm-match-controls{display:flex;flex-wrap:wrap;align-items:end;gap:8px;margin:10px 0}
      .fbm-match-controls label{display:flex;flex:1 1 125px;flex-direction:column;gap:4px;font-size:.75rem;color:var(--secondary-text-color,#666)}
      .fbm-match-controls input{width:100%;box-sizing:border-box;min-height:36px;border:1px solid var(--divider-color,#ddd);border-radius:8px;padding:5px;background:var(--card-background-color,#fff);color:var(--primary-text-color,#222)}
      .fbm-match-controls button{align-self:end}
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
      card.append(table);
      if (result.data.actualizado) card.append(this._element("p", "Actualizado: " + result.data.actualizado, "muted"));
    }
    this.shadowRoot.replaceChildren(style, card);
  }
}
if (!customElements.get("fbm-card")) customElements.define("fbm-card", FBMCard);
window.customCards = window.customCards || [];
if (!window.customCards.some((card) => card.type === "fbm-card")) {
  window.customCards.push({ type: "fbm-card", name: "FBM Card", description: "Calendario y clasificación FBM (en desarrollo)" });
}




