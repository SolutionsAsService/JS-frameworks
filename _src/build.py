"""Builds site/ for the frameworks site.

Every figure the pages print is read from _src/data/measured.json (real builds, see tools/) or
_src/data/profile.json (GitHub code search, see tools/profile-scan.sh). The favicon is written from the
stylesheet's own colour tokens, and the build refuses to emit a page whose internal links resolve to nothing.
"""
import gzip
sys_path = None
import html
import json
import pathlib
import re
import shutil
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from scenes import scene  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC, OUT, TOOLS = ROOT / '_src', ROOT, ROOT / 'tools'
REPO = 'https://github.com/SolutionsAsService/JS-frameworks'
FW = json.loads((SRC / 'data/frameworks.json').read_text(encoding='utf-8'))
MEAS = json.loads((SRC / 'data/measured.json').read_text(encoding='utf-8'))
PROFILE = json.loads((SRC / 'data/profile.json').read_text(encoding='utf-8'))
CSS = (SRC / 'style.css').read_text(encoding='utf-8')
ORDER = list(FW)
# which measured app stands for each framework, and any extra variants shown on its page
MAIN = {k: k for k in FW}
MAIN['astro'] = 'astro-island'
VARIANTS = {'astro': [('astro-island', 'a Preact island, hydrated on load'), ('astro-script', 'a plain script, no UI library')],
            'qwik': [('qwik', 'default settings (idle preloading on)'), ('qwik-nopreload', 'preloading off, so the click loads its own code')]}
CODE = {'react': ['react/src/main.jsx'], 'preact': ['preact/src/main.jsx'], 'vue': ['vue/src/App.vue'], 'svelte': ['svelte/src/App.svelte'],
        'solid': ['solid/src/main.jsx'], 'lit': ['lit/src/main.js'], 'angular': ['angular/src/app/app.ts'], 'htmx': ['htmx/server.mjs'],
        'nextjs': ['nextjs/app/Counter.jsx'], 'nuxt': ['nuxt/app/pages/index.vue'], 'astro': ['astro-island/src/Counter.jsx', 'astro-island/src/pages/index.astro'],
        'qwik': ['qwik/src/routes/index.tsx']}
# each framework's own typeface for its name: (family, weight, style, case, tracking, Google Fonts axis spec)
FACES = {
    'react': ('Space Grotesk', 700, 'normal', 'none', '-.01em', 'Space+Grotesk:wght@700'),
    'preact': ('Sora', 300, 'normal', 'lowercase', '0', 'Sora:wght@300'),
    'solid': ('Archivo Black', 400, 'normal', 'none', '-.01em', 'Archivo+Black'),
    'lit': ('Fraunces', 700, 'italic', 'none', '-.01em', 'Fraunces:ital,wght@1,700'),
    'vue': ('Nunito', 800, 'normal', 'none', '0', 'Nunito:wght@800'),
    'angular': ('Barlow Condensed', 800, 'normal', 'uppercase', '.03em', 'Barlow+Condensed:wght@800'),
    'svelte': ('Syne', 800, 'normal', 'none', '-.01em', 'Syne:wght@800'),
    'qwik': ('Exo 2', 800, 'italic', 'none', '0', 'Exo+2:ital,wght@1,800'),
    'nextjs': ('Inter', 800, 'normal', 'none', '-.045em', None),
    'nuxt': ('Lexend', 700, 'normal', 'none', '-.01em', 'Lexend:wght@700'),
    'astro': ('Unbounded', 700, 'normal', 'none', '0', 'Unbounded:wght@700'),
    'htmx': ('JetBrains Mono', 800, 'normal', 'lowercase', '-.03em', None),
}
GENERATED = ['index.html', 'how.html', 'compare.html', 'profile.html', 'also.html', 'about.html', 'styles.css', 'script.js', 'favicon.svg', 'robots.txt', '.nojekyll']
GROUP_LABEL = {'library': 'Library', 'framework': 'Framework', 'meta': 'Meta-framework', 'other': 'Other model'}
REG = json.loads((SRC / 'data/registry.json').read_text(encoding='utf-8'))
BROTLI = json.loads((SRC / 'data/brotli.json').read_text(encoding='utf-8'))
ON_PROFILE = [k for k in FW if PROFILE['queries'].get(k, {}).get('repos')]


class BuildError(Exception):
    pass


def e(s):
    return html.escape(s, quote=True)


def kb(n):
    return f'{n / 1000:.1f}'


def m(key):
    r = MEAS['results'].get(key)
    if not r or r.get('status') != 'ok':
        raise BuildError(f'no measurement for {key}')
    return r


def face_style(k):
    fam, w, st, tt, ls, _ = FACES[k]
    return f"--fam:'{fam}';--fw:{w};--fs:{st};--tt:{tt};--ls:{ls}"


def font_links(keys):
    """One tiny Google Fonts request per framework, limited to the letters of its own name."""
    from urllib.parse import quote
    out = []
    for k in keys:
        spec = FACES[k][5]
        if spec:
            name = FW[k]['name']
            text = quote(''.join(sorted(set(name + name.upper() + name.lower()))))
            out.append(f'<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family={spec}&text={text}&display=swap">')
    return '\n'.join(out)


def ink_on(hex_):
    """Dark or white text, whichever reads better on this colour."""
    c = [int(hex_[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    c = [v / 12.92 if v <= .03928 else ((v + .055) / 1.055) ** 2.4 for v in c]
    lum = .2126 * c[0] + .7152 * c[1] + .0722 * c[2]
    return '#0f172a' if (lum + .05) / .05 >= 1.05 / (lum + .05) else '#ffffff'


def links(text):
    """Turn {{fw:id}} into a link to that framework's page."""
    return re.sub(r'\{\{fw:(\w+)\}\}', lambda mo: f'<a href="{mo.group(1)}.html">{e(FW[mo.group(1)]["name"])}</a>', text)


# ------------------------------------------------------------------ page shell
def token(name):
    mo = re.search(r'--%s:\s*(#[0-9A-Fa-f]{6})' % name, CSS)
    if not mo:
        raise BuildError(f'no colour token --{name} in the stylesheet')
    return mo.group(1)


def favicon():
    g = [token(n) for n in ('g1', 'g2', 'g3')]
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
            f'<stop offset="0" stop-color="{g[0]}"/><stop offset=".55" stop-color="{g[1]}"/><stop offset="1" stop-color="{g[2]}"/></linearGradient></defs>'
            f'<rect width="32" height="32" rx="8" fill="url(#g)"/><text x="16" y="21.5" text-anchor="middle" font-family="monospace" font-weight="800" font-size="14" fill="#fff">JS</text></svg>\n')


# key, label, file, short label, hidden on phones
TOP = [('index', 'Home', 'index.html', 'Home', True), ('how', 'How they work', 'how.html', 'How', True), ('compare', 'Compare', 'compare.html', 'Compare', False),
       ('profile', 'Author’s repos', 'profile.html', 'Repos', True), ('also', 'Also', 'also.html', 'Also', True), ('about', 'About', 'about.html', 'About', False)]
THEME_BOOT = ("<script>try{var t=localStorage.getItem('theme');if(!t)t=matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light';"
              "document.documentElement.setAttribute('data-theme',t)}catch(e){}</script>")


def shell(key, title, desc, body, pills=True, fonts=()):
    nav = ''.join(f'<li{" class=\"hide-sm\"" if hide else ""}><a href="{f}"{" aria-current=page" if k == key else ""}><span class="long">{t}</span><span class="short" aria-hidden="true">{sh}</span></a></li>'
                  for k, t, f, sh, hide in TOP)
    pill_html = ''
    if pills:
        pill_html = ('<nav class="pills" aria-label="Frameworks"><ul>' + ''.join(
            f'<li><a href="{k}.html" style="--a:{FW[k]["accent"]}"{" aria-current=page" if k == key else ""}>{e(FW[k]["name"])}</a></li>' for k in ORDER) + '</ul></nav>')
    foot_nav = ''.join(f'<li><a href="{f}">{t}</a></li>' for k, t, f, sh, hide in TOP)
    full = title if key == 'index' else f'{title} · JS Frameworks'
    body = re.sub(r'<tr><th scope="row"><a href="(\w+)\.html">', lambda mo: f'<tr style="--a:{FW[mo.group(1)]["accent"]}"><th scope="row"><a href="{mo.group(1)}.html">' if mo.group(1) in FW else mo.group(0), body)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(full)}</title>
<meta name="description" content="{e(desc)}">
<meta property="og:type" content="website">
<meta property="og:title" content="{e(full)}">
<meta property="og:description" content="{e(desc)}">
<meta name="color-scheme" content="light dark">
{THEME_BOOT}
<link rel="icon" href="favicon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;700&display=swap">
{font_links(fonts)}
<link rel="stylesheet" href="styles.css">
<script src="script.js" defer></script>
</head>
<body class="p-{key}">
<a class="skip" href="#main">Skip to content</a>
<header class="top">
<a class="brand" href="index.html" aria-label="JS Frameworks, home"><span class="mark" aria-hidden="true">JS</span><span>JS Frameworks</span></a>
<nav class="nav" aria-label="Site"><ul>{nav}</ul></nav>
<button type="button" class="mode" id="theme-toggle" aria-label="Switch to dark mode"><span class="ico" aria-hidden="true"><svg class="ico-moon" viewBox="0 0 24 24" width="18" height="18"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" fill="currentColor"/></svg><svg class="ico-sun" viewBox="0 0 24 24" width="18" height="18"><circle cx="12" cy="12" r="4.2" fill="currentColor"/><g stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M12 2.5v2.6M12 18.9v2.6M2.5 12h2.6M18.9 12h2.6M5.3 5.3l1.8 1.8M16.9 16.9l1.8 1.8M5.3 18.7l1.8-1.8M16.9 7.1l1.8-1.8"/></g></svg></span><span class="lbl">Dark</span></button>
</header>
{pill_html}
<main id="main">
{body}
</main>
<footer class="foot">
<ul>{foot_nav}</ul>
<p>Every size on this site is the gzipped JavaScript files a real counter app sent to the browser (inline script is not counted), measured on {MEAS['measured_on']} with the script in <a href="{REPO}/tree/main/tools">tools/</a>. How that was done, and what it leaves out, is on <a href="about.html">About</a>.</p>
<p>By SolutionsAsService. This site sets no cookies and collects nothing; the only thing it stores is your light or dark choice, in your browser.</p>
</footer>
</body>
</html>
"""


def pager(key, seq):
    i = [s[2] for s in seq].index(key)
    p, n = seq[i - 1], seq[(i + 1) % len(seq)]
    return (f'<nav class="pager" aria-label="Previous and next"><a href="{p[1]}"><span>Previous</span>{e(p[0])}</a>'
            f'<a href="{n[1]}"><span>Next</span>{e(n[0])}</a></nav>')


def seq_all():
    s = [('Home', 'index.html', 'index')] + [(FW[k]['name'], f'{k}.html', k) for k in ORDER]
    return s + [('How they work', 'how.html', 'how'), ('Compare', 'compare.html', 'compare'), ('On this profile', 'profile.html', 'profile'), ('Also', 'also.html', 'also'), ('About', 'about.html', 'about')]


# ------------------------------------------------------------------ home: twelve themed cards
def tile(k):
    d, r = FW[k], m(MAIN[k])
    star = '<span class="star"><span aria-hidden="true">★</span><span class="starlbl" aria-hidden="true">author’s repos</span><span class="sr">Used in the author’s repositories. </span></span>' if k in ON_PROFILE else ''
    n = r['js_files']
    return (f'<li class="fw" data-fw="{k}" style="--a:{d["accent"]};--on:{ink_on(d["accent"])};{face_style(k)}"><a href="{k}.html">'
            f'<span class="art">{scene(k)}{star}</span>'
            f'<span class="txt"><span class="head"><span class="nm">{e(d["name"])}<span class="sr">. </span></span>'
            + ('<span class="ssr ssr-sm" aria-hidden="true">HTML</span>' if r['ssr'] else '')
            + f'<span class="kind"><span class="sr">Kind: </span>{GROUP_LABEL[d["group"]]}<span class="sr">. </span></span></span>'
            f'<span class="figrow"><span class="fig">{kb(r["js_load_bytes"])}<small>kB</small><span class="sr">. </span></span>'
            + ('<span class="ssr ssr-lg" aria-hidden="true">server HTML</span>' if r['ssr'] else '') + '</span>'
            f'<span class="claim">{e(d["claim"])}<span class="sr">. </span></span>'
            f'<span class="works"><span class="sr">works with </span>{e(d["touches"])}</span>'
            f'<span class="sr">{n} JavaScript file{"s" if n != 1 else ""} loaded{", the page already holds the count" if r["ssr"] else ""}. </span>'
            f'</span></a></li>')


def home():
    tiles = ''.join(tile(k) for k in ORDER)
    rows = ''.join(f'<tr><th scope="row"><a href="{k}.html">{e(d["name"])}</a></th><td>{e(d["claim"])}</td><td>{GROUP_LABEL[d["group"]]}</td><td>{e(d["since"])}</td>'
                   f'<td>{e(d["updates"])}</td><td class="num">{kb(m(MAIN[k])["js_load_bytes"])}</td></tr>' for k, d in FW.items())
    pc = ''.join(f'<tr><th scope="row"><a href="{k}.html">{e(d["name"])}</a></th><td>{links(d["pros"])}</td><td>{links(d["cons"])}</td></tr>' for k, d in FW.items())
    body = f"""<section class="hero" aria-labelledby="hero-h">
<div class="hero-head"><h1 id="hero-h">Twelve JavaScript frameworks, <em>side by side</em></h1>
<p id="wall-note">A framework turns your data into a web page and keeps it up to date. <span class="wide">Each card shows the gzipped JavaScript, in kB, that one real counter app loaded (a counter, not your app, and not a ranking). “Server HTML” means the page already holds the count. ★ used in the author’s (SolutionsAsService) GitHub repos. Choosing? Start with <a href="compare.html">Compare</a>.</span><span class="narrow">Each card: gzipped download size, in kB, of one counter app. Not a ranking. HTML = page already holds the count. ★ author’s SolutionsAsService repos. Start with <a href="compare.html">Compare</a>.</span></p></div>
<ol class="wall" aria-label="The twelve frameworks, grouped by kind" aria-describedby="wall-note">{tiles}</ol>
</section>
<div class="wrap">
<section class="section" aria-labelledby="read-h">
<h2 id="read-h">How to read the cards</h2>
<div class="prose">
<p class="lede">A framework is an answer to one question: how does a change in your data become a change on the screen?</p>
<p>The answers differ in <a href="how.html#where-h">where the HTML is made</a> (the browser, a server, at build time), in <a href="how.html#change-h">how a change is found</a> (compare two trees, track what was read, compile it away, ask the server), and in <a href="how.html#box-h">how much is in the box</a> (a view library, or routing, forms and servers as well). Each card’s drawing is its own answer, and its row says which kind it is: library, framework, meta-framework (a framework built on a library) or a different model.</p>
<p>The number on each card is a measurement, not a ranking. It is the JavaScript files for a page with one button, built the way each framework recommends (script written inside the HTML page is not counted), and the frameworks that make their HTML on the server (marked “server HTML”) also send a page that already has the count in it. A framework’s cost for a real app depends on the app, and a counter says nothing about how that cost grows. <a href="about.html">What was measured and what was not.</a></p>
<p>The star marks the {len(ON_PROFILE)} frameworks that the public repositories of the author’s GitHub profile (SolutionsAsService) use. <a href="profile.html">See which.</a></p>
<p>The twelve were chosen by the author, not by a ranking: the three used in those repositories (React, Next.js, Lit), three the author wanted covered (Angular, Vue, Svelte), and six more that are widely used or take a different road (Nuxt, Solid, Preact, Qwik, Astro, htmx). <a href="also.html">Others that did not get a page.</a></p>
</div>
</section>
<section class="section" aria-labelledby="pc-h">
<h2 id="pc-h">Pros and cons at a glance</h2>
<p class="prose">The first version of this site was a short overview of React, Vue, Angular and Svelte with a pros and cons line each; those four lines are kept below as they were written, and the other eight follow the same form.</p>
<div class="tablewrap" tabindex="0" role="region" aria-label="Pros and cons"><table><thead><tr><th>Framework</th><th>Pros</th><th>Cons</th></tr></thead><tbody>{pc}</tbody></table></div>
</section>
<section class="section" aria-labelledby="all-h">
<h2 id="all-h">All twelve, side by side</h2>
<div class="tablewrap" tabindex="0" role="region" aria-label="All twelve frameworks"><table>
<thead><tr><th>Framework</th><th>In a line (a description, not a measurement)</th><th>Kind</th><th>Since</th><th>Finds changes by</th><th class="num">Counter JS (kB)</th></tr></thead><tbody>{rows}</tbody></table></div>
<p class="prose">More detail: <a href="compare.html">compare them on every axis</a>, <a href="also.html">older and smaller frameworks that did not get a page</a>.</p>
</section>
</div>
{pager('index', seq_all())}"""
    return shell('index', 'JS Frameworks: twelve JavaScript frameworks side by side', 'Twelve JavaScript frameworks explained: how React, Next.js, Vue, Nuxt, Angular, Svelte, Solid, Preact, Qwik, Astro, Lit and htmx work, overlap and differ, with the real JavaScript size of a counter app in each.', body, pills=False, fonts=ORDER)


def code_blocks(k):
    out = []
    for rel in CODE[k]:
        p = TOOLS / 'apps' / rel
        text = p.read_text(encoding='utf-8').rstrip('\n')
        out.append(f'<figure><figcaption>{e(rel)} · <a href="{REPO}/blob/main/tools/apps/{rel}">in the repository</a></figcaption>'
                   f'<pre tabindex="0" aria-label="{e(rel)}"><code>{e(text)}</code></pre></figure>')
    return ''.join(out)


def meas_block(k):
    r = m(MAIN[k])
    cells = [(f'{kb(r["js_load_bytes"])} kB', f'gzipped JS to show the page, in {r["js_files"]} file{"s" if r["js_files"] != 1 else ""}'),
             (f'{kb(r["js_after_click_bytes"])} kB', 'more JS fetched by one click'),
             ('yes' if r['ssr'] else 'no', 'the HTML already says “count: 0” before any JS runs'),
             (e(r['version']), 'version measured')]
    cells_html = ''.join(f'<div><b>{a}</b><span>{b}</span></div>' for a, b in cells)
    notes = []
    if r.get('inline_js_gz'):
        notes.append(f'The page also carries {r["inline_js_gz"]:,} B (gzipped) of inline script, which is not counted above.')
    if k in VARIANTS:
        rows = ''.join(f'<tr><th scope="row">{e(lbl)}</th><td class="num">{kb(m(v)["js_load_bytes"])}</td><td class="num">{m(v)["js_files"]}</td>'
                       f'<td class="num">{kb(m(v)["js_after_click_bytes"])}</td></tr>' for v, lbl in VARIANTS[k])
        notes.append('<div class="tablewrap" tabindex="0" role="region" aria-label="Measured variants"><table><thead><tr><th>Variant</th><th class="num">JS at load (kB)</th>'
                     f'<th class="num">Files</th><th class="num">After one click (kB)</th></tr></thead><tbody>{rows}</tbody></table></div>')
    if k == 'htmx':
        notes.append('htmx’s figure is its one script. Each click then needs a request to a server, which this counter does and a client-only framework does not.')
    if k == 'qwik':
        notes.append('A counter is too small to show what Qwik is for: its aim is that start-up cost stays flat as an app grows, and that is not measured here.')
    return f'<div class="meas">{cells_html}</div>' + ''.join(f'<p class="prose">{n}</p>' if not n.startswith('<div') else n for n in notes)


def registry_text(k):
    r = REG['results'][k]
    if k == 'react':
        return 'not checkable: npm’s 2011 “react” entries are an unrelated package'
    if k == 'nextjs':
        return '1.0.0 on 2016-10-25 (npm’s 2011 “next” entries are an unrelated package)'
    bits = []
    if k not in ('angular',) and r['first_published'] and not r['v1']:
        bits.append(f'first version {r["first_published"]}')
    if k in ('nuxt', 'svelte', 'astro', 'vue'):
        bits = [f'first version {r["first_published"]}']
    for tag, key in (('1.0.0', 'v1'), ('2.0.0', 'v2'), ('3.0.0', 'v3')):
        if r[key] and (key == 'v1' or (k == 'angular' and key == 'v2') or (k in ('lit',) and key == 'v2') or (k == 'vue' and key == 'v3')):
            bits.append(f'{tag} on {r[key]}')
    txt = ', '.join(bits) or 'no version history to check'
    if k == 'vue':
        txt += ' (the 2014 announcement is not on npm)'
    return txt + (' (the name “lit” was another package before 2021)' if k == 'lit' else '')


def fw_page(k):
    d = FW[k]
    facts = [('Kind', d['kind']), ('Made by', d['by']), ('Since', d['since']), ('Written in', d['lang']), ('Checked on npm', registry_text(k))]
    facts_html = ''.join(f'<li><b>{a}</b>{e(b)}</li>' for a, b in facts)
    flow = ''.join(f'<li>{s}</li>' for s in d['pipeline'])
    ov = ''.join(f'<li><a href="{w}.html">{e(FW[w]["name"])}</a>: {t}</li>' for w, t in d['overlap'])
    df = ''.join(f'<li><a href="{w}.html">{e(FW[w]["name"])}</a>: {t}</li>' for w, t in d['differs'])
    good = ''.join(f'<li>{g}</li>' for g in d['good'])
    cost = ''.join(f'<li>{c}</li>' for c in d['costs'])
    srcs = ''.join(f'<li><a href="{u}">{e(t)}</a></li>' for t, u in d['sources'])
    earlier = '<small>From the first version of this site.</small>' if d.get('pros_from_earlier') else ''
    prof = ''
    if k in ON_PROFILE:
        rp = PROFILE['queries'][k]['repos']
        prof = (f'<section class="section" aria-labelledby="prof-h"><h2 id="prof-h">In the author’s repos</h2><div class="prose"><p>{e(d["name"])} is named in {len(rp)} public '
                f'repositor{"y" if len(rp) == 1 else "ies"} of this GitHub profile: ' + ', '.join(f'<a href="https://github.com/SolutionsAsService/{r}">{e(r)}</a>' for r in rp) +
                f'. <a href="profile.html">How that was found.</a></p></div></section>')
    body = f"""<header class="band" data-fw="{k}" style="--a:{d['accent']};--on:{ink_on(d['accent'])};{face_style(k)}"><div class="band-in"><div><p class="kicker">{e(d['kind'])}</p><h1 id="top">{e(d['name'])}</h1>
<p class="band-line">{e(d['tagline'])}</p><ul class="facts">{facts_html}</ul></div><div class="art">{scene(k, True)}</div></div></header>
<div class="wrap" data-fw="{k}" style="--a:{d['accent']};--on:{ink_on(d['accent'])}">
<section class="section" aria-labelledby="pc-h"><h2 id="pc-h">At a glance</h2>
<div class="pc"><div class="pro"><h3>Pros</h3><p>{d['pros']}</p>{earlier}</div><div class="con"><h3>Cons</h3><p>{d['cons']}</p>{earlier}</div></div></section>
<section class="section" aria-labelledby="what-h"><h2 id="what-h">What it is</h2><div class="prose">{''.join(f'<p>{links(p)}</p>' for p in d['what'])}</div></section>
<section class="section" aria-labelledby="how-h"><h2 id="how-h">How it works</h2>
<ol class="flow" aria-label="From source to screen">{flow}</ol>
<div class="prose">{''.join(f'<p>{links(p)}</p>' for p in d['how'])}</div></section>
<section class="section" aria-labelledby="ctr-h"><h2 id="ctr-h">The same counter, measured</h2>
<p class="prose">One heading and one button that counts clicks, built for production the way {e(d['name'])} recommends. This is the whole source that was measured:</p>
{code_blocks(k)}
{meas_block(k)}
<p class="prose"><a href="about.html#proc-h">How the number was measured</a>, and <a href="compare.html">the other eleven beside it</a>.</p></section>
<section class="section" aria-labelledby="rel-h"><h2 id="rel-h">Overlaps and differences</h2>
<div class="two"><div><h3>Overlaps with</h3><ul>{ov}</ul></div><div><h3>Differs from</h3><ul>{df}</ul></div></div></section>
<section class="section" aria-labelledby="tr-h"><h2 id="tr-h">What it is good at, and what it costs</h2>
<div class="two"><div><h3>Good at</h3><ul>{good}</ul></div><div><h3>Costs</h3><ul>{cost}</ul></div></div></section>
{prof}
<section class="section" aria-labelledby="src-h"><h2 id="src-h">Sources</h2><ul class="sources">{srcs}</ul></section>
</div>
{pager(k, seq_all())}"""
    return shell(k, d['name'], f'{d["name"]}: {d["tagline"]} The JavaScript for a counter app in it, measured: {kb(m(MAIN[k])["js_load_bytes"])} kB gzipped.', body, fonts=[k])


# ------------------------------------------------------------------ concept pages
def band(kicker, title, line):
    parade = ''.join(f'<li data-fw="{k}" style="--a:{FW[k]["accent"]};--on:{ink_on(FW[k]["accent"])}">{scene(k)}</li>' for k in ORDER)
    return (f'<header class="band band-plain"><div class="band-in"><div><ul class="parade" aria-hidden="true">{parade}</ul><p class="kicker">{e(kicker)}</p><h1 id="top">{e(title)}</h1>'
            f'<p class="band-line">{e(line)}</p></div></div></header>')


def names(ids):
    return ', '.join(f'<a href="{i}.html">{e(FW[i]["name"])}</a>' for i in ids)


def how():
    where = [('Client rendering', 'The server sends an almost empty page and a script. The browser runs the script, which draws everything.', ['react', 'preact', 'vue', 'svelte', 'solid', 'lit', 'angular'], 'The simplest to host. Nothing appears until the script has run, and search engines and slow phones feel that.'),
             ('Server rendering', 'The server runs the components for each request and sends finished HTML. A script then <i>hydrates</i> it: it runs the components again in the browser to attach the event handlers.', ['nextjs', 'nuxt', 'angular', 'qwik', 'svelte', 'solid'], 'Text shows at once. The page is paid for twice: rendered on the server, then run again in the browser.'),
             ('Static generation', 'The HTML is made once, at build time, and served as files.', ['nextjs', 'nuxt', 'astro', 'svelte'], 'Fast and cheap to serve; the page is only as fresh as the last build.'),
             ('Islands', 'Most of the page is plain HTML. Only components marked as interactive get JavaScript, each hydrating on its own.', ['astro'], 'Content pages ship little script. Interactive pages need other tools.'),
             ('Resumability', 'The server writes the application’s state and its event listeners into the HTML. The browser continues from there and loads code only when an event needs it.', ['qwik'], 'No start-up re-run. The first interaction may wait on a request for its code.'),
             ('Hypermedia', 'The server keeps the state and returns HTML fragments. The browser swaps them into the page.', ['htmx'], 'No client application to build. Every change that matters goes to the server.')]
    wrows = ''.join(f'<tr><th scope="row">{a}</th><td>{b}</td><td>{names(c)}</td><td>{dd}</td></tr>' for a, b, c, dd in where)
    change = [('Compare two trees', 'Run the component again, get a new description of the UI, compare it with the old one, change the nodes that differ.', ['react', 'preact', 'vue'], ['Component runs again', 'New tree compared with the old', 'List of differences', 'DOM nodes patched'], 'Vue also records what each component read, so it re-runs fewer components than React does.'),
              ('Track what was read', 'State is a reactive value. Whatever reads it is remembered, and only that is run again when it changes.', ['vue', 'solid', 'angular', 'svelte', 'preact'], ['Value changes', 'Readers of that value are known', 'Only those run again', 'The matching DOM updates'], 'Solid tracks single expressions; Vue, a whole component render; Angular’s signals, a template binding; Svelte 5’s runes, the compiled update; Preact’s signals, the parts of a component that read them.'),
              ('Compile it away', 'A compiler reads the component at build time and writes the exact update code, so little general-purpose framework code ships.', ['svelte', 'solid'], ['Build reads the component', 'It writes direct DOM updates', 'Small runtime ships', 'A change runs the generated update'], 'The saving is smaller output; the cost is a compiler step and rules to learn.'),
              ('Re-evaluate the template', 'A template is a function of the data. Run it again, but update only the parts of the DOM whose values changed.', ['lit'], ['A property changes', 'Template runs again', 'Only changed values compared', 'Those DOM parts updated'], 'No virtual DOM tree, a small library, and the browser’s own component standard.'),
              ('Check the tree', 'After an event, the framework walks the component tree to see what changed. Angular’s traditional way, triggered by zone.js, which notices asynchronous events.', ['angular'], ['An event or response happens', 'zone.js tells Angular', 'Bindings are checked top-down', 'Changed bindings update'], 'Signals let Angular skip the walk, and it is moving toward them.'),
              ('Ask the server', 'The state is on the server. The browser sends an event, receives HTML, and puts it in place.', ['htmx'], ['An event fires', 'Request to the server', 'HTML fragment returned', 'Fragment swapped in'], 'It does not need client state, and it does need a round trip.')]
    chg = ''.join(f'<h3>{a}</h3><p class="prose">{b} Used by {names(c)}.</p><ol class="flow" aria-label="{e(a)}">' + ''.join(f'<li>{s}</li>' for s in st) + f'</ol><p class="prose">{n}</p>'
                  for a, b, c, st, n in change)
    body = f"""{band('Concepts', 'How they work', 'Three questions every framework answers differently: where the HTML is made, how a change is found, and how much is in the box.')}
<div class="wrap">
<section class="section" aria-labelledby="where-h"><h2 id="where-h">Where the HTML is made</h2>
<div class="prose"><p>Before the first change, there is a first page. A framework decides who writes its HTML and when.</p></div>
<div class="tablewrap" tabindex="0" role="region" aria-label="Where the HTML is made"><table><thead><tr><th>Model</th><th>What happens</th><th>Frameworks here</th><th>The trade</th></tr></thead><tbody>{wrows}</tbody></table></div>
<div class="note"><b>Hydration</b>, in a line: the server’s HTML is only text and boxes until a script runs the components again in the browser and wires them to it. Resumability and islands are two answers to the cost of that second run.</div></section>
<section class="section" aria-labelledby="change-h"><h2 id="change-h">How a change reaches the screen</h2>
<div class="prose"><p>You change a number. Something has to find which part of the page showed that number and change it. There are six ways here, and many frameworks use more than one.</p></div>{chg}</section>
<section class="section" aria-labelledby="box-h"><h2 id="box-h">How much is in the box</h2>
<div class="prose"><p>The word <i>framework</i> covers three different sizes of thing.</p></div>
<div class="tablewrap" tabindex="0" role="region" aria-label="How much is in the box"><table><thead><tr><th>Size</th><th>What it gives you</th><th>Here</th></tr></thead><tbody>
<tr><th scope="row">Rendering library</th><td>Components and a way to update the screen. Routing, data and building are yours to choose.</td><td>{names(['react', 'preact', 'solid', 'lit'])}</td></tr>
<tr><th scope="row">Application framework</th><td>The view layer plus routing, forms, a way to talk to servers and a command-line tool, designed together.</td><td>{names(['angular', 'vue'])}. Vue’s router and store are official add-ons.</td></tr>
<tr><th scope="row">Meta-framework</th><td>Built on a rendering library: file-based routing, server rendering, bundling and deployment.</td><td>{names(['nextjs', 'nuxt'])}. Also SvelteKit on {names(['svelte'])}, SolidStart on {names(['solid'])} and Qwik City on {names(['qwik'])}.</td></tr>
<tr><th scope="row">Something else</th><td>Astro builds content sites and hosts other frameworks’ components; htmx adds behaviour to HTML with no components at all.</td><td>{names(['astro', 'htmx'])}</td></tr></tbody></table></div></section>
</div>
{pager('how', seq_all())}"""
    return shell('how', 'How they work', 'Where the HTML is made, how a change reaches the screen and how much is in the box: the three questions that separate React, Vue, Angular, Svelte, Solid, Qwik, Astro, Lit and htmx.', body)


def relation_map():
    pos = {'preact': (110, 100), 'react': (330, 230), 'solid': (110, 360), 'nextjs': (570, 100), 'vue': (640, 270), 'nuxt': (820, 270),
           'angular': (330, 400), 'qwik': (570, 400), 'svelte': (900, 60), 'astro': (900, 130), 'lit': (900, 350), 'htmx': (900, 420)}
    edges = [('nextjs', 'react', 'built on', 0), ('nuxt', 'vue', 'built on', 0), ('preact', 'react', 'same API', 1), ('solid', 'react', 'same JSX', 1),
             ('qwik', 'angular', 'same author', 1)]
    parts = []
    for a, b, lab, dash in edges:
        (x1, y1), (x2, y2) = pos[a], pos[b]
        parts.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#141414" stroke-width="{2.5 if not dash else 1.8}"{" stroke-dasharray=&quot;7 5&quot;" if dash else ""}/>'
                     f'<text class="el" x="{(x1 + x2) / 2}" y="{(y1 + y2) / 2 - 8}" text-anchor="middle" stroke="#F8F2E4" stroke-width="4" paint-order="stroke">{lab}</text>')
    parts = [p.replace('&quot;', '"') for p in parts]
    parts.append('<rect x="760" y="22" width="224" height="150" fill="none" stroke="#141414" stroke-width="1.5" stroke-dasharray="3 4"/>'
                 '<text class="el" x="770" y="42">stand alone</text>'
                 '<rect x="760" y="312" width="224" height="146" fill="none" stroke="#141414" stroke-width="1.5" stroke-dasharray="3 4"/>'
                 '<text class="el" x="770" y="332">stand alone</text>')
    for k, (x, y) in pos.items():
        w = 12 + 9.4 * len(FW[k]['name'])
        bg = FW[k]['accent']
        fg = ink_on(bg)
        parts.append(f'<a href="{k}.html"><rect x="{x - w / 2}" y="{y - 20}" width="{w}" height="40" fill="{bg}" stroke="#141414" stroke-width="2.5"/>'
                     f'<text x="{x}" y="{y + 5}" text-anchor="middle" style="fill:{fg}">{e(FW[k]["name"])}</text></a>')
    return ('<div class="map"><svg viewBox="0 0 1000 470" role="img" aria-labelledby="map-t"><title id="map-t">Who builds on, copies or shares an author with whom among the frameworks</title>'
            + ''.join(parts) + '</svg></div>')


def compare():
    rows = ''.join(f'<tr><th scope="row"><a href="{k}.html">{e(d["name"])}</a></th><td>{e(d["kind"])}</td><td>{e(d["authoring"])}</td><td>{e(d["rendering"])}</td>'
                   f'<td>{e(d["updates"])}</td><td>{e(d["router"])}</td><td class="num">{kb(m(MAIN[k])["js_load_bytes"])}</td></tr>' for k, d in FW.items())
    sized = sorted(FW, key=lambda k: m(MAIN[k])['js_load_bytes'])
    srows = ''.join(f'<tr><th scope="row"><a href="{k}.html">{e(FW[k]["name"])}</a></th><td class="num">{kb(m(MAIN[k])["js_load_bytes"])}</td><td class="num">{m(MAIN[k])["js_files"]}</td>'
                    f'<td class="num">{kb(m(MAIN[k])["js_after_click_bytes"])}</td><td>{"yes" if m(MAIN[k])["ssr"] else "no"}</td></tr>' for k in sized)
    body = f"""{band('Side by side', 'Compare', 'Where the twelve overlap, where they split, and what each one cost to show a button.')}
<div class="wrap">
<section class="section" aria-labelledby="axes-h"><h2 id="axes-h">Every axis at once</h2>
<div class="tablewrap" tabindex="0" role="region" aria-label="Frameworks compared"><table><thead><tr><th>Framework</th><th>Kind</th><th>You write</th><th>Renders</th><th>Finds changes by</th><th>Router</th><th class="num">Counter JS (kB)</th></tr></thead><tbody>{rows}</tbody></table></div></section>
<section class="section" aria-labelledby="rel-h"><h2 id="rel-h">Who builds on whom</h2>
<div class="prose"><p>Solid lines: one is built on the other. Dashed: it copies the other’s API or syntax, or was made by the same person. The boxes on the right hold the four that stand alone; Astro is the one that hosts the others’ components, as the list below says.</p></div>
{relation_map()}
<ul class="sources"><li>{names(['nextjs'])} is built on {names(['react'])}; {names(['nuxt'])} on {names(['vue'])}.</li><li>{names(['preact'])} has {names(['react'])}’s API; {names(['solid'])} has its JSX.</li><li>{names(['qwik'])} and {names(['angular'])} share an author, Miško Hevery.</li><li>{names(['astro'])} hosts components written in {names(['preact'])}, {names(['svelte'])}, {names(['lit'])} and others.</li></ul></section>
<section class="section" aria-labelledby="fam-h"><h2 id="fam-h">Where they overlap, where they differ</h2>
<div class="two"><div><h3>They overlap on</h3><ul>
<li><b>Components.</b> Every one here builds screens from pieces, except {names(['htmx'])}, which adds behaviour to HTML.</li>
<li><b>Reactivity.</b> {names(['vue'])}, {names(['solid'])}, {names(['svelte'])}, {names(['angular'])} and {names(['preact'])} all offer reactive values, under the name of refs, signals or runes.</li>
<li><b>Templates.</b> {names(['vue'])}, {names(['svelte'])} and {names(['angular'])} write HTML-like templates; {names(['react'])}, {names(['solid'])}, {names(['preact'])} and {names(['qwik'])} write JSX.</li>
<li><b>A meta-framework on top.</b> {names(['nextjs'])}, {names(['nuxt'])}, and the SvelteKit, SolidStart and Qwik City layers.</li></ul></div>
<div><h3>They differ on</h3><ul>
<li><b>Who does the work.</b> {names(['svelte'])} at build time, {names(['react'])} at run time, {names(['htmx'])} on the server, {names(['qwik'])} as late as possible.</li>
<li><b>How much ships.</b> From one script for {names(['htmx'])} to a framework for {names(['angular'])}: see the sizes below.</li>
<li><b>How much you choose.</b> {names(['react'])} leaves the router to you; {names(['angular'])} supplies one.</li>
<li><b>What a change re-runs.</b> A whole component in {names(['react'])}, a single expression in {names(['solid'])}, nothing in {names(['astro'])} pages without islands.</li></ul></div></div></section>
<section class="section" aria-labelledby="size-h"><h2 id="size-h">The counter, smallest to largest</h2>
<div class="prose"><p>The same page, built twelve ways. The smallest is not the best: it is the one that sends least for a page with one button. The gap between {names([sized[0]])} and {names([sized[-1]])} is {m(MAIN[sized[-1]])['js_load_bytes'] / m(MAIN[sized[0]])['js_load_bytes']:.0f} times here, and it would not stay that wide on a large app.</p></div>
<div class="tablewrap" tabindex="0" role="region" aria-label="Counter sizes"><table><thead><tr><th>Framework</th><th class="num">JS at load (kB)</th><th class="num">Files</th><th class="num">More after a click (kB)</th><th>HTML has the count before JS</th></tr></thead><tbody>{srows}</tbody></table></div></section>
</div>
{pager('compare', seq_all())}"""
    return shell('compare', 'Compare', 'JavaScript frameworks side by side: what each writes, how each renders and finds changes, who builds on whom, and the measured JavaScript size of a counter in each.', body)


def profile():
    q = PROFILE['queries']
    fw_rows = ''.join(
        f'<tr><th scope="row"><a href="{k}.html">{e(FW[k]["name"])}</a></th><td class="num">{len(q[k]["repos"])}</td><td>'
        + (', '.join(f'<a href="https://github.com/SolutionsAsService/{r}">{e(r)}</a>' for r in q[k]['repos']) if q[k]['repos'] else '—') + '</td></tr>'
        for k in ORDER)
    other = [('vite', 'Vite', 'build tool'), ('d3', 'D3', 'data-drawing library'), ('three', 'Three.js', '3D library'), ('tailwind', 'Tailwind CSS', 'CSS framework')]
    orows = ''.join(f'<tr><th scope="row">{n}</th><td>{t}</td><td class="num">{len(q[k]["repos"])}</td><td>' + ', '.join(f'<a href="https://github.com/SolutionsAsService/{r}">{e(r)}</a>' for r in q[k]['repos']) + '</td></tr>' for k, n, t in other)
    used = [FW[k]['name'] for k in ON_PROFILE]
    body = f"""{band('This GitHub profile', 'Author’s repos', 'Which of the twelve the public repositories of SolutionsAsService use, found by searching them.')}
<div class="wrap">
<section class="section" aria-labelledby="used-h"><h2 id="used-h">What the repositories use</h2>
<div class="prose"><p class="lede">In the public repositories that GitHub’s search could see on {PROFILE['scanned_on']}, a <code>package.json</code> names {', '.join(f"{FW[k]['name']} ({len(q[k]['repos'])})" for k in ON_PROFILE)}: {len(used)} of the twelve. The other nine have no match.</p>
<p>GitHub’s code search is not exhaustive, so a missing repository is a possible miss, not proof, and the counts are of repositories, not of how much each framework is used in them.</p></div>
<div class="tablewrap" tabindex="0" role="region" aria-label="Frameworks used on the profile"><table><thead><tr><th>Framework</th><th class="num">Repos</th><th>Which</th></tr></thead><tbody>{fw_rows}</tbody></table></div></section>
<section class="section" aria-labelledby="oth-h"><h2 id="oth-h">The tools beside them</h2>
<div class="prose"><p>Not frameworks, but they sit next to them in the same repositories: the build tool and libraries that do the drawing.</p></div>
<div class="tablewrap" tabindex="0" role="region" aria-label="Other tools on the profile"><table><thead><tr><th>Tool</th><th>What it is</th><th class="num">Repos</th><th>Which</th></tr></thead><tbody>{orows}</tbody></table></div></section>
<section class="section" aria-labelledby="note-h"><h2 id="note-h">Two things the search does not show</h2>
<div class="prose"><p>The profile’s earlier <a href="https://github.com/SolutionsAsService/JS-frameworks">JS-frameworks</a> repository is an overview with four framework summaries: React, Vue, Angular and Svelte. Those summaries link to pages that were never written. This site replaces it.</p>
<p>The repository <a href="https://github.com/SolutionsAsService/NextHistoryTimeline">NextHistoryTimeline</a> is described on GitHub as a “project to practice next js framework and shadcn”. It has no <code>package.json</code> in the search index, so the table above does not count it.</p>
<p>How to reproduce the table: <a href="{REPO}/blob/main/tools/profile-scan.sh">tools/profile-scan.sh</a> in the repository, which prints the queries it ran.</p></div></section>
</div>
{pager('profile', seq_all())}"""
    return shell('profile', 'Author’s repos', f'Which JavaScript frameworks the SolutionsAsService GitHub repositories use: {", ".join(used)}.', body)


def also():
    items = [('Remix and React Router', 'Remix was a React framework with server data loading and nested routes, from the makers of React Router. Its ideas were folded back into React Router 7, which can be used as a framework.', 'react', [('React Router', 'https://reactrouter.com/'), ('Wikipedia: Remix', 'https://en.wikipedia.org/wiki/Remix_(web_framework)')]),
             ('Gatsby', 'A React framework for static sites, by Kyle Mathews, from 2015. It pulled data into pages with GraphQL at build time. Netlify bought the company in 2023.', 'nextjs', [('Wikipedia: Gatsby', 'https://en.wikipedia.org/wiki/Gatsby_(framework)')]),
             ('Ember', 'An application framework from 2011 whose rule is convention over configuration: a fixed project layout, a router and a data layer, kept stable across versions for long-lived apps.', 'angular', [('Ember.js', 'https://emberjs.com/'), ('Wikipedia: Ember.js', 'https://en.wikipedia.org/wiki/Ember.js')]),
             ('Alpine.js', 'Caleb Porzio’s small library from 2019 that adds behaviour with attributes in HTML, in the browser, with no build step. The client-side cousin of htmx’s idea.', 'htmx', [('Alpine.js', 'https://alpinejs.dev/'), ('Wikipedia: Alpine.js', 'https://en.wikipedia.org/wiki/Alpine.js')]),
             ('Backbone', 'Jeremy Ashkenas’s 2010 library that gave browser apps models, views and a router and left the rest alone. It has no data binding: views re-render when you tell them to.', 'react', [('Backbone.js', 'https://backbonejs.org/'), ('Wikipedia: Backbone.js', 'https://en.wikipedia.org/wiki/Backbone.js')]),
             ('jQuery', 'John Resig’s 2006 library that made selecting and changing DOM nodes the same in every browser. It is not a component framework, and the frameworks on this site mostly exist because pages outgrew it.', 'react', [('jQuery', 'https://jquery.com/'), ('Wikipedia: jQuery', 'https://en.wikipedia.org/wiki/JQuery')])]
    blocks = ''.join(f'<section class="section" aria-labelledby="a{i}-h"><h2 id="a{i}-h">{e(n)}</h2><div class="prose"><p>{e(t)} Closest here: {names([c])}.</p>'
                     f'<ul class="sources">' + ''.join(f'<li><a href="{u}">{e(x)}</a></li>' for x, u in s) + '</ul></div></section>' for i, (n, t, c, s) in enumerate(items))
    body = f"""{band('Not given a page', 'Also', 'Older and smaller frameworks that shaped the twelve, described without a measurement.')}
<div class="wrap"><div class="note">These were not built or measured for this site, so they have no number. Each is described from its own documentation or its Wikipedia article.</div>{blocks}</div>
{pager('also', seq_all())}"""
    return shell('also', 'Also', 'Remix, Gatsby, Ember, Alpine.js, Backbone and jQuery: frameworks that shaped the twelve on this site, described without a measurement.', body)


def about():
    vrows = ''.join(f'<tr><th scope="row"><code>{k}</code></th><td>{e(v["version"])}</td><td class="num">{v["js_load_bytes"]:,}</td><td class="num">{v["js_files"]}</td><td class="num">{v["js_after_click_bytes"]:,}</td>'
                    f'<td class="num">{v.get("inline_js_gz", 0):,}</td><td class="num">{v["html_gz"]:,}</td><td>{"yes" if v["ssr"] else "no"}</td></tr>' for k, v in MEAS['results'].items())
    body = f"""{band('Method', 'About', 'How the numbers were made, what they leave out, and how the site was designed.')}
<div class="wrap">
<section class="section" aria-labelledby="proc-h"><h2 id="proc-h">How the numbers were measured</h2>
<div class="prose"><p>For each framework, one page: a heading and one button that reads “count: N” and adds one when clicked. It was built with the framework’s production build, using the recommended tooling, then served and opened in a fresh headless Chromium. Every JavaScript response the browser fetched was compressed with gzip at level 9, and the sizes added up. Then the button was clicked once and any further JavaScript was counted too. The click had to change the text from “count: 0” to “count: 1”, or the measurement failed.</p>
<p>The script is <a href="{REPO}/blob/main/tools/measure-sizes.mjs">tools/measure-sizes.mjs</a>; the sources of the fourteen apps (fifteen measurements: Qwik is measured twice), and the commands to build each, are in <a href="{REPO}/tree/main/tools">tools/</a>. Measured on {MEAS['measured_on']} with Node {MEAS['node'].lstrip('v')}.</p></div>
<div class="tablewrap" tabindex="0" role="region" aria-label="All measurements"><table><thead><tr><th>App</th><th>Version</th><th class="num">JS at load (B)</th><th class="num">Files</th><th class="num">After click (B)</th><th class="num">Inline script (B)</th><th class="num">HTML (B)</th><th>HTML has the count</th></tr></thead><tbody>{vrows}</tbody></table></div>
<p class="prose"><code>vanilla</code> is a hand-written counter with no framework, as the floor. All sizes are gzip level 9 of each file.</p></section>
<section class="section" aria-labelledby="not-h"><h2 id="not-h">What this does not tell you</h2>
<div class="prose"><ul>
<li><b>The site’s own JavaScript is one small file.</b> <code>script.js</code> is {len(gzip.compress((SRC / 'script.js').read_bytes(), 9, mtime=0)):,} B gzipped (<code>gzip -9 -n</code>): it only runs the light and dark button, and every page works without it.</li>
<li><b>“Works with” is not measured.</b> The pairs on each scrap (for example Next.js with React and Vercel) come from each project’s own wording about what it builds on or ships with, and are not linked pair by pair.</li>
<li><b>The twelve are the author’s choice.</b> Three are used in the author’s repositories (React, Next.js, Lit), three the author wanted covered (Angular, Vue, Svelte) and six are widely used or take a different road (Nuxt, Solid, Preact, Qwik, Astro, htmx). No ranking or survey chose them, so the set is not the whole field.</li>
<li><b>A counter is not an app.</b> It measures the cost of starting a framework, not how cost grows with features. A framework that is large at the start and small to grow (or the reverse) is hidden here.</li>
<li><b>Bytes are not speed.</b> A small download can still be slow to run, and a larger one can be cached and shared.</li>
<li><b>One run each, one machine.</b> The sizes are deterministic builds, so they repeat; load behaviour such as preloading depends on timing.</li>
<li><b>gzip, not brotli.</b> Servers often send smaller brotli. Checked with brotli at quality 11 ({BROTLI['checked_on']}, <a href="{REPO}/blob/main/tools/brotli-check.mjs">tools/brotli-check.mjs</a>), the eight static builds ({', '.join(BROTLI['order_brotli'])}) {'keep the same order' if BROTLI['order_same'] else 'change order'}; the server-rendered builds were not rechecked.</li>
<li><b>Inline script is excluded</b> and printed separately: a framework that moves script into the HTML would otherwise look smaller.</li>
<li><b>Qwik’s default preloads.</b> With its default settings it fetches the click handler while idle, so the click adds nothing; with preloading off the click loads 2.4 kB more. Both are shown on its page.</li>
<li><b>Bundlers changed too.</b> The Vite-based builds use Vite 8, which no longer minifies with esbuild, so a size here may differ from one measured earlier with another bundler.</li></ul></div></section>
<section class="section" aria-labelledby="dates-h"><h2 id="dates-h">How the dates were checked</h2>
<div class="prose"><p>The “Since” year on each page was compared with the npm registry by <a href="{REPO}/blob/main/tools/registry-dates.mjs">tools/registry-dates.mjs</a> on {REG['checked_on']}: the first version published, and the dates of 1.0.0, 2.0.0 and 3.0.0. The registry shows when a package was published, not who designed the framework or when its design was first shown, so it corroborates a year and never overrides one. React’s, Next.js’s and Lit’s names were used by unrelated packages before the frameworks took them, so their earliest registry dates are not checkable this way.</p>
<p>“Made by” is each project’s own account of itself, linked on its page. It was not checked against a second source: the build session could not reach Wikipedia.</p></div>
<div class="tablewrap" tabindex="0" role="region" aria-label="npm registry dates"><table><thead><tr><th>Framework</th><th>npm package</th><th>First version</th><th>1.0.0</th><th>2.0.0</th><th>3.0.0</th></tr></thead><tbody>{''.join(f'<tr><th scope="row"><a href="{k}.html">{e(FW[k]["name"])}</a></th><td><code>{r["package"]}</code></td><td>{r["first_version"]} ({r["first_published"]}){" (unrelated package)" if k in ("nextjs", "lit", "react") else ""}</td><td>{r["v1"] or "—"}</td><td>{r["v2"] or "—"}</td><td>{r["v3"] or "—"}</td></tr>' for k, r in REG['results'].items())}</tbody></table></div></section>
<section class="section" aria-labelledby="design-h"><h2 id="design-h">The design</h2>
<div class="prose"><p>Each framework is drawn as a small scene of the idea that sets it apart, in its own colour: a component tree that re-renders one branch (React), one signal reaching the exact places that read it (Solid), a compiler that runs once (Svelte), a sea of plain HTML with a few live islands (Astro), a request and a swapped fragment (htmx), and so on. The scenes are decorative; the words on the card say the same thing. The home page holds all twelve on one screen, grouped by kind, and every other page is a plain reference page.</p>
<p>It was directed with the <a href="https://github.com/PrometheusIntelligence/dada">DADA</a> design skill. The first version of this site (a four-framework overview) is kept on the <code>original-overview</code> branch of this repository, and an earlier collage-style version, graded C by the author as “too unappealing”, is in the <a href="https://github.com/SolutionsAsService/frameworks">frameworks</a> repository. The light and dark toggle and the pros and cons form come from the first version.</p>
<p>Each framework page links the project’s documentation and a Wikipedia article to read further. Frameworks change fast: check the documentation for the current version.</p></div></section>
</div>
{pager('about', seq_all())}"""
    return shell('about', 'About', 'How the JavaScript sizes on this site were measured, what they leave out, and how the site was designed.', body)


# ------------------------------------------------------------------ build
def check_links(out):
    written = {p.name for p in out.iterdir() if p.is_file()}
    pages_only = [out / n for n in written if n.endswith('.html')]
    bad = []
    for page in pages_only:
        text = page.read_text(encoding='utf-8')
        ids = set(re.findall(r'\sid="([^"]+)"', text))
        for ref in re.findall(r'(?:href|src)="([^"]+)"', text):
            if re.match(r'(https?:|mailto:|data:)', ref):
                continue
            target, _, frag = ref.partition('#')
            if target and target not in written:
                bad.append(f'{page.name}: {ref}')
            if frag and not target and frag not in ids:
                bad.append(f'{page.name}: #{frag}')
            if frag and target and target in written:
                other = (out / target).read_text(encoding='utf-8')
                if f'id="{frag}"' not in other:
                    bad.append(f'{page.name}: {ref} (no such id)')
    if bad:
        raise BuildError('broken internal links:\n  ' + '\n  '.join(bad))


def build():
    for k in FW:
        for rel in CODE[k]:
            if not (TOOLS / 'apps' / rel).exists():
                raise BuildError(f'missing source {rel}')
        m(MAIN[k])
        if k not in __import__('scenes').SCENES:
            raise BuildError(f'no scene for {k}')
    for name in GENERATED + [f'{k}.html' for k in FW]:
        pathlib.Path(OUT / name).unlink(missing_ok=True)
    (OUT / 'styles.css').write_text(CSS, encoding='utf-8', newline='\n')
    (OUT / 'script.js').write_text((SRC / 'script.js').read_text(encoding='utf-8'), encoding='utf-8', newline='\n')
    (OUT / 'favicon.svg').write_text(favicon(), encoding='utf-8', newline='\n')
    pages = {'index.html': home(), 'how.html': how(), 'compare.html': compare(), 'profile.html': profile(), 'also.html': also(), 'about.html': about()}
    for k in FW:
        pages[f'{k}.html'] = fw_page(k)
    for name, text in pages.items():
        (OUT / name).write_text(text, encoding='utf-8', newline='\n')
    (OUT / 'robots.txt').write_text('User-agent: *\nAllow: /\n', encoding='utf-8', newline='\n')
    (OUT / '.nojekyll').write_text('', encoding='utf-8')
    check_links(OUT)
    print(f'built {len(pages)} pages into {OUT}')


if __name__ == '__main__':
    try:
        build()
    except BuildError as exc:
        sys.exit(f'build failed: {exc}')
