const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");

test("la integración incluye un manifiesto de configuración", () => {
  const manifest = JSON.parse(fs.readFileSync("custom_components/fbm/manifest.json", "utf8"));
  assert.equal(manifest.domain, "fbm");
  assert.equal(manifest.config_flow, true);
  assert.equal(manifest.requirements.length, 0);
});
test("la tarjeta está empaquetada dentro de la integración", () => {
  const card = fs.readFileSync("fbm-card.js", "utf8");
  const bundled = fs.readFileSync("custom_components/fbm/www/fbm-card.js", "utf8");
  assert.equal(bundled, card, "El JS empaquetado debe coincidir con el código fuente");
});
test("la integración no incluye fuentes externas ni credenciales simuladas", () => {
  const files = ["custom_components/fbm/__init__.py", "custom_components/fbm/config_flow.py"];
  for (const path of files) {
    const content = fs.readFileSync(path, "utf8");
    assert.doesNotMatch(content, /requests\.get|aiohttp\.ClientSession|fetch\(/);
  }
});

test("la integración intenta registrar el recurso Lovelace sin duplicados", () => {
  const code = fs.readFileSync("custom_components/fbm/__init__.py", "utf8");
  assert.match(code, /async_create_item/);
  assert.match(code, /async_items\(\)/);
  assert.match(code, /CARD_URL/);
});

test("HACS está configurado como integración y no como tarjeta independiente", () => {
  const hacs = JSON.parse(fs.readFileSync("hacs.json", "utf8"));
  assert.equal(typeof hacs.name, "string");
  assert.equal("filename" in hacs, false);
  assert.equal("content_in_root" in hacs, false);
});
test("el flujo de CI valida la nueva estructura de integración", () => {
  const workflow = fs.readFileSync(".github/workflows/validacion.yml", "utf8");
  assert.match(workflow, /custom_components\/fbm\/manifest\.json/);
  assert.match(workflow, /Validar sintaxis de integración Python/);
});
