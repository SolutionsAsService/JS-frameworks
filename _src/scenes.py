"""One small illustration per framework, drawn from the idea that sets it apart.

Each scene is a 160 x 84 inline SVG that uses only the framework's accent colour (--a) through four classes:
.s (outline), .f (solid), .t (tint), .d (dimmed). They are decorative (aria-hidden); the card's text says the same thing in words.
"""

W, H = 160, 84


def _wrap(body, big=False):
    return (f'<svg class="scene{" scene-big" if big else ""}" viewBox="0 0 {W} {H}" aria-hidden="true" focusable="false" preserveAspectRatio="xMidYMid meet">{body}</svg>')


def _line(x1, y1, x2, y2, cls='s'):
    return f'<line class="{cls}" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}"/>'


def _box(x, y, w, h, cls='s', r=4):
    return f'<rect class="{cls}" x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}"/>'


def _dot(x, y, r, cls='f'):
    return f'<circle class="{cls}" cx="{x}" cy="{y}" r="{r}"/>'


def _arrow(x1, y1, x2, y2, cls='s'):
    # a line with a small arrowhead at the end
    import math
    a = math.atan2(y2 - y1, x2 - x1)
    hx1, hy1 = x2 - 6 * math.cos(a - .5), y2 - 6 * math.sin(a - .5)
    hx2, hy2 = x2 - 6 * math.cos(a + .5), y2 - 6 * math.sin(a + .5)
    return (f'<line class="{cls}" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}"/>'
            f'<polyline class="{cls}" points="{hx1:.1f},{hy1:.1f} {x2},{y2} {hx2:.1f},{hy2:.1f}"/>')


def react(big=False):
    # a component tree: a change re-runs one branch, and React compares it with the old one
    b = _line(80, 18, 36, 40) + _line(80, 18, 80, 40) + _line(80, 18, 124, 40)
    b += _line(36, 40, 22, 64) + _line(36, 40, 50, 64) + _line(124, 40, 110, 64) + _line(124, 40, 138, 64)
    b += _box(70, 6, 20, 14, 'f') + _box(26, 34, 20, 14, 't') + _box(70, 34, 20, 14, 't') + _box(114, 34, 20, 14, 'f')
    b += _box(12, 58, 20, 14, 't') + _box(40, 58, 20, 14, 't') + _box(100, 58, 20, 14, 'f') + _box(128, 58, 20, 14, 'f')
    return _wrap(b, big)


def preact(big=False):
    # the same tree, small, inside a lot of empty room: the whole library is a few kilobytes
    b = '<rect class="s d" x="6" y="6" width="148" height="72" rx="10" stroke-dasharray="4 5"/>'
    b += _line(80, 32, 62, 44) + _line(80, 32, 98, 44) + _box(73, 24, 14, 10, 'f', 3) + _box(55, 42, 14, 10, 't', 3) + _box(91, 42, 14, 10, 'f', 3)
    b += _line(62, 52, 54, 62) + _line(62, 52, 70, 62) + _box(48, 60, 12, 8, 't', 2) + _box(64, 60, 12, 8, 't', 2)
    return _wrap(b, big)


def solid(big=False):
    # one signal, and the exact places that read it
    b = _dot(26, 42, 10) + _dot(26, 42, 16, 's d')
    b += '<path class="s" d="M36 38 C 70 14, 90 18, 112 20"/><path class="s" d="M36 46 C 70 70, 90 66, 112 64"/>'
    b += _box(112, 12, 22, 16, 'f') + _box(112, 56, 22, 16, 'f')
    b += _box(112, 34, 22, 16, 'd') + _box(70, 6, 22, 14, 'd') + _box(70, 64, 22, 14, 'd')
    return _wrap(b, big)


def lit(big=False):
    # a custom element with a shadow boundary around it
    b = '<rect class="s" x="14" y="8" width="132" height="68" rx="12" stroke-dasharray="5 4"/>'
    b += _box(26, 20, 108, 44, 't', 8) + _box(36, 30, 50, 8, 'f', 3) + _box(36, 44, 76, 6, 'd', 3) + _box(36, 54, 40, 6, 'd', 3)
    b += _dot(122, 34, 6, 'f')
    return _wrap(b, big)


def vue(big=False):
    # reactive state, and the template pieces that read it
    b = _dot(24, 22, 10) + _box(62, 8, 84, 68, 's', 8)
    b += _box(72, 18, 50, 7, 'f', 3) + _box(72, 34, 64, 7, 'd', 3) + _box(72, 50, 40, 7, 'f', 3) + _box(72, 62, 54, 6, 'd', 3)
    b += _arrow(34, 22, 70, 21) + '<path class="s" d="M26 32 C 30 54, 46 56, 70 53" fill="none"/>'
    return _wrap(b, big)


def angular(big=False):
    # one platform: layers that are designed to fit together, wired by injection
    ys = (8, 28, 48, 68)
    b = ''.join(_box(10, y, 118, 12, 't' if i % 2 else 'f', 4) for i, y in enumerate(ys))
    b += ''.join(_dot(22 + 12 * j, y + 6, 2.5, 'x') for y in ys for j in range(2))
    b += _line(142, 14, 142, 74) + _arrow(142, 74, 142, 70) + ''.join(_line(130, y + 6, 142, y + 6) for y in ys)
    return _wrap(b, big)


def svelte(big=False):
    # a component file goes in, a compiler runs once, and a little direct code comes out
    b = '<path class="s" d="M14 10 h28 l10 10 v52 h-38 z"/><polyline class="s" points="42,10 42,20 52,20"/>'
    b += _box(20, 30, 26, 5, 'f', 2) + _box(20, 42, 26, 5, 'd', 2) + _box(20, 54, 20, 5, 'f', 2)
    b += _arrow(62, 42, 98, 42) + _dot(80, 42, 7, 't')
    b += _box(106, 26, 40, 6, 'f', 3) + _box(106, 40, 28, 6, 'f', 3) + _box(106, 54, 34, 6, 'd', 3)
    return _wrap(b, big)


def qwik(big=False):
    # lots of code waiting on the page; one click loads just one piece
    b = ''
    for r in range(2):
        for c in range(5):
            on = (r, c) == (1, 3)
            b += _box(20 + c * 24, 14 + r * 22, 18, 14, 'f' if on else 'd', 3)
    b += '<polygon class="f" points="76,62 76,80 82,75 87,84 91,82 86,73 93,73"/>' + _arrow(84, 66, 90, 50)
    return _wrap(b, big)


def nextjs(big=False):
    # folders become routes
    b = _box(10, 10, 14, 10, 'f', 2) + _line(17, 20, 17, 64) + _line(17, 36, 30, 36) + _line(17, 54, 30, 54)
    b += _box(30, 30, 30, 12, 't', 3) + _box(30, 48, 30, 12, 't', 3)
    b += _arrow(66, 36, 98, 36) + _arrow(66, 54, 98, 54)
    b += _box(100, 28, 50, 16, 'f', 8) + _box(100, 46, 50, 16, 'f', 8)
    return _wrap(b, big)


def nuxt(big=False):
    # folders that wire themselves into one app
    b = _box(10, 8, 74, 16, 't', 4) + _box(18, 26, 74, 16, 't', 4) + _box(26, 44, 74, 16, 't', 4)
    b += _arrow(104, 32, 120, 40) + _dot(136, 42, 14) + _dot(136, 42, 8, 'x')
    b += _line(14, 70, 100, 70, 'd')
    return _wrap(b, big)


def astro(big=False):
    # a sea of plain HTML, with a few islands that are alive
    b = ''.join(_line(10, y, 150, y, 'd') for y in (10, 20, 30, 40, 50, 60, 70))
    b += _box(26, 24, 40, 26, 'f', 13) + _box(94, 40, 44, 26, 'f', 13)
    b += _dot(46, 37, 4, 'x') + _dot(116, 53, 4, 'x')
    return _wrap(b, big)


def htmx(big=False):
    # the page asks, the server sends back a piece of HTML, and the page swaps it in
    b = _box(8, 10, 52, 64, 's', 6) + _box(100, 10, 52, 64, 't', 6)
    b += _box(14, 18, 40, 6, 'd', 2) + _box(14, 30, 40, 6, 'd', 2) + _box(14, 46, 40, 14, 'f', 3)
    b += _arrow(62, 28, 98, 28) + _arrow(98, 56, 62, 56)
    b += _box(112, 22, 28, 6, 'd', 2) + _box(112, 50, 28, 14, 'f', 3)
    return _wrap(b, big)


SCENES = {'react': react, 'preact': preact, 'solid': solid, 'lit': lit, 'vue': vue, 'angular': angular, 'svelte': svelte,
          'qwik': qwik, 'nextjs': nextjs, 'nuxt': nuxt, 'astro': astro, 'htmx': htmx}


def scene(key, big=False):
    return SCENES[key](big)
