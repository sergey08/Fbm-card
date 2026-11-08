/* FBM Card DEV — presentación de datos; fuente oficial pendiente de validar. */
class FBMCard extends HTMLElement {
  setConfig(config) {
    if (!config || typeof config !== "object") throw new Error("Configuración inválida");
    this._config = { ...config };
    this._render();
  }
  set hass(hass) { this._hass = hass; this._render(); }
  getCardSize() { return 5; }
  static getStubConfig() { return { title: "FBM Card", equipos: [] }; }

  _teams() {
    if (Array.isArray(this._config?.equipos)) return this._config.equipos.filter(x => x && typeof x.nombre === "string" && typeof x.entidad_datos === "string");
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
      .filter(([id, state]) => id.startsWith("sensor.") && (state.attributes?.fbm?.fuente === "FBM" || state.attributes?.fuente === "FBM"))
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
