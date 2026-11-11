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
  HTMLElement: class {}, window, URL,
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

test("fixed cards recover missing crests by exact FBM team ID", async () => {
  const card = new Card();
  card._config = {};
  const state = card._experimentalState();
  Object.assign(state,{entry:"fbm",selected:"selected",status:{sesion_vigente:true}});
  let calls = 0;
  card._hass = {callWS: async () => {
    calls++;
    return {equipos:[{id:"another",escudo:"WRONG"},{id:"selected",escudo:"AB".repeat(384)}]};
  }};
  const team = {id:"selected",nombre:"Equipo",club:"Club",categoria:"Alevín",temporada:"26/27"};
  assert.equal(await card._recoverFixedCrest(state,team),true);
  assert.equal(card._fixedCrestCandidates(state,team)[0].endsWith("AB".repeat(384)),true);
  assert.equal(await card._recoverFixedCrest(state,team),false);
  assert.equal(calls,1);
  assert.match(card._fixedCardYaml({...team,escudo:"ABCD"}), /escudo: "ABCD"/);
});

test("fixed card uses official crest URLs and archived fixture images", () => {
  const card = new Card();
  card._config = {};
  const team = {id:"selected",nombre:"Equipo",escudo:"https://fbm.es/crest.png"};
  const state = {schedule:{partidos:[{local:" equipo ",img_local:"data:image/png;base64,AA=="}]}};
  const urls = card._fixedCrestCandidates(state,team);
  assert.equal(urls[0],"https://fbm.es/crest.png");
  assert.equal(urls[1],"data:image/png;base64,AA==");
});
