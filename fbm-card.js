/* FBM Card DEV: todavía no consulta datos de FBM. */
class FBMCard extends HTMLElement {
  setConfig(config) {
    if (!config || typeof config !== "object") throw new Error("Configuración inválida");
    this._config = { ...config };
    this._render();
  }
  set hass(hass) { this._hass = hass; this._render(); }
  getCardSize() { return 3; }
  static getStubConfig() { return { title: "FBM Card" }; }
  _render() {
    if (!this._config) return;
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });
    const card = document.createElement("ha-card");
    const wrapper = document.createElement("div");
    wrapper.style.cssText = "padding:16px;line-height:1.5";
    const heading = document.createElement("strong");
    heading.textContent = String(this._config.title || "FBM Card");
    const team = document.createElement("p");
    team.textContent = "Equipo: " + String(this._config.equipo || "Sin seleccionar");
    const status = document.createElement("p");
    status.textContent = "Versión DEV: conexión con datos oficiales de FBM pendiente.";
    const note = document.createElement("small");
    note.textContent = "No se muestran partidos ni clasificaciones hasta validar la consulta pública.";
    wrapper.append(heading, team, status, note);
    card.append(wrapper);
    this.shadowRoot.replaceChildren(card);
  }
}
if (!customElements.get("fbm-card")) customElements.define("fbm-card", FBMCard);
window.customCards = window.customCards || [];
if (!window.customCards.some((card) => card.type === "fbm-card")) {
  window.customCards.push({ type: "fbm-card", name: "FBM Card", description: "Resultados de la FBM (en desarrollo)" });
}
