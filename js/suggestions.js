'use strict';
// ============================================================
//  suggestions.js — Page suggestions · Scanaddiction
// ============================================================

document.addEventListener('DOMContentLoaded', () => {
  const form       = document.getElementById('suggestion-form');
  const listEl     = document.getElementById('suggestions-list');
  const countEl    = document.getElementById('sug-count');
  const filterEl   = document.getElementById('filtre-statut-sug');

  renderList();

  // ── Formulaire ───────────────────────────────────────────────
  if (form) {
    form.addEventListener('submit', e => {
      e.preventDefault();
      const titre  = document.getElementById('sug-titre')?.value?.trim();
      const auteur = document.getElementById('sug-auteur')?.value?.trim();
      const raison = document.getElementById('sug-raison')?.value?.trim();
      const type   = document.getElementById('sug-type')?.value;
      const pseudo = document.getElementById('sug-pseudo')?.value?.trim();

      if (!titre) { App.toast('Le titre est requis', 'warn'); return; }
      if (!raison || raison.length < 30) { App.toast('Argumentez un peu plus votre suggestion (30 caractères min.)', 'warn'); return; }

      App.LS.addSuggestion({ titre, auteur, raison, type, pseudo: pseudo || 'Anonyme' });
      form.reset();
      renderList();
      App.toast('Suggestion envoyée ! Merci 🙏', 'success');
      // Scroll vers la liste
      listEl?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  }

  // ── Filtre ────────────────────────────────────────────────────
  if (filterEl) filterEl.addEventListener('change', renderList);

  // ── Rendu liste ───────────────────────────────────────────────
  function renderList() {
    const all     = App.LS.getSuggestions();
    const statut  = filterEl?.value || '';
    const list    = statut ? all.filter(s => s.statut === statut) : all;

    if (countEl) countEl.textContent = `${all.length} suggestion${all.length !== 1 ? 's' : ''}`;

    if (!listEl) return;
    if (!list.length) {
      listEl.innerHTML = `<div class="empty-state py-12">
        <div class="empty-state-icon">💡</div>
        <p class="font-semibold text-slate-300 mb-1">Aucune suggestion ${statut ? 'pour ce filtre' : 'pour l\'instant'}</p>
        <p class="text-sm">Soyez le premier à proposer une œuvre !</p>
      </div>`;
      return;
    }

    listEl.innerHTML = list.map(s => {
      const badgeCls = {
        'en_attente': 'bg-slate-800/60 text-slate-400 border border-slate-700/50',
        'retenue'   : 'bg-emerald-900/40 text-emerald-400 border border-emerald-800/50',
        'refusee'   : 'bg-red-900/40 text-red-400 border border-red-800/50'
      }[s.statut] || 'bg-slate-800 text-slate-400';
      const badgeTxt = {
        'en_attente': '⏳ En attente',
        'retenue'   : '✓ Retenue',
        'refusee'   : '✕ Refusée'
      }[s.statut] || s.statut;

      return `
<div class="bg-[#111120] rounded-2xl border border-[#1e1e35] p-5 hover:border-[#2a2a45] transition-colors">
  <div class="flex items-start justify-between gap-4 flex-wrap mb-3">
    <div class="flex-1 min-w-0">
      <div class="flex flex-wrap items-center gap-2 mb-1">
        <h3 class="font-bold text-slate-100 text-base">${escHtml(s.titre)}</h3>
        ${s.type ? `<span class="px-2 py-0.5 bg-purple-900/30 text-purple-400 border border-purple-800/40 rounded text-xs font-semibold">${s.type}</span>` : ''}
      </div>
      ${s.auteur ? `<p class="text-xs text-slate-500">Auteur : <span class="text-slate-400">${escHtml(s.auteur)}</span></p>` : ''}
    </div>
    <span class="px-2.5 py-1 rounded-lg text-xs font-semibold shrink-0 ${badgeCls}">${badgeTxt}</span>
  </div>
  <p class="text-sm text-slate-300 leading-relaxed mb-3">${escHtml(s.raison)}</p>
  <div class="flex items-center justify-between text-xs text-slate-600">
    <span>par <span class="text-slate-500">${escHtml(s.pseudo || 'Anonyme')}</span></span>
    <span>${App.formatDate(s.date)}</span>
  </div>
</div>`;
    }).join('');
  }
});

function escHtml(str) {
  return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
