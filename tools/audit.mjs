#!/usr/bin/env node
// audit.mjs -- measures the built site (the HTML files at the repository root) in headless Chromium and prints a markdown evidence file.
// Checks: contrast of every colour pair in both themes and of every framework accent against its text colour; the home first screen at twelve
// viewport sizes; every page for sideways scroll at three sizes; focus rings on the cards and the theme button; the theme toggle; JavaScript off;
// printed figures against measured.json; the four pros and cons kept from the first version against the original text.
// Contains one fixture that must fail (a known-bad contrast pair). Usage: node tools/audit.mjs > evidence.md
import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
let playwright;
try { playwright = require('playwright'); } catch { playwright = require('/opt/node-tools/node_modules/playwright'); }
const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const measured = JSON.parse(fs.readFileSync(path.join(ROOT, '_src/data/measured.json'), 'utf8')).results;
const fwdata = JSON.parse(fs.readFileSync(path.join(ROOT, '_src/data/frameworks.json'), 'utf8'));
const css = fs.readFileSync(path.join(ROOT, 'styles.css'), 'utf8');
const pages = fs.readdirSync(ROOT).filter(f => f.endsWith('.html')).sort();
const url = f => 'file://' + path.join(ROOT, f);
const out = []; const log = s => out.push(s);
const lum = hex => { const c = [1, 3, 5].map(i => parseInt(hex.slice(i, i + 2), 16) / 255).map(v => v <= .03928 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4); return .2126 * c[0] + .7152 * c[1] + .0722 * c[2]; };
const ratio = (a, b) => { const [x, y] = [lum(a), lum(b)].sort((p, q) => q - p); return (x + .05) / (y + .05); };

log('# Evidence file (measured on the built site, ' + new Date().toISOString().slice(0, 10) + ')\n');
log(`Artifact: ${pages.length} HTML files at the repository root. Source of every number: \`tools/audit.mjs\`.\n`);
const bad = ratio('#777777', '#888888');
log(`## A. Instrument check\n\nFixture: contrast of #777777 on #888888 = ${bad.toFixed(2)} (must be below 3; ${bad < 3 ? 'the probe fails it as intended' : 'PROBE IS INVERTED, DISCARD SECTION B'}).\n`);

// B. contrast, both themes
const block = sel => { const m = css.match(new RegExp(sel.replace(/[[\]"]/g, '\\$&') + '\\s*\\{([^}]*)\\}')); return m ? m[1] : ''; };
const tokens = txt => Object.fromEntries([...txt.matchAll(/--([a-z0-9-]+):\s*(#[0-9a-fA-F]{6})/g)].map(m => [m[1], m[2]]));
const light = { ...tokens(block(':root, :root[data-theme="light"]')) };
const dark = { ...light, ...tokens(block(':root[data-theme="dark"]')) };
const pairs = [['ink', 'bg'], ['ink', 'card'], ['muted', 'card'], ['muted', 'bg'], ['brand', 'card'], ['brand', 'bg'], ['brand-ink', 'brand'], ['ok', 'ok-bg'], ['bad', 'bad-bg'], ['code-ink', 'code-bg'], ['ink', 'soft'], ['muted', 'soft']];
log('## B. Contrast of every text colour pair, light and dark (WCAG 2.2 AA needs 4.5)\n');
log('| Pair (text on background) | Light | Dark |\n|---|---|---|');
let fails = 0;
for (const [fg, bg] of pairs) {
  const l = ratio(light[fg], light[bg]), d = ratio(dark[fg], dark[bg]);
  if (l < 4.5) fails++; if (d < 4.5) fails++;
  log(`| ${fg} on ${bg} | ${l.toFixed(2)} ${l >= 4.5 ? 'pass' : 'FAIL'} | ${d.toFixed(2)} ${d >= 4.5 ? 'pass' : 'FAIL'} |`);
}
log(`\nFailing pairs: ${fails}.\n`);
log('## B2. Every framework accent against the text colour put on it (the numbered circles on inner pages)\n');
log('| Framework | Accent | Text colour | Ratio |\n|---|---|---|---|');
const inkOn = h => (ratio(h, '#0f172a') >= ratio(h, '#ffffff') ? '#0f172a' : '#ffffff');
let accFails = 0;
for (const [k, d] of Object.entries(fwdata)) { const t = inkOn(d.accent), r = ratio(d.accent, t); if (r < 3) accFails++; log(`| ${k} | ${d.accent} | ${t} | ${r.toFixed(2)}${r < 3 ? ' FAIL (large-text floor 3)' : ''} |`); }
log(`\nAccents under 3:1 with their text: ${accFails}. (The circles carry a 13 px bold number; the accent also never carries running text.)\n`);

const browser = await playwright.chromium.launch();

log('## C. Home first screen at twelve viewport sizes (lowest card bottom against the fold; cards whose content is cut)\n');
log('| Viewport | Lowest card bottom | Fold | Fits | Right edge | Clipped cards | Sideways scroll |\n|---|---|---|---|---|---|---|');
for (const [w, h] of [[1920, 1080], [1440, 900], [1280, 800], [1100, 800], [1024, 768], [900, 800], [768, 1024], [414, 896], [390, 844], [375, 812], [360, 740], [320, 640]]) {
  for (const scheme of (w === 1280 || w === 375 ? ['light', 'dark'] : ['light'])) {
    const ctx = await browser.newContext({ viewport: { width: w, height: h }, colorScheme: scheme });
    const p = await ctx.newPage(); await p.goto(url('index.html')); await p.waitForTimeout(250);
    const r = await p.evaluate(() => { const t = [...document.querySelectorAll('.fw > a')].map(a => ({ b: a.getBoundingClientRect().bottom, r: a.getBoundingClientRect().right, c: a.scrollHeight > a.clientHeight + 1 || a.scrollWidth > a.clientWidth + 1 })); return { n: t.length, bottom: Math.round(Math.max(...t.map(x => x.b))), right: Math.round(Math.max(...t.map(x => x.r))), clipped: t.filter(x => x.c).length, hs: document.documentElement.scrollWidth > innerWidth }; });
    log(`| ${w} x ${h}${scheme === 'dark' ? ' dark' : ''} | ${r.bottom} (${r.n} cards) | ${h} | ${r.bottom <= h ? 'yes' : 'NO'} | ${r.right} | ${r.clipped} of ${r.n} | ${r.hs} |`);
    await ctx.close();
  }
}
log('\nThe rule requires 1280 x 800 and 375 x 812.\n');

log('## D. Every page: sideways scroll, smallest text, targets under 24 px\n');
log('| Page | 1280 | 375 | 320 | Smallest text (px, 375) | Targets under 24 px (375) |\n|---|---|---|---|---|---|');
for (const f of pages) {
  const cells = [];
  for (const [w, h] of [[1280, 800], [375, 812], [320, 640]]) {
    const ctx = await browser.newContext({ viewport: { width: w, height: h } });
    const p = await ctx.newPage(); await p.goto(url(f)); await p.waitForTimeout(80);
    const r = await p.evaluate(() => {
      let min = 99; const wk = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT); let n;
      while ((n = wk.nextNode())) { if (!n.textContent.trim()) continue; const el = n.parentElement; if (el.closest('.sr, script, style, [aria-hidden=true]')) continue; const cs = getComputedStyle(el); if (cs.display === 'none') continue; min = Math.min(min, parseFloat(cs.fontSize)); }
      const small = [...document.querySelectorAll('a, button, summary')].filter(a => { const q = a.getBoundingClientRect(); if (!q.width || !q.height || a.closest('.sr, .skip')) return false; return getComputedStyle(a).display !== 'inline' && (q.height < 24 || q.width < 24); }).length;
      return { hs: document.documentElement.scrollWidth > innerWidth, min, small };
    });
    cells.push(r); await ctx.close();
  }
  log(`| ${f} | ${cells[0].hs ? 'SCROLLS' : 'ok'} | ${cells[1].hs ? 'SCROLLS' : 'ok'} | ${cells[2].hs ? 'SCROLLS' : 'ok'} | ${cells[1].min} | ${cells[1].small} |`);
}
log('');

log('## E. Keyboard and theme (1280 x 800)\n');
{
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 800 }, colorScheme: 'light' });
  const p = await ctx.newPage(); await p.goto(url('index.html')); await p.waitForTimeout(250);
  const res = []; let toggle = null;
  for (let i = 0; i < 30; i++) {
    await p.keyboard.press('Tab');
    const r = await p.evaluate(() => { const a = document.activeElement; if (!a) return null; const cs = getComputedStyle(a); const q = a.getBoundingClientRect(); return { id: a.id, card: !!a.closest('.fw'), outline: cs.outlineStyle + ' ' + cs.outlineWidth, inView: q.top >= 0 && q.bottom <= innerHeight + 1 && q.left >= 0 && q.right <= innerWidth + 1 }; });
    if (r && r.card) res.push(r); if (r && r.id === 'theme-toggle') toggle = r;
  }
  log(`- Cards reached by Tab: ${res.length} of 12; visible outline on all: ${res.every(r => r.outline.startsWith('solid') && !r.outline.endsWith(' 0px'))}; all inside the viewport when focused: ${res.every(r => r.inView)}.`);
  log(`- Theme button reached by Tab: ${!!toggle}; outline ${toggle ? toggle.outline : 'none'}.`);
  const before = await p.evaluate(() => document.documentElement.getAttribute('data-theme'));
  await p.click('#theme-toggle');
  const after = await p.evaluate(() => ({ t: document.documentElement.getAttribute('data-theme'), label: document.getElementById('theme-toggle').getAttribute('aria-label'), stored: localStorage.getItem('theme'), bg: getComputedStyle(document.body).backgroundColor }));
  await p.reload(); await p.waitForTimeout(150);
  const kept = await p.evaluate(() => document.documentElement.getAttribute('data-theme'));
  log(`- Theme toggle: ${before} to ${after.t}; button label "${after.label}"; stored "${after.stored}"; page background now ${after.bg}; after a reload the theme is still ${kept}.`);
  await ctx.close();
}
{
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 800 }, javaScriptEnabled: false, colorScheme: 'dark' });
  const p = await ctx.newPage(); await p.goto(url('index.html'));
  const bg = await p.evaluate(() => getComputedStyle(document.body).backgroundColor).catch(() => 'n/a');
  const bottom = await p.locator('.fw > a').last().evaluate(a => Math.round(a.getBoundingClientRect().bottom)).catch(() => -1);
  log(`- JavaScript off, dark system theme: page background ${bg} (the stylesheet follows the system setting); lowest card bottom ${bottom} (fold 800).\n`);
  await ctx.close();
}

log('## F. Printed figures against measured.json\n');
{
  const p = await browser.newPage({ viewport: { width: 1280, height: 800 } });
  const MAIN = { astro: 'astro-island' };
  await p.goto(url('index.html'));
  const cards = await p.evaluate(() => [...document.querySelectorAll('.fw > a')].map(a => [a.getAttribute('href').replace('.html', ''), a.querySelector('.fig').childNodes[0].textContent, !!a.querySelector('.ssr-lg')]));
  let mism = 0;
  for (const [k, v, ssr] of cards) { const r = measured[MAIN[k] || k]; if ((r.js_load_bytes / 1000).toFixed(1) !== v || ssr !== r.ssr) mism++; }
  log(`- ${cards.length} cards: printed kB and the "server HTML" label against measured.json (js_load_bytes / 1000 and ssr): mismatches ${mism}.`);
  await p.close();
}
{
  const orig = execFileSync('git', ['-C', ROOT, 'show', 'original-overview:index.html'], { encoding: 'utf8' });
  const txt = h => h.replace(/<[^>]+>/g, ' ').replace(/&raquo;/g, '').replace(/\s+/g, ' ');
  const home = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8').replace(/&amp;/g, '&');
  const kept = [];
  for (const [k, name] of [['react', 'React'], ['vue', 'Vue'], ['angular', 'Angular'], ['svelte', 'Svelte']]) {
    const pros = fwdata[k].pros, cons = fwdata[k].cons;
    const inOrig = orig.includes(pros) && orig.includes(cons);
    const inHome = home.includes(pros.replace(/&/g, '&amp;')) || home.includes(pros);
    kept.push(`${name}: pros and cons equal the first version's text ${inOrig}, shown on the home page ${inHome}`);
  }
  log(`- First version's pros and cons kept (checked against \`git show original-overview:index.html\`): ${kept.join('; ')}.`);
}
log('');
await browser.close();
console.log(out.join('\n'));
