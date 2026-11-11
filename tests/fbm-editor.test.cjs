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

const registry = new Map();
vm.runInNewContext(fs.readFileSync("fbm-card.js", "utf8"), {
  HTMLElement: Element,
  CustomEvent: class { constructor(type, options) { Object.assign(this, options, { type }); } },
  document: { createElement(tag) { const C = registry.get(tag); return C ? new C() : new Element(tag); } },
  customElements: { get: key => registry.get(key), define: (key, value) => registry.set(key, value) },
  window: {}
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
  change(editor, "Título", "Nuevo");
  assert.equal(editor.lastEvent.type, "config-changed");
  assert.equal(editor.lastEvent.detail.config.title, "Nuevo");
  assert.equal(editor.lastEvent.detail.config.id_tarjeta, "existente");
  assert.equal(editor.lastEvent.detail.config.extra.custom, true);
  assert.equal(editor.lastEvent.composed, true);
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
  nodes.find(node => node.type === "search").value = "Equipo A";
  await nodes.find(node => node.tagName === "button" && node.textContent === "Buscar equipo").listeners.click();
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
