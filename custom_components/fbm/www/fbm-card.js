/* FBM Card DEV — presentación de datos; fuente oficial pendiente de validar. */
class FBMCard extends HTMLElement {
  setConfig(config) {
    if (!config || typeof config !== "object") throw new Error("Configuración inválida");
    if (this._config && (this._config.modo_experimental !== config.modo_experimental || this._config.id_tarjeta !== config.id_tarjeta)) this._experimental = null;
    this._config = { ...config };
    this._render();
  }
  set hass(hass) {
    if (this._hass && this._hass.user?.id !== hass?.user?.id) this._experimental = null;
    this._hass = hass; this._render();
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
      selected: "", rounds: null, round: "", phaseName: "", start: "", end: "", schedule: null, standings: null, showGroup: false, message: "", busy: false };
  }

  _experimentalPreferenceKey(entryId) {
    const user = this._hass?.user?.id;
    if (typeof user !== "string" || !user || typeof entryId !== "string" || !entryId) return null;
    return "fbm-card:experimental-equipo:v1:" + JSON.stringify([user, String(this._config?.id_tarjeta || "predeterminada"), entryId]);
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
    try { window.localStorage?.setItem(key, JSON.stringify(data)); } catch (_) { /* almacenamiento deshabilitado */ }
  }

  _clearExperimentalTeam(entryId) {
    const key = this._experimentalPreferenceKey(entryId);
    if (!key) return;
    try { window.localStorage?.removeItem(key); } catch (_) { /* almacenamiento deshabilitado */ }
  }

  _restoreExperimentalTeam(entryId) {
    const key = this._experimentalPreferenceKey(entryId);
    if (!key) return null;
    try {
      const team = JSON.parse(window.localStorage?.getItem(key) || "null");
      if (!this._experimentalTeamIsValid(team)) return null;
      return { id: team.id, nombre: team.nombre, club: team.club, categoria: team.categoria, temporada: team.temporada };
    } catch (_) { return null; }
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
        } else if (action === "phases") {
          if (!state.selected) throw new Error("Elige un equipo.");
          remoteAttempted = true;
          const data = await this._hass.callWS({ type: "fbm/team/phases", ...common, equipo: state.selected });
          if (!Array.isArray(data.rondas)) throw new Error("Respuesta de fases no válida.");
          state.rounds = data.rondas; state.round = ""; state.phaseName = data.nombre_fase || ""; state.schedule = null;
          state.message = state.rounds.length ? "Elige una ronda." : "Fase sin rondas: se utilizará el grupo actual.";
        } else if (action === "schedule") {
          if (!state.selected || !state.start || !state.end || !Array.isArray(state.rounds) || (state.rounds.length && !state.round)) throw new Error("Elige equipo, fase y fechas.");
          const request = { type: state.rounds.length ? "fbm/team/schedule_round" : "fbm/team/schedule", ...common,
            equipo: state.selected, desde: state.start, hasta: state.end };
          if (state.rounds.length) request.ronda = state.round;
          remoteAttempted = true;
          state.schedule = await this._hass.callWS(request);
        } else if (action === "standings") {
          if (!state.selected) throw new Error("Elige un equipo.");
          remoteAttempted = true;
          const data = await this._hass.callWS({ type: "fbm/team/standings", ...common, equipo: state.selected });
          if (!Array.isArray(data.clasificacion)) throw new Error("Clasificación no válida.");
          state.standings = data.clasificacion;
        }
      }
    } catch (_) {
      if (remoteAttempted && ["register", "recover_registration", "connect", "search", "phases", "schedule", "standings"].includes(action) && state.entry) {
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
    card.append(this._element("p", "Conexión experimental. Disponible para administradores; aún no validada en Home Assistant.", "muted"));
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
      button("Crear identidad local", "create", !state.status.identidad_creada);
      input("Versión del perfil Android experimental", "release");
      button("Registrar dispositivo en FBM", "register", state.status.identidad_creada && !state.status.candidato_guardado && !state.status.registro_pendiente);
      if (state.status.registro_pendiente) {
        card.append(this._element("p", "Recuperar envía una nueva solicitud de registro con la misma identidad.", "muted"));
        button("Recuperar registro pendiente", "recover_registration");
      }
      button("Conectar", "connect", state.status.candidato_guardado);
      input("Buscar equipo", "query");
      button("Buscar", "search", connected);
      if (state.teams.length) {
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
          if (selectedTeam) this._saveExperimentalTeam(state.entry, selectedTeam);
          else if (!state.selected) this._clearExperimentalTeam(state.entry);
          this._render();
        });
        label.append(select); card.append(label);
        button("Consultar clasificación del grupo actual", "standings", !!state.selected && connected);
        button("Consultar fase y rondas", "phases", !!state.selected && connected);
        if (Array.isArray(state.rounds)) {
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
        input("Desde", "start", "date"); input("Hasta", "end", "date");
        button("Consultar horarios", "schedule", !!state.selected && connected && Array.isArray(state.rounds) && (!state.rounds.length || !!state.round));
      }
      if (Array.isArray(state.standings)) {
        card.append(this._element("h3", "Clasificación del grupo actual"));
        if (!state.standings.length) card.append(this._element("p", "No hay clasificación disponible.", "muted"));
        else {
          const table = document.createElement("table"); table.className = "standings";
          const head = document.createElement("tr");
          for (const title of ["Pos.", "Equipo", "PJ", "G", "P", "Pts"]) head.append(this._element("th", title));
          const thead = document.createElement("thead"); thead.append(head); table.append(thead);
          const body = document.createElement("tbody");
          for (const team of state.standings) {
            const row = document.createElement("tr");
            for (const field of ["posicion", "equipo", "jugados", "ganados", "perdidos", "puntos"]) row.append(this._element("td", team[field] ?? "—"));
            body.append(row);
          }
          table.append(body); card.append(table);
        }
      }
      if (state.schedule && Array.isArray(state.schedule.partidos)) {
        const visible = this._experimentalMatches();
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
      .standings th,.standings td{text-align:left;padding:6px;border-bottom:1px solid var(--divider-color,#ddd)}
      .standings td.num,.standings th.num{text-align:right}
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
