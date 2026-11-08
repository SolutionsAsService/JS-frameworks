import { defineConfig } from 'astro/config'
// assetsInlineLimit 0 keeps Astro's bundled <script> as a separate .js file so the
// measurement sees it as a JS response (otherwise small scripts are inlined into the HTML).
export default defineConfig({ vite: { build: { assetsInlineLimit: 0 } } })
