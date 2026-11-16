/*
 * De kaart tegen wat de sensor werkelijk publiceert.
 *
 * tests/fixtures/sensor.json is gemaakt door uitvoer.py (zie
 * maak_sensor_fixture.py); tests/test_kaart.py bewaakt dat het daar nog mee
 * klopt. Hier wordt gekeken of de kaart er de goede zinnen van maakt, en of
 * er nergens `undefined` of `NaN` in de HTML belandt — dat geeft geen
 * foutmelding, alleen een rare tekst op het dashboard.
 *
 *   node --test tests/kaart.test.mjs
 */

import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

// Net genoeg browser om de module te laden. Geen `document`: alles wat de
// kaart bij het laden al zou bouwen, faalt dan hier.
globalThis.HTMLElement = class {};
globalThis.customElements = { get: () => undefined, define() {} };
globalThis.window = globalThis;

const kaart = await import('../custom_components/time_to_leave/www/time-to-leave-card.js');
const staten = JSON.parse(readFileSync(new URL('./fixtures/sensor.json', import.meta.url), 'utf8'));

// 07:34 op 17 november 2026, Amsterdam — het moment van de fixture
const NU = Date.parse('2026-11-17T07:34:00+01:00');

function schoon(html, wat) {
  assert.ok(!/undefined|NaN|\[object Object\]/.test(html), `${wat} bevat undefined, NaN of [object Object]:\n${html}`);
}

test('vertrek om: tijd en aftellen', () => {
  const r = kaart.statusRegel(staten.berekend, NU);
  assert.equal(r.soort, 'normaal');
  assert.equal(r.tekst, 'Vertrek om 07:52 · over 18 min');
});

test('het aftellen loopt mee met de klok, ook zonder nieuwe ronde', () => {
  const later = Date.parse('2026-11-17T07:47:30+01:00');
  assert.match(kaart.statusRegel(staten.berekend, later).tekst, /over 5 min$/);
  const voorbij = Date.parse('2026-11-17T07:52:30+01:00');
  assert.deepEqual(kaart.statusRegel(staten.berekend, voorbij), { tekst: 'Vertrek nu', soort: 'let_op' });
});

test('de tweede regel noemt doel, marge, wegen en file', () => {
  const regel = kaart.tweedeRegel(staten.berekend);
  assert.equal(regel, 'voor 08:30, 5 min marge · via Sample Street · A10 · 3 min file');
});

test('te laat en vertrek nu', () => {
  const a = Object.assign({}, staten.berekend, { status: 'te_laat', te_laat_min: 11, aankomst_hhmm: '08:41' });
  assert.deepEqual(kaart.statusRegel(a, NU), {
    tekst: 'Vertrek nu · aankomst 08:41 · 11 min te laat', soort: 'te_laat',
  });
  const b = Object.assign({}, staten.berekend, { status: 'vertrek_nu' });
  assert.equal(kaart.statusRegel(b, NU).soort, 'let_op');
});

test('buiten het venster: wanneer hij terugkomt', () => {
  assert.equal(kaart.statusRegel(staten.buiten_venster, NU).tekst, 'Weer in beeld morgen 06:30');
});

test('een fout zegt wat TomTom zei', () => {
  const r = kaart.statusRegel(staten.fout, NU);
  assert.equal(r.soort, 'fout');
  assert.match(r.tekst, /403/);
});

test('drukte volgt de vertraging, niet een verzonnen grens per route', () => {
  assert.equal(kaart.drukte({ vertraging_min: 0, vrij_min: 30 }), 'rustig');
  assert.equal(kaart.drukte({ vertraging_min: 5, vrij_min: 60 }), 'druk');
  assert.equal(kaart.drukte({ vertraging_min: 3, vrij_min: 10 }), 'druk');
  assert.equal(kaart.drukte({ vertraging_min: 15, vrij_min: 100 }), 'file');
  assert.equal(kaart.drukte({}), 'onbekend');
});

test('minuten worden leesbaar', () => {
  assert.equal(kaart.minuten(34), '34 min');
  assert.equal(kaart.minuten(60), '1 u');
  assert.equal(kaart.minuten(72), '1 u 12 min');
  assert.equal(kaart.minuten(null), '');
});

test('normaliseer gooit nooit en levert altijd iets bruikbaars', () => {
  assert.deepEqual(kaart.normaliseer(undefined).entities, []);
  const c = kaart.normaliseer({ entity: 'sensor.a', entities: 'sensor.b, sensor.a', design: 'paars', show: 'x' });
  assert.deepEqual(c.entities, ['sensor.a', 'sensor.b']);
  assert.equal(c.design, 'default');
  assert.equal(c.show, 'window');
  assert.equal(kaart.normaliseer({ design: 'bubble' }).design, 'bubble');
  assert.deepEqual(kaart.normaliseer({ entities: [{ entity: 'sensor.c' }] }).entities, ['sensor.c']);
});

test('zichtbaar: alleen binnen het venster, behalve als iets stuk is', () => {
  const c = kaart.normaliseer({});
  assert.equal(kaart.zichtbaar({ state: '34', attributes: staten.berekend }, c), true);
  assert.equal(kaart.zichtbaar({ state: 'unknown', attributes: staten.buiten_venster }, c), false);
  assert.equal(kaart.zichtbaar({ state: 'unknown', attributes: staten.buiten_venster }, kaart.normaliseer({ show: 'always' })), true);
  // stuk: altijd in beeld, anders verdwijnt juist het probleem
  assert.equal(kaart.zichtbaar({ state: 'unavailable', attributes: {} }, c), true);
  assert.equal(kaart.zichtbaar(undefined, c), true);
});

test('de rij en het venster bevatten geen undefined of NaN', () => {
  const c = kaart.normaliseer({});
  for (const [naam, a] of Object.entries(staten)) {
    const rij = kaart.routeRij('sensor.naar_werk_reistijd', { state: '3', attributes: a }, c, NU);
    schoon(rij, `rij (${naam})`);
    schoon(kaart.detail(a, NU, c), `venster (${naam})`);
  }
  schoon(kaart.routeRij('sensor.weg', undefined, c, NU), 'rij zonder sensor');
  schoon(kaart.routeRij('sensor.x', { state: 'unavailable', attributes: {} }, c, NU), 'rij onbeschikbaar');
});

test('het venster toont de bronnen van de getallen', () => {
  const html = kaart.detail(staten.berekend, NU, kaart.normaliseer({}));
  assert.match(html, /Gebruikelijk op dit uur/);
  assert.match(html, /Zonder verkeer/);
  assert.match(html, /file/);
  assert.match(html, /Stationsplein 1, 3511 ED Utrecht/);
  assert.match(html, /bron: TomTom/);
});

test('een Waze-knop alleen voor een echte Waze-link', () => {
  const c = kaart.normaliseer({});
  const a = Object.assign({}, staten.berekend, { waze_url: 'javascript:alert(1)' });
  const rij = kaart.routeRij('sensor.x', { state: '3', attributes: a }, c, NU);
  assert.ok(!/javascript:/.test(rij), 'een vreemde link werd een knop');
  const echt = kaart.routeRij('sensor.x', { state: '3', attributes: staten.berekend }, c, NU);
  assert.match(echt, /href="https:\/\/waze\.com\/ul\?ll=/);
  const zonder = kaart.routeRij('sensor.x', { state: '3', attributes: staten.berekend }, kaart.normaliseer({ waze: false }), NU);
  assert.ok(!/waze\.com/.test(zonder));
});

test('de versie staat in de kaart', () => {
  assert.match(kaart.VERSIE, /^\d+\.\d+\.\d+$/);
});
