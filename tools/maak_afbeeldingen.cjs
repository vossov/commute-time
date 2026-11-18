/*
 * Maakt de afbeeldingen voor de README: docs/img/*.png.
 *
 *   npm install --no-save playwright   (of een bestaande Playwright gebruiken)
 *   node tools/maak_afbeeldingen.cjs
 *
 * Wat je ziet is de echte kaart (custom_components/time_to_leave/www/), getekend
 * in Chromium tegen de attributen uit tests/fixtures/sensor.json, met een eigen
 * `ha-card` en `ha-icon` en de kleuren van het standaardthema van Home
 * Assistant. Het zijn dus voorbeeldgegevens en geen schermafbeeldingen uit
 * Home Assistant zelf; de README zegt dat erbij.
 *
 * De twee iconen zijn paden uit Material Design Icons (Pictogrammers,
 * Apache-2.0): mdi:car-clock en mdi:navigation-variant.
 */
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const WORTEL = path.resolve(__dirname, '..');
const UIT = path.resolve(process.argv[2] || path.join(WORTEL, 'docs', 'img'));
const kaart = fs.readFileSync(path.join(WORTEL, 'custom_components/time_to_leave/www/time-to-leave-card.js'), 'utf8');
const staten = JSON.parse(fs.readFileSync(path.join(WORTEL, 'tests/fixtures/sensor.json'), 'utf8'));

const MDI = {
  'car-clock': 'M23 8C23 4.13 19.87 1 16 1C12.47 1 9.57 3.61 9.08 7H4.5C3.84 7 3.28 7.42 3.08 8L1 14V22C1 22.55 1.45 23 2 23H3C3.55 23 4 22.55 4 22V21H16V22C16 22.55 16.45 23 17 23H18C18.55 23 19 22.55 19 22V14.32C21.36 13.19 23 10.79 23 8M4.5 8.5H9.03C9.15 10.26 9.92 11.84 11.11 13H3L4.5 8.5M4.5 18C3.67 18 3 17.33 3 16.5S3.67 15 4.5 15 6 15.67 6 16.5 5.33 18 4.5 18M15.5 18C14.67 18 14 17.33 14 16.5S14.67 15 15.5 15 17 15.67 17 16.5 16.33 18 15.5 18M16 13C14.61 13 13.44 12.5 12.47 11.53C11.5 10.56 11 9.39 11 8C11 6.64 11.5 5.46 12.47 4.5C13.44 3.5 14.61 3 16 3C17.36 3 18.54 3.5 19.5 4.5C20.5 5.46 21 6.64 21 8C21 9.39 20.5 10.56 19.5 11.53C18.54 12.5 17.36 13 16 13M16.5 8.25L19.36 9.94L18.61 11.16L15 9V4H16.5V8.25Z',
  'navigation-variant': 'M21 3L3 10.53V11.5L9.84 14.16L12.5 21H13.46L21 3Z',
};

const DONKER = '--primary-background-color:#111111;--secondary-background-color:#282828;--card-background-color:#1c1c1c;--primary-text-color:#e1e1e1;--divider-color:#3a3a3a;--primary-color:#03a9f4';
const LICHT = '--primary-background-color:#fafafa;--secondary-background-color:#e5e5e5;--card-background-color:#ffffff;--primary-text-color:#212121;--divider-color:#e0e0e0;--primary-color:#03a9f4';

// de voorbeeldroutes: wat er in de fixture staat, met eigen namen en getallen
function voorbeelden() {
  const b = staten.berekend;
  // de getallen horen bij elkaar: 33 min zonder verkeer + 8 min vertraging = 41 min,
  // en wie nu om 07:34 vertrekt is er om 08:15. Anders staat er in het venster
  // "nu 41 min, gebruikelijk 3 min", en dat is geen voorbeeld maar een tegenspraak.
  const druk = Object.assign({}, b, { route: 'Naar kantoor', reistijd_min: 41, vertraging_min: 8, vrij_min: 33,
    normaal_min: 36, reistijd_bij_vertrek_min: 38, afstand_km: 31.4, aankomst_hhmm: '08:15', via: ['A2', 'A10'],
    files: [{ soort: 'file', weg: 'A10', vertraging_min: 8, snelheid_kmh: 41, ernst: 1 }] });
  const zonder = Object.assign({}, staten.zonder_doel, { route: 'Naar de sportschool', reistijd_min: 18, vertraging_min: 0, vrij_min: 18, via: ['N237'], files: [] });
  const nu = Object.assign({}, b, { route: 'Naar de tennisbaan', status: 'vertrek_nu', reistijd_min: 22, vertraging_min: 1, vrij_min: 21, via: ['N237'], files: [] });
  const laat = Object.assign({}, b, { route: 'Naar school en werk', status: 'te_laat', te_laat_min: 11, reistijd_min: 47,
    vertraging_min: 16, vrij_min: 31, via: ['A12', 'A27'], files: [{ soort: 'file', weg: 'A12', vertraging_min: 11, snelheid_kmh: 23, ernst: 2 }] });
  const stil = Object.assign({}, staten.buiten_venster, { route: 'Naar oma' });
  const st = (a, s) => ({ state: s, attributes: a, last_updated: '1' });
  return { states: {
    'sensor.kantoor': st(druk, '41'), 'sensor.sport': st(zonder, '18'), 'sensor.tennis': st(nu, '22'),
    'sensor.school': st(laat, '47'), 'sensor.oma': st(stil, 'unknown'),
  } };
}

const ROUTES = ['sensor.kantoor', 'sensor.sport', 'sensor.tennis', 'sensor.school', 'sensor.oma'];

(async () => {
  fs.mkdirSync(UIT, { recursive: true });
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 900, height: 1300 }, deviceScaleFactor: 2 });
  const fouten = [];
  page.on('pageerror', (e) => fouten.push(String(e)));
  page.on('console', (m) => { if (m.type() === 'error') fouten.push(m.text()); });

  await page.setContent(`<!doctype html><html><head><style>
    body{margin:0;background:#111;font-family:Roboto,Arial,sans-serif}
    /* inline-flex: het blok is zo breed als zijn inhoud, geen lege strook ernaast */
    .rij{display:inline-flex;align-items:flex-start}
    .doos{box-sizing:border-box;padding:16px;background:var(--primary-background-color);color:var(--primary-text-color)}
    .doos > * + *{margin-top:10px}
    .doos .k{font-size:12px;opacity:.55;margin:0 0 6px 4px}
  </style></head><body><div id="werk"></div></body></html>`);

  await page.evaluate((MDI) => {
    Date.now = () => Date.parse('2026-11-17T07:34:00+01:00');
    // ha-card zoals Home Assistant: de achtergrond staat op :host, zodat een
    // regel van buiten (onze stijl) hem kan overschrijven
    customElements.define('ha-card', class extends HTMLElement {
      constructor() {
        super();
        this.attachShadow({ mode: 'open' }).innerHTML =
          '<style>:host{display:block;background:var(--ha-card-background,var(--card-background-color));' +
          'border-radius:var(--ha-card-border-radius,12px);border:1px solid var(--divider-color);box-sizing:border-box}</style><slot></slot>';
      }
    });
    customElements.define('ha-icon', class extends HTMLElement {
      static get observedAttributes() { return ['icon']; }
      constructor() {
        super();
        this.attachShadow({ mode: 'open' }).innerHTML =
          '<style>:host{display:inline-flex;width:var(--mdc-icon-size,24px);height:var(--mdc-icon-size,24px)}' +
          'svg{width:100%;height:100%;fill:currentColor;display:block}</style><span id="i"></span>';
      }
      connectedCallback() { this.teken(); }
      attributeChangedCallback() { this.teken(); }
      teken() {
        const p = MDI[(this.getAttribute('icon') || '').replace('mdi:', '')];
        if (p) this.shadowRoot.getElementById('i').innerHTML = '<svg viewBox="0 0 24 24"><path d="' + p + '"/></svg>';
      }
    });
  }, MDI);
  await page.addScriptTag({ content: kaart, type: 'module' });
  await page.waitForFunction(() => customElements.get('time-to-leave-card'));

  // één blok op de pagina zetten en er een afbeelding van nemen
  async function neem(naam, bouw, args) {
    await page.evaluate(({ bouw, args }) => {
      const werk = document.getElementById('werk');
      werk.innerHTML = '';
      // eslint-disable-next-line no-new-func
      new Function('werk', 'args', bouw)(werk, args);
    }, { bouw, args });
    await page.waitForTimeout(150);
    await page.locator('#blok').screenshot({ path: path.join(UIT, naam) });
    console.log('geschreven:', naam);
  }

  const hass = voorbeelden();
  const kaartDoos = `
    function doos(klasse, vars, titel, config) {
      const d = document.createElement('div'); d.className = 'doos'; d.setAttribute('style', vars + ';width:' + (config.breedte || 420) + 'px');
      d.innerHTML = '<div class="k">' + titel + '</div>';
      const k = document.createElement('time-to-leave-card');
      k.setConfig(config.kaart); k.hass = args.hass; d.appendChild(k); return d;
    }`;

  // 1. de Bubble-stijl, donker en licht naast elkaar
  await neem('bubble.png', kaartDoos + `
    const rij = document.createElement('div'); rij.className = 'rij'; rij.id = 'blok';
    const kaart = { entities: args.routes, design: 'bubble', show: 'always' };
    rij.appendChild(doos('', args.donker, 'Bubble-stijl, donker', { kaart }));
    rij.appendChild(doos('', args.licht, 'Bubble-stijl, licht', { kaart }));
    werk.appendChild(rij);`, { hass, routes: ROUTES, donker: DONKER, licht: LICHT });

  // 2. de andere twee vormgevingen
  await neem('vormgevingen.png', kaartDoos + `
    const rij = document.createElement('div'); rij.className = 'rij'; rij.id = 'blok';
    const alle = args.routes.slice(0, 4);
    rij.appendChild(doos('', args.donker, 'Standaard (design: default)', { kaart: { entities: alle, design: 'default', show: 'always' } }));
    rij.appendChild(doos('', args.donker, 'Home Assistant-thema (design: ha)', { kaart: { entities: alle, design: 'ha', show: 'always', title: 'Onderweg' } }));
    werk.appendChild(rij);`, { hass, routes: ROUTES, donker: DONKER });

  // 3. het detailvenster
  await page.setViewportSize({ width: 420, height: 1400 });
  await neem('venster.png', kaartDoos + `
    const d = doos('', args.donker, '', { breedte: 420, kaart: { entities: ['sensor.kantoor'], design: 'bubble', show: 'always' } });
    werk.appendChild(d);
    const k = d.querySelector('time-to-leave-card');
    k.shadowRoot.querySelector('[data-route="sensor.kantoor"]').click();
    // alleen de tegel verbergen: het venster staat naast hem in de schaduw-DOM
    // en verdwijnt mee als je de hele kaart met display: none wegzet
    k.shadowRoot.querySelector('ha-card').style.visibility = 'hidden';
    // de focusring op de sluitknop komt van het programmatisch klikken
    if (k.shadowRoot.activeElement) k.shadowRoot.activeElement.blur();
    const dlg = k.shadowRoot.querySelector('dialog'); dlg.id = 'blok';`, { hass, donker: DONKER });

  // 4. de banner, met de echte kaart rechts
  await page.setViewportSize({ width: 1200, height: 300 });
  await page.evaluate(({ MDI, hass }) => {
    const werk = document.getElementById('werk');
    werk.innerHTML = '';
    const b = document.createElement('div'); b.id = 'blok';
    b.setAttribute('style', 'width:1200px;height:300px;box-sizing:border-box;display:flex;align-items:center;justify-content:space-between;' +
      'padding:0 56px;background:linear-gradient(135deg,#161b27 0%,#26324d 100%);color:#eef2f8;' +
      '--secondary-background-color:#34405c;--card-background-color:#1a2133;--primary-text-color:#eef2f8;--divider-color:#3a3a3a');
    b.innerHTML = '<div style="display:flex;align-items:center">' +
      '<div style="width:100px;height:100px;border-radius:50%;background:rgba(67,160,71,.22);color:#6fd072;display:flex;align-items:center;justify-content:center;margin-right:24px;flex:none">' +
      '<svg viewBox="0 0 24 24" width="58" height="58" fill="currentColor"><path d="' + MDI['car-clock'] + '"/></svg></div>' +
      '<div><div style="font-size:56px;font-weight:700;letter-spacing:-1px;line-height:1.05;white-space:nowrap">Time to Leave</div>' +
      '<div style="font-size:22px;opacity:.78;margin-top:10px;white-space:nowrap">Rijtijd en vertrektijd voor je vaste routes</div></div></div>' +
      '<div id="kaartplek" style="width:400px;flex:none"></div>';
    werk.appendChild(b);
    // in de banner korte regels, zodat geen pil over drie regels loopt
    const kort = JSON.parse(JSON.stringify(hass));
    Object.assign(kort.states['sensor.kantoor'].attributes, { via: ['A2'], files: [] });
    const k = document.createElement('time-to-leave-card');
    k.setConfig({ entities: ['sensor.kantoor', 'sensor.tennis'], design: 'bubble', show: 'always' });
    k.hass = kort;
    b.querySelector('#kaartplek').appendChild(k);
  }, { MDI, hass });
  await page.waitForTimeout(200);
  await page.locator('#blok').screenshot({ path: path.join(UIT, 'banner.png') });
  console.log('geschreven: banner.png');

  console.log('fouten:', JSON.stringify(fouten));
  await browser.close();
  if (fouten.length) process.exit(1);
})();
