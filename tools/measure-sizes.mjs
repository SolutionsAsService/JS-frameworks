#!/usr/bin/env node
// measure-sizes.mjs -- the single measurement procedure for every framework.
//
// PROCEDURE (identical for all targets):
//  1. Target is either a static directory (served by a tiny built-in static
//     server, no compression, index.html fallback) or an http(s) URL already
//     served by the framework's own production server (SSR / htmx apps).
//  2. Open the page in headless Chromium (Playwright) in a FRESH browser
//     context (empty cache, no storage), wait for load + network idle.
//  3. Record every JavaScript response (content-type contains "javascript"/
//     "ecmascript", or URL path ends in .js/.mjs). Size of each = length of
//     zlib gzip level 9 of the raw response body (our own gzip; server
//     compression is irrelevant). js_load_bytes = sum, js_files = count.
//  4. Click the first <button> (or the selector given) once, wait for network
//     idle, and record JS responses requested after the click as
//     js_after_click_bytes (same gzip-9 method).
//  5. Verify the visible text goes from "count: 0" to "count: 1"; throw (exit
//     non-zero) otherwise.
//  6. (informational) inline_js_gz = sum of gzip-9 sizes of inline <script> blocks in
//     the initial HTML (excluding JSON/importmap data blocks); NOT included in js_load_bytes.
//  7. html_gz = gzip-9 size of the initial document response body.
//     ssr = plain fetch() of the URL (no JS) contains "count: 0".
//
// Usage: node measure-sizes.mjs name=dir-or-url[@button-selector] ... [--out file.json]
//   e.g. node measure-sizes.mjs react=/tmp/fwwork/react/dist nextjs=http://localhost:3000
//   Results printed as JSON; with --out they are merged into that file's "results".
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
let playwright;
try { playwright = require('playwright'); } catch { playwright = require('/opt/node-tools/node_modules/playwright'); }
const { chromium } = playwright;

const MIME = { '.html':'text/html', '.js':'text/javascript', '.mjs':'text/javascript', '.css':'text/css',
  '.json':'application/json', '.svg':'image/svg+xml', '.png':'image/png', '.ico':'image/x-icon', '.woff2':'font/woff2', '.map':'application/json' };

function serveStatic(dir) {
  const root = path.resolve(dir);
  const server = http.createServer((req, res) => {
    let p = decodeURIComponent(new URL(req.url, 'http://x').pathname);
    let f = path.join(root, p);
    if (!f.startsWith(root)) { res.writeHead(403).end(); return; }
    if (fs.existsSync(f) && fs.statSync(f).isDirectory()) f = path.join(f, 'index.html');
    if (!fs.existsSync(f)) { res.writeHead(404).end('not found'); return; }
    res.writeHead(200, { 'content-type': MIME[path.extname(f)] || 'application/octet-stream' });
    fs.createReadStream(f).pipe(res);
  });
  return new Promise(r => server.listen(0, '127.0.0.1', () => r({ server, url: `http://127.0.0.1:${server.address().port}/` })));
}

const gz = b => zlib.gzipSync(b, { level: 9 }).length;
const isJs = (url, ct) => /javascript|ecmascript/i.test(ct || '') || /\.(m?js)$/i.test(new URL(url).pathname);

async function measure(name, target) {
  let selector = 'button';
  const at = target.lastIndexOf('@');
  if (at > 0 && !target.slice(at).includes('/')) { selector = target.slice(at + 1); target = target.slice(0, at); }
  let srv = null, url = target;
  if (!/^https?:\/\//.test(target)) { srv = await serveStatic(target); url = srv.url; }
  const browser = await chromium.launch();
  try {
    const raw = await (await fetch(url)).text();
    const ssr = raw.includes('count: 0');
    let inline = 0;
    for (const m of raw.matchAll(/<script(?![^>]*\bsrc=)([^>]*)>([\s\S]*?)<\/script>/gi))
      if (!/json|importmap/i.test(m[1]) && m[2].trim()) inline += gz(Buffer.from(m[2]));
    const ctx = await browser.newContext(); // fresh: no cache/storage
    const page = await ctx.newPage();
    let phase = 'load';
    const jobs = [];
    const js = { load: [], click: [] };
    let doc = null;
    page.on('response', resp => {
      const req = resp.request();
      jobs.push((async () => {
        try {
          const ct = resp.headers()['content-type'] || '';
          const u = resp.url();
          const ph = phase;
          if (req.resourceType() === 'document' && !doc && req.frame() === page.mainFrame()) doc = gz(await resp.body());
          if (isJs(u, ct)) js[ph].push({ url: u, gz: gz(await resp.body()) });
        } catch (e) { /* redirects etc. have no body */ }
      })());
    });
    await page.goto(url, { waitUntil: 'networkidle' });
    await page.waitForLoadState('networkidle');
    await Promise.all(jobs);
    const btn = page.locator(selector).first();
    await btn.waitFor();
    const before = (await btn.textContent()).trim();
    phase = 'click';
    await btn.click();
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(500);
    await page.waitForLoadState('networkidle');
    await Promise.all(jobs);
    const after = (await page.locator(selector).first().textContent()).trim();
    if (before !== 'count: 0' || after !== 'count: 1')
      throw new Error(`${name}: click check failed: before="${before}" after="${after}"`);
    const sum = a => a.reduce((s, x) => s + x.gz, 0);
    return { js_load_bytes: sum(js.load), js_files: js.load.length, js_after_click_bytes: sum(js.click),
      js_after_click_files: js.click.length, html_gz: doc, ssr, inline_js_gz: inline,
      files: js.load.map(x => `${new URL(x.url).pathname} ${x.gz}`) };
  } finally { await browser.close(); if (srv) srv.server.close(); }
}

const args = process.argv.slice(2);
let out = null;
const oi = args.indexOf('--out');
if (oi >= 0) { out = args[oi + 1]; args.splice(oi, 2); }
const results = {};
for (const a of args) {
  const i = a.indexOf('=');
  const name = a.slice(0, i), target = a.slice(i + 1);
  try { results[name] = { ...(await measure(name, target)), status: 'ok' }; }
  catch (e) { console.error(e.message); results[name] = { status: 'failed', reason: e.message.split('\n')[0] }; }
}
console.log(JSON.stringify(results, null, 2));
if (out) {
  let j = fs.existsSync(out) ? JSON.parse(fs.readFileSync(out, 'utf8')) : {};
  j.results = { ...(j.results || {}), ...results };
  fs.writeFileSync(out, JSON.stringify(j, null, 2));
}
if (Object.values(results).some(r => r.status !== 'ok')) process.exitCode = 1;
