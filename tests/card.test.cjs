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

test("el campo de búsqueda conserva foco y texto cuando Home Assistant actualiza hass", () => {
  const { elements } = loadCard();
  const card = new (elements.get("fbm-card"))();
  card._config = { modo_experimental: true };
  let renders = 0;
  card._render = () => { renders++; };
  card._experimental = { query: "Pinto", status: { identidad_creada: true } };
  const initial = { user: { id: "user-1" }, callWS: async () => ({}) };
  card.hass = initial;
  assert.equal(renders, 1);
  card.hass = { user: { id: "user-1" }, callWS: async () => ({}) };
  assert.equal(renders, 1, "una actualización de hass no debe sustituir el DOM activo");
  assert.equal(card._experimental.query, "Pinto");
  card.hass = { user: { id: "user-2" }, callWS: async () => ({}) };
  assert.equal(renders, 2, "el cambio de usuario sí obliga a reconstruir");
  assert.equal(card._experimental, null);
});

test("equipo seleccionado en buscador se comparte con tarjeta fija del mismo usuario", () => {
  const {elements,sandbox} = loadCard();
  const memory = new Map();
  sandbox.window.localStorage = {
    getItem:key=>memory.get(key)??null,
    setItem:(key,val)=>memory.set(key,val)
  };
  const Card = elements.get("fbm-card");
  const team = {id:"deportivo",nombre:"Pinto",club:"Club",categoria:"Alevín",temporada:"26/27"};
  const search = new Card();
  search._config = {tipo_tarjeta:"busqueda",id_tarjeta:"buscador"};
  search._hass = {user:{id:"usuario-a"}};
  search._saveRecentTeam("entry-a",team);
  const fixed = new Card();
  fixed._config = {tipo_tarjeta:"equipo",id_tarjeta:"equipo-fijo"};
  fixed._hass = {user:{id:"usuario-a"}};
  assert.equal(fixed._restoreRecentTeam("entry-a").id,team.id);
  assert.equal(fixed._restoreRecentTeam("entry-b"),null);
  fixed._hass = {user:{id:"usuario-b"}};
  assert.equal(fixed._restoreRecentTeam("entry-a"),null);
});

test("favoritos experimentales múltiples se comparten con tarjetas fijas del mismo usuario", () => {
  const {elements,sandbox} = loadCard();
  const memory = new Map();
  sandbox.window.localStorage = {
    getItem:key=>memory.get(key)??null,
    setItem:(key,value)=>memory.set(key,value),
    removeItem:key=>memory.delete(key)
  };
  const Card=elements.get("fbm-card");
  const search=new Card();
  search._config={modo_experimental:true,tipo_tarjeta:"busqueda",id_tarjeta:"buscar"};
  search._hass={user:{id:"user-a"}};
  const a={id:"id-a",nombre:"Equipo A",club:"Club A",categoria:"Alevín",temporada:"26/27"};
  const b={id:"id-b",nombre:"Equipo B",club:"Club B",categoria:"Infantil",temporada:"26/27"};
  assert.equal(search._toggleExperimentalFavorite("entry",a),true);
  assert.equal(search._toggleExperimentalFavorite("entry",b),true);
  assert.equal(search._experimentalFavorites("entry").length,2);
  assert.equal(search._toggleExperimentalFavorite("entry",a),true);
  assert.equal(search._experimentalFavorites("entry")[0].id,"id-b");
  const fixed=new Card();
  fixed._config={modo_experimental:true,tipo_tarjeta:"equipo",id_tarjeta:"fijo-1"};
  fixed._hass={user:{id:"user-a"}};
  assert.equal(fixed._experimentalFavorites("entry").length,1);
  fixed._saveExperimentalTeam("entry",b);
  const another=new Card();
  another._config={modo_experimental:true,tipo_tarjeta:"equipo",id_tarjeta:"fijo-2"};
  another._hass={user:{id:"user-a"}};
  assert.equal(another._restoreExperimentalTeam("entry"),null);
  assert.equal(another._experimentalFavorites("entry")[0].id,"id-b");
  another._hass={user:{id:"user-b"}};
  assert.equal(another._experimentalFavorites("entry").length,0);
  assert.equal(another._restoreExperimentalTeam("entry"),null);
});

test("los favoritos no contienen claves privadas ni aceptan equipos inválidos", () => {
  const {elements,sandbox}=loadCard();
  const memory=new Map();
  sandbox.window.localStorage={getItem:key=>memory.get(key)??null,setItem:(key,val)=>memory.set(key,val)};
  const card=new (elements.get("fbm-card"))();
  card._config={tipo_tarjeta:"busqueda"};
  card._hass={user:{id:"user-a"}};
  const team={id:"id-a",nombre:"Equipo A",club:"C",categoria:"Alevín",temporada:"26/27",key:"privada",uid:"secreto"};
  assert.equal(card._toggleExperimentalFavorite("entry",team),true);
  assert.doesNotMatch([...memory.values()].join(" "),/privada|secreto|uid/);
  assert.equal(card._toggleExperimentalFavorite("entry",{id:"x"}),false);
  assert.equal(card._experimentalFavorites("entry").length,1);
});

test("buscador genera configuración portable de equipo fijo sin credenciales", () => {
  const {elements} = loadCard();
  const card = new (elements.get("fbm-card"))();
  card._config = {tipo_tarjeta:"busqueda",modo_experimental:true};
  const team = {id:"deporte123",nombre:"Pintobasket",club:"Club",categoria:"Alevín",temporada:"26/27"};
  const yaml=card._fixedCardYaml(team);
  assert.match(yaml,/tipo_tarjeta: equipo/);
  assert.match(yaml,/equipo_fijo:/);
  assert.match(yaml,/Pintobasket/);
  const another = {...team,id:"deporte123-otro"};
  const yaml2=card._fixedCardYaml(another);
  const extract = y => y.match(/^id_tarjeta:.*$/m)?.[0];
  assert.notEqual(extract(yaml), extract(yaml2), "dos favoritos no deben compartir id_tarjeta");

  assert.doesNotMatch(yaml,/api.key|dispositivo|uid/i);
  const fixed = new (elements.get("fbm-card"))();
  fixed._config={tipo_tarjeta:"equipo",modo_experimental:true,equipo_fijo:team};
  fixed._hass={user:{id:"otro-usuario"}};
  assert.equal(fixed._restoreExperimentalTeam("entrada").id,team.id);
  assert.equal(fixed._restoreExperimentalTeam("entrada").categoria,"Alevín");
});

test("cada copia de un favorito crea una tarjeta con identificador independiente", () => {
  const {elements} = loadCard();
  const card = new (elements.get("fbm-card"))();
  card._config={tipo_tarjeta:"busqueda",modo_experimental:true};
  const team={id:"equipo-uno",nombre:"Pinto",club:"Club",categoria:"Alevín",temporada:"26/27"};
  const first=card._fixedCardYaml(team);
  const second=card._fixedCardYaml(team);
  const id = yaml => yaml.match(/^id_tarjeta:\s*(.+)$/m)?.[1];
  assert.ok(id(first));
  assert.notEqual(id(first),id(second));
  assert.match(first,/tipo_tarjeta: equipo/);
  assert.match(second,/equipo_fijo:/);
});

test("cambiar configuración fija invalida estado y no mezcla clasificaciones", () => {
  const {elements}=loadCard();
  const Card=elements.get("fbm-card");
  const card=new Card();
  card._render=()=>{};
  const a={id:"uno",nombre:"A",club:"C",categoria:"Alevín",temporada:"26/27"};
  const b={...a,id:"dos",nombre:"B"};
  card.setConfig({modo_experimental:true,tipo_tarjeta:"equipo",id_tarjeta:"tarjeta-unica",equipo_fijo:a});
  card._experimentalState().standings=[{equipo:"A",posicion:1}];
  card._fixedInit=true;
  card.setConfig({modo_experimental:true,tipo_tarjeta:"equipo",id_tarjeta:"tarjeta-unica",equipo_fijo:b});
  assert.equal(card._experimentalState().standings,null);
  assert.equal(card._restoreExperimentalTeam("entrada").id,"dos");
  assert.equal(card._fixedInit,false);
  assert.throws(()=>card.setConfig({modo_experimental:true,tipo_tarjeta:"equipo"}),/id_tarjeta distinto/);
});

test("las pestañas de un equipo son independientes y no filtran partidos de grupo", () => {
  const {elements,sandbox}=loadCard();
  class Elem {
    constructor(tag) {this.tag=tag;this.children=[];this.listeners={};this.textContent="";}
    append(...items){this.children.push(...items);}
    addEventListener(type,handler){this.listeners[type]=handler;}
    setAttribute(key,value){this[key]=value;}
  }
  sandbox.document={createElement:tag=>new Elem(tag)};
  const Team=elements.get("fbm-card");
  const make=(id,tab)=>{
    const card=new Team();
    card._config={modo_experimental:true,tipo_tarjeta:"equipo",id_tarjeta:id};
    card._hass={user:{id:"u"},callWS:async()=>({})};
    card._render=()=>{};
    const state=card._experimentalState();
    state.entry="entry";state.status={sesion_vigente:true};state.tab=tab;
    state.teams=[{id:"a",nombre:"A",club:"C",categoria:"Alv",temporada:"26/27"}];
    state.selected="a";state.standings=[{posicion:1,equipo:"A"}];
    card._restoreExperimentalTeam=()=>state.teams[0];
    return card;
  };
  const cardA=make("gael","clasificacion");
  const cardB=make("zoe","partidos");
  const flatten=el=>[el,...(el.children||[]).flatMap(flatten)];
  const a=new Elem("card"),b=new Elem("card");
  cardA._renderExperimental(a);
  cardB._renderExperimental(b);
  assert.ok(flatten(a).some(el=>el.textContent==="Clasificación del grupo actual"));
  assert.ok(!flatten(b).some(el=>el.textContent==="Clasificación del grupo actual"));
  assert.ok(flatten(b).some(el=>el.textContent==="Consultar fases oficiales"));
  const buttons=flatten(b).filter(el=>el.tag==="button");
  const players=buttons.find(el=>el.textContent==="Jugadores");
  players.listeners.click();
  assert.equal(cardB._experimentalState().tab,"jugadores");
  assert.equal(cardA._experimentalState().tab,"clasificacion");
});

test("escudos solo de dominios oficiales HTTPS", () => {
  const {elements,sandbox}=loadCard();
  sandbox.URL=URL;
  const card=new (elements.get("fbm-card"))();
  assert.equal(card._officialLogoUrl("http://fbm.es/logo.png"),"");
  assert.equal(card._officialLogoUrl("https://example.com/logo.png"),"");
  assert.equal(card._officialLogoUrl("https://fbm.es/escudo.png"),"https://fbm.es/escudo.png");
});

test("tarjeta fija guarda equipo separado por tarjeta y recupera clasificación al abrir", async () => {
  const { elements, sandbox } = loadCard();
  const store = new Map();
  sandbox.window.localStorage = {
    getItem: key => store.get(key) ?? null,
    setItem: (key, value) => store.set(key, value),
    removeItem: key => store.delete(key),
  };
  const Card = elements.get("fbm-card");
  const card = new Card();
  card._config = {modo_experimental:true,tipo_tarjeta:"equipo",id_tarjeta:"equipo-a"};
  card._hass = {user:{id:"usuario"},callWS:async msg => {
    if (msg.type === "fbm/client/entries") return {entries:["entrada"]};
    if (msg.type === "fbm/client/status") return {identidad_creada:true,candidato_guardado:true,sesion_vigente:true};
    if (msg.type === "fbm/team/standings") return {clasificacion:[{equipo:"A",posicion:1}]};
    throw Error("Petición inesperada");
  }};
  card._render = () => {};
  const state = card._experimentalState();
  const team = {id:"equipo-id",nombre:"A",club:"C",categoria:"Infantil",temporada:"26/27"};
  state.entry = "entrada"; state.status = {sesion_vigente:true}; state.teams=[team];state.selected=team.id;
  await card._experimentalAction("fix_team");
  assert.equal(card._restoreExperimentalTeam("entrada").id,team.id);
  assert.equal(state.standings[0].posicion,1);
  const separate = new Card();
  separate._config={modo_experimental:true,tipo_tarjeta:"equipo",id_tarjeta:"equipo-b"};
  separate._hass=card._hass;
  assert.equal(separate._restoreExperimentalTeam("entrada"),null);
  const loaded = new Card();
  loaded._config=card._config;loaded._hass=card._hass;loaded._render=()=>{};
  await loaded._initializeFixed();
  assert.equal(loaded._experimentalState().selected,team.id);
  assert.equal(loaded._experimentalState().standings[0].posicion,1);
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

test("selección experimental se separa por usuario, tarjeta e integración y omite secretos", () => {
  const { elements, sandbox } = loadCard();
  const memory = new Map();
  sandbox.window.localStorage = { getItem: key => memory.get(key) ?? null,
    setItem: (key, value) => memory.set(key, value), removeItem: key => memory.delete(key) };
  const card = new (elements.get("fbm-card"))();
  card._config = { id_tarjeta: "card-a" }; card._hass = { user: { id: "user-a" } };
  const team = { id: "sport-id", nombre: "Equipo", club: "Club", categoria: "Cat", temporada: "26/27", key: "secret" };
  card._saveExperimentalTeam("entry-a", team);
  const key = card._experimentalPreferenceKey("entry-a");
  assert.doesNotMatch(memory.get(key), /secret|"key"/);
  assert.equal(card._restoreExperimentalTeam("entry-a").id, "sport-id");
  assert.equal(card._restoreExperimentalTeam("entry-b"), null);
  card._hass = { user: { id: "user-b" } };
  assert.equal(card._restoreExperimentalTeam("entry-a"), null);
  card._hass = { user: { id: "user-a" } }; card._config.id_tarjeta = "card-b";
  assert.equal(card._restoreExperimentalTeam("entry-a"), null);
  card._config.id_tarjeta = "card-a"; card._clearExperimentalTeam("entry-a");
  assert.equal(card._restoreExperimentalTeam("entry-a"), null);
});

test("restaurar selección no inicia búsquedas ni conexiones FBM", async () => {
  const { elements, sandbox } = loadCard();
  const memory = new Map();
  sandbox.window.localStorage = { getItem: key => memory.get(key) ?? null, setItem: (key, value) => memory.set(key, value) };
  const card = new (elements.get("fbm-card"))();
  card._config = { modo_experimental: true }; card._render = () => {};
  const calls = [];
  card._hass = { user: { id: "user" }, callWS: async msg => {
    calls.push(msg.type);
    if (msg.type === "fbm/client/entries") return { entries: ["entry"] };
    if (msg.type === "fbm/client/status") return { identidad_creada: true, candidato_guardado: true, sesion_en_memoria: false };
    throw new Error("unexpected network request");
  } };
  card._saveExperimentalTeam("entry", { id: "a", nombre: "Equipo", club: "Club", categoria: "Cat", temporada: "26/27" });
  await card._experimentalAction("status");
  assert.equal(card._experimentalState().selected, "a");
  assert.deepEqual(calls, ["fbm/client/entries", "fbm/client/status"]);
});

test("cambio de usuario descarta el estado experimental en memoria", () => {
  const { elements } = loadCard();
  const card = new (elements.get("fbm-card"))(); card._render = () => {};
  card.hass = { user: { id: "user-a" } };
  card._experimentalState().selected = "private-selection";
  card.hass = { user: { id: "user-b" } };
  assert.equal(card._experimentalState().selected, "");
});

test("selecciones corruptas o sin usuario no se restauran", () => {
  const { elements, sandbox } = loadCard();
  sandbox.window.localStorage = { getItem: () => '{"id":"x"}', setItem: () => { throw new Error("blocked"); } };
  const card = new (elements.get("fbm-card"))(); card._config = {}; card._hass = { user: { id: "user" } };
  assert.equal(card._restoreExperimentalTeam("entry"), null);
  card._hass = {};
  assert.equal(card._experimentalPreferenceKey("entry"), null);
});

test("modo experimental busca y consulta solo el equipo seleccionado", async () => {
  const { elements } = loadCard();
  const card = new (elements.get("fbm-card"))();
  const calls = [];
  card._config = { modo_experimental: true, mostrar_horarios: true };
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
  card._config = { modo_experimental: true, mostrar_horarios: true }; card._render = () => {};
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

test("muestra el equipo por nombre o el grupo completo sin hacer peticiones", () => {
  const { elements } = loadCard();
  const card = new (elements.get("fbm-card"))();
  card._render = () => {};
  let calls = 0; card._hass = { callWS: async () => { calls++; } };
  const state = card._experimentalState();
  state.teams = [{ id: "team", nombre: "Equipo A" }]; state.selected = "team";
  state.schedule = { partidos: [
    { local: "Equipo A", visitante: "B" }, { local: "C", visitante: "equipo a" },
    { local: "Equipo AA", visitante: "D" }
  ] };
  assert.equal(card._experimentalMatches().length, 2);
  card._toggleExperimentalGroup();
  assert.equal(card._experimentalMatches().length, 3);
  card._toggleExperimentalGroup();
  assert.equal(card._experimentalMatches().length, 2);
  assert.equal(calls, 0);
});

test("sin equipo coincidente no atribuye partidos a otro equipo", () => {
  const { elements } = loadCard();
  const card = new (elements.get("fbm-card"))();
  const state = card._experimentalState();
  state.selected = "missing"; state.teams = [];
  state.schedule = { partidos: [{ local: "A", visitante: "B" }] };
  assert.equal(card._experimentalMatches().length, 0);
});

test("la tarjeta conserva fecha, hora y marcador tal como se recibieron", () => {
  const { elements, sandbox } = loadCard();
  class Element {
    constructor(tag) { this.tag = tag; this.children = []; this.listeners = {}; this.textContent = ""; }
    append(...children) { this.children.push(...children); }
    addEventListener(name, callback) { this.listeners[name] = callback; }
    setAttribute() {}
  }
  sandbox.document = { createElement: tag => new Element(tag) };
  const card = new (elements.get("fbm-card"))();
  card._config = { modo_experimental: true, mostrar_horarios: true };
  const state = card._experimentalState();
  state.status = { identidad_creada: true, candidato_guardado: true, sesion_en_memoria: true };
  state.teams = [{ id: "a", nombre: "A", club: "C", categoria: "Cat", temporada: "26/27" }];
  state.selected = "a"; state.schedule = { partidos: [{ local: "A", visitante: "B", fecha: "07/11/2026", hora: "00:00:00", marcador: { local: 32, visitante: 57 } }] };
  const parent = new Element("card"); card._renderExperimental(parent);
  const row = parent.children.find(el => el.className === "row");
  assert.equal(row.children[0].children[0].textContent, "07/11/2026 00:00:00");
  assert.equal(row.children[1].textContent, "32–57");
});

test("v0.1 oculta los horarios por defecto incluso si existen resultados previos", async () => {
  const { elements, sandbox } = loadCard();
  class Element {
    constructor(tag) { this.tag = tag; this.children = []; this.listeners = {}; this.textContent = ""; }
    append(...children) { this.children.push(...children); }
    addEventListener(name, callback) { this.listeners[name] = callback; }
    setAttribute() {}
  }
  sandbox.document = { createElement: tag => new Element(tag) };
  const card = new (elements.get("fbm-card"))();
  card._config = { modo_experimental: true };
  const state = card._experimentalState();
  state.status = { identidad_creada: true, candidato_guardado: true, sesion_en_memoria: true, sesion_vigente: true };
  state.teams = [{ id: "a", nombre: "A", club: "C", categoria: "Cat", temporada: "26/27" }];
  state.selected = "a"; state.rounds = [];
  state.schedule = { partidos: [{ local: "A", visitante: "B" }] };
  const cardElement = new Element("card"); card._renderExperimental(cardElement);
  const flatten = el => [el, ...(el.children || []).flatMap(flatten)];
  const texts = flatten(cardElement).map(el => String(el.textContent));
  assert.ok(!texts.some(text => /Consultar horarios|Partidos del equipo|Partidos del grupo/.test(text)));
  card._render = () => {};
  let called = false;
  card._hass = { callWS: async () => { called = true; return {}; } };
  state.entry = "entry"; state.start = "2026-11-01"; state.end = "2026-11-30";
  await card._experimentalAction("schedule");
  assert.equal(called, false);
});

test("la clasificación se solicita solo al pulsar y conserva los datos del servidor", async () => {
  const { elements } = loadCard();
  const card = new (elements.get("fbm-card"))();
  card._config = { modo_experimental: true }; card._render = () => {};
  const calls = [];
  card._hass = { callWS: async msg => { calls.push(msg); return { clasificacion: [
    { id: "id", equipo: "Equipo", posicion: 2, jugados: 4, ganados: 3, perdidos: 1, puntos: 7 }
  ] }; } };
  const state = card._experimentalState(); state.entry = "entry"; state.selected = "team";
  assert.equal(calls.length, 0);
  await card._experimentalAction("standings");
  assert.equal(calls[0].type, "fbm/team/standings");
  assert.equal(calls[0].equipo, "team");
  assert.equal(state.standings[0].puntos, 7);
});

test("error de registro avisa de posible procesamiento sin reintentar", async () => {
  const { elements } = loadCard();
  const card = new (elements.get("fbm-card"))();
  card._config = { modo_experimental: true }; card._render = () => {};
  const calls = [];
  card._hass = { callWS: async msg => {
    calls.push(msg.type);
    if (msg.type === "fbm/client/status") return { identidad_creada: true, candidato_guardado: false, registro_pendiente: true };
    throw new Error("private");
  } };
  const state = card._experimentalState(); state.entry = "entry";
  await card._experimentalAction("register");
  assert.deepEqual(calls, ["fbm/client/register", "fbm/client/status"]);
  assert.equal(state.status.registro_pendiente, true);
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

test("registro pendiente bloquea alta normal y exige recuperación explícita", async () => {
  const { elements, sandbox } = loadCard();
  class Element {
    constructor(tag) { this.tag = tag; this.children = []; this.listeners = {}; this.textContent = ""; }
    append(...children) { this.children.push(...children); }
    addEventListener(name, callback) { this.listeners[name] = callback; }
    setAttribute() {}
  }
  sandbox.document = { createElement: tag => new Element(tag) };
  const card = new (elements.get("fbm-card"))();
  card._config = { modo_experimental: true }; card._render = () => {};
  const calls = [];
  card._hass = { callWS: async msg => {
    calls.push(msg.type);
    return msg.type === "fbm/client/status" ? { identidad_creada: true, candidato_guardado: true, registro_pendiente: false } : {};
  } };
  const state = card._experimentalState();
  state.entry = "entry"; state.status = { identidad_creada: true, candidato_guardado: false, registro_pendiente: true, sesion_en_memoria: false };
  const parent = new Element("card"); card._renderExperimental(parent);
  const register = parent.children.find(el => el.textContent === "Registrar dispositivo en FBM");
  const recover = parent.children.find(el => el.textContent === "Recuperar registro pendiente");
  assert.equal(register, undefined);
  assert.equal(calls.length, 0);
  await recover.listeners.click();
  assert.deepEqual(calls, ["fbm/client/recover_registration", "fbm/client/status"]);
});

test("una sesión caducada muestra reconexión y bloquea búsquedas", () => {
  const { elements, sandbox } = loadCard();
  class Element {
    constructor(tag) { this.tag = tag; this.children = []; this.listeners = {}; this.textContent = ""; }
    append(...children) { this.children.push(...children); }
    addEventListener(name, callback) { this.listeners[name] = callback; }
    setAttribute() {}
  }
  sandbox.document = { createElement: tag => new Element(tag) };
  const card = new (elements.get("fbm-card"))(); card._config = { modo_experimental: true };
  const state = card._experimentalState();
  state.status = { identidad_creada: true, candidato_guardado: true, sesion_en_memoria: true, sesion_vigente: false };
  const parent = new Element("card"); card._renderExperimental(parent);
  assert.equal(parent.children.find(el => el.textContent === "Buscar").disabled, true);
  assert.ok(parent.children.some(el => el.textContent.includes("necesita reconexión")));
});

test("una nueva conexión borra resultados previos sin consultar datos", async () => {
  const { elements } = loadCard();
  const card = new (elements.get("fbm-card"))(); card._config = {}; card._render = () => {};
  const calls = [];
  card._hass = { callWS: async msg => { calls.push(msg.type); return msg.type === "fbm/client/status" ? { sesion_vigente: true } : {}; } };
  const state = card._experimentalState(); state.entry = "entry";
  state.schedule = { partidos: [{ local: "old", visitante: "old" }] }; state.standings = [{ equipo: "old" }]; state.rounds = [{ id: "old" }];
  await card._experimentalAction("connect");
  assert.equal(state.schedule, null); assert.equal(state.standings, null); assert.equal(state.rounds, null);
  assert.deepEqual(calls, ["fbm/client/connect", "fbm/client/status"]);
});

test("si falla la comprobación posterior se bloquea el registro en la tarjeta", async () => {
  const { elements } = loadCard();
  const card = new (elements.get("fbm-card"))();
  card._config = { modo_experimental: true }; card._render = () => {};
  card._hass = { callWS: async () => { throw new Error("failure"); } };
  const state = card._experimentalState();
  state.entry = "entry"; state.status = { identidad_creada: true, candidato_guardado: false };
  await card._experimentalAction("register");
  assert.equal(state.status.registro_pendiente, true);
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
