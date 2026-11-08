# JS Frameworks

Twelve JavaScript frameworks explained side by side: React, Preact, Solid, Lit, Vue, Angular, Svelte, Qwik, Next.js, Nuxt, Astro and htmx.

Each home-page card is themed to its framework's kind and style, and shows the gzipped JavaScript that one real counter app loaded (measured with `tools/measure-sizes.mjs`; a counter, not a ranking). The site also has how-they-work, compare, author's-repos and per-framework pages with pros and cons, light and dark themes, and no tracking.

## Build

The pages at the repo root are generated. Edit `_src/` and run:

    python3 _src/build.py

Open `index.html`, or run `npx serve .`.

## History

- Branch `original-overview` keeps the first version of this site (four frameworks, pros and cons).
- A separate collage-style version lives in [SolutionsAsService/frameworks](https://github.com/SolutionsAsService/frameworks).

MIT licensed (see `LICENSE`).
