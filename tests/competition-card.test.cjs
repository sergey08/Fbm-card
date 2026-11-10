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
    window:{customCards:[]},console};
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
    ranking:[{id:"team1",equipo:"Equipo A",posicion:1,jugados:4,puntos:8}]
  }]}}},callWS:async request=>{
    calls.push(request.type);
    if(request.type==="fbm/client/entries")return {entries:["entry"]};
    if(request.type==="fbm/competition/team_roster")
      return {jugadores:[{id:"p1",nombre:"Jugador de prueba"}]};
    throw Error("Unexpected call");
  }};
  const buttons=walk(c.shadowRoot,x=>x.tagName==="button");
  assert.equal(buttons.length,1);
  buttons[0].listeners.click();
  await new Promise(resolve=>setImmediate(resolve));
  assert.deepEqual(calls,["fbm/client/entries","fbm/competition/team_roster"]);
  assert.equal(c._roster.length,1);
  assert.ok(walk(c.shadowRoot,x=>x.textContent==="Jugador de prueba").length);
  const back=walk(c.shadowRoot,x=>x.textContent==="‹ Volver a clasificación")[0];
  back.listeners.click();
  assert.equal(c._teamId,null);
});
test("competition card rejects invalid sensor and group index",()=>{
  assert.throws(()=>card().setConfig({entity:"light.kitchen"}),/sensor/);
  assert.throws(()=>card().setConfig({group_index:-1}),/Índice/);
});
