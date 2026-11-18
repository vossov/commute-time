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
const STANDAARD = kaart.normaliseer({});
const MET_DOEL = kaart.normaliseer({ target: true });
// de scheiding in een regel: een vaste spatie vóór de punt, zodat een regel die
// omslaat de punt bij het woord ervoor laat en niet met een los "· 3 min file" begint
const PUNT = ' · ';

function schoon(html, wat) {
  assert.ok(!/undefined|NaN|\[object Object\]/.test(html), `${wat} bevat undefined, NaN of [object Object]:\n${html}`);
}

// ── het hoofdgetal ──────────────────────────────────────────────────

test('met een aankomsttijd is de vertrektijd het hoofdgetal', () => {
  const w = kaart.weergave(staten.berekend, NU, STANDAARD);
  assert.deepEqual(w.hoofd, { label: 'Vertrek', waarde: '07:52' });
  assert.equal(w.soort, 'normaal');
});

test('zonder aankomsttijd is de rijtijd het hoofdgetal', () => {
  const w = kaart.weergave(staten.zonder_doel, NU, STANDAARD);
  assert.deepEqual(w.hoofd, { label: '', waarde: '3 min' });
  assert.equal(w.soort, 'normaal');
  assert.ok(!/vertrek/i.test(w.regel), 'er is geen vertrektijd om te noemen: ' + w.regel);
});

test('een aankomsttijd die al voorbij is werkt als geen aankomsttijd', () => {
  const a = Object.assign({}, staten.berekend, { status: 'doel_voorbij', vertrek: null, vertrek_hhmm: null });
  assert.deepEqual(kaart.weergave(a, NU, STANDAARD).hoofd, { label: '', waarde: '3 min' });
});

test('er staat geen aftelling', () => {
  for (const [naam, a] of Object.entries(staten)) {
    const w = kaart.weergave(a, NU, STANDAARD);
    const alles = JSON.stringify(w) + kaart.routeRij('sensor.x', { state: '3', attributes: a }, STANDAARD, NU) +
      kaart.detail(a, NU, STANDAARD);
    assert.ok(!/\bover \d+ (min|u)\b/.test(alles), `aftelling in ${naam}: ${alles}`);
  }
});

test('is de vertrektijd voorbij, dan zegt de kaart nu, ook zonder nieuwe ronde', () => {
  const voorbij = Date.parse('2026-11-17T07:52:30+01:00');
  const w = kaart.weergave(staten.berekend, voorbij, STANDAARD);
  assert.deepEqual(w.hoofd, { label: 'Vertrek', waarde: 'nu' });
  assert.equal(w.soort, 'let_op');
});

test('vertrek nu en te laat', () => {
  const nu = Object.assign({}, staten.berekend, { status: 'vertrek_nu' });
  const a = kaart.weergave(nu, NU, STANDAARD);
  assert.deepEqual(a.hoofd, { label: 'Vertrek', waarde: 'nu' });
  assert.equal(a.soort, 'let_op');

  const laat = Object.assign({}, staten.berekend, { status: 'te_laat', te_laat_min: 11 });
  const b = kaart.weergave(laat, NU, STANDAARD);
  assert.deepEqual(b.hoofd, { label: 'Vertrek', waarde: 'nu' });
  assert.equal(b.soort, 'te_laat');
  assert.match(b.regel, /^11 min te laat/);
});

// ── wat eronder staat ───────────────────────────────────────────────

test('onder de naam: rijtijd, wegen en file', () => {
  const w = kaart.weergave(staten.berekend, NU, STANDAARD);
  assert.equal(w.regel, ['3 min rijden', 'via Sample Street', 'A10', '3 min file'].join(PUNT));
});

test('zonder aankomsttijd staat de rijtijd niet nog een keer onder de naam', () => {
  const w = kaart.weergave(staten.zonder_doel, NU, STANDAARD);
  assert.equal(w.regel, ['via Sample Street', 'A10', '3 min file'].join(PUNT));
});

test('een route zonder wegen of files zegt toch wat de rijtijd is', () => {
  const kaal = Object.assign({}, staten.zonder_doel, { via: [], files: [] });
  assert.equal(kaart.weergave(kaal, NU, STANDAARD).regel, 'Rijtijd met het verkeer van nu');
});

test('de ingevoerde aankomsttijd en marge staan er standaard niet', () => {
  const w = kaart.weergave(staten.berekend, NU, STANDAARD);
  assert.ok(!/08:30|marge/.test(w.regel), w.regel);
  const rij = kaart.routeRij('sensor.x', { state: '3', attributes: staten.berekend }, STANDAARD, NU);
  assert.ok(!/08:30|marge/.test(rij), 'de rij noemt de ingevoerde aankomsttijd of marge');
  const venster = kaart.detail(staten.berekend, NU, STANDAARD);
  assert.ok(!/Aankomen om|Marge|08:30/.test(venster), 'het venster noemt de ingevoerde aankomsttijd of marge');
});

test('met target staan ze er wel, op de tegel en in het venster', () => {
  const w = kaart.weergave(staten.berekend, NU, MET_DOEL);
  assert.match(w.regel, /voor 08:30, 5 min marge/);
  const venster = kaart.detail(staten.berekend, NU, MET_DOEL);
  assert.match(venster, /Aankomen om/);
  assert.match(venster, /Marge/);
  assert.match(venster, /Op tijd zijn/);
});

test('het venster houdt het vertrek ook zonder target', () => {
  const venster = kaart.detail(staten.berekend, NU, STANDAARD);
  assert.match(venster, /<h3>Vertrek<\/h3>/);
  assert.match(venster, /Vertrekken om/);
});

test('zonder aankomsttijd is er niets over het plan', () => {
  const venster = kaart.detail(staten.zonder_doel, NU, MET_DOEL);
  assert.ok(!/Aankomen om|Vertrekken om/.test(venster));
  assert.match(venster, /3 min rijden/);
});

test('een aankomsttijd mag ontbreken', () => {
  // wat de sensor publiceert als er geen aankomsttijd is: geen doel, geen vertrek
  const a = staten.zonder_doel;
  assert.equal(a.doel_hhmm, null);
  assert.equal(a.vertrek, null);
  assert.equal(a.status, 'geen_doel');
});

// ── buiten het venster en fouten ────────────────────────────────────

test('buiten het venster: wanneer hij terugkomt', () => {
  const w = kaart.weergave(staten.buiten_venster, NU, STANDAARD);
  assert.equal(w.regel, 'Weer in beeld morgen 06:30');
  assert.equal(w.hoofd, null);
});

test('een fout zegt wat TomTom zei', () => {
  const w = kaart.weergave(staten.fout, NU, STANDAARD);
  assert.equal(w.soort, 'fout');
  assert.equal(w.hoofd, null);
  assert.match(w.regel, /403/);
});

// ── de rij ──────────────────────────────────────────────────────────

test('de rij heeft het hoofdgetal rechts en de tekst links', () => {
  const rij = kaart.routeRij('sensor.x', { state: '3', attributes: staten.berekend }, STANDAARD, NU);
  assert.match(rij, /<span class="lab">Vertrek<\/span><span class="waarde">07:52<\/span>/);
  assert.match(rij, /<div class="naam">Naar werk<\/div>/);

  const zonder = kaart.routeRij('sensor.x', { state: '3', attributes: staten.zonder_doel }, STANDAARD, NU);
  assert.match(zonder, /<span class="waarde">3 min<\/span>/);
  assert.ok(!/class="lab"/.test(zonder), 'zonder aankomsttijd hoort er geen label bij');
});

test('de kleur volgt de vertraging; te laat is rood en een fout oranje', () => {
  const kleur = (a) => /\bt-(\w+)"/.exec(kaart.routeRij('sensor.x', { state: '3', attributes: a }, STANDAARD, NU))[1];
  assert.equal(kleur(Object.assign({}, staten.berekend, { vertraging_min: 0, vrij_min: 30 })), 'rustig');
  assert.equal(kleur(Object.assign({}, staten.berekend, { vertraging_min: 6, vrij_min: 60 })), 'druk');
  assert.equal(kleur(Object.assign({}, staten.berekend, { status: 'te_laat', te_laat_min: 4, vertraging_min: 0 })), 'file');
  assert.equal(kleur(staten.fout), 'druk');
});

test('de rij en het venster bevatten geen undefined of NaN', () => {
  for (const config of [STANDAARD, MET_DOEL]) {
    for (const [naam, a] of Object.entries(staten)) {
      schoon(kaart.routeRij('sensor.naar_werk_reistijd', { state: '3', attributes: a }, config, NU), `rij (${naam})`);
      schoon(kaart.detail(a, NU, config), `venster (${naam})`);
    }
  }
  schoon(kaart.routeRij('sensor.weg', undefined, STANDAARD, NU), 'rij zonder sensor');
  schoon(kaart.routeRij('sensor.x', { state: 'unavailable', attributes: {} }, STANDAARD, NU), 'rij onbeschikbaar');
});

test('een Waze-knop alleen voor een echte Waze-link', () => {
  const a = Object.assign({}, staten.berekend, { waze_url: 'javascript:alert(1)' });
  const rij = kaart.routeRij('sensor.x', { state: '3', attributes: a }, STANDAARD, NU);
  assert.ok(!/javascript:/.test(rij), 'een vreemde link werd een knop');
  const echt = kaart.routeRij('sensor.x', { state: '3', attributes: staten.berekend }, STANDAARD, NU);
  assert.match(echt, /href="https:\/\/waze\.com\/ul\?ll=/);
  const zonder = kaart.routeRij('sensor.x', { state: '3', attributes: staten.berekend }, kaart.normaliseer({ waze: false }), NU);
  assert.ok(!/waze\.com/.test(zonder));
});

// ── de rest ─────────────────────────────────────────────────────────

test('het venster toont de bronnen van de getallen', () => {
  const html = kaart.detail(staten.berekend, NU, STANDAARD);
  assert.match(html, /Gebruikelijk op dit uur/);
  assert.match(html, /Zonder verkeer/);
  assert.match(html, /file/);
  assert.match(html, /Stationsplein 1, 3511 ED Utrecht/);
  assert.match(html, /bron: TomTom/);
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

test('target staat standaard uit en gaat alleen aan met een uitdrukkelijk true', () => {
  assert.equal(kaart.normaliseer({}).target, false);
  assert.equal(kaart.normaliseer({ target: true }).target, true);
  for (const onzin of ['true', 1, 'ja', null, undefined, {}]) {
    assert.equal(kaart.normaliseer({ target: onzin }).target, false, String(onzin));
  }
});

test('zichtbaar: alleen binnen het venster, behalve als iets stuk is', () => {
  assert.equal(kaart.zichtbaar({ state: '34', attributes: staten.berekend }, STANDAARD), true);
  assert.equal(kaart.zichtbaar({ state: 'unknown', attributes: staten.buiten_venster }, STANDAARD), false);
  assert.equal(kaart.zichtbaar({ state: 'unknown', attributes: staten.buiten_venster }, kaart.normaliseer({ show: 'always' })), true);
  // stuk: altijd in beeld, anders verdwijnt juist het probleem
  assert.equal(kaart.zichtbaar({ state: 'unavailable', attributes: {} }, STANDAARD), true);
  assert.equal(kaart.zichtbaar(undefined, STANDAARD), true);
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

test('de versie staat in de kaart', () => {
  assert.match(kaart.VERSIE, /^\d+\.\d+\.\d+$/);
});
