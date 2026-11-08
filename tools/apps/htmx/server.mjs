import http from 'node:http'
import fs from 'node:fs'
const btn = n => `<button hx-post="/inc" hx-vals='{"n":${n + 1}}' hx-swap="outerHTML">count: ${n}</button>`
const page = `<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>counter</title>
<script src="/htmx.min.js"></script></head>
<body><h1>Counter</h1><div id="app">${btn(0)}</div></body></html>`
http.createServer((req, res) => {
  if (req.url === '/htmx.min.js') {
    res.writeHead(200, { 'content-type': 'text/javascript' })
    return res.end(fs.readFileSync(new URL('./node_modules/htmx.org/dist/htmx.min.js', import.meta.url)))
  }
  if (req.method === 'POST' && req.url === '/inc') {
    let b = ''; req.on('data', d => (b += d)); req.on('end', () => {
      const n = Number(new URLSearchParams(b).get('n')) || 0
      res.writeHead(200, { 'content-type': 'text/html' }); res.end(btn(n))
    }); return
  }
  res.writeHead(200, { 'content-type': 'text/html' }); res.end(page)
}).listen(Number(process.env.PORT) || 3100)
