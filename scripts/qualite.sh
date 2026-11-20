#!/usr/bin/env bash
# scripts/qualite.sh — contrôles qualité communs (CI, agents IA, humains).
# Usage : bash scripts/qualite.sh        → tous les contrôles
# Code de sortie ≠ 0 si au moins un contrôle échoue.
set -uo pipefail
cd "$(dirname "$0")/.."

TAILWIND="tailwindcss@3.4.17"
fail=0
ok()   { echo "  ✅ $1"; }
ko()   { echo "  ❌ $1"; [ -n "${GITHUB_ACTIONS:-}" ] && echo "::error::$1"; fail=1; }

echo "🎨 Tailwind compilé à jour"
if npx --yes "$TAILWIND" -i css/tailwind.src.css -o css/tailwind.css --minify >/dev/null 2>&1; then
  if git diff --quiet -- css/tailwind.css; then ok "css/tailwind.css à jour"
  else ko "css/tailwind.css n'est pas à jour : lancer npx $TAILWIND -i css/tailwind.src.css -o css/tailwind.css --minify puis committer"; fi
else
  ko "compilation Tailwind impossible (réseau ou npx indisponible)"
fi

echo "🚫 Interdits"
if grep -l 'cdn.tailwindcss.com' -- *.html >/dev/null 2>&1; then ko "CDN Tailwind présent dans une page"; else ok "pas de CDN Tailwind"; fi
if git ls-files --error-unmatch .mcp.json >/dev/null 2>&1; then ko ".mcp.json est versionné (jetons)"; else ok ".mcp.json non versionné"; fi
if git grep -nIE '(ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|sk-ant-[A-Za-z0-9_-]{20,}|sk-[A-Za-z0-9]{40,}|hf_[A-Za-z0-9]{30,})' -- . >/dev/null 2>&1; then
  ko "un jeton/secret semble committé (git grep pour le localiser)"
else ok "aucun jeton détecté"; fi

echo "🧹 Fichiers corrompus (octets nuls)"
bad=$(git ls-files -z | xargs -0 grep -lP '\x00' --binary-files=text -- 2>/dev/null | grep -vE '\.(png|jpe?g|webp|gif|ico|woff2?)$' || true)
if [ -n "$bad" ]; then ko "octets nuls dans : $bad"; else ok "aucun"; fi

echo "🔧 Syntaxe JavaScript"
for f in functions/api/*.js js/*.js; do
  node --check "$f" 2>/dev/null || ko "erreur de syntaxe : $f"
done
[ $fail -eq 0 ] && ok "functions/ et js/"

echo "🐍 Syntaxe Python"
for f in *.py; do python3 -m py_compile "$f" 2>/dev/null || ko "erreur de syntaxe : $f"; done
rm -rf __pycache__

echo "📄 YAML des workflows"
for f in .github/workflows/*.yml; do
  python3 -c "import sys,yaml; yaml.safe_load(open(sys.argv[1]))" "$f" 2>/dev/null || ko "YAML invalide : $f"
done

echo "📊 Catalogue"
python3 check_catalogue.py >/dev/null 2>&1 && ok "data/catalogue-fr.json valide" || ko "catalogue invalide ou vide"
for f in data/*.json scans/*.json; do
  python3 -c "import json,sys; json.load(open(sys.argv[1]))" "$f" 2>/dev/null || ko "JSON invalide : $f"
done

echo
if [ $fail -eq 0 ]; then echo "✅ Tous les contrôles passent"; else echo "❌ Des contrôles échouent"; fi
exit $fail
