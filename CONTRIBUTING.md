# Contributing

The pages at the repo root are generated, so please edit the sources and rebuild.

1. Change text or figures in `_src/data/*.json`, layout in `_src/build.py`, styling in `_src/style.css`, illustrations in `_src/scenes.py`.
2. Run `python3 _src/build.py` (it refuses broken internal links).
3. Preview with `npx serve .`.
4. Optional checks: `tools/` holds the size measurement and the Playwright audit (`node tools/audit.mjs`); see `tools/README.md`.

Keep the site static (no framework or build step needed to view it) and keep both light and dark themes working.
