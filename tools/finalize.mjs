#!/usr/bin/env node
// finalize.mjs <workdir> <measured.json>
// 1) pins every dependency in tools/apps/*/package.json to the exact version found in
//    <workdir>/<app>/node_modules (so the source tree reproduces the measured build);
// 2) stamps procedure/date/node and per-framework exact versions (read from node_modules)
//    into measured.json next to the numbers produced by measure-sizes.mjs.
import fs from 'node:fs';
import path from 'node:path';
const [work, out] = process.argv.slice(2);
const apps = path.join(path.dirname(new URL(import.meta.url).pathname), 'apps');
const MAIN = { react:'react', preact:'preact', vue:'vue', svelte:'svelte', solid:'solid-js', lit:'lit', angular:'@angular/core',
  htmx:'htmx.org', nextjs:'next', nuxt:'nuxt', 'astro-island':'astro', 'astro-script':'astro', qwik:'@builder.io/qwik', vanilla:'vite' };
const ver = (app, pkg) => JSON.parse(fs.readFileSync(path.join(work, app, 'node_modules', pkg, 'package.json'), 'utf8')).version;
for (const app of fs.readdirSync(apps)) {
  const f = path.join(apps, app, 'package.json');
  const p = JSON.parse(fs.readFileSync(f, 'utf8'));
  for (const k of ['dependencies', 'devDependencies'])
    for (const d of Object.keys(p[k] || {})) p[k][d] = ver(app, d);
  fs.writeFileSync(f, JSON.stringify(p, null, 2) + '\n');
}
const j = JSON.parse(fs.readFileSync(out, 'utf8'));
j.procedure = 'Production build of an identical heading+counter-button app per framework; served via static server (or the framework\'s own prod server for SSR/htmx); fresh headless Chromium context; wait networkidle; every JavaScript response (content-type or .js/.mjs) sized as zlib gzip level 9 of its body, summed = js_load_bytes; click button once, extra JS requested = js_after_click_bytes; click verified count: 0 -> count: 1; html_gz = gzip-9 of initial document; ssr = plain fetch contains "count: 0". Inline <script> blocks are not in js_load_bytes (see inline_js_gz). See tools/measure-sizes.mjs.';
j.measured_on = new Date().toISOString().slice(0, 10);
j.node = process.version;
for (const [name, r] of Object.entries(j.results)) {
  const app = name.replace(/-nopreload$/, '');
  if (!MAIN[app]) continue;
  r.version = ver(app, MAIN[app]);
  if (app === 'astro-island') r.preact_version = ver(app, 'preact');
  if (MAIN[app] !== 'vite' && fs.existsSync(path.join(work, app, 'node_modules/vite/package.json'))) r.vite_version = ver(app, 'vite');
}
fs.writeFileSync(out, JSON.stringify(j, null, 2) + '\n');
