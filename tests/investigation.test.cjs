// Offline tests for the real inline page code. No network, SDK, or DOM package.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');
const ROOT = path.resolve(__dirname, '..');
const d3 = require('../src/vendor/d3.v7.9.0.min.js');

// Minimal DOM for the list/drawer only. Chart geometry is checked in a browser.
class Element {
  constructor(tag, text = '') {
    this.tagName = tag;
    this.nodeType = tag === '#text' ? 3 : 1;
    this.children = [];
    this.attributes = {};
    this.events = {};
    this._text = text;
    this.classList = new Set();
    this.classList.remove = this.classList.delete.bind(this.classList);
    this.style = {};
  }
  set textContent(text) { this._text = String(text); this.children = []; }
  get textContent() { return this._text + this.children.map(n => n.textContent).join(''); }
  setAttribute(key, value) { this.attributes[key] = String(value); }
  addEventListener(key, fn) { this.events[key] = fn; }
  append(...nodes) { this.children.push(...nodes); }
  appendChild(node) { this.append(node); return node; }
  replaceChildren(...nodes) { this._text = ''; this.children = [...nodes]; }
  focus() {}
  click() { this.events.click?.({currentTarget: this}); }
}
const descendants = (node, tag) => node.children.flatMap(n => [
  ...(n.tagName === tag ? [n] : []), ...descendants(n, tag),
]);

function pageHarness(data) {
  const template = fs.readFileSync(path.join(ROOT, 'src/page.template.html'), 'utf8');
  const nodes = new Map([...template.matchAll(/id="([^"]+)"/g)].map(m => [m[1], new Element('div')]));
  nodes.get('pg-data').textContent = JSON.stringify(data);
  const document = {
    querySelector: selector => nodes.get(selector.slice(1)) || null,
    querySelectorAll: () => [],
    createElement: tag => new Element(tag),
    createTextNode: text => new Element('#text', text),
    addEventListener: () => {},
    documentElement: new Element('html'),
  };
  let script = template.slice(template.lastIndexOf('<script>') + '<script>'.length, template.lastIndexOf('</script>'));
  // Suppress startup rendering/polling, not the functions being exercised.
  script = script.replace("setView(location.hash.slice(1) === 'proofs' ? 'proofs' : 'attacks', false);", '').replace('poll(true);', '');
  const end = script.lastIndexOf('})();');
  script = script.slice(0, end) + `globalThis.page = {
    ingest, renderHero, render,
    renderInvestigation: typeof renderInvestigation === 'function' ? renderInvestigation : null,
    get incidents() { return INC; }, get smallChain() { return SMALL_CHAIN; }
  };` + script.slice(end);
  const context = vm.createContext({
    document, d3, URL, innerWidth: 1200,
    localStorage: {getItem: () => null}, addEventListener: () => {}, setInterval: () => {},
  });
  vm.runInContext(script, context, {filename: 'page.template.html'});
  return {page: context.page, nodes, template};
}
const readData = () => JSON.parse(fs.readFileSync(path.join(ROOT, 'site/data.json'), 'utf8'));

// Synthetic names deliberately prevent a Binance-specific keyword rule.
const fixture = (extra = {}) => ({
  id: 'fixture', victim: 'Example exchange', date: '2026-10-29',
  claim_status: 'reported', impact: 'Cause and amount remain unconfirmed.',
  code_flaw: false, zero_day: false, under_investigation: true,
  band: 'Smart contracts & chains', theme: 'crypto', func: 'Unknown',
  source_url: 'https://example.com/incident', amount_lost_usd: '', people: 0, ...extra,
});

test('marked incidents have a headline highlight directly above the treemap caption, source, and drawer', () => {
  const data = readData();
  data.incidents = [fixture(), fixture({id: 'unmarked', victim: 'Binance', under_investigation: false})];
  const {page, nodes, template} = pageHarness(data);
  const hero = template.match(/<header class="hero wrap">([\s\S]*?)<\/header>/)[1];
  assert.ok(/<aside[^>]+id="a-investigation"[\s\S]*?<\/aside>\s*<p[^>]+id="dots-sub"/.test(hero),
    'the incident highlight must be directly before the treemap caption inside the hero');
  assert.ok(!/<section[^>]+id="a-investigation"/.test(template), 'no separate investigation section');
  assert.ok(!/>Under investigation</.test(template), 'no standalone Under investigation heading');
  assert.equal(typeof page.renderInvestigation, 'function');
  assert.match(page.render.toString(), /renderInvestigation\(\)/, 'the normal render path must include the highlight');
  page.renderInvestigation();
  const section = nodes.get('a-investigation'), list = nodes.get('investigation-list');
  assert.equal(section.hidden, false);
  const buttons = descendants(list, 'button');
  assert.equal(buttons.length, 1);
  assert.equal(buttons[0].textContent, 'Example exchange incident: what we know so far');
  assert.match(list.textContent, /Cause unconfirmed/);
  assert.match(list.textContent, /Excluded from code-flaw totals/);
  const links = descendants(list, 'a');
  assert.equal(links.length, 1);
  assert.equal(links[0].attributes.href, 'https://example.com/incident');
  assert.equal(links[0].attributes.rel, 'noopener noreferrer');
  buttons[0].click();
  assert.equal(nodes.get('dr-t').textContent, 'Example exchange');
  assert.match(nodes.get('dr-k').textContent, /reported/);
  assert.match(nodes.get('dr-b').textContent, /Cause and amount remain unconfirmed/);
  assert.equal(nodes.get('drawer').attributes['aria-hidden'], 'false');
});

test('the optional marker is strict, never includes code flaws, and hides when empty', () => {
  const data = readData();
  data.incidents = [fixture(), fixture({id: 'false', under_investigation: false}),
    fixture({id: 'string', under_investigation: 'true'}),
    fixture({id: 'code', code_flaw: true, amount_lost_usd: '10000000'})];
  const {page, nodes} = pageHarness(data);
  assert.equal(typeof page.renderInvestigation, 'function');
  page.renderInvestigation();
  assert.equal(descendants(nodes.get('investigation-list'), 'button').length, 1);
  data.incidents = data.incidents.slice(1);
  page.ingest(data);
  page.renderInvestigation();
  assert.equal(nodes.get('a-investigation').hidden, true);
  assert.equal(nodes.get('investigation-list').children.length, 0);
});

test('investigation text is not HTML and unsafe source schemes never become links', () => {
  const data = readData();
  data.incidents = [fixture({victim: '<img src=x onerror=alert(1)>', source_url: 'javascript:alert(1)'})];
  const {page, nodes} = pageHarness(data);
  assert.equal(typeof page.renderInvestigation, 'function');
  page.renderInvestigation();
  const list = nodes.get('investigation-list');
  assert.match(list.textContent, /<img src=x onerror=alert\(1\)>/);
  assert.equal(descendants(list, 'img').length, 0);
  assert.equal(descendants(list, 'a').length, 0);
});

test('Binance is absent from chart inputs and all headline code-flaw metrics', () => {
  const data = readData();
  const {page, nodes} = pageHarness(data);
  const totals = () => {
    page.renderHero();
    return {ids: Array.from(page.incidents, r => r.id), stats: nodes.get('a-stats').textContent};
  };
  const withBinance = totals();
  const archive = JSON.parse(fs.readFileSync(path.join(ROOT, 'data/archive/incidents.json'), 'utf8'));
  const row = [...data.incidents, ...archive].find(r => r.victim === 'Binance' && r.date === '2026-10-29');
  assert.ok(row);
  assert.equal(page.incidents.some(r => r.id === row.id), false);
  assert.equal(page.smallChain.some(r => r.id === row.id), false);
  data.incidents = data.incidents.filter(r => r.id !== row.id);
  page.ingest(data);
  assert.deepEqual(totals(), withBinance);

});
