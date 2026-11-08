#!/usr/bin/env node
// registry-dates.mjs -- checks the "since" years on the framework pages against the npm registry.
// For each package it records the first version ever published, and the dates of 1.0.0 / 2.0.0 / 3.0.0 where they exist.
// Output: _src/data/registry.json. Limits: the registry shows when a package was published, not who designed the
// framework or when its design was first shown, and some names (react 2011, lit 2012) were used by unrelated packages
// before the framework took them, so a registry date only corroborates a year, it never overrides one.
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
const PKG = { react: 'react', nextjs: 'next', vue: 'vue', nuxt: 'nuxt', angular: '@angular/core', svelte: 'svelte', solid: 'solid-js', preact: 'preact', qwik: '@builder.io/qwik', astro: 'astro', lit: 'lit', htmx: 'htmx.org' };
const out = { checked_on: new Date().toISOString().slice(0, 10), results: {} };
for (const [id, pkg] of Object.entries(PKG)) {
  const t = JSON.parse(execFileSync('npm', ['view', pkg, 'time', '--json'], { encoding: 'utf8' }));
  const v = Object.entries(t).filter(([k]) => k !== 'created' && k !== 'modified');
  const at = x => (t[x] ? t[x].slice(0, 10) : null);
  out.results[id] = { package: pkg, first_version: v[0][0], first_published: v[0][1].slice(0, 10), v1: at('1.0.0'), v2: at('2.0.0'), v3: at('3.0.0') };
}
fs.writeFileSync(new URL('../_src/data/registry.json', import.meta.url), JSON.stringify(out, null, 2) + '\n');
console.log(JSON.stringify(out.results));
