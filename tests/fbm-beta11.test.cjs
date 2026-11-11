const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const registered = new Map();
const values = new Map();
const window = {
  localStorage: { getItem: key => values.get(key), setItem: (key, value) => values.set(key, value) }
};
vm.runInNewContext(fs.readFileSync(path.join(__dirname, "../fbm-card.js"), "utf8"), {
  HTMLElement: class {}, window,
  customElements: { get: key => registered.get(key), define: (key, value) => registered.set(key, value) },
});
const Card = registered.get("fbm-card");

test("the visual picker creates a working search configuration", () => {
  assert.ok(window.customCards.some(card => card.type === "fbm-card"));
  const config = Card.getStubConfig();
  assert.equal(config.type, "custom:fbm-card");
  assert.equal(config.modo_experimental, true);
  assert.equal(config.tipo_tarjeta, "busqueda");
});

test("switching a configured fixed card does not change another card", () => {
  const original = { id: "a", nombre: "A", club: "A", categoria: "A", temporada: "26/27" };
  const replacement = { ...original, id: "b", nombre: "B" };
  const create = id => Object.assign(new Card(), {
    _config: { tipo_tarjeta: "equipo", id_tarjeta: id, equipo_fijo: original },
    _hass: { user: { id: "user" } }
  });
  const first = create("first"), second = create("second");
  first._saveExperimentalTeam("entry", replacement);
  assert.equal(first._restoreExperimentalTeam("entry").id, "b");
  assert.equal(second._restoreExperimentalTeam("entry").id, "a");
});

test("search reuses archived standings without a remote standings query", async () => {
  const card = new Card();
  card._config = Card.getStubConfig();
  card._render = () => {};
  const calls = [];
  card._hass = { callWS: async request => {
    calls.push(request.type);
    return { found: true, standings: { clasificacion: [{ equipo: "A" }] } };
  } };
  const state = card._experimentalState();
  Object.assign(state, { entry: "entry", selected: "a", teams: [{ id: "a" }] });
  await card._experimentalAction("standings");
  assert.deepEqual(calls, ["fbm/competition/team_snapshot"]);
  assert.equal(state.standings[0].equipo, "A");
});
