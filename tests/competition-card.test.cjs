"use strict";
const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const source = fs.readFileSync("fbm-card.js","utf8");
class E {
  constructor(tag) {
    this.tagName=tag;this.children=[];this.listeners={};this.textContent="";
    this.shadowRoot=null;
  }
  append(...nodes){this.children.push(...nodes);}
  addEventListener(name,cb){this.listeners[name]=cb;}
  replaceChildren(...nodes){this.children=nodes;}
  attachShadow(){this.shadowRoot=new E("shadow");return this.shadowRoot;}
  setAttribute(){}
}
function card() {
  const registry=new Map();
  const context={HTMLElement:E,document:{createElement:t=>new E(t)},
    customElements:{define:(k,v)=>registry.set(k,v),get:k=>registry.get(k)},
    window:{customCards:[]},console,URL};
  vm.runInNewContext(source,context);
  return new (registry.get("fbm-competition-card"))();
}
function walk(node, pred, found=[]) {
  if(pred(node))found.push(node);
  for (const child of node.children||[]) walk(child,pred,found);
  return found;
}
test("competition card shows standings and loads roster on team click",async()=>{
  const c=card();let calls=[];
  c.setConfig({entity:"sensor.competiciones"});
  c.hass={states:{"sensor.competiciones":{state:"1",attributes:{groups:[{
    season_id:"26/27",phase_id:"phase",group_id:"group",matches:30,
    round_status:{current:3,last_completed:2,next:4},
    ranking:[{id:"team1",equipo:"Equipo A",posicion:1,jugados:4,puntos:8,
      escudo:"https://fbm.es/equipo-a.png"}]
  }]}}},callWS:async request=>{
    calls.push(request.type);
    if(request.type==="fbm/client/entries")return {entries:["entry"]};
    if(request.type==="fbm/competition/team_roster")
      return {jugadores:[{id:"p1",nombre:"Jugador de prueba"}],
        partidos:[{local:"Equipo A",visitante:"Equipo B",fecha:"12/11/2026",jornada:3,marcador:{local:44,visitante:39}},
          {local:"Equipo B",visitante:"Equipo A",fecha:"19/11/2026",jornada:4}]};
    if(request.type==="fbm/team/schedule")
      return {partidos:[{local:"Equipo A",visitante:"Equipo B",escudo_visitante:"ABC123"}]};
    if(request.type==="fbm/team/players")
      return {jugadores:[{id:"p1",nombre:"Jugador de prueba",foto:"data:image/png;base64,iVBORw0KGgo="}]};
    if(request.type==="fbm/competition/team_player_stats")
      return {estadisticas:{globales:{puntos_totales:22,media_puntos:11},
        partidos:[{fecha:"12/11/2026",rival:"Equipo B",puntos:12,asistencias:2}]}};
    throw Error("Unexpected call");
  }};
  assert.equal(walk(c.shadowRoot,x=>x.textContent==="Jornada actual: 3").length,1);
  assert.equal(walk(c.shadowRoot,x=>x.textContent==="Última jornada disputada: 2").length,1);
  assert.equal(walk(c.shadowRoot,x=>x.textContent==="Próxima jornada: 4").length,1);
  const buttons=walk(c.shadowRoot,x=>x.tagName==="button");
  assert.equal(buttons.length,1);
  buttons[0].listeners.click();
  await new Promise(resolve=>setImmediate(resolve));
  assert.deepEqual(calls,["fbm/client/entries","fbm/competition/team_roster","fbm/team/schedule"]);
  assert.equal(c._roster.length,1);
  assert.ok(walk(c.shadowRoot,x=>x.className==="fbm-fixture-logo" && x.src.endsWith("id=ABC123")).length);
  assert.ok(walk(c.shadowRoot,x=>x.textContent==="44 – 39").length);
  assert.ok(walk(c.shadowRoot,x=>x.className==="fbm-fixture-logo" && x.src==="https://fbm.es/equipo-a.png").length);
  assert.ok(walk(c.shadowRoot,x=>x.tagName==="option" && x.textContent==="Jornada 3").length);
  const rounds=walk(c.shadowRoot,x=>x.tagName==="select")[0];
  rounds.listeners.change({target:{value:"3"}});
  assert.ok(walk(c.shadowRoot,x=>x.textContent==="44 – 39").length);
  assert.equal(walk(c.shadowRoot,x=>x.textContent==="vs").length,0);
  walk(c.shadowRoot,x=>x.tagName==="button" && x.textContent==="Clasificación")[0].listeners.click();
  assert.ok(walk(c.shadowRoot,x=>x.tagName==="table").length);
  walk(c.shadowRoot,x=>x.tagName==="button" && x.textContent==="Jugadores")[0].listeners.click();
  assert.deepEqual(calls,["fbm/client/entries","fbm/competition/team_roster","fbm/team/schedule","fbm/team/players"]);
  await new Promise(resolve=>setImmediate(resolve));
  assert.ok(walk(c.shadowRoot,x=>x.className==="fbm-roster").length);
  assert.ok(walk(c.shadowRoot,x=>x.className==="fbm-player-photo").length);
  const playerButton=walk(c.shadowRoot,x=>x.tagName==="button" && x.textContent==="Ver ficha")[0];
  playerButton.listeners.click();
  walk(c.shadowRoot,x=>x.textContent==="Consultar estadísticas por partido")[0].listeners.click();
  await new Promise(resolve=>setImmediate(resolve));
  assert.deepEqual(calls,["fbm/client/entries","fbm/competition/team_roster","fbm/team/schedule","fbm/team/players","fbm/competition/team_player_stats"]);
  assert.ok(walk(c.shadowRoot,x=>x.tagName==="strong" && x.textContent==="22").length);
  assert.ok(walk(c.shadowRoot,x=>x.tagName==="strong" && x.textContent==="12").length);
  const back=walk(c.shadowRoot,x=>x.textContent==="‹ Volver a la competición")[0];
  back.listeners.click();
  assert.equal(c._teamId,null);
});
test("competition card uses only verified official crest URLs",()=>{
  const c=card();
  const official="https://appaficionfbm.gesdeportiva.es/imagenes.ashx?tipo=escudo&id=ABC123";
  assert.equal(c._verifiedCrest(official),official);
  assert.equal(c._verifiedCrest("PRIVATE_IMAGE"),"");
  assert.equal(c._verifiedCrest("http://appaficionfbm.gesdeportiva.es/imagenes.ashx?tipo=escudo&id=ABC123"),"");
  assert.equal(c._verifiedCrest("https://appaficionfbm.gesdeportiva.es.bad.test/imagenes.ashx?tipo=escudo&id=ABC123"),"");
});

test("competition card rejects invalid sensor and group index",()=>{
  assert.throws(()=>card().setConfig({entity:"light.kitchen"}),/sensor/);
  assert.throws(()=>card().setConfig({group_index:-1}),/Índice/);
});

test("competition selector shows names and retains selection after group order changes", () => {
  const c = card();
  c.setConfig({entity:"sensor.competiciones"});
  const a = {season_id:"26/27", phase_id:"p", group_id:"a", competition_name:"Alevín Plata"};
  const b = {season_id:"26/27", phase_id:"p", group_id:"b", team_name:"Equipo de referencia"};
  const state = groups => ({states:{"sensor.competiciones":{attributes:{groups}}}});
  c.hass = state([a, b]);
  const select = walk(c.shadowRoot,x=>x.tagName==="select")[0];
  assert.equal(select.children[0].textContent,"Alevín Plata · 26/27");
  select.listeners.focus();
  c.hass = state([{...a, matches: 10}, b]);
  assert.equal(walk(c.shadowRoot,x=>x.tagName==="select")[0], select);
  select.listeners.change({target:{value:"1"}});
  c.hass = state([b, a]);
  assert.ok(walk(c.shadowRoot,x=>x.tagName==="h3" && x.textContent==="Equipo de referencia").length);
  assert.ok(walk(c.shadowRoot,x=>x.textContent==="Clasificación pendiente de sincronizar.").length);
});
