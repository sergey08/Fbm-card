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

test("modo experimental consulta estado y no registra automaticamente", async () => {
  const { elements } = loadCard();
  const card = new (elements.get("fbm-card"))();
  const calls = [];
  card._config = { modo_experimental: true };
  card._render = () => {};
  card._hass = { callWS: async msg => {
    calls.push(msg.type);
    if (msg.type === "fbm/client/entries") return { entries: ["entry"] };
    if (msg.type === "fbm/client/status") return { identidad_creada: false, candidato_guardado: false, sesion_en_memoria: false };
    throw new Error("unexpected");
  } };
  card._experimentalState();
  assert.equal(calls.length, 0);
  await card._experimentalAction("status");
  assert.deepEqual(calls, ["fbm/client/entries", "fbm/client/status"]);
  assert.equal(card._experimentalState().status.identidad_creada, false);
});

test("modo experimental busca y consulta solo el equipo seleccionado", async () => {
  const { elements } = loadCard();
  const card = new (elements.get("fbm-card"))();
  const calls = [];
  card._config = { modo_experimental: true };
  card._render = () => {};
  card._hass = { callWS: async msg => {
    calls.push(msg);
    if (msg.type === "fbm/team/search") return { equipos: [{ id: "opaque", nombre: "A", club: "C", categoria: "Cat", temporada: "26/27" }] };
    if (msg.type === "fbm/team/phases") return { nombre_fase: "Fase", rondas: [] };
    if (msg.type === "fbm/team/schedule") return { partidos: [] };
    throw new Error("unexpected");
  } };
  const state = card._experimentalState();
  state.entry = "entry"; state.query = "Equipo"; state.start = "2026-11-01"; state.end = "2026-12-31";
  await card._experimentalAction("search");
  assert.equal(state.teams[0].id, "opaque");
  assert.equal(state.selected, "");
  state.selected = "opaque";
  await card._experimentalAction("phases");
  await card._experimentalAction("schedule");
  assert.equal(calls[2].type, "fbm/team/schedule");
  assert.equal(calls[2].equipo, "opaque");
});

test("una ronda requiere selección explícita antes de consultar horarios", async () => {
  const { elements } = loadCard();
  const card = new (elements.get("fbm-card"))();
  const calls = [];
  card._config = { modo_experimental: true }; card._render = () => {};
  card._hass = { callWS: async msg => { calls.push(msg); return msg.type === "fbm/team/phases" ? { nombre_fase: "Final", rondas: [{ id: "r", nombre: "Final" }] } : { partidos: [] }; } };
  const state = card._experimentalState();
  state.entry = "entry"; state.selected = "team"; state.start = "2026-11-01"; state.end = "2026-12-31";
  await card._experimentalAction("phases");
  await card._experimentalAction("schedule");
  assert.equal(calls.length, 1);
  state.round = "r";
  await card._experimentalAction("schedule");
  assert.equal(calls[1].type, "fbm/team/schedule_round");
  assert.equal(calls[1].ronda, "r");
});

test("error de registro avisa de posible procesamiento sin reintentar", async () => {
  const { elements } = loadCard();
  const card = new (elements.get("fbm-card"))();
  card._config = { modo_experimental: true }; card._render = () => {};
  let calls = 0;
  card._hass = { callWS: async () => { calls++; throw new Error("private"); } };
  const state = card._experimentalState(); state.entry = "entry";
  await card._experimentalAction("register");
  assert.equal(calls, 1);
  assert.match(state.message, /podría haberlo procesado/);
  assert.doesNotMatch(state.message, /private/);
});

test("tarjeta experimental no hace peticiones al mostrarse y requiere pulsar estado", async () => {
  const { elements, sandbox } = loadCard();
  class Element {
    constructor(tag) { this.tag = tag; this.children = []; this.listeners = {}; this.textContent = ""; }
    append(...children) { this.children.push(...children); }
    addEventListener(name, callback) { this.listeners[name] = callback; }
    setAttribute() {}
  }
  sandbox.document = { createElement: tag => new Element(tag) };
  const card = new (elements.get("fbm-card"))();
  card.attachShadow = () => { card.shadowRoot = { replaceChildren: (...items) => { card.shadowRoot.items = items; } }; };
  const calls = [];
  card.setConfig({ modo_experimental: true });
  card.hass = { callWS: async msg => {
    calls.push(msg.type);
    return msg.type === "fbm/client/entries" ? { entries: ["entry"] } : { identidad_creada: false, candidato_guardado: false, sesion_en_memoria: false };
  } };
  assert.equal(calls.length, 0);
  const checkButton = card.shadowRoot.items[1].children.find(el => el.textContent === "Comprobar estado");
  await checkButton.listeners.click();
  assert.deepEqual(calls, ["fbm/client/entries", "fbm/client/status"]);
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
    fuente: "FBM",
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
  assert.match(card._data().error, /fuente oficial/);
});

test("la configuración inicial no impone Pintobasket", () => {
  const { elements } = loadCard();
  assert.equal(elements.get("fbm-card").getStubConfig().equipos.length, 0);
});
test("admite varios equipos y selecciona el primero si no hay preferencia", () => {
  const { elements } = loadCard();
  const card = new (elements.get("fbm-card"))();
  card._config = { equipos: [
    { nombre: "Equipo A", entidad_datos: "sensor.fbm_a" },
    { nombre: "Equipo B", entidad_datos: "sensor.fbm_b" }
  ] };
  assert.equal(card._teams().length, 2);
  assert.equal(card._selectedTeam().nombre, "Equipo A");
});
test("sin identidad de usuario no crea clave de preferencias compartidas", () => {
  const { elements } = loadCard();
  const card = new (elements.get("fbm-card"))();
  card._config = {};
  assert.equal(card._storageKey(), null);
});

test("sin usuario no se guardan favoritos", () => {
  const { elements } = loadCard();
  const card = new (elements.get("fbm-card"))();
  card._config = { equipos: [{ nombre: "A", entidad_datos: "sensor.a" }] };
  assert.equal(card._favoriteKey(), null);
  assert.deepEqual(Array.from(card._favorites()), []);
  card._toggleFavorite("sensor.a");
});
test("los favoritos se separan por identificador de usuario y tarjeta", () => {
  const { elements } = loadCard();
  const card = new (elements.get("fbm-card"))();
  card._config = { id_tarjeta: "mis_equipos" };
  card._hass = { user: { id: "usuario-1" } };
  assert.match(card._favoriteKey(), /usuario-1:mis_equipos$/);
  card._hass = { user: { id: "usuario-2" } };
  assert.match(card._favoriteKey(), /usuario-2:mis_equipos$/);
});

test("rechaza resultados de entidades sin procedencia FBM declarada", () => {
  const { elements } = loadCard();
  const card = new (elements.get("fbm-card"))();
  card._config = { entidad_datos: "sensor.terceros" };
  card._hass = { states: { "sensor.terceros": { state: "ok", attributes: {
    partidos: [], clasificacion: [], fuente: "TERCEROS"
  } } } };
  assert.match(card._data().error, /Datos rechazados/);
});
test("rechaza estructuras incompletas aunque declaren FBM", () => {
  const { elements } = loadCard();
  const card = new (elements.get("fbm-card"))();
  card._config = { entidad_datos: "sensor.fbm" };
  card._hass = { states: { "sensor.fbm": { state: "ok", attributes: {
    fuente: "FBM", partidos: []
  } } } };
  assert.match(card._data().error, /formato esperado/);
});

test("descubre únicamente sensores con estructura FBM válida", () => {
  const { elements } = loadCard();
  const card = new (elements.get("fbm-card"))();
  card._config = {};
  card._hass = { states: {
    "sensor.fbm_a": { state: "ok", attributes: { friendly_name: "Equipo A", fbm: { fuente: "FBM", partidos: [], clasificacion: [] } } },
    "sensor.tercero": { state: "ok", attributes: { fuente: "TERCEROS", partidos: [], clasificacion: [] } },
    "sensor.fbm_incompleto": { state: "ok", attributes: { fuente: "FBM", partidos: [] } }
  } };
  assert.equal(card._availableOfficialEntities().length, 1);
  assert.equal(card._availableOfficialEntities()[0].entidad_datos, "sensor.fbm_a");
});

test("el descubrimiento automático es opcional y utiliza solo sensores declarados FBM", () => {
  const { elements } = loadCard();
  const card = new (elements.get("fbm-card"))();
  card._config = { descubrir_entidades: true };
  card._hass = { states: {
    "sensor.fbm_a": { state: "ok", attributes: { friendly_name: "A", fbm: { fuente: "FBM", partidos: [], clasificacion: [] } } },
    "sensor.otro": { state: "ok", attributes: { friendly_name: "Otro", fuente: "OTRO", partidos: [], clasificacion: [] } }
  } };
  assert.equal(card._teams().length, 1);
  assert.equal(card._selectedTeam().entidad_datos, "sensor.fbm_a");
  card._config = { descubrir_entidades: false };
  assert.equal(card._teams().length, 0);
});

test("descubre sensores incluso si la configuración inicial contiene equipos vacíos", () => {
  const { elements } = loadCard();
  const card = new (elements.get("fbm-card"))();
  card._config = { equipos: [], descubrir_entidades: true };
  card._hass = { states: {
    "sensor.fbm": { state: "ok", attributes: { fuente: "FBM", partidos: [], clasificacion: [] } }
  } };
  assert.equal(card._teams().length, 1);
});
test("no ofrece sensores FBM no disponibles", () => {
  const { elements } = loadCard();
  const card = new (elements.get("fbm-card"))();
  card._config = { descubrir_entidades: true };
  card._hass = { states: {
    "sensor.fbm_caido": { state: "unavailable", attributes: { fuente: "FBM", partidos: [], clasificacion: [] } }
  } };
  assert.equal(card._teams().length, 0);
});
