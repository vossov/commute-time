/*
 * Time to Leave - Lovelace-kaart
 *
 * Wordt door de integratie zelf geregistreerd; je hoeft niets aan resources
 * toe te voegen. Op je dashboard:
 *
 *   type: custom:time-to-leave-card
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
 *   details   true (standaard) opent bij een tik het detailvenster
 *   waze      true (standaard) zet een knop "Rijden met Waze" bij de route
 *
 * De kaart rekent niets uit wat de sensor niet levert. Alleen "over 18 min"
 * telt hij zelf af, vanaf de vertrektijd die de sensor gaf; tussen twee
 * rondes van de sensor zou dat anders stil blijven staan.
 *
 * Ondergrens: Chrome 61 (oude WebViews op wandpanelen). Geen ?. of ??, geen
 * flexbox-gap, geen catch zonder variabele. tests/floor.mjs controleert dat.
 */

/* De versie van deze kaart. Gelijk aan VERSION in const.py en version in
 * manifest.json; tests/test_repo.py bewaakt alle drie. Hij staat hier apart
 * omdat dit bestand statisch is: Home Assistant meldt de versie van de
 * Python-kant, en een browser kan een oudere kaart uit de cache draaien.
 * Het nummer staat in de console en onder in het bewerkscherm. */
const VERSIE = '0.1.0';

const VORMGEVING = [
  { value: 'default', label: 'Standaard (eigen opmaak)' },
  { value: 'ha', label: 'Home Assistant-thema' },
  { value: 'bubble', label: 'Bubble-stijl' },
];
const VORMGEVING_SLEUTELS = VORMGEVING.map(function (v) { return v.value; });

const TONEN = [
  { value: 'window', label: 'Alleen binnen het venster' },
  { value: 'always', label: 'Altijd' },
];

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

/** `34 min`, `1 u 12 min`. */
function minuten(n) {
  const m = getal(n);
  if (m === null) return '';
  if (m < 60) return Math.round(m) + ' min';
  const u = Math.floor(m / 60);
  const rest = Math.round(m - u * 60);
  return rest ? u + ' u ' + rest + ' min' : u + ' u';
}

function km(n) {
  const k = getal(n);
  return k === null ? '' : String(k).replace('.', ',') + ' km';
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
    details: g.details !== false,
    waze: g.waze !== false,
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

/** `via A12 · A27`, of leeg. */
function wegen(a) {
  return Array.isArray(a.via) && a.via.length ? 'via ' + a.via.map(String).join(' · ') : '';
}

/** Minuten tot een ISO-tijdstip, naar boven afgerond; null zonder tijdstip. */
function minutenTot(iso, nuMs) {
  const t = Date.parse(iso);
  if (!isFinite(t)) return null;
  return Math.ceil((t - nuMs) / 60000);
}

/** Wat de route op dit moment moet zeggen: de regel op de tegel, en hoe
 * zwaar hij moet wegen ('normaal', 'let_op', 'te_laat', 'fout'). */
function statusRegel(a, nuMs) {
  const status = String(a.status || '');
  if (status === 'fout') {
    return { tekst: a.fout ? String(a.fout) : 'TomTom gaf geen antwoord', soort: 'fout' };
  }
  if (status === 'buiten_venster') {
    return {
      tekst: a.volgend_venster_tekst
        ? 'Weer in beeld ' + a.volgend_venster_tekst
        : 'Geen venster ingesteld in het rooster',
      soort: 'normaal',
    };
  }
  if (status === 'vertrek_om') {
    const over = minutenTot(a.vertrek, nuMs);
    // de sensor zei "nog niet", maar sindsdien is de tijd verstreken: dan
    // is het nu, ook al heeft de volgende ronde dat nog niet bevestigd
    if (over !== null && over <= 0) return { tekst: 'Vertrek nu', soort: 'let_op' };
    return {
      tekst: 'Vertrek om ' + a.vertrek_hhmm + (over !== null ? ' · over ' + minuten(over) : ''),
      soort: 'normaal',
    };
  }
  if (status === 'vertrek_nu') {
    return { tekst: 'Vertrek nu · aankomst ' + a.aankomst_hhmm, soort: 'let_op' };
  }
  if (status === 'te_laat') {
    return {
      tekst: 'Vertrek nu · aankomst ' + a.aankomst_hhmm + ' · ' + a.te_laat_min + ' min te laat',
      soort: 'te_laat',
    };
  }
  if (status === 'geen_doel' || status === 'doel_voorbij') {
    return { tekst: 'Aankomst ' + a.aankomst_hhmm + ' als je nu vertrekt', soort: 'normaal' };
  }
  return { tekst: '', soort: 'normaal' };
}

/** De tweede regel: voor wanneer, met welke marge, en via welke wegen. */
function tweedeRegel(a) {
  const delen = [];
  if (a.doel_hhmm && a.status !== 'doel_voorbij' && a.status !== 'buiten_venster') {
    delen.push('voor ' + a.doel_hhmm + (getal(a.marge_min) ? ', ' + a.marge_min + ' min marge' : ''));
  }
  const via = wegen(a);
  if (via) delen.push(via);
  const files = Array.isArray(a.files) ? a.files : [];
  const vertraging = files.reduce(function (som, f) { return som + (getal(f.vertraging_min) || 0); }, 0);
  if (vertraging > 0) delen.push(minuten(vertraging) + ' file');
  return delen.join(' · ');
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
  .stip {
    position: absolute; right: -1px; bottom: -1px; width: 12px; height: 12px;
    border-radius: 50%; border: 2px solid var(--card-background-color, #1c1c1c);
  }
  .tekst { flex: 1; min-width: 0; }
  .naam, .regel2 { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .naam { font-size: 15px; font-weight: 700; }
  /* de statusregel is waar het om gaat: liever twee regels dan afgekapt.
     -webkit-line-clamp kent Chrome al lang, ook op oude WebViews */
  .regel {
    font-size: 13.5px; margin-top: 1px; overflow: hidden;
    display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
  }
  .regel.let_op, .regel.te_laat { font-weight: 700; }
  .regel2 { font-size: 12.5px; opacity: .65; margin-top: 1px; }
  /* reistijd en de Waze-knop onder elkaar: naast elkaar namen ze zoveel
     breedte dat de vertrektijd werd afgekapt */
  .rechts { flex: none; display: flex; flex-direction: column; align-items: flex-end; }
  .rechts > * + * { margin-top: 4px; }
  .tijd { font-size: 20px; font-weight: 700; font-variant-numeric: tabular-nums; white-space: nowrap; }
  .tijd .eenheid { font-size: 12px; font-weight: 600; opacity: .7; margin-left: 2px; }
  .waze {
    display: inline-block; padding: 3px 10px; border-radius: 12px;
    border: 1px solid var(--divider-color, rgba(127, 127, 127, .45));
    color: inherit; text-decoration: none; font-size: 12px; font-weight: 700; white-space: nowrap;
  }
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
  li .waze { margin-top: 0; }
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
  /* Nagebouwd, niet overgenomen: Bubble Card is er niet voor nodig. Wat de
     stijl herkenbaar maakt: sterk afgerond, elke route een eigen bel met
     het icoon in een rondje, de reistijd in een pilletje, en een venster
     dat onderaan het scherm plakt. Zoals in cycling-next-race. */
  ha-card.thema-bubble {
    border-radius: 32px; box-shadow: none; border: none; padding: 10px;
    background: none;
  }
  .thema-bubble .kaartkop { padding: 2px 10px 8px; }
  .thema-bubble .routes > * + * { margin-top: 8px; }
  .thema-bubble .route {
    border-radius: 32px; padding: 6px 8px 6px 6px;
    background: var(--ha-card-background, var(--card-background-color, #1c1c1c));
  }
  .thema-bubble .icoon { width: 42px; height: 42px; background: var(--secondary-background-color, rgba(127, 127, 127, .18)); }
  .thema-bubble .tijd {
    display: inline-block; padding: 4px 12px; border-radius: 18px; font-size: 16px;
    background: var(--secondary-background-color, rgba(127, 127, 127, .18));
  }
  .thema-bubble .waze { border-radius: 18px; }
  dialog.thema-bubble {
    border-radius: 32px 32px 0 0; width: 100%; max-width: 640px;
    /* onderaan plakken. Oudere WebViews plaatsen een modale dialog zelf in
       het midden; dan klopt alleen de plek niet, de kaart werkt gewoon. */
    margin: auto auto 0;
  }
`;

/* ── stukjes HTML ────────────────────────────────────────────────── */

function wazeKnop(url, tekst) {
  if (!url || String(url).indexOf('https://waze.com/ul?') !== 0) return '';
  return '<a class="waze" data-waze="1" href="' + esc(url) + '" target="_blank" rel="noopener">' +
    esc(tekst || 'Rijden met Waze') + '</a>';
}

function routeRij(id, st, config, nuMs) {
  const klik = config.details ? ' klik' : '';
  if (!st) {
    return '<div class="route"><div class="tekst"><div class="naam">' + esc(id) +
      '</div><div class="regel2">bestaat niet; kies de reistijd-sensor van een route</div></div></div>';
  }
  const a = st.attributes || {};
  const s = String(st.state);
  if (s === 'unavailable' || (s === 'unknown' && !a.status)) {
    return '<div class="route"><div class="tekst"><div class="naam">' + esc(a.route || id) +
      '</div><div class="regel2">' + (s === 'unavailable' ? 'niet beschikbaar' : 'nog onbekend') +
      ' — kijk in het logboek van Home Assistant op time_to_leave</div></div></div>';
  }
  const regel = statusRegel(a, nuMs);
  const druk = drukte(a);
  let stipKleur = KLEUR[druk];
  if (regel.soort === 'te_laat') stipKleur = KLEUR.file;
  if (regel.soort === 'fout') stipKleur = KLEUR.druk;
  const tijd = getal(a.reistijd_min) !== null
    ? '<div class="tijd">' + Math.round(a.reistijd_min) + '<span class="eenheid">min</span></div>'
    : '';
  // kort op de tegel; in het venster staat "Rijden met Waze" voluit
  const knop = config.waze && a.in_venster ? wazeKnop(a.waze_url, 'Waze') : '';
  return '<div class="route' + klik + '" data-route="' + esc(id) + '">' +
    '<div class="icoon"><ha-icon icon="mdi:car-clock"></ha-icon>' +
    (stipKleur !== 'transparent' ? '<span class="stip" style="background:' + stipKleur + '"></span>' : '') +
    '</div>' +
    '<div class="tekst"><div class="naam">' + esc(a.route || id) + '</div>' +
    '<div class="regel ' + regel.soort + '">' + esc(regel.tekst) + '</div>' +
    (tweedeRegel(a) ? '<div class="regel2">' + esc(tweedeRegel(a)) + '</div>' : '') +
    '</div>' +
    (tijd || knop ? '<div class="rechts">' + tijd + knop + '</div>' : '') +
    '</div>';
}

function feit(links, rechts) {
  if (rechts === '' || rechts == null) return '';
  return '<li><span class="l">' + esc(links) + '</span><span class="r">' + esc(rechts) + '</span></li>';
}

/** De inhoud van het detailvenster voor één route. */
function detail(a, nuMs, config) {
  const regel = statusRegel(a, nuMs);
  const delen = [];
  delen.push('<div class="groot">' + esc(regel.tekst) + '</div>');
  const sub = tweedeRegel(a);
  if (sub) delen.push('<div class="sub">' + esc(sub) + '</div>');

  if (a.status === 'fout' || a.status === 'buiten_venster') {
    if (a.venster_van && a.venster_tot) {
      delen.push('<div class="sub">Venster vandaag ' + esc(a.venster_van) + '–' + esc(a.venster_tot) + '</div>');
    }
    delen.push('<div class="voet">Bron: ' + esc(a.bron || 'TomTom') + '</div>');
    return delen.join('');
  }

  const reistijd = [
    feit('Nu', minuten(a.reistijd_min)),
    feit('Gebruikelijk op dit uur', minuten(a.normaal_min)),
    feit('Zonder verkeer', minuten(a.vrij_min)),
    a.vertrek_hhmm && getal(a.reistijd_bij_vertrek_min) !== null
      ? feit('Verwacht bij vertrek om ' + a.vertrek_hhmm, minuten(a.reistijd_bij_vertrek_min))
      : '',
    feit('Afstand', km(a.afstand_km)),
    feit('Aankomst als je nu vertrekt', a.aankomst_hhmm || ''),
  ].join('');
  delen.push('<section><h3>Reistijd</h3><ul>' + reistijd + '</ul></section>');

  if (a.doel_hhmm) {
    const plan = [
      feit('Aankomen om', a.doel_hhmm),
      feit('Marge', getal(a.marge_min) !== null ? a.marge_min + ' min' : ''),
      getal(a.stops) ? feit('Stoptijd', a.stops + ' × ' + a.stoptijd_min + ' min') : '',
      feit('Vertrekken om', a.vertrek_hhmm || ''),
    ].join('');
    delen.push('<section><h3>Op tijd zijn</h3><ul>' + plan + '</ul></section>');
  }

  if (wegen(a)) delen.push('<section><h3>Route</h3><ul><li><span class="l">' + esc(wegen(a)) + '</span></li></ul></section>');

  if (Array.isArray(a.files)) {
    const files = a.files.map(function (f) {
      const wat = (f.soort || 'hinder') + (f.weg ? ' op de ' + f.weg : '');
      const extra = [];
      if (getal(f.snelheid_kmh) !== null) extra.push(f.snelheid_kmh + ' km/u');
      if (getal(f.vertraging_min) !== null) extra.push('+' + minuten(f.vertraging_min));
      return feit(wat, extra.join(' · '));
    }).join('');
    delen.push('<section><h3>Files en hinder</h3><ul>' +
      (files || '<li><span class="l">TomTom meldt niets op deze route.</span></li>') + '</ul></section>');
  }

  if (Array.isArray(a.etappes) && a.etappes.length) {
    const etappes = a.etappes.map(function (e) {
      return '<li><span class="l">' + esc(e.van) + ' → ' + esc(e.naar) + '</span><span class="r">' +
        esc(minuten(e.reistijd_min)) + '</span>' + (config.waze ? wazeKnop(e.waze_url, 'Waze') : '') + '</li>';
    }).join('');
    delen.push('<section><h3>Etappes</h3><ul>' + etappes + '</ul></section>');
  }

  if (Array.isArray(a.alternatieven) && a.alternatieven.length) {
    const andere = a.alternatieven.map(function (r) {
      const via = Array.isArray(r.via) && r.via.length ? 'via ' + r.via.join(' · ') : 'andere route';
      const verschil = getal(r.verschil_min);
      return feit(via, minuten(r.reistijd_min) + (verschil !== null ? ' (+' + verschil + ')' : ''));
    }).join('');
    delen.push('<section><h3>Andere routes</h3><ul>' + andere + '</ul></section>');
  }

  if (Array.isArray(a.punten) && a.punten.length) {
    const punten = a.punten.map(function (p, i) {
      const rol = i === 0 ? 'Start' : (i === a.punten.length - 1 ? 'Bestemming' : 'Stop ' + i);
      const gevonden = p.soort === 'adres' && p.gevonden !== p.invoer ? p.gevonden : '';
      return '<li><span class="l">' + esc(rol) + ': ' + esc(p.soort === 'entiteit' ? p.gevonden : p.invoer) +
        (gevonden ? ' → ' + esc(gevonden) : '') + '</span></li>';
    }).join('');
    delen.push('<section><h3>Adressen zoals gevonden</h3><ul>' + punten + '</ul></section>');
  }

  if (config.waze && a.waze_url) delen.push('<div class="knoppen">' + wazeKnop(a.waze_url) + '</div>');
  delen.push('<div class="voet">' + (a.bijgewerkt_hhmm ? 'Bijgewerkt ' + esc(a.bijgewerkt_hhmm) + ' · ' : '') +
    'bron: ' + esc(a.bron || 'TomTom') + ' · kaart v' + VERSIE + '</div>');
  return delen.join('');
}

/* ── de kaart ────────────────────────────────────────────────────── */

const TIK_MS = 30000;

class TimeToLeaveCard extends HTMLElement {
  static getConfigElement() {
    return document.createElement('time-to-leave-card-editor');
  }

  static getStubConfig(hass) {
    const staten = hass && hass.states ? hass.states : {};
    const routes = Object.keys(staten).filter(function (id) {
      const a = staten[id] && staten[id].attributes;
      return id.indexOf('sensor.') === 0 && a && a.bron === 'TomTom' && 'route' in a;
    });
    return { entities: routes.slice(0, 3), design: 'default' };
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
      this._fail(err, 'kon de instellingen niet verwerken');
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
      this._fail(err, 'kon de kaart niet bijwerken');
    }
  }

  set preview(waarde) {
    const nieuw = Boolean(waarde);
    if (nieuw === this._preview) return;
    this._preview = nieuw;
    this._stempel = null;
    if (this._hass && this._config) {
      try { this._ververs(true); } catch (err) { this._fail(err, 'kon de voorvertoning niet tekenen'); }
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
        kaart._fail(err, 'kon de tijd niet bijwerken');
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
      console.error('time-to-leave-card: kon niet netjes opruimen', err);
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
      '<button class="sluit" aria-label="Sluiten">×</button></div><div class="inhoud"></div></dialog>';
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
        kaart._fail(err, 'kon het venster niet openen');
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
      this._lijst.innerHTML = '<div class="melding">Kies in de editor de reistijd-sensor van een route.</div>';
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
    console.error('time-to-leave-card: ' + waar, err);
    this._gebouwd = false;
    try {
      if (!this.shadowRoot) this.attachShadow({ mode: 'open' });
      const melding = err && err.message ? String(err.message) : String(err);
      this.style.display = 'block';
      this.shadowRoot.innerHTML =
        '<div style="padding:14px 16px;border-radius:12px;border-left:4px solid #fb8c00;' +
        'background:rgba(127,127,127,.12);color:var(--primary-text-color,#212121);font-size:13px;line-height:1.45">' +
        '<b>Time to Leave kon niet tekenen</b><br>' +
        '<span style="opacity:.75">Dit is geen fout in je configuratie; bij de volgende update probeert de kaart het opnieuw.</span><br>' +
        '<code style="font-size:11px;word-break:break-word">v' + esc(VERSIE) + ' · ' + esc(waar) + ': ' + esc(melding) + '</code></div>';
    } catch (genest) {
      console.error('time-to-leave-card: ook dat melden lukte niet', genest);
    }
  }
}

/* Aanmelden mag maar één keer. Een tweede `define` met dezelfde naam gooit,
 * en dan stopt de module: de editor eronder komt dan niet meer aan bod. Dat
 * gebeurt als het bestand ook nog als resource is toegevoegd. */
if (!customElements.get('time-to-leave-card')) customElements.define('time-to-leave-card', TimeToLeaveCard);

/* ── visuele editor ──────────────────────────────────────────────── */

const VELDEN = [
  {
    name: 'entities',
    label: 'Routes',
    uitleg: 'De reistijd-sensoren van je routes, in de volgorde waarin ze op de kaart staan.',
    selector: {
      entity: {
        multiple: true,
        filter: { integration: 'time_to_leave', domain: 'sensor', device_class: 'duration' },
      },
    },
  },
  {
    name: 'title',
    label: 'Kop',
    uitleg: 'Leeg is geen kop.',
    selector: { text: {} },
  },
  {
    name: 'design',
    label: 'Vormgeving',
    uitleg: 'Eigen opmaak, het thema van Home Assistant, of in de stijl van Bubble Card.',
    selector: { select: { mode: 'dropdown', options: VORMGEVING } },
  },
  {
    name: 'show',
    label: 'Tonen',
    uitleg: 'Alleen binnen het venster uit het rooster van de route, of altijd.',
    selector: { select: { mode: 'dropdown', options: TONEN } },
  },
  {
    name: 'details',
    label: 'Detailvenster bij aantikken',
    uitleg: 'Files, andere routes, etappes en de adressen zoals TomTom ze vond.',
    selector: { boolean: {} },
  },
  {
    name: 'waze',
    label: 'Knop "Rijden met Waze"',
    uitleg: 'Opent Waze met de bestemming; Waze rekent zelf de route vanaf waar je bent.',
    selector: { boolean: {} },
  },
];

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

class TimeToLeaveCardEditor extends HTMLElement {
  setConfig(config) {
    this._config = normaliseer(config);
    if (!this.shadowRoot) this.attachShadow({ mode: 'open' });
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
    this._config = config;
    const uit = {
      type: 'custom:time-to-leave-card',
      entities: config.entities,
      design: config.design,
      show: config.show,
      details: config.details,
      waze: config.waze,
    };
    // een lege kop voegt niets toe en hoort niet in de YAML
    if (config.title) uit.title = config.title;
    this.dispatchEvent(new CustomEvent('config-changed', {
      detail: { config: uit }, bubbles: true, composed: true,
    }));
  }

  _teken() {
    if (!this.shadowRoot || !this._config) return;
    const editor = this;
    const versie = '<div class="versie">Time to Leave-kaart v' + esc(VERSIE) + '</div>';

    if (customElements.get('ha-form')) {
      const form = document.createElement('ha-form');
      form.hass = this._hass;
      form.data = this._config;
      form.schema = VELDEN.map(function (v) { return { name: v.name, selector: v.selector }; });
      form.computeLabel = function (v) {
        const veld = VELDEN.filter(function (x) { return x.name === v.name; })[0];
        return veld ? veld.label : v.name;
      };
      form.computeHelper = function (v) {
        const veld = VELDEN.filter(function (x) { return x.name === v.name; })[0];
        return veld ? veld.uitleg : '';
      };
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
    this.shadowRoot.innerHTML = '<style>' + EDITOR_STIJL + '</style><div class="eigen">' +
      '<label>Routes<span class="uitleg">Reistijd-sensoren, één per regel.</span>' +
      '<textarea name="entities" rows="3">' + esc(c.entities.join('\n')) + '</textarea></label>' +
      '<label>Kop<span class="uitleg">Leeg is geen kop.</span>' +
      '<input type="text" name="title" value="' + esc(c.title) + '"></label>' +
      '<label>Vormgeving<select name="design">' + keuzes(VORMGEVING, c.design) + '</select></label>' +
      '<label>Tonen<select name="show">' + keuzes(TONEN, c.show) + '</select></label>' +
      '<label class="schakel"><input type="checkbox" name="details"' + (c.details ? ' checked' : '') +
      '>Detailvenster bij aantikken</label>' +
      '<label class="schakel"><input type="checkbox" name="waze"' + (c.waze ? ' checked' : '') +
      '>Knop "Rijden met Waze"</label>' + versie + '</div>';
    const doos = this.shadowRoot.querySelector('.eigen');
    doos.addEventListener('change', function () {
      const lees = function (n) { return doos.querySelector('[name="' + n + '"]'); };
      editor._wijzig({
        entities: lees('entities').value,
        title: lees('title').value.trim(),
        design: lees('design').value,
        show: lees('show').value,
        details: lees('details').checked,
        waze: lees('waze').checked,
      });
    });
  }
}

if (!customElements.get('time-to-leave-card-editor')) {
  customElements.define('time-to-leave-card-editor', TimeToLeaveCardEditor);
}

window.customCards = window.customCards || [];
if (!window.customCards.some(function (k) { return k.type === 'time-to-leave-card'; })) {
  window.customCards.push({
    type: 'time-to-leave-card',
    name: 'Time to Leave',
    description: 'Reistijd en vertrektijd van je routes, met de files erop.',
    preview: false,
    documentationURL: 'https://github.com/vossov/time-to-leave',
  });
}

console.info('%c TIME-TO-LEAVE-CARD %c v' + VERSIE + ' ', 'background:#2e7d32;color:#fff;border-radius:3px 0 0 3px', 'background:#444;color:#fff;border-radius:0 3px 3px 0');

export {
  VERSIE,
  VORMGEVING,
  VELDEN,
  normaliseer,
  drukte,
  wegen,
  minuten,
  minutenTot,
  statusRegel,
  tweedeRegel,
  zichtbaar,
  routeRij,
  detail,
};
