'use strict';
// ============================================================
//  oeuvre.js — Fiche œuvre · Scanaddiction
// ============================================================

document.addEventListener('DOMContentLoaded', async () => {
  const id = App.getParam('id');
  if (!id) { window.location.href = '/catalogue.html'; return; }

  const mainEl = document.getElementById('oeuvre-main');

  // Skeleton
  mainEl.innerHTML = `<div class="animate-pulse space-y-4 max-w-4xl mx-auto px-4 pt-8">
    <div class="flex gap-6"><div class="skeleton w-36 h-52 shrink-0 rounded-xl"></div>
    <div class="flex-1 space-y-3"><div class="skeleton h-8 w-3/4 rounded"></div>
    <div class="skeleton h-4 w-1/2 rounded"></div><div class="skeleton h-4 w-1/3 rounded"></div></div></div>
    <div class="skeleton h-24 rounded-xl"></div></div>`;

  let oeuvre;
  try {
    const data = await App.getOeuvres();
    oeuvre = (data.oeuvres || []).find(o => o.id === id);
  } catch (e) {}

  if (!oeuvre) {
    mainEl.innerHTML = `<div class="empty-state py-20"><div class="empty-state-icon">🔍</div>
      <p class="font-semibold text-xl text-slate-300 mb-3">Œuvre introuvable</p>
      <a href="/catalogue.html" class="btn-primary">Retour au catalogue</a></div>`;
    return;
  }

  document.title = `${oeuvre.titre} — Scanaddiction`;
  const metaDesc = document.querySelector('meta[name="description"]');
  if (metaDesc) metaDesc.content = oeuvre.synopsis.slice(0, 155) + '…';

  renderPage(oeuvre);
});

function renderPage(o) {
  const mainEl = document.getElementById('oeuvre-main');
  const isFav  = App.LS.isFavori(o.id);
  const bm     = App.LS.getBookmark(o.id);
  const myNote = App.LS.getRating(o.id);
  const firstChap = o.chapitres[0];
  const lastChap  = o.chapitres[o.chapitres.length - 1];

  mainEl.innerHTML = `
<!-- Breadcrumb -->
<nav class="text-xs text-slate-500 mb-6 flex items-center gap-2">
  <a href="/catalogue.html" class="hover:text-purple-400 transition-colors">Catalogue</a>
  <span>›</span>
  <span class="text-slate-300">${o.titre}</span>
</nav>

<!-- Hero -->
<div class="flex flex-col sm:flex-row gap-6 mb-8">
  <!-- Cover -->
  <div class="shrink-0 w-full sm:w-44 md:w-52">
    <img src="${o.cover}" alt="Cover ${o.titre}"
         class="w-full rounded-xl border border-[#2a2a45] shadow-xl shadow-black/50"
         style="aspect-ratio:5/7;object-fit:cover"
         onerror="this.style.background='#${o.couleur||'1e1e35'}';this.src=''">
  </div>
  <!-- Infos -->
  <div class="flex-1 min-w-0">
    <div class="flex flex-wrap items-start gap-2 mb-2">
      ${App.typeBadge(o.type)}
      ${App.statutBadge(o.statut)}
      ${o.nouveau ? '<span class="px-2 py-0.5 rounded-md text-xs font-bold bg-purple-600 text-white">NOUVEAU</span>' : ''}
    </div>
    <h1 class="text-2xl sm:text-3xl font-black text-white mb-1">${o.titre}</h1>
    ${o.titreFr ? `<p class="text-slate-400 text-sm mb-3">${o.titreFr}</p>` : ''}

    <div class="flex flex-wrap gap-x-6 gap-y-1 text-sm text-slate-400 mb-4">
      <span><span class="text-slate-500">Auteur</span> · <span class="text-slate-200">${o.auteur}</span></span>
      ${o.artiste !== o.auteur ? `<span><span class="text-slate-500">Artiste</span> · <span class="text-slate-200">${o.artiste}</span></span>` : ''}
      <span><span class="text-slate-500">Année</span> · <span class="text-slate-200">${o.annee}</span></span>
    </div>

    <div class="flex flex-wrap gap-2 mb-5">
      ${o.genres.map(g => `<span class="badge-genre">${g}</span>`).join('')}
    </div>

    <!-- Stats -->
    <div class="flex flex-wrap gap-5 text-sm mb-5">
      <div class="text-center">
        <div class="text-xl font-bold text-amber-400">${o.note}</div>
        <div class="text-xs text-slate-500">${App.starHTML(o.note)}</div>
      </div>
      <div class="text-center">
        <div class="text-xl font-bold text-slate-200">${o.vues.toLocaleString('fr-FR')}</div>
        <div class="text-xs text-slate-500">vues</div>
      </div>
      <div class="text-center">
        <div class="text-xl font-bold text-red-400">♥ ${o.nbFavoris.toLocaleString('fr-FR')}</div>
        <div class="text-xs text-slate-500">favoris</div>
      </div>
      <div class="text-center">
        <div class="text-xl font-bold text-purple-400">${o.chapitres.length}</div>
        <div class="text-xs text-slate-500">chapitres</div>
      </div>
    </div>

    <!-- Actions -->
    <div class="flex flex-wrap gap-3">
      ${firstChap ? `<a href="/lecteur.html?id=${o.id}&ch=${bm || firstChap.numero}"
           class="flex items-center gap-2 px-5 py-2.5 bg-purple-600 hover:bg-purple-500 text-white rounded-xl font-semibold text-sm transition-colors">
           <svg width="15" height="15" fill="currentColor" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
           ${bm ? `Reprendre · Ch.${bm}` : 'Commencer la lecture'}
         </a>` : ''}
      <button id="btn-favori" onclick="toggleFavori('${o.id}')"
              class="flex items-center gap-2 px-4 py-2.5 border rounded-xl font-semibold text-sm transition-all
              ${isFav ? 'border-red-700 bg-red-900/20 text-red-400 hover:bg-red-900/30' : 'border-[#2a2a45] text-slate-400 hover:border-purple-600 hover:text-purple-400'}">
        <span id="fav-icon">${isFav ? '♥' : '♡'}</span>
        <span id="fav-text">${isFav ? 'Dans les favoris' : 'Ajouter aux favoris'}</span>
      </button>
    </div>
  </div>
</div>

<!-- Synopsis -->
<section class="mb-8 bg-[#111120] rounded-2xl p-5 border border-[#1e1e35]">
  <h2 class="font-bold text-slate-200 mb-3 flex items-center gap-2">
    <svg width="16" height="16" fill="currentColor" viewBox="0 0 24 24" class="text-purple-400"><path d="M4 6h16M4 10h16M4 14h10"/></svg>
    Synopsis
  </h2>
  <p class="text-slate-300 leading-relaxed text-sm">${o.synopsis}</p>
</section>

<!-- Ma note -->
<section class="mb-8 bg-[#111120] rounded-2xl p-5 border border-[#1e1e35]">
  <h2 class="font-bold text-slate-200 mb-3">Ma note</h2>
  <div id="user-stars" class="flex gap-1">
    ${[1,2,3,4,5].map(n => `
    <button onclick="setNote('${o.id}', ${n})"
            class="star-interactive text-2xl transition-transform ${n <= myNote ? 'text-amber-400' : 'text-slate-700'}"
            data-star="${n}" title="${n} étoile${n>1?'s':''}">★</button>`).join('')}
  </div>
  <p id="note-msg" class="text-xs text-slate-500 mt-2">${myNote ? `Votre note : ${myNote}/5` : 'Cliquez pour noter'}</p>
</section>

<!-- Chapitres -->
<section class="mb-10">
  <div class="flex items-center justify-between mb-4">
    <h2 class="font-bold text-lg text-slate-100">Chapitres <span class="text-slate-500 text-sm font-normal">(${o.chapitres.length})</span></h2>
    ${bm ? `<span class="text-xs text-purple-400 bg-purple-900/20 px-2 py-1 rounded-lg">Lu jusqu'au Ch.${bm}</span>` : ''}
  </div>
  <div class="flex flex-col gap-1.5">
    ${o.chapitres.slice().reverse().map(ch => {
      const isRead = App.LS.getBookmark(o.id) && ch.numero <= App.LS.getBookmark(o.id);
      return `
    <a href="/lecteur.html?id=${o.id}&ch=${ch.numero}"
       class="flex items-center justify-between px-4 py-3 rounded-xl border bg-[#111120] hover:bg-[#161628] transition-colors group
       ${isRead ? 'border-[#1e1e35] opacity-60' : 'border-[#1e1e35] hover:border-purple-800/50'}">
      <div class="flex items-center gap-3">
        <span class="text-sm font-bold text-purple-400 w-10 shrink-0">Ch.${ch.numero}</span>
        <span class="text-sm text-slate-200 group-hover:text-white transition-colors">${ch.titre}</span>
        ${isRead ? '<span class="text-xs text-slate-600 ml-2">lu</span>' : ''}
      </div>
      <div class="flex items-center gap-3 text-xs text-slate-500">
        <span class="hidden sm:block">${ch.pages} pages</span>
        <span>${App.formatDate(ch.date)}</span>
        <svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" class="text-slate-600 group-hover:text-purple-400 transition-colors"><path d="M9 18l6-6-6-6"/></svg>
      </div>
    </a>`}).join('')}
  </div>
</section>

<!-- Commentaires -->
<section class="mb-10" id="comments-section">
  <h2 class="font-bold text-lg text-slate-100 mb-4">Commentaires</h2>
  <div id="comment-form-area" class="bg-[#111120] rounded-2xl p-5 border border-[#1e1e35] mb-6">
    <div class="flex flex-col gap-3">
      <input id="com-author" class="form-input" placeholder="Votre pseudo (optionnel)" maxlength="30">
      <textarea id="com-text" class="form-input resize-none" rows="3" placeholder="Votre commentaire sur cette œuvre..." maxlength="500"></textarea>
      <div class="flex justify-end">
        <button onclick="postComment('oeuvre_${o.id}')"
                class="px-5 py-2 bg-purple-700 hover:bg-purple-600 text-white rounded-xl text-sm font-semibold transition-colors">
          Publier
        </button>
      </div>
    </div>
  </div>
  <div id="comments-list"></div>
</section>`;

  // Rendu commentaires
  renderComments(`oeuvre_${o.id}`);
}

// ── Commentaires ─────────────────────────────────────────────
function renderComments(key) {
  const el = document.getElementById('comments-list');
  if (!el) return;
  const list = App.LS.getComments(key);
  if (!list.length) {
    el.innerHTML = `<div class="empty-state py-10"><div class="empty-state-icon">💬</div><p>Soyez le premier à commenter !</p></div>`;
    return;
  }
  el.innerHTML = list.map(c => `
<div class="comment-card mb-3" id="com-${c.id}">
  <div class="flex items-start justify-between gap-3">
    <div class="flex items-center gap-2">
      <div class="w-8 h-8 rounded-full bg-purple-900/50 flex items-center justify-center text-sm font-bold text-purple-300">
        ${c.author.charAt(0).toUpperCase()}
      </div>
      <div>
        <span class="font-semibold text-sm text-slate-200">${escHtml(c.author)}</span>
        <span class="text-xs text-slate-500 ml-2">${App.timeAgo(c.date)}</span>
      </div>
    </div>
    <button onclick="deleteComment('${key}', ${c.id})"
            class="text-xs text-slate-600 hover:text-red-400 transition-colors shrink-0" title="Supprimer">✕</button>
  </div>
  <p class="mt-2 text-sm text-slate-300 leading-relaxed pl-10">${escHtml(c.text)}</p>
</div>`).join('');
}

function postComment(key) {
  const author = document.getElementById('com-author')?.value || '';
  const text   = document.getElementById('com-text')?.value || '';
  if (!text.trim()) { App.toast('Écrivez quelque chose !', 'warn'); return; }
  App.LS.addComment(key, author, text);
  document.getElementById('com-text').value = '';
  renderComments(key);
  App.toast('Commentaire publié !', 'success');
}

function deleteComment(key, id) {
  App.LS.deleteComment(key, id);
  renderComments(key);
}

// ── Favoris ───────────────────────────────────────────────────
function toggleFavori(id) {
  const added = App.LS.toggleFavori(id);
  const btn   = document.getElementById('btn-favori');
  const icon  = document.getElementById('fav-icon');
  const text  = document.getElementById('fav-text');
  if (added) {
    btn.className = btn.className.replace('border-[#2a2a45] text-slate-400 hover:border-purple-600 hover:text-purple-400', 'border-red-700 bg-red-900/20 text-red-400 hover:bg-red-900/30');
    icon.textContent = '♥';
    text.textContent = 'Dans les favoris';
    App.toast('Ajouté aux favoris ♥', 'success');
  } else {
    btn.className = btn.className.replace('border-red-700 bg-red-900/20 text-red-400 hover:bg-red-900/30', 'border-[#2a2a45] text-slate-400 hover:border-purple-600 hover:text-purple-400');
    icon.textContent = '♡';
    text.textContent = 'Ajouter aux favoris';
    App.toast('Retiré des favoris', 'info');
  }
}

// ── Notes ─────────────────────────────────────────────────────
function setNote(id, note) {
  App.LS.setRating(id, note);
  const stars = document.querySelectorAll('#user-stars button');
  stars.forEach((s, i) => {
    s.className = s.className.replace(i < note ? 'text-slate-700' : 'text-amber-400',
                                      i < note ? 'text-amber-400' : 'text-slate-700');
    if (i < note) s.classList.add('text-amber-400'); else s.classList.remove('text-amber-400');
    if (i < note) s.classList.remove('text-slate-700'); else s.classList.add('text-slate-700');
  });
  const msg = document.getElementById('note-msg');
  if (msg) msg.textContent = `Votre note : ${note}/5`;
  App.toast(`Note de ${note}/5 enregistrée !`, 'success');
}

// ── Utils ─────────────────────────────────────────────────────
function escHtml(str) {
  return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
