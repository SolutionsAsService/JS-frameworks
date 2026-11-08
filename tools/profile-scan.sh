#!/usr/bin/env bash
# Which JavaScript frameworks do the public repos of SolutionsAsService use?
# Procedure: GitHub code search, one query per name, scoped to the user. A repo counts
# when a manifest or source file names the package. Paths under node_modules, .next
# and lockfiles are ignored. GitHub's code search is not exhaustive, so a missing
# repo is a possible miss, not proof of absence. Output: _src/data/profile.json
set -euo pipefail
OWNER=SolutionsAsService
out=_src/data/profile.json
declare -A Q=(
  [react]='filename:package.json "react"'
  [nextjs]='filename:package.json "next"'
  [lit]='filename:package.json "lit"'
  [preact]='filename:package.json "preact"'
  [vue]='filename:package.json "vue"'
  [angular]='filename:package.json "@angular/core"'
  [svelte]='filename:package.json "svelte"'
  [solid]='filename:package.json "solid-js"'
  [astro]='filename:package.json "astro"'
  [nuxt]='filename:package.json "nuxt"'
  [qwik]='filename:package.json "@builder.io/qwik"'
  [htmx]='htmx.org'
  [vite]='filename:package.json "vite"'
  [three]='filename:package.json "three"'
  [d3]='filename:package.json "d3"'
  [tailwind]='filename:package.json "tailwindcss"'
)
echo '{' > "$out"
echo "\"procedure\": \"GitHub code search scoped to user:$OWNER; ignores node_modules, .next and lockfiles; not exhaustive\"," >> "$out"
echo "\"scanned_on\": \"$(date -u +%F)\"," >> "$out"
echo '"queries": {' >> "$out"
first=1
for k in react nextjs lit preact vue angular svelte solid astro nuxt qwik htmx vite three d3 tailwind; do
  q="user:$OWNER ${Q[$k]}"
  repos='[]'
  IFS='|' read -ra parts <<< "${Q[$k]//||/|}"
  for part in "${parts[@]}"; do
    part="${part#"${part%%[![:space:]]*}"}"; part="${part%"${part##*[![:space:]]}"}"
    [ -n "$part" ] || continue
    got=$(gh api -X GET search/code -f q="user:$OWNER $part" -f per_page=100 --jq '[.items[] | select(.path|test("node_modules|\\.next/|package-lock|yarn.lock|pnpm-lock")|not) | .repository.name]' 2>/dev/null || echo '[]')
    repos=$(python3 -c 'import json,sys;print(json.dumps(sorted(set(json.loads(sys.argv[1])+json.loads(sys.argv[2])))))' "$repos" "$got")
    sleep 3
  done
  [ $first = 1 ] || echo ',' >> "$out"; first=0
  printf '"%s": {"query": %s, "repos": %s}' "$k" "$(printf '%s' "$q" | python3 -c 'import json,sys;print(json.dumps(sys.stdin.read()))')" "$repos" >> "$out"
  sleep 3
done
echo '}}' >> "$out"
python3 -m json.tool "$out" > "$out.tmp" && mv "$out.tmp" "$out"
