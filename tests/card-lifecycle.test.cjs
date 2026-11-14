"use strict";
const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");

const source = fs.readFileSync(path.join(__dirname, "..", "fbm-card.js"), "utf8");
function makeCard() {
  const registered = new Map();
  const sandbox = {
    HTMLElement: class {},
    window: { customCards: [] },
    customElements: {
      get(name) { return registered.get(name); },
      define(name, value) { registered.set(name, value); }
    },
    Promise, Date, JSON, console
  };
  vm.runInNewContext(source, sandbox, { filename: "fbm-card.js" });
  const Card = registered.get("fbm-card");
  const card = new Card();
  card._render = () => {};
  return card;
}

test("search card discovers existing integration session automatically", async () => {
  const card = makeCard();
  const calls = [];
  card._hass = {
    user: { id: "test-user" },
    callWS: async request => {
      calls.push(request.type);
      if (request.type === "fbm/client/entries") return { entries: ["test-entry"] };
      if (request.type === "fbm/client/status")
        return { sesion_vigente: true, identidad_creada: true };
      throw Error("Unexpected FBM request");
    }
  };
  card.setConfig({ modo_experimental: true, tipo_tarjeta: "busqueda" });
  await new Promise(resolve => setImmediate(resolve));
  assert.deepEqual(calls, ["fbm/client/entries", "fbm/client/status"]);
  assert.equal(card._experimentalState().status.sesion_vigente, true);
  card.setConfig({ modo_experimental: true, tipo_tarjeta: "busqueda" });
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(calls.length, 2, "No repeated registration or session probing");
});

test("players tab has automatic refresh and manual retry is conditional", () => {
  assert.match(source, /name === "jugadores"/);
  assert.match(source, /cached \? "refresh_players" : "players"/);
  assert.match(source, /lastPlayersUpdate >= 15 \* 60 \* 1000/);
  assert.match(source, /"Reintentar plantilla"/);
  assert.doesNotMatch(source, /button\("Actualizar plantilla"/);
});

test("technical photo diagnostics are hidden unless explicitly configured", () => {
  assert.match(source, /this\._config\.mostrar_diagnostico === true/);
  assert.match(source, /button\("Diagnosticar fotos"/);
});

test("archived results repaint after a change even with no live FBM session", async () => {
  const card = makeCard();
  card._config = { modo_experimental: true, tipo_tarjeta: "equipo" };
  const state = card._experimentalState();
  Object.assign(state, { entry: "entry", selected: "team", archivedData: true,
    status: { sesion_vigente: false }, lastArchiveCheck: 0 });
  card._restoreExperimentalTeam = () => ({ id: "team" });
  const requests = [];
  card._hass = { callWS: async request => {
    requests.push(request.type);
    return { found: true, standings: { clasificacion: [] },
      fixtures: { partidos: [{ marcador: { local: 44, visitante: 84 } }] } };
  }};
  let paints = 0;
  card._render = () => { paints++; };
  await card._autoRefresh();
  assert.equal(state.schedule.partidos[0].marcador.visitante, 84);
  assert.equal(paints, 1);
  state.lastArchiveCheck = 0;
  await card._autoRefresh();
  assert.equal(paints, 1);
  assert.deepEqual(requests, ["fbm/competition/team_snapshot", "fbm/competition/team_snapshot"]);
});
