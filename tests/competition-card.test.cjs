"use strict";
const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const source = fs.readFileSync("fbm-card.js","utf8");
class E {
  constructor(tag) {
    this.tagName=tag;this.children=[];this.listeners={};this.attributes={};this.textContent="";
    this.shadowRoot=null;
  }
  append(...nodes){this.children.push(...nodes);}
  addEventListener(name,cb){this.listeners[name]=cb;}
  replaceChildren(...nodes){this.children=nodes;}
  attachShadow(){this.shadowRoot=new E("shadow");return this.shadowRoot;}
  setAttribute(name,value){this.attributes[name]=value;}
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
    recent_results:[{local:"Equipo A",visitante:"Equipo B",fecha:"12/11/2026",marcador:{local:44,visitante:39}}],
    ranking:[{id:"team1",equipo:"Equipo A",posicion:1,jugados:4,puntos:8,
      escudo:""}]
  }]}}},callWS:async request=>{
    calls.push(request.type);
    if(request.type==="fbm/client/entries")return {entries:["entry"]};
    if(request.type==="fbm/competition/team_roster")
      return {jugadores:[{id:"p1",nombre:"Jugador de prueba"}],
        partidos:[{local:"Equipo A",visitante:"Equipo B",fecha:"12/11/2026",jornada:3,marcador:{local:44,visitante:39}},
          {local:"Equipo B",visitante:"Equipo A",fecha:"19/04/2027",jornada:4}]};
    if(request.type==="fbm/team/schedule") {
      assert.equal(request.desde, "2026-11-12");
      assert.equal(request.hasta, "2027-03-17");
      return {partidos:[{local:"Equipo A",visitante:"equipo b ",img_local:"https://fbm.es/equipo-a.png",escudo_visitante:"ABC+/="}]};
    }
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
  assert.ok(walk(c.shadowRoot,x=>x.textContent==="44 – 39").length);
  const buttons=walk(c.shadowRoot,x=>x.tagName==="button" && x.className==="team");
  assert.equal(buttons.length,1);
  buttons[0].listeners.click();
  await new Promise(resolve=>setImmediate(resolve));
  assert.deepEqual(calls,["fbm/client/entries","fbm/competition/team_roster","fbm/team/schedule"]);
  assert.equal(c._roster.length,1);
  assert.ok(walk(c.shadowRoot,x=>x.className==="team-logo" && x.src==="https://fbm.es/equipo-a.png").length);
  assert.ok(walk(c.shadowRoot,x=>x.className==="fbm-fixture-logo" && x.src.endsWith("id=ABC%2B%2F%3D")).length);
  assert.ok(walk(c.shadowRoot,x=>x.textContent==="44 – 39").length);
  assert.ok(walk(c.shadowRoot,x=>x.className==="fbm-fixture-logo" && x.src==="https://fbm.es/equipo-a.png").length);
  assert.ok(walk(c.shadowRoot,x=>x.tagName==="option" && x.textContent==="Jornada 3").length);
  const rounds=walk(c.shadowRoot,x=>x.tagName==="select")[0];
  rounds.listeners.change({target:{value:"3"}});
  assert.ok(walk(c.shadowRoot,x=>x.textContent==="44 – 39").length);
  assert.equal(walk(c.shadowRoot,x=>x.textContent==="vs").length,0);
  walk(c.shadowRoot,x=>x.tagName==="button" && x.textContent==="Clasificación").at(-1).listeners.click();
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

test("agenda opens on the next matchday and navigates past and future",()=>{
  const c=card();
  c.setConfig({entity:"sensor.competiciones",initial_tab:"upcoming"});
  const match=(jornada,fecha)=>({id:String(jornada),jornada,fecha,
    local:"Equipo A",visitante:"Equipo B",hora:"10:30",campo:"Pabellón",direccion:"Calle 9"});
  c.hass={states:{"sensor.competiciones":{attributes:{groups:[{
    season_id:"26/27",phase_id:"phase",group_id:"group",
    past_fixtures:[{...match(5,"2026-11-15"),marcador:{local:42,visitante:39}}],
    upcoming:[match(6,"2026-11-22"), match(7,"2026-11-29")]
  }]}}}};
  const contains=text=>walk(c.shadowRoot,x=>x.textContent===text).length>0;
  const arrow=name=>walk(c.shadowRoot,x=>x.attributes["aria-label"]===name)[0];
  assert.ok(contains("Jornada 6"));
  assert.ok(contains("10:30 · Pabellón"));
  assert.equal(contains("10:30 · Pabellón · Calle 9"),false);
  assert.equal(contains("42 – 39"),false);
  arrow("Jornada anterior").listeners.click();
  assert.ok(contains("Jornada 5"));
  assert.ok(contains("42 – 39"));
  assert.ok(walk(c.shadowRoot,x=>x.className==="fbm-fixture-score" && x.textContent==="42 – 39").length);
  arrow("Jornada siguiente").listeners.click();
  arrow("Jornada siguiente").listeners.click();
  assert.ok(contains("Jornada 7"));
  assert.equal(arrow("Jornada siguiente").disabled,true);
});

test("agenda shows official standings and locally archived fixture crests",async()=>{
  const c=card();
  c.setConfig({entity:"sensor.competiciones",initial_tab:"upcoming"});
  const inline="data:image/png;base64,iVBORw0KGgo=";
  const official="https://fbm.es/equipo-b.png";
  const observed="2026-11-16T00:00:00Z";
  const calls=[];
  c.hass={states:{"sensor.competiciones":{attributes:{groups:[{
    season_id:"26/27",phase_id:"phase",group_id:"group",fixtures_at:observed,
    ranking:[{id:"a",equipo:"Equipo A"},{id:"b",equipo:"Equipo B",escudo:official}],
    upcoming:[{id:"m1",jornada:6,fecha:"2026-11-22",local:"equipo A",visitante:"Equipo B"}]
  }]}}},callWS:async request=>{
    calls.push(request.type);
    if(request.type==="fbm/client/entries") return {entries:["entry"]};
    return {observed_at:{fixtures:observed},fixtures:{escudos:{"Equipo A":inline}}};
  }};
  await new Promise(resolve=>setImmediate(resolve));
  assert.deepEqual(calls,["fbm/client/entries","fbm/competition/team_snapshot"]);
  const logos=walk(c.shadowRoot,x=>x.tagName==="img").map(x=>x.src);
  assert.deepEqual(logos,[inline,official]);
});
