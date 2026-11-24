/*
 * Commute Time - Lovelace-kaart
 *
 * Wordt door de integratie zelf geregistreerd; je hoeft niets aan resources
 * toe te voegen. Op je dashboard:
 *
 *   type: custom:commute-time-card
 *   entities:
 *     - sensor.naar_werk_reistijd
 *
 * Opties (allemaal ook in de visuele editor):
 *   entities  de reistijd-sensoren van je routes; één of meer
 *   title     eigen kop boven de kaart; leeg is geen kop
 *   design    'default' (eigen opmaak), 'ha' (volgt het Home Assistant-
 *             thema) of 'bubble' (in de trant van Bubble Card, zonder die
 *             kaart nodig te hebben)
 *   show      'window' (standaard): een route staat er alleen binnen zijn
 *             venster, en zonder route in beeld verbergt de kaart zich.
 *             'always': altijd, met buiten het venster wanneer hij terugkomt
 *   target    false (standaard): de ingevoerde aankomsttijd en marge staan er
 *             niet. true toont ze, onder de naam en in het venster
 *   details   true (standaard) opent bij een tik het detailvenster
 *   waze      true (standaard) zet een knop "Drive with Waze" bij de route
 *   language  'en' (standaard) of 'nl': de taal van de kaart en de editor
 *
 * Bovenaan staat met een aankomsttijd de vertrektijd ("Leave 07:52"), en
 * zonder aankomsttijd de rijtijd ("34 min"). Een aankomsttijd invullen is
 * optioneel en gaat per weekdag in het rooster van de route.
 *
 * De kaart rekent niets uit wat de sensor niet levert. Alleen "nu" zegt hij
 * zelf zodra de vertrektijd voorbij is, ook als de sensor nog niet ververst
 * heeft.
 *
 * Ondergrens: Chrome 61 (oude WebViews op wandpanelen). Geen ?. of ??, geen
 * flexbox-gap, geen catch zonder variabele. tests/floor.mjs controleert dat.
 */

/* De versie van deze kaart. Gelijk aan VERSION in const.py en version in
 * manifest.json; tests/test_repo.py bewaakt alle drie. Hij staat hier apart
 * omdat dit bestand statisch is: Home Assistant meldt de versie van de
 * Python-kant, en een browser kan een oudere kaart uit de cache draaien.
 * Het nummer staat in de console en onder in het bewerkscherm. */
const VERSIE = '0.4.0';

/* De talen van de kaart. Engels is de standaard: de documentatie is Engels,
 * en wie niets kiest krijgt dezelfde taal als in de README. */
const TALEN = ['en', 'nl'];
const TAAL = [
  { value: 'en', label: 'English' },
  { value: 'nl', label: 'Nederlands' },
];

/* Alle tekst op de kaart en in de editor, per taal. {naam} wordt ingevuld
 * door t(). Een sleutel die in de ene taal staat en in de andere niet, laat
 * tests/kaart.test.mjs falen. */
const TEKST = {
  en: {
    vorm_default: 'Default (own style)', vorm_ha: 'Home Assistant theme', vorm_bubble: 'Bubble style',
    toon_window: 'Only within the window', toon_always: 'Always',
    uur: 'h', kmh: 'km/h', decimaal: '.',
    geen_antwoord: 'TomTom gave no answer',
    weer_in_beeld: 'Shown again {wanneer}',
    geen_venster: 'No window set in the schedule',
    vandaag: 'today', morgen: 'tomorrow',
    dagen: ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'],
    vertrek: 'Leave', nu: 'now',
    te_laat: '{n} min late', te_laat_kaal: 'Late',
    rijden: '{t} driving', via: 'via', file: '{t} in traffic',
    voor: 'by {tijd}', marge_kort: ', {n} min margin',
    rijtijd_nu: 'Driving time with current traffic',
    venster_vandaag: 'Window today {van}–{tot}', bron_groot: 'Source: {bron}',
    h_reistijd: 'Travel time', f_nu: 'Now', f_gebruikelijk: 'Usual at this hour',
    f_vrij: 'Without traffic', f_verwacht: 'Expected when leaving at {t}',
    f_afstand: 'Distance', f_aankomst: 'Arrival if you leave now',
    h_op_tijd: 'Arriving on time', h_vertrek: 'Departure',
    f_aankomen: 'Arrive at', f_marge: 'Margin', f_stoptijd: 'Stop time', f_vertrekken: 'Leave at',
    h_route: 'Route', h_files: 'Traffic and delays', geen_files: 'TomTom reports nothing on this route.',
    cat_JAM: 'traffic jam', cat_ROAD_WORK: 'roadworks', cat_ROAD_CLOSURE: 'road closure', cat_OTHER: 'delay',
    op_weg: '{wat} on the {weg}',
    h_etappes: 'Legs', h_andere: 'Other routes', andere_route: 'other route',
    start: 'Start', bestemming: 'Destination', stop: 'Stop {i}',
    h_adressen: 'Addresses as found',
    bijgewerkt: 'Updated {t}', bron: 'source: {bron}', kaart_v: 'card v{v}',
    waze_lang: 'Drive with Waze',
    bestaat_niet: 'does not exist; pick the travel time sensor of a route',
    niet_beschikbaar: 'unavailable', nog_onbekend: 'not known yet',
    kijk_log: ' — check the Home Assistant log for commute_time',
    kies_route: 'Pick the travel time sensor of a route in the editor.',
    sluiten: 'Close',
    faal_kop: 'Commute Time could not render',
    faal_uitleg: 'This is not an error in your configuration; the card tries again on the next update.',
    editor_versie: 'Commute Time card v{v}',
    l_entities: 'Routes', u_entities: 'The travel time sensors of your routes, in the order they appear on the card.',
    u_entities_kaal: 'Travel time sensors, one per line.',
    l_title: 'Title', u_title: 'Empty means no title.',
    l_design: 'Design', u_design: 'Own style, the Home Assistant theme, or in the style of Bubble Card.',
    l_show: 'Show', u_show: 'Only within the window from the route\'s schedule, or always.',
    l_target: 'Show arrival time and margin',
    u_target: 'The arrival time and margin you entered yourself. Off: only the departure time, or the driving time if you set no arrival time.',
    l_details: 'Details on tap', u_details: 'Traffic, other routes, legs and the addresses as TomTom found them.',
    l_waze: 'Button "Drive with Waze"', u_waze: 'Opens Waze with the destination; Waze works out the route from where you are.',
    l_language: 'Language', u_language: 'The language of the card and this editor.',
    fout_geweigerd: 'TomTom refuses the key{voor} (403): invalid, not enabled for this product, or the daily quota is used up',
    fout_voor_search: ' for the Search API', fout_voor_routing: ' for the Routing API',
    fout_te_vaak: 'TomTom is getting too many requests for this key (429)',
    fout_geen_route: 'TomTom cannot find a route between these points (400)',
    fout_status: 'TomTom answered with {status}',
    fout_onverwacht: 'TomTom sent an unexpected answer',
    fout_time_out: 'TomTom did not answer within {seconden} seconds',
    fout_onbereikbaar: 'TomTom unreachable: {detail}',
    fout_geen_adres: 'TomTom finds no address for “{adres}”',
    fout_geen_locatie: '{entiteit} has no location right now',
    fout_geen_routes: 'TomTom returned no route',
  },
  nl: {
    vorm_default: 'Standaard (eigen opmaak)', vorm_ha: 'Home Assistant-thema', vorm_bubble: 'Bubble-stijl',
    toon_window: 'Alleen binnen het venster', toon_always: 'Altijd',
    uur: 'u', kmh: 'km/u', decimaal: ',',
    geen_antwoord: 'TomTom gaf geen antwoord',
    weer_in_beeld: 'Weer in beeld {wanneer}',
    geen_venster: 'Geen venster ingesteld in het rooster',
    vandaag: 'vandaag', morgen: 'morgen',
    dagen: ['maandag', 'dinsdag', 'woensdag', 'donderdag', 'vrijdag', 'zaterdag', 'zondag'],
    vertrek: 'Vertrek', nu: 'nu',
    te_laat: '{n} min te laat', te_laat_kaal: 'Te laat',
    rijden: '{t} rijden', via: 'via', file: '{t} file',
    voor: 'voor {tijd}', marge_kort: ', {n} min marge',
    rijtijd_nu: 'Rijtijd met het verkeer van nu',
    venster_vandaag: 'Venster vandaag {van}–{tot}', bron_groot: 'Bron: {bron}',
    h_reistijd: 'Reistijd', f_nu: 'Nu', f_gebruikelijk: 'Gebruikelijk op dit uur',
    f_vrij: 'Zonder verkeer', f_verwacht: 'Verwacht bij vertrek om {t}',
    f_afstand: 'Afstand', f_aankomst: 'Aankomst als je nu vertrekt',
    h_op_tijd: 'Op tijd zijn', h_vertrek: 'Vertrek',
    f_aankomen: 'Aankomen om', f_marge: 'Marge', f_stoptijd: 'Stoptijd', f_vertrekken: 'Vertrekken om',
    h_route: 'Route', h_files: 'Files en hinder', geen_files: 'TomTom meldt niets op deze route.',
    cat_JAM: 'file', cat_ROAD_WORK: 'werk in uitvoering', cat_ROAD_CLOSURE: 'afsluiting', cat_OTHER: 'hinder',
    op_weg: '{wat} op de {weg}',
    h_etappes: 'Etappes', h_andere: 'Andere routes', andere_route: 'andere route',
    start: 'Start', bestemming: 'Bestemming', stop: 'Stop {i}',
    h_adressen: 'Adressen zoals gevonden',
    bijgewerkt: 'Bijgewerkt {t}', bron: 'bron: {bron}', kaart_v: 'kaart v{v}',
    waze_lang: 'Rijden met Waze',
    bestaat_niet: 'bestaat niet; kies de reistijd-sensor van een route',
    niet_beschikbaar: 'niet beschikbaar', nog_onbekend: 'nog onbekend',
    kijk_log: ' — kijk in het logboek van Home Assistant op commute_time',
    kies_route: 'Kies in de editor de reistijd-sensor van een route.',
    sluiten: 'Sluiten',
    faal_kop: 'Commute Time kon niet tekenen',
    faal_uitleg: 'Dit is geen fout in je configuratie; bij de volgende update probeert de kaart het opnieuw.',
    editor_versie: 'Commute Time-kaart v{v}',
    l_entities: 'Routes', u_entities: 'De reistijd-sensoren van je routes, in de volgorde waarin ze op de kaart staan.',
    u_entities_kaal: 'Reistijd-sensoren, één per regel.',
    l_title: 'Kop', u_title: 'Leeg is geen kop.',
    l_design: 'Vormgeving', u_design: 'Eigen opmaak, het thema van Home Assistant, of in de stijl van Bubble Card.',
    l_show: 'Tonen', u_show: 'Alleen binnen het venster uit het rooster van de route, of altijd.',
    l_target: 'Aankomsttijd en marge tonen',
    u_target: 'De aankomsttijd en marge die je zelf hebt ingevoerd. Uit: alleen de vertrektijd, of de rijtijd als je geen aankomsttijd hebt ingesteld.',
    l_details: 'Detailvenster bij aantikken', u_details: 'Files, andere routes, etappes en de adressen zoals TomTom ze vond.',
    l_waze: 'Knop "Rijden met Waze"', u_waze: 'Opent Waze met de bestemming; Waze rekent zelf de route vanaf waar je bent.',
    l_language: 'Taal', u_language: 'De taal van de kaart en van deze editor.',
    fout_geweigerd: 'TomTom weigert de sleutel{voor} (403): ongeldig, voor dit product niet aangezet, of het dagkwotum is op',
    fout_voor_search: ' voor de Search API', fout_voor_routing: ' voor de Routing API',
    fout_te_vaak: 'TomTom krijgt te veel verzoeken voor deze sleutel (429)',
    fout_geen_route: 'TomTom kan hier geen route tussen leggen (400)',
    fout_status: 'TomTom antwoordde met {status}',
    fout_onverwacht: 'TomTom stuurde een onverwacht antwoord',
    fout_time_out: 'TomTom antwoordde niet binnen {seconden} seconden',
    fout_onbereikbaar: 'TomTom niet bereikbaar: {detail}',
    fout_geen_adres: 'TomTom vindt geen adres bij “{adres}”',
    fout_geen_locatie: '{entiteit} heeft nu geen locatie',
    fout_geen_routes: 'TomTom gaf geen route terug',
  },
};

/** De tekst onder `sleutel` in de taal van de configuratie, met {naam}
 * ingevuld. Een onbekende taal wordt Engels, een onbekende sleutel de sleutel
 * zelf: liever een rare tekst dan een kaart die gooit. */
function t(taal, sleutel, waarden) {
  const tabel = TEKST[taal] || TEKST.en;
  const tekst = sleutel in tabel ? tabel[sleutel] : (sleutel in TEKST.en ? TEKST.en[sleutel] : sleutel);
  if (typeof tekst !== 'string') return tekst;
  return tekst.replace(/\{(\w+)\}/g, function (heel, naam) {
    return waarden && waarden[naam] != null ? String(waarden[naam]) : '';
  });
}

/** De taal uit een (genormaliseerde) configuratie. */
function taalVan(config) {
  return config && TALEN.indexOf(config.language) >= 0 ? config.language : 'en';
}

const VORMGEVING_SLEUTELS = ['default', 'ha', 'bubble'];
function vormgeving(taal) {
  return VORMGEVING_SLEUTELS.map(function (v) { return { value: v, label: t(taal, 'vorm_' + v) }; });
}
const VORMGEVING = vormgeving('en');

function tonen(taal) {
  return ['window', 'always'].map(function (v) { return { value: v, label: t(taal, 'toon_' + v) }; });
}

/* Wanneer een route druk heet. Dit is een keuze van de kaart, geen meting:
 * TomTom geeft de vertraging ten opzichte van een lege weg, en daar hangt
 * alleen de kleur van het stipje aan. De getallen zelf staan erbij. */
const DRUK_MIN = 5;
const DRUK_DEEL = 0.15;
const FILE_MIN = 15;
const FILE_DEEL = 0.35;

const KLEUR = { rustig: '#43a047', druk: '#fb8c00', file: '#e53935', onbekend: 'transparent' };

/* ── pure functies; tests/kaart.test.mjs roept ze los aan ─────────── */

function esc(waarde) {
  return String(waarde == null ? '' : waarde)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function getal(waarde) {
  return typeof waarde === 'number' && isFinite(waarde) ? waarde : null;
}

/** `34 min`, `1 h 12 min` (of `1 u 12 min` in het Nederlands). */
function minuten(n, taal) {
  const m = getal(n);
  if (m === null) return '';
  if (m < 60) return Math.round(m) + ' min';
  const uur = t(taal, 'uur');
  const u = Math.floor(m / 60);
  const rest = Math.round(m - u * 60);
  return rest ? u + ' ' + uur + ' ' + rest + ' min' : u + ' ' + uur;
}

function km(n, taal) {
  const k = getal(n);
  return k === null ? '' : String(k).replace('.', t(taal, 'decimaal')) + ' km';
}

/** De configuratie, met onzin teruggezet. Mag nooit gooien: Home Assistant
 * maakt van een uitzondering in setConfig een foutkaart. */
function normaliseer(config) {
  const g = config && typeof config === 'object' ? config : {};
  let lijst = [];
  if (Array.isArray(g.entities)) lijst = g.entities;
  else if (typeof g.entities === 'string') lijst = g.entities.split(/[\s,]+/);
  if (typeof g.entity === 'string' && g.entity) lijst = [g.entity].concat(lijst);
  const gezien = {};
  const entities = [];
  lijst.forEach(function (e) {
    const id = String(e && typeof e === 'object' ? e.entity : e || '').trim();
    if (id && !gezien[id]) {
      gezien[id] = true;
      entities.push(id);
    }
  });
  return {
    entities: entities,
    title: typeof g.title === 'string' ? g.title : '',
    design: VORMGEVING_SLEUTELS.indexOf(String(g.design)) >= 0 ? String(g.design) : 'default',
    show: g.show === 'always' ? 'always' : 'window',
    // standaard uit: alleen een uitdrukkelijk true telt
    target: g.target === true,
    details: g.details !== false,
    waze: g.waze !== false,
    // standaard Engels; alleen een taal die de kaart kent telt
    language: TALEN.indexOf(String(g.language)) >= 0 ? String(g.language) : 'en',
  };
}

/** Rustig, druk of file, op grond van de vertraging die TomTom meldt. */
function drukte(a) {
  const vertraging = getal(a.vertraging_min);
  const vrij = getal(a.vrij_min);
  if (vertraging === null) return 'onbekend';
  const deel = vrij ? vertraging / vrij : 0;
  if (vertraging >= FILE_MIN || deel >= FILE_DEEL) return 'file';
  if (vertraging >= DRUK_MIN || deel >= DRUK_DEEL) return 'druk';
  return 'rustig';
}

/* De scheiding tussen delen van een regel. Een vaste spatie vóór de punt, zodat
 * een regel die omslaat de punt bij het woord ervoor laat en niet met een los
 * "· 3 min file" begint. */
const PUNT = ' · ';

/** `via A12 · A27`, of leeg. */
function wegen(a, taal) {
  return Array.isArray(a.via) && a.via.length ? t(taal, 'via') + ' ' + a.via.map(String).join(PUNT) : '';
}

/** De foutmelding in de gekozen taal. Met een code uit tomtom.FOUTCODES
 * maakt de kaart de zin zelf; zonder code (een oudere integratie, of iets
 * onvoorziens) staat de tekst van de sensor er zoals hij is. */
function foutTekst(a, taal) {
  const code = a.fout_code ? String(a.fout_code) : '';
  const p = a.fout_param && typeof a.fout_param === 'object' ? a.fout_param : {};
  if (!code || !(('fout_' + code) in TEKST.en)) return a.fout ? String(a.fout) : t(taal, 'geen_antwoord');
  if (code === 'geweigerd') {
    const voor = p.dienst === 'search' || p.dienst === 'routing' ? t(taal, 'fout_voor_' + p.dienst) : '';
    return t(taal, 'fout_geweigerd', { voor: voor }) + (p.detail ? '. ' + p.detail : '');
  }
  // TomTom's eigen uitleg bij een 400 is beter dan onze algemene zin
  if (code === 'geen_route' && p.detail) return String(p.detail);
  return t(taal, 'fout_' + code, p);
}

/** "tomorrow 06:30": wanneer de route weer in beeld komt. Uit de taalloze
 * velden als de sensor die heeft, anders de Nederlandse tekst van de sensor. */
function wanneer(a, taal) {
  const dagen = getal(a.volgend_venster_dagen);
  const weekdag = getal(a.volgend_venster_weekdag);
  if (a.volgend_venster_hhmm && dagen !== null) {
    let dag = '';
    if (dagen === 0) dag = t(taal, 'vandaag');
    else if (dagen === 1) dag = t(taal, 'morgen');
    else if (weekdag !== null && weekdag >= 0 && weekdag < 7) dag = t(taal, 'dagen')[weekdag];
    return (dag ? dag + ' ' : '') + a.volgend_venster_hhmm;
  }
  return a.volgend_venster_tekst ? String(a.volgend_venster_tekst) : '';
}

/** Minuten tot een ISO-tijdstip, naar boven afgerond; null zonder tijdstip. */
function minutenTot(iso, nuMs) {
  const t = Date.parse(iso);
  if (!isFinite(t)) return null;
  return Math.ceil((t - nuMs) / 60000);
}

/** Vaste spaties: een getal en zijn eenheid breken niet uit elkaar ("3 min
 * file" liep anders over twee regels met "3" op de eerste). Alleen voor korte
 * stukjes; een straatnaam moet wel kunnen afbreken. */
function vast(tekst) {
  return String(tekst).replace(/ /g, ' ');
}

/** Hoeveel minuten file er in totaal op de route staat. */
function fileMinuten(a) {
  const files = Array.isArray(a.files) ? a.files : [];
  return files.reduce(function (som, f) { return som + (getal(f.vertraging_min) || 0); }, 0);
}

/** Wat een route nu zegt: het getal bovenaan en de tekst eronder.
 *
 *   hoofd  { label, waarde }, of null. Met een aankomsttijd is het de
 *          vertrektijd ("Vertrek 07:52", of "Vertrek nu"); zonder
 *          aankomsttijd de rijtijd ("34 min"). Een aftelling ("over 18 min")
 *          staat er niet: die hoeft niet, en de vertrektijd zegt het al.
 *   regel  de rest die ertoe doet: hoe lang je rijdt, via welke wegen, hoeveel
 *          file. De ingevoerde aankomsttijd en marge staan er alleen bij als
 *          config.target aan staat; de aankomst die volgt als je nu vertrekt
 *          staat alleen in het venster.
 *   soort  hoe zwaar het weegt: 'normaal', 'let_op', 'te_laat' of 'fout'.
 *
 * Wat de kaart zelf doet is alleen "nu" zeggen zodra de vertrektijd voorbij
 * is, ook als de sensor nog niet ververst heeft.
 */
function weergave(a, nuMs, config) {
  const taal = taalVan(config);
  const status = String(a.status || '');
  if (status === 'fout') {
    return { hoofd: null, soort: 'fout', regel: foutTekst(a, taal) };
  }
  if (status === 'buiten_venster') {
    const terug = wanneer(a, taal);
    return {
      hoofd: null,
      soort: 'normaal',
      regel: terug ? t(taal, 'weer_in_beeld', { wanneer: terug }) : t(taal, 'geen_venster'),
    };
  }

  const reistijd = minuten(a.reistijd_min, taal);
  let hoofd = null;
  let soort = 'normaal';
  let kop = '';
  if (status === 'vertrek_om' || status === 'vertrek_nu' || status === 'te_laat') {
    let nu = status !== 'vertrek_om';
    if (!nu) {
      // de sensor zei "nog niet", maar sindsdien is de tijd verstreken: dan
      // is het nu, ook al heeft de volgende ronde dat nog niet bevestigd
      const over = minutenTot(a.vertrek, nuMs);
      nu = over !== null && over <= 0;
    }
    const waarde = nu ? t(taal, 'nu') : String(a.vertrek_hhmm || '');
    if (waarde) hoofd = { label: t(taal, 'vertrek'), waarde: waarde };
    if (nu) soort = 'let_op';
    if (status === 'te_laat') {
      soort = 'te_laat';
      kop = getal(a.te_laat_min) !== null ? vast(t(taal, 'te_laat', { n: a.te_laat_min })) : t(taal, 'te_laat_kaal');
    }
  }
  // zonder aankomsttijd (of zonder vertrektijd) is de rijtijd het hoofdgetal
  if (!hoofd && reistijd) hoofd = { label: '', waarde: reistijd };

  const delen = [];
  if (kop) delen.push(kop);
  if (hoofd && hoofd.label && reistijd) delen.push(vast(t(taal, 'rijden', { t: reistijd })));
  const via = wegen(a, taal);
  if (via) delen.push(via);
  const file = fileMinuten(a);
  if (file > 0) delen.push(vast(t(taal, 'file', { t: minuten(file, taal) })));
  if (config && config.target && a.doel_hhmm && status !== 'doel_voorbij') {
    delen.push(t(taal, 'voor', { tijd: a.doel_hhmm }) +
      (getal(a.marge_min) ? t(taal, 'marge_kort', { n: a.marge_min }) : ''));
  }
  if (!delen.length) delen.push(t(taal, 'rijtijd_nu'));

  return { hoofd: hoofd, soort: soort, regel: delen.join(PUNT) };
}

/** Of een route op de kaart hoort. Een sensor die er niet is of niet werkt
 * staat er altijd: verbergen zou juist het probleem verbergen. */
function zichtbaar(st, config) {
  if (!st) return true;
  const a = st.attributes || {};
  const s = String(st.state);
  // buiten het venster is de reistijd ook "unknown", maar dan staat er een
  // status bij; zonder status heeft de integratie niets opgeleverd
  if (s === 'unavailable' || (s === 'unknown' && !a.status)) return true;
  if (config.show === 'always') return true;
  return Boolean(a.in_venster);
}

/* ── opmaak ──────────────────────────────────────────────────────── */

const STIJL = `
  :host { display: block; }
  ha-card { padding: 12px 14px; overflow: hidden; }
  .kaartkop {
    font-size: 15px; font-weight: 700; padding: 2px 4px 8px;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  }
  /* geen gap: dat werkt pas vanaf Chrome 84; marges tussen buren wel */
  .routes > * + * { margin-top: 10px; }
  .route { display: flex; align-items: center; border-radius: 12px; }
  .route > * + * { margin-left: 12px; }
  .route.klik { cursor: pointer; }
  .icoon {
    flex: none; position: relative; width: 40px; height: 40px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    background: rgba(127, 127, 127, .16);
  }
  /* het stipje: groen, oranje of rood naar de vertraging die TomTom meldt */
  .stip {
    position: absolute; right: -1px; bottom: -1px; width: 12px; height: 12px;
    border-radius: 50%; border: 2px solid var(--card-background-color, #1c1c1c);
  }
  .t-rustig .stip { background: ${KLEUR.rustig}; }
  .t-druk .stip { background: ${KLEUR.druk}; }
  .t-file .stip { background: ${KLEUR.file}; }
  .t-onbekend .stip { display: none; }
  .tekst { flex: 1; min-width: 0; }
  .naam, .regel2 { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .naam { font-size: 15px; font-weight: 700; }
  /* de regel onder de naam: liever twee regels dan afgekapt.
     -webkit-line-clamp kent Chrome al lang, ook op oude WebViews */
  .regel {
    font-size: 13px; margin-top: 1px; overflow: hidden; opacity: .75;
    display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
  }
  .regel.let_op, .regel.te_laat, .regel.fout { opacity: 1; }
  .regel.let_op, .regel.te_laat { font-weight: 700; }
  .regel2 { font-size: 12.5px; opacity: .65; margin-top: 1px; }
  .rechts { flex: none; display: flex; align-items: center; }
  .rechts > * + * { margin-left: 10px; }
  /* het hoofdgetal: de vertrektijd, of zonder aankomsttijd de rijtijd */
  .hoofd { display: flex; flex-direction: column; align-items: flex-end; line-height: 1.15; }
  .hoofd .lab { font-size: 11px; opacity: .65; }
  .hoofd .waarde { font-size: 20px; font-weight: 700; font-variant-numeric: tabular-nums; white-space: nowrap; }
  .waze {
    display: inline-block; padding: 3px 10px; border-radius: 12px;
    border: 1px solid var(--divider-color, rgba(127, 127, 127, .45));
    color: inherit; text-decoration: none; font-size: 12px; font-weight: 700; white-space: nowrap;
  }
  /* het icoon is voor de Bubble-stijl; elders staat het woord er */
  .waze ha-icon { display: none; }
  .melding { font-size: 13px; opacity: .8; padding: 4px 2px; }

  dialog {
    border: none; border-radius: 22px; padding: 0; max-width: 560px; width: 92vw;
    max-height: 86vh; overflow: auto;
    background: var(--card-background-color, #1c1c1c);
    color: var(--primary-text-color, #e8eef4);
  }
  dialog::backdrop { background: rgba(0, 0, 0, .55); }
  .kop { display: flex; align-items: center; padding: 14px 18px 4px; font-size: 17px; font-weight: 700; }
  .kop .sluit {
    margin-left: auto; cursor: pointer; border: none; background: none;
    color: inherit; font-size: 22px; line-height: 1; padding: 4px 8px;
  }
  .inhoud { padding: 0 18px 18px; }
  .groot { font-size: 22px; font-weight: 700; margin-top: 6px; }
  .sub { font-size: 13px; opacity: .7; margin-top: 2px; }
  section { margin-top: 14px; }
  h3 { margin: 0 0 6px; font-size: 14px; font-weight: 700; }
  ul { list-style: none; margin: 0; padding: 0; font-size: 13.5px; }
  li { display: flex; padding: 3px 0; align-items: baseline; }
  li > * + * { margin-left: 8px; }
  li .l { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; }
  li .r { flex: none; font-variant-numeric: tabular-nums; font-weight: 600; white-space: nowrap; }
  .voet { margin-top: 16px; font-size: 12px; opacity: .6; }
  .knoppen { margin-top: 14px; }
  .knoppen .waze { font-size: 13px; padding: 6px 14px; }

  /* ── vormgeving: Home Assistant ─────────────────────────────────── */
  ha-card.thema-ha { padding: 8px 16px 16px; }
  .thema-ha .kaartkop {
    font-size: 24px; font-weight: 400; padding: 10px 0 16px;
    color: var(--ha-card-header-color, var(--primary-text-color, #e8eef4));
  }
  .thema-ha .icoon { background: none; color: var(--state-icon-color, var(--primary-color, #03a9f4)); }
  .thema-ha .waze { border-color: var(--primary-color, #03a9f4); }
  dialog.thema-ha {
    border-radius: var(--ha-card-border-radius, 12px);
    background: var(--ha-card-background, var(--card-background-color, #1c1c1c));
  }

  /* ── vormgeving: Bubble-stijl ───────────────────────────────────── */
  /* Nagebouwd naar Bubble Card zelf, nagelezen in dist/bubble-card.js op
     18 november 2026; de kaart is er niet voor nodig en wordt niet gebruikt.
     Wat de stijl maakt, in die volgorde:
       - de pil is de secundaire achtergrond en het icoonrondje daarin de
         kaartachtergrond. Dat is omgekeerd aan een gewone kaart, en
         daardoor ziet de pil er als een pil uit;
       - 50 px hoog, afgerond met de helft van de rijhoogte (28 px);
       - naam 13 px vet, status 12 px op 70% dekking;
       - waarden rechts als pillen van 36 px hoog (sub-knoppen);
       - dezelfde terugvalketens als Bubble Card, dus een thema dat
         --bubble-main-background-color en de rest instelt, werkt hier ook.
     Het icoonrondje krijgt de kleur van de vertraging, zoals Bubble Card een
     actief icoon inkleurt: de glyph in die kleur en het rondje op 20%. */
  ha-card.thema-bubble {
    background: none; border: none; box-shadow: none; border-radius: 0;
    padding: 0; overflow: visible;
  }
  .thema-bubble .kaartkop {
    font-size: 13px; font-weight: 600; padding: 0 12px 6px; opacity: .8;
    color: var(--primary-text-color, #e8eef4);
  }
  .thema-bubble .routes > * + * { margin-top: 8px; }
  .thema-bubble .route {
    position: relative; box-sizing: border-box; min-height: 50px;
    padding-right: 8px;
    border-radius: var(--bubble-card-type-border-radius, var(--bubble-border-radius, 28px));
    background-color: var(--bubble-card-type-main-background-color, var(--bubble-main-background-color, var(--background-color-2, var(--secondary-background-color, #202020))));
    box-shadow: var(--bubble-card-type-box-shadow, var(--bubble-box-shadow, none));
  }
  .thema-bubble .route > * + * { margin-left: 0; }
  .thema-bubble .icoon {
    width: 38px; height: 38px; margin: 6px; overflow: hidden;
    border-radius: var(--bubble-card-type-icon-border-radius, var(--bubble-icon-border-radius, var(--bubble-border-radius, 50%)));
    background-color: var(--bubble-card-type-icon-background-color, var(--bubble-icon-background-color, var(--bubble-secondary-background-color, var(--card-background-color, #1c1c1c))));
    color: var(--primary-text-color, #e8eef4);
  }
  .thema-bubble .icoon::before {
    content: ''; position: absolute; top: 0; right: 0; bottom: 0; left: 0;
    background: currentColor; opacity: 0;
  }
  .thema-bubble .icoon ha-icon { position: relative; z-index: 1; --mdc-icon-size: 24px; }
  .thema-bubble .stip { display: none; }
  .thema-bubble .t-rustig .icoon { color: ${KLEUR.rustig}; }
  .thema-bubble .t-druk .icoon { color: ${KLEUR.druk}; }
  .thema-bubble .t-file .icoon { color: ${KLEUR.file}; }
  .thema-bubble .t-rustig .icoon::before,
  .thema-bubble .t-druk .icoon::before,
  .thema-bubble .t-file .icoon::before { opacity: .2; }
  .thema-bubble .tekst { margin: 0 12px 0 4px; }
  .thema-bubble .naam { font-size: 13px; font-weight: 600; line-height: 18px; }
  .thema-bubble .regel { font-size: 12px; font-weight: normal; line-height: 18px; margin-top: 0; opacity: .7; }
  .thema-bubble .regel.let_op, .thema-bubble .regel.te_laat, .thema-bubble .regel.fout { opacity: 1; }
  .thema-bubble .rechts > * + * { margin-left: 8px; }
  .thema-bubble .hoofd {
    box-sizing: border-box; flex-direction: row; align-items: center; height: 36px;
    padding: 0 12px; line-height: 1;
    border-radius: var(--bubble-sub-button-border-radius, var(--bubble-border-radius, 18px));
    background-color: var(--bubble-sub-button-background-color, var(--bubble-icon-background-color, var(--bubble-secondary-background-color, var(--card-background-color, #1c1c1c))));
  }
  .thema-bubble .hoofd .lab { margin-right: 6px; font-size: 12px; }
  .thema-bubble .hoofd .waarde { font-size: 14px; }
  .thema-bubble .rechts .waze {
    box-sizing: border-box; display: flex; align-items: center; justify-content: center;
    width: 36px; height: 36px; padding: 0; border: none;
    border-radius: var(--bubble-sub-button-border-radius, var(--bubble-border-radius, 18px));
    background-color: var(--bubble-sub-button-background-color, var(--bubble-icon-background-color, var(--bubble-secondary-background-color, var(--card-background-color, #1c1c1c))));
  }
  .thema-bubble .rechts .waze ha-icon { display: block; --mdc-icon-size: 20px; }
  .thema-bubble .rechts .waze .wtekst { display: none; }
  dialog.thema-bubble {
    width: 100%; max-width: 640px;
    border-radius: var(--bubble-pop-up-border-radius, var(--bubble-border-radius, 42px)) var(--bubble-pop-up-border-radius, var(--bubble-border-radius, 42px)) 0 0;
    background-color: var(--bubble-pop-up-main-background-color, var(--bubble-pop-up-background-color, var(--bubble-secondary-background-color, var(--background-color, var(--secondary-background-color, #202020)))));
    /* onderaan plakken, zoals de pop-up van Bubble Card. Oudere WebViews
       plaatsen een modale dialog nog zelf; daar blijft hij in het midden
       staan: alleen de plaats klopt dan niet, de kaart werkt gewoon. */
    margin: auto auto 0;
  }
  .thema-bubble .kop { padding: 14px 18px 6px; }
  .thema-bubble .kop .sluit {
    width: 36px; height: 36px; padding: 0; border-radius: 50%; font-size: 20px;
    background-color: var(--bubble-icon-background-color, var(--bubble-secondary-background-color, var(--card-background-color, #1c1c1c)));
  }
  .thema-bubble section {
    padding: 12px 16px; border-radius: 24px;
    background-color: var(--bubble-icon-background-color, var(--bubble-secondary-background-color, var(--card-background-color, #1c1c1c)));
  }
  .thema-bubble .knoppen .waze {
    box-sizing: border-box; height: 36px; padding: 0 16px; border: none;
    display: inline-flex; align-items: center;
    border-radius: var(--bubble-sub-button-border-radius, var(--bubble-border-radius, 18px));
    background-color: var(--bubble-icon-background-color, var(--bubble-secondary-background-color, var(--card-background-color, #1c1c1c)));
  }
`;

/* ── stukjes HTML ────────────────────────────────────────────────── */

function wazeKnop(url, tekst, taal) {
  if (!url || String(url).indexOf('https://waze.com/ul?') !== 0) return '';
  const lang = t(taal, 'waze_lang');
  const naam = tekst || lang;
  return '<a class="waze" data-waze="1" href="' + esc(url) + '" target="_blank" rel="noopener"' +
    ' title="' + esc(lang) + '" aria-label="' + esc(lang) + '">' +
    '<ha-icon icon="mdi:navigation-variant"></ha-icon><span class="wtekst">' + esc(naam) + '</span></a>';
}

function routeRij(id, st, config, nuMs) {
  const taal = taalVan(config);
  const klik = config.details ? ' klik' : '';
  if (!st) {
    return '<div class="route"><div class="tekst"><div class="naam">' + esc(id) +
      '</div><div class="regel2">' + esc(t(taal, 'bestaat_niet')) + '</div></div></div>';
  }
  const a = st.attributes || {};
  const s = String(st.state);
  if (s === 'unavailable' || (s === 'unknown' && !a.status)) {
    return '<div class="route"><div class="tekst"><div class="naam">' + esc(a.route || id) +
      '</div><div class="regel2">' + esc(t(taal, s === 'unavailable' ? 'niet_beschikbaar' : 'nog_onbekend') +
      t(taal, 'kijk_log')) + '</div></div></div>';
  }
  const w = weergave(a, nuMs, config);
  // de kleur van het stipje (en in de Bubble-stijl van het icoon)
  let toon = drukte(a);
  if (w.soort === 'te_laat') toon = 'file';
  if (w.soort === 'fout') toon = 'druk';
  const hoofd = w.hoofd
    ? '<div class="hoofd">' + (w.hoofd.label ? '<span class="lab">' + esc(w.hoofd.label) + '</span>' : '') +
      '<span class="waarde">' + esc(w.hoofd.waarde) + '</span></div>'
    : '';
  // kort op de tegel; in het venster staat "Drive with Waze" voluit
  const knop = config.waze && a.in_venster ? wazeKnop(a.waze_url, 'Waze', taal) : '';
  return '<div class="route' + klik + ' t-' + toon + '" data-route="' + esc(id) + '">' +
    '<div class="icoon"><ha-icon icon="mdi:car-clock"></ha-icon><span class="stip"></span></div>' +
    '<div class="tekst"><div class="naam">' + esc(a.route || id) + '</div>' +
    '<div class="regel ' + w.soort + '">' + esc(w.regel) + '</div></div>' +
    (hoofd || knop ? '<div class="rechts">' + hoofd + knop + '</div>' : '') +
    '</div>';
}

function feit(links, rechts) {
  if (rechts === '' || rechts == null) return '';
  return '<li><span class="l">' + esc(links) + '</span><span class="r">' + esc(rechts) + '</span></li>';
}

/** De inhoud van het detailvenster voor één route. */
function detail(a, nuMs, config) {
  const taal = taalVan(config);
  const toonDoel = Boolean(config && config.target);
  const w = weergave(a, nuMs, config);
  const delen = [];
  if (w.hoofd) {
    delen.push('<div class="groot">' +
      esc(w.hoofd.label ? w.hoofd.label + ' ' + w.hoofd.waarde : t(taal, 'rijden', { t: w.hoofd.waarde })) + '</div>');
    delen.push('<div class="sub">' + esc(w.regel) + '</div>');
  } else {
    delen.push('<div class="groot">' + esc(w.regel) + '</div>');
  }

  if (a.status === 'fout' || a.status === 'buiten_venster') {
    if (a.venster_van && a.venster_tot) {
      delen.push('<div class="sub">' + esc(t(taal, 'venster_vandaag', { van: a.venster_van, tot: a.venster_tot })) + '</div>');
    }
    delen.push('<div class="voet">' + esc(t(taal, 'bron_groot', { bron: a.bron || 'TomTom' })) + '</div>');
    return delen.join('');
  }

  const reistijd = [
    feit(t(taal, 'f_nu'), minuten(a.reistijd_min, taal)),
    feit(t(taal, 'f_gebruikelijk'), minuten(a.normaal_min, taal)),
    feit(t(taal, 'f_vrij'), minuten(a.vrij_min, taal)),
    a.vertrek_hhmm && getal(a.reistijd_bij_vertrek_min) !== null
      ? feit(t(taal, 'f_verwacht', { t: a.vertrek_hhmm }), minuten(a.reistijd_bij_vertrek_min, taal))
      : '',
    feit(t(taal, 'f_afstand'), km(a.afstand_km, taal)),
    feit(t(taal, 'f_aankomst'), a.aankomst_hhmm || ''),
  ].join('');
  delen.push('<section><h3>' + esc(t(taal, 'h_reistijd')) + '</h3><ul>' + reistijd + '</ul></section>');

  // de ingevoerde aankomsttijd en marge alleen als de kaart dat vraagt
  if (a.doel_hhmm) {
    const plan = [
      toonDoel ? feit(t(taal, 'f_aankomen'), a.doel_hhmm) : '',
      toonDoel && getal(a.marge_min) !== null ? feit(t(taal, 'f_marge'), a.marge_min + ' min') : '',
      getal(a.stops) ? feit(t(taal, 'f_stoptijd'), a.stops + ' × ' + a.stoptijd_min + ' min') : '',
      feit(t(taal, 'f_vertrekken'), a.vertrek_hhmm || ''),
    ].join('');
    if (plan) delen.push('<section><h3>' + esc(t(taal, toonDoel ? 'h_op_tijd' : 'h_vertrek')) + '</h3><ul>' + plan + '</ul></section>');
  }

  const via = wegen(a, taal);
  if (via) delen.push('<section><h3>' + esc(t(taal, 'h_route')) + '</h3><ul><li><span class="l">' + esc(via) + '</span></li></ul></section>');

  if (Array.isArray(a.files)) {
    const files = a.files.map(function (f) {
      // de categorie van TomTom in de gekozen taal; een oudere sensor zonder
      // categorie geeft alleen zijn Nederlandse woord
      const soort = f.categorie && ('cat_' + f.categorie) in TEKST.en
        ? t(taal, 'cat_' + f.categorie)
        : (f.soort || t(taal, 'cat_OTHER'));
      const wat = f.weg ? t(taal, 'op_weg', { wat: soort, weg: f.weg }) : soort;
      const extra = [];
      if (getal(f.snelheid_kmh) !== null) extra.push(f.snelheid_kmh + ' ' + t(taal, 'kmh'));
      if (getal(f.vertraging_min) !== null) extra.push('+' + minuten(f.vertraging_min, taal));
      return feit(wat, extra.join(' · '));
    }).join('');
    delen.push('<section><h3>' + esc(t(taal, 'h_files')) + '</h3><ul>' +
      (files || '<li><span class="l">' + esc(t(taal, 'geen_files')) + '</span></li>') + '</ul></section>');
  }

  if (Array.isArray(a.etappes) && a.etappes.length) {
    const etappes = a.etappes.map(function (e) {
      return '<li><span class="l">' + esc(e.van) + ' → ' + esc(e.naar) + '</span><span class="r">' +
        esc(minuten(e.reistijd_min, taal)) + '</span>' + (config && config.waze ? wazeKnop(e.waze_url, 'Waze', taal) : '') + '</li>';
    }).join('');
    delen.push('<section><h3>' + esc(t(taal, 'h_etappes')) + '</h3><ul>' + etappes + '</ul></section>');
  }

  if (Array.isArray(a.alternatieven) && a.alternatieven.length) {
    const andere = a.alternatieven.map(function (r) {
      const langs = Array.isArray(r.via) && r.via.length ? t(taal, 'via') + ' ' + r.via.join(' · ') : t(taal, 'andere_route');
      const verschil = getal(r.verschil_min);
      return feit(langs, minuten(r.reistijd_min, taal) + (verschil !== null ? ' (+' + verschil + ')' : ''));
    }).join('');
    delen.push('<section><h3>' + esc(t(taal, 'h_andere')) + '</h3><ul>' + andere + '</ul></section>');
  }

  if (Array.isArray(a.punten) && a.punten.length) {
    const punten = a.punten.map(function (p, i) {
      const rol = i === 0 ? t(taal, 'start') : (i === a.punten.length - 1 ? t(taal, 'bestemming') : t(taal, 'stop', { i: i }));
      const gevonden = p.soort === 'adres' && p.gevonden !== p.invoer ? p.gevonden : '';
      return '<li><span class="l">' + esc(rol) + ': ' + esc(p.soort === 'entiteit' ? p.gevonden : p.invoer) +
        (gevonden ? ' → ' + esc(gevonden) : '') + '</span></li>';
    }).join('');
    delen.push('<section><h3>' + esc(t(taal, 'h_adressen')) + '</h3><ul>' + punten + '</ul></section>');
  }

  if (config && config.waze && a.waze_url) delen.push('<div class="knoppen">' + wazeKnop(a.waze_url, '', taal) + '</div>');
  delen.push('<div class="voet">' + (a.bijgewerkt_hhmm ? esc(t(taal, 'bijgewerkt', { t: a.bijgewerkt_hhmm })) + ' · ' : '') +
    esc(t(taal, 'bron', { bron: a.bron || 'TomTom' })) + ' · ' + esc(t(taal, 'kaart_v', { v: VERSIE })) + '</div>');
  return delen.join('');
}

/* ── de kaart ────────────────────────────────────────────────────── */

const TIK_MS = 30000;

class CommuteTimeCard extends HTMLElement {
  static getConfigElement() {
    return document.createElement('commute-time-card-editor');
  }

  static getStubConfig(hass) {
    const staten = hass && hass.states ? hass.states : {};
    const routes = Object.keys(staten).filter(function (id) {
      const a = staten[id] && staten[id].attributes;
      return id.indexOf('sensor.') === 0 && a && a.bron === 'TomTom' && 'route' in a;
    });
    return { entities: routes.slice(0, 3), design: 'default', language: 'en' };
  }

  setConfig(config) {
    // mag niet gooien: Home Assistant maakt er een foutkaart van die de
    // gebruiker niet kan repareren. Wat er ook binnenkomt, hierna staat er
    // iets bruikbaars
    try {
      this._config = normaliseer(config);
      this._stempel = null;
      if (!this.shadowRoot) this.attachShadow({ mode: 'open' });
      this._gebouwd = false;
      if (this._hass) this._ververs(true);
    } catch (err) {
      this._fail(err, 'could not read the configuration');
    }
  }

  /* Home Assistant roept dit aan bij elke statuswijziging in het hele huis,
   * en vangt een uitzondering hier op door de kaart te vervangen door een
   * grijze "Configuratiefout" zonder hass — tot de pagina herlaadt. Zie
   * Skywatch. Dus: alles vangen, melden, en de volgende ronde opnieuw. */
  set hass(hass) {
    this._hass = hass;
    if (!this._config) return;
    try {
      this._ververs(false);
    } catch (err) {
      this._fail(err, 'could not update the card');
    }
  }

  set preview(waarde) {
    const nieuw = Boolean(waarde);
    if (nieuw === this._preview) return;
    this._preview = nieuw;
    this._stempel = null;
    if (this._hass && this._config) {
      try { this._ververs(true); } catch (err) { this._fail(err, 'could not render the preview'); }
    }
  }

  get preview() {
    return this._preview === true;
  }

  getCardSize() {
    const n = this._config ? this._config.entities.length : 1;
    return 1 + Math.max(1, n);
  }

  connectedCallback() {
    if (this._tikker) return;
    const kaart = this;
    // de klok loopt door tussen twee rondes van de sensor; "over 18 min"
    // moet meelopen. Een timer meldt zijn fouten nergens, dus hier vangen
    this._tikker = window.setInterval(function () {
      try {
        if (kaart._hass && kaart._config) kaart._ververs(true);
      } catch (err) {
        kaart._fail(err, 'could not update the time');
      }
    }, TIK_MS);
  }

  /* Home Assistant vangt hier niets op; een fout zou ontsnappen naar wat het
   * dashboard aan het opruimen is. */
  disconnectedCallback() {
    try {
      if (this._tikker) window.clearInterval(this._tikker);
      this._tikker = null;
      if (this._venster && this._venster.open) this._venster.close();
    } catch (err) {
      console.error('commute-time-card: could not clean up', err);
    }
  }

  _bouw() {
    const root = this.shadowRoot;
    const thema = 'thema-' + this._config.design;
    root.innerHTML = '<style>' + STIJL + '</style>' +
      '<ha-card class="' + thema + '">' +
      (this._config.title ? '<div class="kaartkop">' + esc(this._config.title) + '</div>' : '') +
      '<div class="routes"></div></ha-card>' +
      '<dialog class="' + thema + '"><div class="kop"><span class="titel"></span>' +
      '<button class="sluit" aria-label="' + esc(t(taalVan(this._config), 'sluiten')) + '">×</button></div><div class="inhoud"></div></dialog>';
    this._lijst = root.querySelector('.routes');
    this._venster = root.querySelector('dialog');
    const kaart = this;
    this._lijst.addEventListener('click', function (e) {
      try {
        // de Waze-knop is een gewone link en mag het venster niet openen
        if (e.target.closest && e.target.closest('[data-waze]')) return;
        const rij = e.target.closest ? e.target.closest('[data-route]') : null;
        if (rij && kaart._config.details) kaart._open(rij.getAttribute('data-route'));
      } catch (err) {
        kaart._fail(err, 'could not open the details');
      }
    });
    this._venster.querySelector('.sluit').addEventListener('click', function () {
      kaart._venster.close();
    });
    // een tik naast het venster (op de achtergrond) sluit het
    this._venster.addEventListener('click', function (e) {
      if (e.target === kaart._venster) kaart._venster.close();
    });
    this._gebouwd = true;
  }

  _ververs(altijd) {
    const root = this.shadowRoot;
    if (!root) return;
    const staten = (this._hass && this._hass.states) || {};
    const ids = this._config.entities;
    const stempel = ids.map(function (id) {
      const st = staten[id];
      return st ? id + '|' + st.state + '|' + st.last_updated : id + '|weg';
    }).join(';');
    if (!altijd && stempel === this._stempel && this._gebouwd) return;
    this._stempel = stempel;
    if (!this._gebouwd) this._bouw();

    const nu = Date.now();
    const config = this._config;
    const zien = ids.filter(function (id) { return zichtbaar(staten[id], config); });
    if (!ids.length) {
      this.style.display = 'block';
      this._lijst.innerHTML = '<div class="melding">' + esc(t(taalVan(config), 'kies_route')) + '</div>';
      return;
    }
    if (!zien.length && !this.preview) {
      // geen route in beeld: de kaart verbergt zich, zoals bij
      // visible_days in cycling-next-race
      this.style.display = 'none';
      return;
    }
    this.style.display = 'block';
    const lijst = (zien.length ? zien : ids);
    this._lijst.innerHTML = lijst.map(function (id) {
      return routeRij(id, staten[id], config, nu);
    }).join('');
    if (this._venster && this._venster.open && this._openId) this._vulVenster(this._openId);
  }

  _open(id) {
    this._openId = id;
    this._vulVenster(id);
    if (!this._venster.open) {
      if (typeof this._venster.showModal === 'function') this._venster.showModal();
      else this._venster.setAttribute('open', '');
    }
  }

  _vulVenster(id) {
    const st = this._hass && this._hass.states[id];
    const a = (st && st.attributes) || {};
    this._venster.querySelector('.titel').textContent = a.route || id;
    this._venster.querySelector('.inhoud').innerHTML = detail(a, Date.now(), this._config);
  }

  /* Wat er staat als de vangnetten hierboven iets vangen. Een lege kaart en
   * de grijze foutkaart van Home Assistant zien er op een gewoon dashboard
   * hetzelfde uit, en dan wordt er in de YAML gezocht. Dus: naam, versie en
   * de melding, in een kaal blokje dat niets nodig heeft van wat net faalde. */
  _fail(err, waar) {
    console.error('commute-time-card: ' + waar, err);
    this._gebouwd = false;
    try {
      if (!this.shadowRoot) this.attachShadow({ mode: 'open' });
      const melding = err && err.message ? String(err.message) : String(err);
      this.style.display = 'block';
      this.shadowRoot.innerHTML =
        '<div style="padding:14px 16px;border-radius:12px;border-left:4px solid #fb8c00;' +
        'background:rgba(127,127,127,.12);color:var(--primary-text-color,#212121);font-size:13px;line-height:1.45">' +
        '<b>' + esc(t(taalVan(this._config), 'faal_kop')) + '</b><br>' +
        '<span style="opacity:.75">' + esc(t(taalVan(this._config), 'faal_uitleg')) + '</span><br>' +
        '<code style="font-size:11px;word-break:break-word">v' + esc(VERSIE) + ' · ' + esc(waar) + ': ' + esc(melding) + '</code></div>';
    } catch (genest) {
      console.error('commute-time-card: reporting that failed too', genest);
    }
  }
}

/* Aanmelden mag maar één keer. Een tweede `define` met dezelfde naam gooit,
 * en dan stopt de module: de editor eronder komt dan niet meer aan bod. Dat
 * gebeurt als het bestand ook nog als resource is toegevoegd. */
if (!customElements.get('commute-time-card')) customElements.define('commute-time-card', CommuteTimeCard);

/* ── visuele editor ──────────────────────────────────────────────── */

/* De velden van de editor. Labels en uitleg staan in TEKST, als l_<naam> en
 * u_<naam>, zodat de editor dezelfde taal spreekt als de kaart. */
const VELDEN = [
  {
    name: 'entities',
    selector: {
      entity: {
        multiple: true,
        filter: { integration: 'commute_time', domain: 'sensor', device_class: 'duration' },
      },
    },
  },
  { name: 'title', selector: { text: {} } },
  { name: 'design', keuzes: vormgeving },
  { name: 'show', keuzes: tonen },
  { name: 'target', selector: { boolean: {} } },
  { name: 'details', selector: { boolean: {} } },
  { name: 'waze', selector: { boolean: {} } },
  { name: 'language', keuzes: function () { return TAAL; } },
];

/** Het schema voor ha-form, in de gekozen taal. */
function schema(taal) {
  return VELDEN.map(function (v) {
    return {
      name: v.name,
      selector: v.keuzes ? { select: { mode: 'dropdown', options: v.keuzes(taal) } } : v.selector,
    };
  });
}

const EDITOR_STIJL = `
  .eigen { display: flex; flex-direction: column; padding: 8px 0; }
  .eigen > * + * { margin-top: 14px; }
  .eigen label { display: flex; flex-direction: column; font-size: 14px; }
  .eigen label > * + * { margin-top: 4px; }
  .eigen .uitleg { font-size: 12px; opacity: .6; }
  .eigen .schakel { flex-direction: row; align-items: center; }
  .eigen .schakel > * + * { margin-top: 0; margin-left: 10px; }
  .eigen input, .eigen select, .eigen textarea {
    padding: 8px; border-radius: 8px; border: 1px solid var(--divider-color, #444);
    background: var(--card-background-color, #1c1c1c); color: inherit; font: inherit;
  }
  .versie { font-size: 11px; opacity: .5; padding: 10px 0 2px; }
`;

function keuzes(lijst, gekozen) {
  return lijst.map(function (o) {
    return '<option value="' + esc(o.value) + '"' + (o.value === gekozen ? ' selected' : '') + '>' + esc(o.label) + '</option>';
  }).join('');
}

class CommuteTimeCardEditor extends HTMLElement {
  setConfig(config) {
    const vorige = this._config ? this._config.language : null;
    this._config = normaliseer(config);
    if (!this.shadowRoot) this.attachShadow({ mode: 'open' });
    // in de code-editor een andere taal gekozen: de labels opnieuw
    if (this._form && vorige !== this._config.language) this._form = null;
    // ha-form houdt zijn eigen data bij en stuurt die bij een wijziging
    // terug. Verandert de configuratie buiten het formulier om (de
    // code-editor), dan moet het formulier dat weten, anders slaat de
    // volgende klik de oude waarden weer op. Zie cycling-next-race.
    if (this._form) this._form.data = this._config;
    else this._teken();
  }

  set hass(hass) {
    this._hass = hass;
    if (this._form) this._form.hass = hass;
    else if (this._config) this._teken();
  }

  _wijzig(waarden) {
    const config = normaliseer(waarden);
    const andereTaal = this._config && this._config.language !== config.language;
    this._config = config;
    const uit = {
      type: 'custom:commute-time-card',
      entities: config.entities,
      design: config.design,
      show: config.show,
      target: config.target,
      details: config.details,
      waze: config.waze,
      language: config.language,
    };
    // een lege kop voegt niets toe en hoort niet in de YAML
    if (config.title) uit.title = config.title;
    this.dispatchEvent(new CustomEvent('config-changed', {
      detail: { config: uit }, bubbles: true, composed: true,
    }));
    // een andere taal: de labels opnieuw, in de nieuwe taal
    if (andereTaal) {
      this._form = null;
      this._teken();
    }
  }

  _teken() {
    if (!this.shadowRoot || !this._config) return;
    const editor = this;
    const taal = taalVan(this._config);
    const versie = '<div class="versie">' + esc(t(taal, 'editor_versie', { v: VERSIE })) + '</div>';

    if (customElements.get('ha-form')) {
      const form = document.createElement('ha-form');
      form.hass = this._hass;
      form.data = this._config;
      form.schema = schema(taal);
      form.computeLabel = function (v) { return t(taal, 'l_' + v.name); };
      form.computeHelper = function (v) { return t(taal, 'u_' + v.name); };
      form.addEventListener('value-changed', function (e) {
        e.stopPropagation();
        editor._wijzig(e.detail.value);
      });
      this.shadowRoot.innerHTML = '<style>' + EDITOR_STIJL + '</style>';
      this.shadowRoot.appendChild(form);
      const voet = document.createElement('div');
      voet.innerHTML = versie;
      this.shadowRoot.appendChild(voet);
      this._form = form;
      return;
    }

    // terugval zonder ha-form: hetzelfde, met gewone velden
    const c = this._config;
    const veld = function (naam, inhoud) {
      return '<label>' + esc(t(taal, 'l_' + naam)) + inhoud + '</label>';
    };
    const schakel = function (naam, aan) {
      return '<label class="schakel"><input type="checkbox" name="' + naam + '"' + (aan ? ' checked' : '') + '>' +
        esc(t(taal, 'l_' + naam)) + '</label>';
    };
    this.shadowRoot.innerHTML = '<style>' + EDITOR_STIJL + '</style><div class="eigen">' +
      veld('entities', '<span class="uitleg">' + esc(t(taal, 'u_entities_kaal')) + '</span>' +
        '<textarea name="entities" rows="3">' + esc(c.entities.join('\n')) + '</textarea>') +
      veld('title', '<span class="uitleg">' + esc(t(taal, 'u_title')) + '</span>' +
        '<input type="text" name="title" value="' + esc(c.title) + '">') +
      veld('design', '<select name="design">' + keuzes(vormgeving(taal), c.design) + '</select>') +
      veld('show', '<select name="show">' + keuzes(tonen(taal), c.show) + '</select>') +
      schakel('target', c.target) +
      schakel('details', c.details) +
      schakel('waze', c.waze) +
      veld('language', '<select name="language">' + keuzes(TAAL, c.language) + '</select>') +
      versie + '</div>';
    const doos = this.shadowRoot.querySelector('.eigen');
    doos.addEventListener('change', function () {
      const lees = function (n) { return doos.querySelector('[name="' + n + '"]'); };
      editor._wijzig({
        entities: lees('entities').value,
        title: lees('title').value.trim(),
        design: lees('design').value,
        show: lees('show').value,
        target: lees('target').checked,
        details: lees('details').checked,
        waze: lees('waze').checked,
        language: lees('language').value,
      });
    });
  }
}

if (!customElements.get('commute-time-card-editor')) {
  customElements.define('commute-time-card-editor', CommuteTimeCardEditor);
}

window.customCards = window.customCards || [];
if (!window.customCards.some(function (k) { return k.type === 'commute-time-card'; })) {
  window.customCards.push({
    type: 'commute-time-card',
    name: 'Commute Time',
    description: 'Travel time and departure time for your routes, with the traffic on them.',
    preview: false,
    documentationURL: 'https://github.com/vossov/commute-time',
  });
}

console.info('%c COMMUTE-TIME-CARD %c v' + VERSIE + ' ', 'background:#2e7d32;color:#fff;border-radius:3px 0 0 3px', 'background:#444;color:#fff;border-radius:0 3px 3px 0');

export {
  VERSIE,
  VORMGEVING,
  VELDEN,
  TEKST,
  t,
  normaliseer,
  drukte,
  wegen,
  minuten,
  minutenTot,
  fileMinuten,
  weergave,
  zichtbaar,
  routeRij,
  detail,
};
