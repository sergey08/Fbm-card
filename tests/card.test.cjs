const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const source = fs.readFileSync("fbm-card.js", "utf8");
function loadCard() {
  const elements = new Map();
  const sandbox = {
    HTMLElement: class {},
    customElements: { get: name => elements.get(name), define: (name, cls) => elements.set(name, cls) },
    window: { customCards: [] }
  };
  vm.runInNewContext(source, sandbox);
  return { elements, sandbox };
}
test("registra la tarjeta Lovelace", () => {
  const { elements, sandbox } = loadCard();
  assert.equal(typeof elements.get("fbm-card"), "function");
  assert.equal(sandbox.window.customCards.length, 1);
});
test("la configuración inicial está disponible", () => {
  const { elements } = loadCard();
  assert.equal(elements.get("fbm-card").getStubConfig().title, "FBM Card");
});
test("rechaza configuración no válida", () => {
  const { elements } = loadCard();
  const card = new (elements.get("fbm-card"))();
  assert.throws(() => card.setConfig(null), /Configuración inválida/);
});
test("no hay resultados ficticios ni solicitudes automáticas", () => {
  assert.match(source, /Pendiente de conectar una fuente de datos oficiales de FBM/);
  assert.doesNotMatch(source, /fetch\s*\(/);
});

test("sin entidad muestra estado pendiente", () => {
  const { elements } = loadCard();
  const card = new (elements.get("fbm-card"))();
  card._config = { equipo: "GRUPO EGIDO PINTOBASKET NEGRO" };
  assert.match(card._data().error, /Pendiente/);
});
test("acepta partidos y clasificación desde una entidad de HA", () => {
  const { elements } = loadCard();
  const card = new (elements.get("fbm-card"))();
  card._config = { entidad_datos: "sensor.fbm" };
  card._hass = { states: { "sensor.fbm": { state: "ok", attributes: { fbm: {
    partidos: [{ local: "A", visitante: "B", resultado: "50-48" }],
    clasificacion: [{ posicion: 1, equipo: "A", jugados: 3, puntos: 6 }]
  } } } } };
  assert.equal(card._data().data.partidos.length, 1);
  assert.equal(card._data().data.clasificacion.length, 1);
});
test("rechaza entidades con formato incompleto", () => {
  const { elements } = loadCard();
  const card = new (elements.get("fbm-card"))();
  card._config = { entidad_datos: "sensor.fbm" };
  card._hass = { states: { "sensor.fbm": { state: "ok", attributes: {} } } };
  assert.match(card._data().error, /formato esperado/);
});
