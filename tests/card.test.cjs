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
  assert.match(source, /conexión con datos oficiales de FBM pendiente/);
  assert.doesNotMatch(source, /fetch\s*\(/);
});
