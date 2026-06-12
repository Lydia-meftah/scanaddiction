#!/bin/bash
# deploy.sh — Init git + push vers GitHub
# Usage : bash deploy.sh https://github.com/TON-PSEUDO/scanaddiction.git

set -e

REPO_URL="${1}"

if [ -z "$REPO_URL" ]; then
  echo "Usage: bash deploy.sh https://github.com/TON-PSEUDO/scanaddiction.git"
  exit 1
fi

echo "→ Init git..."
git init

echo "→ Ajout .gitignore..."
cat > .gitignore << 'GITIGNORE'
.DS_Store
Thumbs.db
*.log
node_modules/
.env
GITIGNORE

echo "→ Ajout de tous les fichiers..."
git add .

echo "→ Premier commit..."
git commit -m "feat: init Scanaddiction — site scantrad complet

- 10 pages HTML (accueil, catalogue, oeuvre, lecteur, suggestions...)
- 5 modules JS vanilla (app, catalogue, oeuvre, lecteur, suggestions)
- CSS custom dark theme manga
- 6 oeuvres de démo dans data/oeuvres.json
- localStorage : favoris, bookmarks, notes, commentaires, suggestions
- SEO : sitemap.xml + robots.txt
- Prêt pour Cloudflare Pages (zéro build)"

echo "→ Connexion au remote..."
git remote add origin "$REPO_URL"

echo "→ Push vers GitHub..."
git branch -M main
git push -u origin main

echo ""
echo "✓ Déployé sur GitHub !"
echo ""
echo "Étapes suivantes :"
echo "1. Va sur https://pages.cloudflare.com"
echo "2. Connect to Git → sélectionne ton repo"
echo "3. Build command : (vide)  |  Output directory : /"
echo "4. Deploy !"
