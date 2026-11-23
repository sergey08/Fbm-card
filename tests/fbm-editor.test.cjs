const assert = require("node:assert/strict");
const fs = require("node:fs");
const test = require("node:test");
const vm = require("node:vm");

class Element {
  constructor(tag) { this.tagName = tag; this.children = []; this.listeners = {}; }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.children = children; }
  attachShadow() { return this.shadowRoot = new Element("shadow"); }
  addEventListener(name, fn) { this.listeners[name] = fn; }
  dispatchEvent(event) { this.lastEvent = event; }
  setAttribute() {}
}

const storedTeams = new Map();
const registry = new Map();
vm.runInNewContext(fs.readFileSync("fbm-card.js", "utf8"), {
  HTMLElement: Element,
  CustomEvent: class { constructor(type, options) { Object.assign(this, options, { type }); } },
  document: { createElement(tag) { const C = registry.get(tag); return C ? new C() : new Element(tag); } },
  customElements: { get: key => registry.get(key), define: (key, value) => registry.set(key, value) },
  window: {localStorage: {getItem: key => storedTeams.get(key) ?? null}}
});

function descendants(node) {
  return [node, ...node.children.flatMap(descendants)];
}
function field(editor, label) {
  return descendants(editor.shadowRoot).find(node =>
    node.tagName === "label" && node.children[0]?.textContent === label).children[1];
}
function change(editor, label, value) {
  const control = field(editor, label);
  control.value = value;
  control.listeners.change();
}

test("existing search card edits title and retains unknown YAML and its ID", () => {
  const editor = registry.get("fbm-card").getConfigElement();
  editor.setConfig({type:"custom:fbm-card", modo_experimental:true, tipo_tarjeta:"busqueda",
    title:"Anterior", id_tarjeta:"existente", extra:{custom:true}});
  const title = field(editor, "Título");
  title.value = "Nuevo";
  title.listeners.input();
  editor.setConfig(editor.lastEvent.detail.config);
  assert.equal(field(editor, "Título"), title);
  assert.equal(editor.lastEvent.type, "config-changed");
  assert.equal(editor.lastEvent.detail.config.title, "Nuevo");
  assert.equal(editor.lastEvent.detail.config.id_tarjeta, "existente");
  assert.equal(editor.lastEvent.detail.config.extra.custom, true);
  assert.equal(editor.lastEvent.composed, true);
  title.value = "";
  title.listeners.input();
  assert.equal(Object.hasOwn(editor.lastEvent.detail.config, "title"), false);
});

test("fixed team can be created visually and selected from official search", async () => {
  const editor = registry.get("fbm-card").getConfigElement();
  editor.setConfig({type:"custom:fbm-card", modo_experimental:true, tipo_tarjeta:"busqueda"});
  change(editor, "Tipo de tarjeta", "equipo");
  const id = editor.lastEvent.detail.config.id_tarjeta;
  assert.match(id, /^fbm-equipo-/);
  editor.hass = {callWS: async request => request.type === "fbm/client/entries"
    ? {entries:["entry"]} : {equipos:[{id:"official",nombre:"Equipo A",club:"Club",categoria:"Alevín",temporada:"26/27"}]}};
  const nodes = descendants(editor.shadowRoot);
  const input = nodes.find(node => node.type === "search");
  const button = nodes.find(node => node.tagName === "button" && node.textContent === "Buscar en FBM");
  await button.listeners.click();
  assert.ok(nodes.some(node => node.textContent === "Escribe el nombre de un equipo para buscar."));
  input.value = "Equipo A";
  input.listeners.input();
  const pending = button.listeners.click();
  editor.setConfig({...editor._config, title:"Equipo elegido"});
  await pending;
  change(editor, "Equipo, categoría y temporada", "0");
  assert.equal(editor.lastEvent.detail.config.equipo_fijo.id, "official");
  assert.equal(editor.lastEvent.detail.config.id_tarjeta, id);
});

test("competition editor uses names and saves the numeric group index", () => {
  const editor = registry.get("fbm-competition-card").getConfigElement();
  editor.hass = {states:{"sensor.competiciones":{attributes:{groups:[
    {team_name:"Pinto",group_name:"Grupo 1"}, {team_name:"Getafe",group_name:"Grupo 2"}
  ]}}}};
  editor.setConfig({type:"custom:fbm-competition-card", entity:"sensor.competiciones"});
  assert.equal(field(editor, "Competición inicial").children[1].textContent, "Getafe · Grupo 2");
  change(editor, "Competición inicial", "1");
  assert.equal(editor.lastEvent.detail.config.group_index, 1);
});

test("standard editor exposes only user-facing card types and hides internal settings", () => {
  const editor = registry.get("fbm-card").getConfigElement();
  editor.setConfig({type:"custom:fbm-card", modo_experimental:true, tipo_tarjeta:"equipo",
    id_tarjeta:"keep", logo_equipo:"https://fbm.es/existing.png"});
  const mode = field(editor, "Tipo de tarjeta");
  assert.deepEqual(Array.from(mode.children, item => item.value), ["busqueda", "competicion", "equipo", "proximos", "jugador"]);
  assert.ok(!descendants(editor.shadowRoot).some(node =>
    ["URL del escudo", "Identificador de la tarjeta"].includes(node.textContent)));
  change(editor, "Título", "Mi equipo");
  assert.equal(editor.lastEvent.detail.config.id_tarjeta, "keep");
  assert.equal(editor.lastEvent.detail.config.logo_equipo, "https://fbm.es/existing.png");
});

test("following a player saves the official team and player selected in the editor", async () => {
  const card = new (registry.get("fbm-card"))();
  const editor = card.constructor.getConfigElement();
  editor.setConfig({type:"custom:fbm-card", modo_experimental:true, tipo_tarjeta:"busqueda"});
  change(editor, "Tipo de tarjeta", "jugador");
  assert.equal(field(editor, "Buscar por").value, "jugador");
  change(editor, "Buscar por", "equipo");
  const requests = [];
  const hass = {callWS: async request => {
    requests.push(request);
    if (request.type === "fbm/client/entries") return {entries:["entry"]};
    if (request.type === "fbm/team/search") return {
      equipos:[{id:"team",nombre:"Equipo A",club:"Club",categoria:"Alevín",temporada:"26/27"}]
    };
    assert.equal(request.type, "fbm/team/players");
    assert.equal(request.equipo, "team");
    return {jugadores:[{id:"p2",nombre:"Zoe"},{id:"p1",nombre:"García, Ana",partidos_jugados:5}]};
  }};
  editor.hass = hass;
  const nodes = descendants(editor.shadowRoot);
  const input = nodes.find(node => node.type === "search");
  input.value = "Equipo A";
  input.listeners.input();
  await nodes.find(node => node.textContent === "Buscar en FBM").listeners.click();
  const team = field(editor, "Equipo, categoría y temporada");
  team.value = "0";
  team.listeners.change();
  await new Promise(resolve => setImmediate(resolve));
  const name = descendants(editor.shadowRoot).find(node => node.placeholder === "Buscar en la plantilla");
  name.value = "ana garcia";
  name.listeners.input();
  assert.equal(field(editor, "Jugador").children.length, 2);
  change(editor, "Jugador", "0");
  const config = editor.lastEvent.detail.config;
  assert.equal(config.equipo_fijo.id, "team");
  assert.equal(config.jugador_fijo.id, "p1");
  assert.equal(config.jugador_fijo.nombre, "García, Ana");
  card._hass = hass;
  card._config = config;
  card._render = () => {};
  await card._loadFollowedPlayer();
  assert.equal(card._experimentalState().players.length, 1);
  assert.equal(card._experimentalState().players[0].partidos_jugados, 5);
  assert.equal(requests.filter(request => request.type === "fbm/team/players").length, 2);
});

test("unified editor exposes both competition views and keeps legacy configuration usable", () => {
  const editor = registry.get("fbm-card").getConfigElement();
  editor.setConfig({type:"custom:fbm-card", modo_experimental:true, tipo_tarjeta:"busqueda"});
  change(editor, "Tipo de tarjeta", "proximos");
  assert.equal(editor.lastEvent.detail.config.tipo_tarjeta, "proximos");
  assert.equal(field(editor, "Sensor de competiciones").value, "sensor.competiciones");
  const card = new (registry.get("fbm-card"))();
  card.setConfig(editor.lastEvent.detail.config);
  assert.equal(card._competitionView._config.initial_tab, "upcoming");
  assert.ok(registry.get("fbm-competition-card"));
});

test("name search keeps archived players even when FBM returns other results", async () => {
  const editor = registry.get("fbm-card").getConfigElement();
  editor.setConfig({type:"custom:fbm-card", modo_experimental:true, tipo_tarjeta:"jugador"});
  editor.hass = {callWS: async ({type}) => {
    if (type === "fbm/client/entries") return {entries:["entry"]};
    if (type === "fbm/player/search") return {jugadores:[
      {jugador:{id:"other",nombre:"Otro jugador"},equipo:{}},
      {jugador:{id:"local",nombre:"Jugador local"},equipo:{}}
    ]};
    assert.equal(type, "fbm/player/search_archived");
    return {jugadores:[{jugador:{id:"local",nombre:"Jugador local"},equipo:{id:"team",nombre:"Equipo"}}]};
  }};
  const nodes = descendants(editor.shadowRoot);
  const input = nodes.find(node => node.type === "search");
  input.value = "jugador";
  input.listeners.input();
  await nodes.find(node => node.textContent === "Buscar jugador").listeners.click();
  assert.equal(field(editor, "Jugador").children.length, 3);
  change(editor, "Jugador", "0");
  assert.equal(editor.lastEvent.detail.config.jugador_fijo.id, "local");
  assert.equal(editor.lastEvent.detail.config.equipo_fijo.id, "team");
});

test("name search finds a saved player on the dashboard without a federation match", async () => {
  const editor = registry.get("fbm-card").getConfigElement();
  editor.setConfig({type:"custom:fbm-card", modo_experimental:true, tipo_tarjeta:"jugador"});
  editor.hass = {callWS: async ({type}) => {
    if (type === "fbm/client/entries") return {entries:["entry"]};
    if (type === "lovelace/config") return {views:[{sections:[{cards:[{
      type:"custom:fbm-card", tipo_tarjeta:"jugador",
      jugador_fijo:{id:"player",nombre:"Pérez, Julián"}, equipo_fijo:{id:"team",nombre:"Equipo"}
    }]}]}]};
    return {jugadores:[]};
  }};
  const nodes = descendants(editor.shadowRoot);
  const input = nodes.find(node => node.type === "search");
  input.value = "julian";
  input.listeners.input();
  await nodes.find(node => node.textContent === "Buscar jugador").listeners.click();
  assert.equal(field(editor, "Jugador").children.length, 2);
  change(editor, "Jugador", "0");
  assert.equal(editor.lastEvent.detail.config.jugador_fijo.id, "player");
});

test("name search finds a player loaded by a team card in the same panel", async () => {
  const Card = registry.get("fbm-card");
  const card = new Card();
  const editor = Card.getConfigElement();
  const connection = {};
  const callWS = async ({type}) => {
    if (type === "fbm/client/entries") return {entries:["entry"]};
    if (type === "fbm/team/players") return {jugadores:[{id:"p1",nombre:"Pérez Ruiz, Julián"}]};
    return {jugadores:[]};
  };
  card._hass = {connection, callWS};
  card._render = () => {};
  Object.assign(card._experimentalState(), {entry:"entry",selected:"team",
    teams:[{id:"team",nombre:"Equipo A",temporada:"26/27"}]});
  await card._experimentalAction("players");

  editor.setConfig({type:"custom:fbm-card",modo_experimental:true,tipo_tarjeta:"jugador"});
  editor.hass = {connection, callWS};
  const nodes = descendants(editor.shadowRoot);
  const input = nodes.find(node => node.type === "search");
  input.value = "julian";
  input.listeners.input();
  await nodes.find(node => node.textContent === "Buscar jugador").listeners.click();
  assert.equal(field(editor, "Jugador").children.length, 2);
  change(editor, "Jugador", "0");
  assert.equal(editor.lastEvent.detail.config.jugador_fijo.id, "p1");
  assert.equal(editor.lastEvent.detail.config.equipo_fijo.id, "team");
});

test("name search queries a fixed team even before its roster is opened", async () => {
  const editor = registry.get("fbm-card").getConfigElement();
  editor.setConfig({type:"custom:fbm-card", modo_experimental:true, tipo_tarjeta:"jugador"});
  editor.hass = {callWS: async ({type, equipo}) => {
    if (type === "fbm/client/entries") return {entries:["entry"]};
    if (type === "lovelace/config") return {views:[{cards:[{
      type:"custom:fbm-card", tipo_tarjeta:"equipo", equipo_fijo:{id:"team",nombre:"Equipo"}
    }]}]};
    if (type === "fbm/team/players") {
      assert.equal(equipo, "team");
      return {jugadores:[{id:"p1",nombre:"Pérez Ruiz, Julián"}]};
    }
    return {jugadores:[]};
  }};
  const nodes = descendants(editor.shadowRoot);
  const input = nodes.find(node => node.type === "search");
  input.value = "julian";
  input.listeners.input();
  await nodes.find(node => node.textContent === "Buscar jugador").listeners.click();
  change(editor, "Jugador", "0");
  assert.equal(editor.lastEvent.detail.config.jugador_fijo.id, "p1");
  assert.equal(editor.lastEvent.detail.config.equipo_fijo.id, "team");
});

test("name search queries a team pinned locally by a legacy card", async () => {
  const editor = registry.get("fbm-card").getConfigElement();
  editor.setConfig({type:"custom:fbm-card", modo_experimental:true, tipo_tarjeta:"jugador"});
  storedTeams.set('fbm-card:experimental-equipo:v1:["user","legacy","entry"]',
    JSON.stringify({id:"team",nombre:"Equipo",club:"Club",categoria:"Alevín",temporada:"26/27"}));
  editor.hass = {user:{id:"user"},callWS: async ({type, equipo}) => {
    if (type === "fbm/client/entries") return {entries:["entry"]};
    if (type === "lovelace/config") return {views:[{cards:[{
      type:"custom:fbm-card", tipo_tarjeta:"equipo", id_tarjeta:"legacy"
    }]}]};
    if (type === "fbm/team/players") {
      assert.equal(equipo, "team");
      return {jugadores:[{id:"p1",nombre:"Pérez Ruiz, Julián"}]};
    }
    return {jugadores:[]};
  }};
  const nodes = descendants(editor.shadowRoot);
  const input = nodes.find(node => node.type === "search");
  input.value = "julian";
  input.listeners.input();
  await nodes.find(node => node.textContent === "Buscar jugador").listeners.click();
  change(editor, "Jugador", "0");
  assert.equal(editor.lastEvent.detail.config.jugador_fijo.id, "p1");
  assert.equal(editor.lastEvent.detail.config.equipo_fijo.id, "team");
});

test("following a player uses the player's name as the title placeholder", () => {
  const editor = registry.get("fbm-card").getConfigElement();
  const config = {type:"custom:fbm-card", modo_experimental:true, tipo_tarjeta:"jugador",
    jugador_fijo:{id:"p1", nombre:"PÉREZ RUIZ, JULIÁN"}, title:"FBM Card"};
  editor.setConfig(config);
  assert.equal(field(editor, "Título").value, "");
  assert.equal(field(editor, "Título").placeholder, config.jugador_fijo.nombre);
  editor.setConfig({...config, title:"Mi jugador"});
  assert.equal(field(editor, "Título").value, "Mi jugador");
});
