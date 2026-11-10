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
  assert.ok(flatten(b).some(el=>el.textContent==="Actualizar partidos"));
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

test("el campo Escudo construye la URL oficial sin inyectar parámetros", () => {
  const {elements}=loadCard(); const card=new (elements.get("fbm-card"))();
  assert.equal(card._apkCrestUrl("abc&x=otro"), "https://appaficionfbm.gesdeportiva.es/imagenes.ashx?tipo=escudo&id=abc%26x%3Dotro");
  for (const invalid of [null, "", "  ", "a\n", "x".repeat(1025)]) assert.equal(card._apkCrestUrl(invalid), "");
});

test("un favorito conserva el escudo oficial sin datos ajenos", () => {
  const {elements,sandbox}=loadCard(); const data=new Map();
  sandbox.window.localStorage={getItem:k=>data.get(k)??null,setItem:(k,v)=>data.set(k,v)};
  const card=new (elements.get("fbm-card"))(); card._hass={user:{id:"u"}};
  card._config={tipo_tarjeta:"equipo",id_tarjeta:"a"};
  const team={id:"a",nombre:"A",club:"C",categoria:"Cat",temporada:"26/27",escudo:"crest-id",key:"privada"};
  card._saveExperimentalTeam("entry",team);
  assert.equal(card._restoreExperimentalTeam("entry").escudo,"crest-id");
  assert.ok(![...data.values()].join().includes("privada"));
  card._toggleExperimentalFavorite("entry",team);
  assert.equal(card._experimentalFavorites("entry")[0].escudo,"crest-id");
});

test("un escudo inaccesible recupera el símbolo neutro", () => {
  const {elements,sandbox}=loadCard(); sandbox.URL=URL;
  class Elem {
    constructor(tag){this.tag=tag;this.children=[];this.listeners={};this.textContent="";}
    append(...items){this.children.push(...items);}
    addEventListener(type,fn){this.listeners[type]=fn;}
    setAttribute(key,value){this[key]=value;}
    replaceWith(item){this.replacement=item;}
  }
  sandbox.document={createElement:tag=>new Elem(tag)};
  const card=new (elements.get("fbm-card"))();
  card._config={modo_experimental:true,tipo_tarjeta:"equipo",id_tarjeta:"a"};
  card._hass={user:{id:"u"},callWS:async()=>({})};
  const state=card._experimentalState(); state.entry="entry"; state.status={sesion_vigente:true};
  const team={id:"a",nombre:"Equipo",club:"PINTOBASKET E.C.B.",categoria:"Cat",temporada:"26/27"};
  state.teams=[team]; state.selected="a"; card._restoreExperimentalTeam=()=>team;
  state.standings=[{id:"a",escudo:"identificador-fbm"}];
  const root=new Elem("card"); card._renderExperimental(root);
  const flatten=el=>[el,...(el.children||[]).flatMap(flatten)];
  const img=flatten(root).find(el=>el.tag==="img");
  assert.equal(img.src,"https://appaficionfbm.gesdeportiva.es/imagenes.ashx?tipo=escudo&id=identificador-fbm");
  img.listeners.error(); assert.equal(img.replacement.textContent,"🏀");
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





test("la plantilla solo se consulta a demanda y cada tarjeta conserva sus datos", async () => {
  const { elements } = loadCard();
  const Card = elements.get("fbm-card");
  const a = new Card(); const b = new Card();
  a._config = { modo_experimental: true }; b._config = { modo_experimental: true };
  a._render = () => {}; b._render = () => {};
  const calls = [];
  const hass = { callWS: async msg => {
    calls.push(msg);
    return { jugadores: [{ id: "p1", nombre: "Jugador de prueba", puntos_totales: 7 }], total: 1 };
  } };
  a._hass = hass; b._hass = hass;
  const sa = a._experimentalState(), sb = b._experimentalState();
  sa.entry = "entry"; sa.selected = "team-a";
  sb.entry = "entry"; sb.selected = "team-b";
  assert.equal(calls.length, 0);
  await a._experimentalAction("players");
  assert.equal(calls.length, 1);
  assert.equal(calls[0].type, "fbm/team/players");
  assert.equal(calls[0].equipo, "team-a");
  assert.equal(sa.playersTeamId, "team-a");
  assert.equal(sa.players[0].puntos_totales, 7);
  assert.equal(sb.players, null);
});

test("una respuesta de plantilla malformada no se presenta como lista valida", async () => {
  const { elements } = loadCard();
  const card = new (elements.get("fbm-card"))(); card._config = { modo_experimental: true };
  card._render = () => {};
  card._hass = { callWS: async () => ({ error: "not-ready" }) };
  const state = card._experimentalState(); state.entry = "entry"; state.selected = "team";
  await card._experimentalAction("players");
  assert.equal(state.players, null);
  assert.equal(state.playersTeamId, "");
  assert.match(state.message, /No se pudo completar/);
});

test("la ficha de un jugador solo se solicita explícitamente y no afecta a otra tarjeta", async () => {
  const { elements } = loadCard();
  const Card = elements.get("fbm-card");
  const first = new Card(), second = new Card();
  first._config = { modo_experimental: true }; second._config = { modo_experimental: true };
  first._render = () => {}; second._render = () => {};
  const requests = [];
  const hass = { callWS: async request => {
    requests.push(request);
    return { jugador: { id: "p1", nombre: "Jugador ficticio", puntos_totales: 8 }, fuente: "FBM" };
  } };
  first._hass = hass; second._hass = hass;
  const a = first._experimentalState(), b = second._experimentalState();
  a.entry = "entry"; a.selected = "teamA";
  a.players = [{id:"p1", nombre:"Jugador ficticio"}]; a.playersTeamId = "teamA"; a.playersEntryId = "entry";
  b.entry = "entry"; b.selected = "teamB";
  b.players = [{id:"p2", nombre:"Otro jugador"}]; b.playersTeamId = "teamB"; b.playersEntryId = "entry";
  assert.equal(requests.length, 0);
  await first._experimentalPlayerDetail("p1");
  assert.equal(requests.length, 1);
  assert.equal(requests[0].type, "fbm/player/detail");
  assert.equal(requests[0].entry_id, "entry");
  assert.equal(requests[0].jugador, "p1");
  assert.equal(a.playerDetail.puntos_totales, 8);
  assert.equal(a.playerDetailTeamId, "teamA");
  assert.equal(b.playerDetail, null);
});

test("la ficha se rechaza si no pertenece a la plantilla o cambia el equipo", async () => {
  const { elements } = loadCard();
  const card = new (elements.get("fbm-card"))(); card._config = { modo_experimental: true };
  card._render = () => {};
  let finish;
  const calls = [];
  card._hass = {callWS: async request => {
    calls.push(request);
    return await new Promise(resolve => { finish = resolve; });
  }};
  const state = card._experimentalState(); state.entry = "entry"; state.selected = "teamA";
  state.players = [{id:"p1", nombre:"Ficticio"}]; state.playersTeamId = "teamA"; state.playersEntryId = "entry";
  await card._experimentalPlayerDetail("wrong");
  assert.equal(calls.length, 0);
  const pending = card._experimentalPlayerDetail("p1");
  state.selected = "teamB";
  finish({ jugador: { id:"p1", nombre:"Ficticio" }, fuente:"FBM" });
  await pending;
  assert.equal(calls.length, 1);
  assert.equal(state.playerDetail, null);
});

test("ignora una plantilla que llega después de cambiar de equipo", async () => {
  const { elements } = loadCard();
  const card = new (elements.get("fbm-card"))();
  card._config = { modo_experimental: true }; card._render = () => {};
  let reply;
  card._hass = { callWS: async () => await new Promise(resolve => { reply = resolve; }) };
  const state = card._experimentalState(); state.entry = "entry"; state.selected = "team-a";
  const pending = card._experimentalAction("players");
  state.selected = "team-b";
  reply({ jugadores: [{ id: "player-a", nombre: "Ejemplo" }], total: 1 });
  await pending;
  assert.equal(state.players, null);
  assert.equal(state.playersTeamId, "");
});

test("al refrescar la plantilla se descarta la ficha individual anterior", async () => {
  const { elements } = loadCard();
  const card = new (elements.get("fbm-card"))();
  card._config = { modo_experimental: true }; card._render = () => {};
  card._hass = { callWS: async () => ({ jugadores: [{ id: "player", nombre: "Ejemplo" }], total: 1 }) };
  const state = card._experimentalState(); state.entry = "entry"; state.selected = "team";
  state.playerDetail = { id: "old", nombre: "Anterior" };
  state.playerDetailTeamId = "team"; state.playerDetailPlayerId = "old";
  await card._experimentalAction("players");
  assert.equal(state.playerDetail, null);
  assert.equal(state.playerDetailTeamId, "");
  assert.equal(state.playersTeamId, "team");
});


test("oculta estadísticas no disponibles pero muestra ceros y valoraciones negativas", () => {
  const { elements, sandbox } = loadCard();
  class Elem {
    constructor(tag) { this.tag=tag; this.children=[]; this.listeners={}; this.textContent=""; }
    append(...items) { this.children.push(...items); }
    addEventListener(name,fn) { this.listeners[name]=fn; }
    setAttribute() {}
  }
  sandbox.document={createElement:tag=>new Elem(tag)};
  const card=new (elements.get("fbm-card"))();
  const team={id:"equipo",nombre:"Equipo Prueba",club:"Club",categoria:"Alevín",temporada:"26/27"};
  card._config={modo_experimental:true,tipo_tarjeta:"equipo",id_tarjeta:"jugadores",equipo_fijo:team};
  card._hass={user:{id:"u"},callWS:async()=>({})};
  card._restoreExperimentalTeam=()=>team;
  const state=card._experimentalState();
  state.entry="entry";state.status={sesion_vigente:true};
  state.selected=team.id;state.tab="jugadores";
  state.playersTeamId=team.id;state.playersEntryId="entry";
  state.players=[{id:"j1",nombre:"Jugador Ejemplo",temporada:"26/27",
    partidos_jugados:4,puntos_por_partido:0,minutos_por_partido:null,puntos_totales:null}];
  state.playerDetailTeamId=team.id;state.playerDetailPlayerId="j1";
  state.playerDetail={id:"j1",nombre:"Jugador Ejemplo",equipo:"Equipo Prueba"};
  state.playerStatsTeamId=team.id;state.playerStatsPlayerId="j1";state.playerStatsEntryId="entry";
  state.playerStats={
    jugador:"j1",equipo:team.id,
    globales:{estadisticas:{puntos_totales:null,asistencias:null,valoracion:-3}},
    partidos:{partidos:[{id_partido:"p1",rival:"Equipo Rival",fecha:"2026-11-08",
      puntos:0,asistencias:null,faltas_cometidas:2,faltas_recibidas:null,
      rebotes:null,rebotes_defensivos:null,rebotes_ofensivos:null,
      recuperaciones:null,perdidas:null,valoracion:-3}]}
  };
  const output=new Elem("card");
  card._renderExperimental(output);
  const flatten=node=>[node,...(node.children||[]).flatMap(flatten)];
  const nodes=flatten(output);
  const statLabels=nodes.filter(n=>n.className==="fbm-stat-label").map(n=>n.textContent);
  const statValues=nodes.filter(n=>n.className==="fbm-stat-value").map(n=>n.textContent);
  assert.ok(statLabels.includes("Puntos"));
  assert.ok(statLabels.includes("Faltas"));
  assert.ok(statLabels.includes("Valoración"));
  assert.ok(statValues.includes("0"),"el cero real debe mostrarse");
  assert.ok(statValues.includes("-3"),"la valoración negativa debe mostrarse");
  for(const absent of ["Asist.","F. recib.","Rebotes","Reb. def.","Reb. of.","Recup.","Pérdidas","Min/partido"]) {
    assert.ok(!statLabels.includes(absent),absent+" no debe aparecer si carece de dato");
  }
  assert.ok(!statValues.includes("—"),"ninguna casilla debe mostrar guiones");
});


test("jornadas oficiales muestran enfrentamientos y permiten filtrar solo mi equipo", () => {
  const {elements,sandbox}=loadCard();
  class Elem {
    constructor(tag){this.tag=tag;this.children=[];this.listeners={};this.textContent="";}
    append(...children){this.children.push(...children);}
    addEventListener(event,handler){this.listeners[event]=handler;}
    setAttribute(name,value){this[name]=value;}
  }
  sandbox.document={createElement:tag=>new Elem(tag)};
  const team={id:"t1",nombre:"Pinto Negro",club:"Pinto",categoria:"Alevín",temporada:"26/27"};
  const card=new (elements.get("fbm-card"))();
  card._config={modo_experimental:true,tipo_tarjeta:"equipo",id_tarjeta:"gael",equipo_fijo:team};
  card._hass={user:{id:"u"},callWS:async()=>({})};
  card._render=()=>{};
  const state=card._experimentalState();
  state.entry="entry";state.status={sesion_vigente:true};
  state.selected=team.id;state.tab="partidos";state.partidosTab="jornadas";
  state.scheduleTeamId=team.id;state.scheduleEntryId=state.entry;state.showGroup=true;
  state.schedule={jornada_actual:2,partidos:[
    {id:"m1",jornada:1,fecha:"18/10/2026",local:"Pinto Negro",visitante:"Rival 1",marcador:{local:23,visitante:18}},
    {id:"m2",jornada:1,fecha:"10/10/2026",local:"Rival 2",visitante:"Rival 3",marcador:null},
    {id:"m3",jornada:2,fecha:"25/10/2026",local:"Rival 4",visitante:"Pinto Negro",marcador:{local:10,visitante:12}}
  ]};
  const flatten=node=>[node,...(node.children||[]).flatMap(flatten)];
  const root=new Elem("card");card._renderExperimental(root);
  const nodes=flatten(root);
  assert.ok(nodes.some(n=>n.textContent==="3 enfrentamientos del grupo"));
  assert.ok(nodes.some(n=>n.textContent==="Jornada 1 · 10/10/2026 – 18/10/2026"));
  assert.ok(nodes.some(n=>n.textContent==="Jornada 2 · 25/10/2026"));
  assert.ok(nodes.some(n=>n.textContent==="23 – 18"));
  const fixtures=nodes.filter(n=>n.className==="fbm-fixture");
  assert.equal(fixtures.length,3);
  assert.ok(flatten(fixtures[0]).some(n=>n.textContent==="Rival 2"),"fechas se ordenan día/mes/año");
  const btn=nodes.find(n=>n.textContent==="Ver solo mi equipo");
  assert.ok(btn);
  btn.listeners.click();
  assert.equal(state.showGroup,false);
  const other=new Elem("card");card._renderExperimental(other);
  const filtered=flatten(other);
  assert.equal(filtered.filter(n=>n.className==="fbm-fixture").length,2);
  assert.ok(filtered.some(n=>n.textContent==="2 partidos de tu equipo"));
});

test("la tarjeta fija consulta el calendario oficial y conserva identificadores independientes", async () => {
  const {elements}=loadCard();
  const team={id:"team-a",nombre:"Equipo",club:"Club",categoria:"Alevín",temporada:"26/27"};
  const card=new (elements.get("fbm-card"))();
  card._config={modo_experimental:true,tipo_tarjeta:"equipo",id_tarjeta:"uno",equipo_fijo:team};
  card._render=()=>{};
  const calls=[];
  card._hass={user:{id:"u"},callWS:async query=>{
    calls.push(query);
    return {jornada_actual:1,partidos:[{id:"p1",jornada:1,fecha:"10/10/2026",local:"Equipo",visitante:"Otro"}]};
  }};
  const state=card._experimentalState();
  state.entry="entry";state.status={sesion_vigente:true};state.selected=team.id;
  state.matchStart="2026-10-01";state.matchEnd="2026-12-31";
  await card._experimentalAction("fixed_schedule");
  assert.equal(calls.length,1);
  assert.equal(calls[0].type,"fbm/team/schedule");
  assert.equal(calls[0].equipo,team.id);
  assert.equal(calls[0].desde,"2026-10-01");
  assert.equal(calls[0].hasta,"2026-12-31");
  assert.equal(state.scheduleTeamId,team.id);
  assert.equal(state.scheduleEntryId,"entry");
  assert.equal(state.showGroup,true);
  assert.equal(state.schedule.partidos.length,1);
  state.selected="team-b";
  assert.equal(card._fixedMatchesAvailable(state,"team-b"),false);
});

test("refresco periódico de 15 minutos solo para datos visibles ya consultados", async () => {
  const {elements,sandbox}=loadCard();
  const team={id:"team-a",nombre:"Equipo",club:"Club",categoria:"Alevín",temporada:"26/27"};
  const card=new (elements.get("fbm-card"))();
  card._config={modo_experimental:true,tipo_tarjeta:"equipo",equipo_fijo:team};
  card._hass={callWS:async()=>({})};
  card._restoreExperimentalTeam=()=>team;
  const calls=[];
  card._experimentalAction=async action=>calls.push(action);
  const state=card._experimentalState();
  state.entry="entry";state.selected=team.id;state.status={sesion_vigente:true};
  state.tab="clasificacion";state.standings=[];
  state.lastStandingsUpdate=Date.now()-16*60000;
  await card._autoRefresh();
  assert.deepEqual(calls,["standings"]);
  calls.length=0;
  state.lastStandingsUpdate=Date.now();
  await card._autoRefresh();
  assert.equal(calls.length,0);
  state.tab="partidos";state.scheduleEntryId="entry";state.scheduleTeamId=team.id;
  state.schedule={partidos:[]};state.lastScheduleUpdate=Date.now()-16*60000;
  await card._autoRefresh();
  assert.deepEqual(calls,["refresh_schedule"]);
  calls.length=0;
  sandbox.document={visibilityState:"hidden"};
  await card._autoRefresh();
  assert.equal(calls.length,0);
});

test("el selector omite la fecha cuando no consta oficialmente", () => {
  const {elements}=loadCard();
  const card=new (elements.get("fbm-card"))();
  assert.equal(card._roundDateLabel([{fecha:null},{fecha:""}]),"");
  assert.equal(card._roundDateLabel([{fecha:"08/11/2026"},{fecha:"08/11/2026"}]),"08/11/2026");
  assert.equal(card._roundDateLabel([
    {fecha:"09/11/2026"}, {fecha:"07/11/2026"}, {fecha:"08/11/2026"}
  ]),"07/11/2026 – 09/11/2026");
});

test("diagnóstico de foto solo muestra categorías permitidas sin datos privados", async () => {
  const {elements}=loadCard();
  const card=new (elements.get("fbm-card"))();
  card._config={modo_experimental:true,tipo_tarjeta:"equipo"};
  card._render=()=>{};
  const state=card._experimentalState();
  state.entry="entry";state.selected="team";state.status={sesion_vigente:true};
  const calls=[];
  card._hass={callWS:async req=>{
    calls.push(req);
    return {ok:true,shape:{player_photo_format:{
      kind:"opaque_reference",length_band:"257-1024",text_form:"hex",
      hex_decoded_kind:"utf16le_url",private_value:"SECRET-PLAYER-URL"
    }}};
  }};
  await card._experimentalAction("photo_diagnostic");
  assert.equal(calls[0].type,"fbm/team/diagnostic");
  assert.equal(calls[0].kind,"roster");
  assert.equal(calls[0].equipo,"team");
  assert.match(state.photoDiagnostic,/hex_decoded_kind=utf16le_url/);
  assert.ok(!state.photoDiagnostic.includes("SECRET"));
  state.photoDiagnostic=null;
  card._hass.callWS=async()=>({ok:true,shape:{player_photo_format:{
    kind:"opaque_reference",text_form:"<private data>",base64_magic:"PRIVATE"
  }}});
  await card._experimentalAction("photo_diagnostic");
  assert.ok(!state.photoDiagnostic.includes("PRIVATE"));
  assert.ok(!state.photoDiagnostic.includes("<private"));
});
