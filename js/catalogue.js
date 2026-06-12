'use strict';
// ============================================================
//  catalogue.js — Page catalogue · Scanaddiction
// ============================================================

document.addEventListener('DOMContentLoaded', async () => {
  const grid      = document.getElementById('catalogue-grid');
  const countEl   = document.getElementById('result-count');
  const searchEl  = document.getElementById('search-input');
  const filtreGenre  = document.getElementById('filtre-genre');
  const filtreType   = document.getElementById('filtre-type');
  const filtreStatut = document.getElementById('filtre-statut');
  const filtreOrdre  = document.getElementById('filtre-ordre');
  const btnReset     = document.getElementById('btn-reset-filtres');

  let oeuvres = [];

  // ── Chargement ──────────────────────────────────────────────
  try {
    const data = await App.getOeuvres();
    oeuvres = data.oeuvres || [];
    populateGenreFilter(oeuvres);
    render();
  } catch (e) {
    grid.innerHTML = `<div class="col-span-full empty-state"><div class="empty-state-icon">⚠️</div><p>Erreur de chargement. Rechargez la page.</p></div>`;
  }

  // ── Remplir filtre genres ───────────────────────────────────
  function populateGenreFilter(list) {
    const genres = [...new Set(list.flatMap(o => o.genres))].sort();
    genres.forEach(g => {
      const opt = document.createElement('option');
      opt.value = g; opt.textContent = g;
      filtreGenre.appendChild(opt);
    });
  }

  // ── Filtre + tri ────────────────────────────────────────────
  function getFiltered() {
    let list = [...oeuvres];
    const q = (searchEl.value || '').toLowerCase().trim();
    const g = filtreGenre.value;
    const t = filtreType.value;
    const s = filtreStatut.value;
    const o = filtreOrdre.value;

    if (q) list = list.filter(x =>
      x.titre.toLowerCase().includes(q) ||
      (x.titreFr||'').toLowerCase().includes(q) ||
      (x.auteur||'').toLowerCase().includes(q) ||
      x.genres.some(gg => gg.toLowerCase().includes(q))
    );
    if (g) list = list.filter(x => x.genres.includes(g));
    if (t) list = list.filter(x => x.type === t);
    if (s) list = list.filter(x => x.statut === s);

    const sorts = {
      'note'     : (a, b) => b.note - a.note,
      'vues'     : (a, b) => b.vues - a.vues,
      'favoris'  : (a, b) => b.nbFavoris - a.nbFavoris,
      'recent'   : (a, b) => {
        const lastA = a.chapitres[a.chapitres.length-1]?.date || '';
        const lastB = b.chapitres[b.chapitres.length-1]?.date || '';
        return lastB.localeCompare(lastA);
      },
      'az'       : (a, b) => a.titre.localeCompare(b.titre)
    };
    list.sort(sorts[o] || sorts['note']);
    return list;
  }

  // ── Rendu carte ─────────────────────────────────────────────
  function cardHTML(o) {
    const isFav = App.LS.isFavori(o.id);
    const bm    = App.LS.getBookmark(o.id);
    const lastChap = o.chapitres[o.chapitres.length - 1];
    return `
<a href="/oeuvre.html?id=${o.id}" class="card-oeuvre group flex flex-col">
  <div class="relative overflow-hidden" style="aspect-ratio:5/7">
    <img src="${o.cover}" alt="Cover ${o.titre}" loading="lazy"
         onerror="this.style.background='#${o.couleur||'1e1e35'}';this.src='https://placehold.co/300x420/${o.couleur||'1e1e35'}/7c3aed?text=Cover'">
    <div class="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
    <div class="absolute top-2 right-2 flex flex-col gap-1">
      ${o.nouveau ? '<span class="px-1.5 py-0.5 bg-purple-600 text-white text-[10px] font-bold rounded">NOUVEAU</span>' : ''}
      ${isFav ? '<span title="Dans vos favoris" class="text-red-400 text-sm">♥</span>' : ''}
    </div>
    ${bm ? `<div class="absolute bottom-2 left-2 px-1.5 py-0.5 bg-black/80 text-purple-300 text-[10px] rounded">Ch.${bm} lu</div>` : ''}
  </div>
  <div class="flex flex-col gap-1.5 p-3 flex-1">
    <p class="font-bold text-sm text-slate-100 leading-tight line-clamp-2">${o.titre}</p>
    ${o.titreFr ? `<p class="text-xs text-slate-500 line-clamp-1">${o.titreFr}</p>` : ''}
    <div class="flex items-center gap-1.5 flex-wrap mt-auto pt-1.5">
      ${App.typeBadge(o.type)}
      ${App.statutBadge(o.statut)}
    </div>
    <div class="flex items-center justify-between text-xs text-slate-500 mt-1">
      <span>${App.starHTML(o.note)} ${o.note}</span>
      <span>${o.chapitres.length} ch.</span>
    </div>
    ${lastChap ? `<p class="text-[11px] text-slate-600">Dernier : Ch.${lastChap.numero} · ${App.formatDate(lastChap.date)}</p>` : ''}
  </div>
</a>`;
  }

  // ── Rendu principal ─────────────────────────────────────────
  function render() {
    const list = getFiltered();
    if (countEl) countEl.textContent = `${list.length} œuvre${list.length !== 1 ? 's' : ''}`;
    if (!list.length) {
      grid.innerHTML = `<div class="col-span-full empty-state"><div class="empty-state-icon">🔍</div><p class="font-semibold text-slate-300 mb-1">Aucun résultat</p><p class="text-sm">Essayez d'autres filtres ou un autre terme de recherche.</p></div>`;
      return;
    }
    grid.innerHTML = list.map(cardHTML).join('');
  }

  // ── Événements ──────────────────────────────────────────────
  [searchEl, filtreGenre, filtreType, filtreStatut, filtreOrdre].forEach(el => {
    if (el) el.addEventListener('input', render);
    if (el) el.addEventListener('change', render);
  });

  if (btnReset) {
    btnReset.addEventListener('click', () => {
      searchEl.value = '';
      filtreGenre.value = '';
      filtreType.value = '';
      filtreStatut.value = '';
      filtreOrdre.value = 'note';
      render();
    });
  }
});
