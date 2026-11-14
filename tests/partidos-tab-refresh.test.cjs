const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");

const source = fs.readFileSync("fbm-card.js", "utf8");
const bundled = fs.readFileSync("custom_components/fbm/www/fbm-card.js", "utf8");

test("la tarjeta y el paquete contienen el mismo código", () => {
  assert.equal(bundled, source);
});

test("no se presenta el botón manual Actualizar partidos", () => {
  assert.doesNotMatch(source, /this\._element\("button", "Actualizar partidos"/);
  assert.doesNotMatch(source, /Pulsa Actualizar partidos para consultar/);
});

test("al abrir Partidos se consulta el calendario ausente o caducado", () => {
  assert.match(source, /if \(name === "partidos"\) \{\s+const cached = this\._fixedMatchesAvailable\(state, pinned\.id\)/);
  assert.match(source, /if \(!cached\) void this\._experimentalAction\("fixed_schedule"\)/);
  assert.match(source, /else if \(!state\.archivedData && stale\) void this\._experimentalAction\("refresh_schedule"\)/);
  assert.match(source, /Date\.now\(\) - state\.lastScheduleUpdate >= 15 \* 60 \* 1000/);
  assert.match(source, /if \(!connected \|\| !pinned\?\.id \|\| state\.busy\) return/);
});
