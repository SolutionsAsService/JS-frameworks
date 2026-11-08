# Size measurement harness

`measure-sizes.mjs` is the single measurement procedure (see its header). Sources in `apps/<name>/` are hand-written minimal
counter apps (heading + button showing `count: N`). Dependency versions in each `package.json` are pinned to what was measured
(`finalize.mjs` does the pinning and stamps versions into `_src/data/measured.json`).

Requires Node 22 and Playwright with Chromium (`require('playwright')`).

## Build commands (per app: copy `apps/<name>` to a work dir, then `npm install` there)

| app | build | serve for measurement |
|---|---|---|
| react, preact, vue, svelte, solid, lit, vanilla | `npx vite build` | static dir `dist` |
| angular | `npx ng build` | static dir `dist/ng/browser` (project name is `ng` in angular.json) |
| htmx | none | `PORT=3100 node server.mjs` (serves `htmx.min.js` from node_modules, `hx-post` fragment) |
| nextjs | `npx next build` | `npx next start -p 3101` |
| nuxt | `npx nuxt build` | `PORT=3102 node .output/server/index.mjs` |
| astro-island, astro-script | `npx astro build` | static dir `dist` |
| qwik (Qwik City 1.x) | `npm run build` (vite client build + `--ssr src/entry.preview.tsx`) | `npm start` (vite preview, port 3105) |
| qwik-nopreload | same, with `preloader: false` added to the `renderToStream` options in `src/entry.ssr.tsx` | port 3106 |

## Measure

```
node tools/measure-sizes.mjs react=/work/react/dist nextjs=http://localhost:3101 ... --out _src/data/measured.json
node tools/finalize.mjs /work _src/data/measured.json
```
Targets are `name=dir` (static) or `name=url`; optional `@selector` suffix overrides the `button` selector.

## Notes
- Qwik is 1.20.3 (latest stable; 2.x is still rc). Its default preloader eagerly fetches handler bundles when idle, so
  `js_after_click_bytes` is 0 by default; `qwik-nopreload` shows the pure resumability behaviour.
- `astro-script` sets `vite.build.assetsInlineLimit: 0` so Astro's bundled script is an external file rather than inlined in HTML.
- Inline `<script>` blocks (Next flight data, Astro island bootstrap, Qwik loader) are not in `js_load_bytes`; they are reported
  as `inline_js_gz`.
- Vite 8 (rolldown/oxc minifier) is the current default; Qwik City pulls vite 7.
