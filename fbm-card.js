/* FBM Card DEV — presentación de datos; fuente oficial pendiente de validar. */
class FBMCard extends HTMLElement {
  setConfig(config) {
    if (!config || typeof config !== "object") throw new Error("Configuración inválida");
    this._config = { ...config };
    this._render();
  }
  set hass(hass) { this._hass = hass; this._render(); }
  getCardSize() { return 5; }
  static getStubConfig() { return { title: "FBM Card", equipo: "GRUPO EGIDO PINTOBASKET NEGRO" }; }

  _data() {
    const entityId = this._config.entidad_datos;
    if (!entityId) return { error: "Pendiente de conectar una fuente de datos oficiales de FBM." };
    const state = this._hass?.states?.[entityId];
    if (!state) return { error: "La entidad de datos no está disponible: " + entityId };
    if (["unknown", "unavailable"].includes(state.state)) return { error: "La entidad de datos no está disponible." };
    const data = state.attributes?.fbm || state.attributes;
    if (!data || !Array.isArray(data.partidos) || !Array.isArray(data.clasificacion)) {
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
    const team = this._element("div", this._config.equipo || "Sin equipo seleccionado", "muted");
    card.append(title, team);
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
