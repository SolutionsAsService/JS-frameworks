#!/usr/bin/env node
// brotli-check.mjs -- does the size order change if the JavaScript is compressed with brotli (quality 11) instead of gzip (level 9)?
// Usage: node tools/brotli-check.mjs name=/path/to/dist ... > _src/data/brotli.json
// Only static builds can be checked this way (the server-rendered ones were not re-measured with brotli).
import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';
const out = { checked_on: new Date().toISOString().slice(0, 10), method: 'sum over every .js/.mjs file in the build directory of gzip level 9 and brotli quality 11', results: {} };
const walk = (p, acc = []) => { for (const f of fs.readdirSync(p)) { const q = path.join(p, f); fs.statSync(q).isDirectory() ? walk(q, acc) : /\.(js|mjs)$/.test(f) && acc.push(q); } return acc; };
for (const arg of process.argv.slice(2)) {
  const [name, dir] = arg.split('=');
  let gz = 0, br = 0;
  for (const f of walk(dir)) { const b = fs.readFileSync(f); gz += zlib.gzipSync(b, { level: 9 }).length; br += zlib.brotliCompressSync(b, { params: { [zlib.constants.BROTLI_PARAM_QUALITY]: 11 } }).length; }
  out.results[name] = { gzip9: gz, brotli11: br };
}
const order = k => Object.entries(out.results).sort((a, b) => a[1][k] - b[1][k]).map(e => e[0]);
out.order_gzip = order('gzip9'); out.order_brotli = order('brotli11'); out.order_same = JSON.stringify(out.order_gzip) === JSON.stringify(out.order_brotli);
console.log(JSON.stringify(out, null, 2));
