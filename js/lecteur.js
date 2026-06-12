'use strict';
// ============================================================
//  lecteur.js — Lecteur chapitre · Scanaddiction
// ============================================================

document.addEventListener('DOMContentLoaded', async () => {
  const oeuvreId  = App.getParam('id');
  const chapNum   = parseInt(App.getParam('ch') || '1', 10);
  const mainEl    = document.getElementById('reader-main');
  const pagesEl   = document.getElementById('reader-pages');
  const toolbarEl = document.getElementById('reader-toolbar');

  if (!oeuvreId) { window.location.href = '/catalogue.html'; return; }

  let oeuvre, chapitre, chapIndex, allChaps;

  // ── Chargement ───────────────────────────────────────────────
  try {
    const data = await App.getOeuvres();
    oeuvre  = (data.oeuvres || []).find(o => o.id === oeuvreId);
    if (!oeuvre) throw new Error('Œuvre introuvable');
    allChaps  = oeuvre.chapitres;
    chapIndex = allChaps.findIndex(c => c.numero === chapNum);
    chapitre  = chapIndex !== -1 ? allChaps[chapIndex] : allChaps[0];
    if (!chapitre) throw new Error('Chapitre introuvable');
  } catch(e) {
    mainEl.innerHTML = `<div class="empty-state py-20"><div class="empty-state-icon">📖</div>
      <p class="font-semibold text-xl text-slate-300 mb-3">Chapitre introuvable</p>
      <a href="/catalogue.html" class="px-5 py-2.5 bg-purple-700 text-white rounded-xl font-semibold text-sm">Catalogue</a></div>`;
    return;
  }

  document.title = `${oeuvre.titre} · Ch.${chapitre.numero} — Scanaddiction`;

  // Bookmark
  App.LS.setBookmark(oeuvreId, chapitre.numero);

  const prevChap = chapIndex > 0 ? allChaps[chapIndex - 1] : null;
  const nextChap = chapIndex < allChaps.length - 1 ? allChaps[chapIndex + 1] : null;

  // ── Rendu toolbar ────────────────────────────────────────────
  toolbarEl.innerHTML = `
<div class="max-w-4xl mx-auto px-4 py-3 flex items-center justify-between gap-4 flex-wrap">
  <div class="flex items-center gap-3 min-w-0">
    <a href="/oeuvre.html?id=${oeuvreId}" class="text-slate-400 hover:text-white transition-colors shrink-0" title="Retour à la fiche">
      <svg width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M19 12H5M12 5l-7 7 7 7"/></svg>
    </a>
    <div class="min-w-0">
      <p class="font-bold text-sm text-white truncate">${oeuvre.titre}</p>
      <p class="text-xs text-slate-400 truncate">Ch.${chapitre.numero} · ${chapitre.titre}</p>
    </div>
  </div>
  <div class="flex items-center gap-2 shrink-0">
    ${prevChap ? `<a href="/lecteur.html?id=${oeuvreId}&ch=${prevChap.numero}"
         class="flex items-center gap-1 px-3 py-1.5 bg-[#1e1e35] hover:bg-purple-900/40 text-slate-300 hover:text-white rounded-lg text-xs font-semibold transition-colors">
         <svg width="12" height="12" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M15 18l-6-6 6-6"/></svg> Préc.
       </a>` : ''}
    <span id="chap-selector-wrap">
      <select id="chap-selector" class="bg-[#1e1e35] border border-[#2a2a45] text-slate-200 text-xs rounded-lg px-2 py-1.5 outline-none cursor-pointer">
        ${allChaps.map(c => `<option value="${c.numero}" ${c.numero === chapitre.numero ? 'selected' : ''}>Ch.${c.numero} · ${c.titre}</option>`).join('')}
      </select>
    </span>
    ${nextChap ? `<a href="/lecteur.html?id=${oeuvreId}&ch=${nextChap.numero}"
         class="flex items-center gap-1 px-3 py-1.5 bg-purple-700 hover:bg-purple-600 text-white rounded-lg text-xs font-semibold transition-colors">
         Suiv. <svg width="12" height="12" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M9 18l6-6-6-6"/></svg>
       </a>` : '<span class="px-3 py-1.5 bg-[#1e1e35] text-slate-600 rounded-lg text-xs font-semibold">Fin</span>'}
    <!-- Largeur images -->
    <div class="hidden sm:flex items-center gap-1.5 ml-2">
      <span class="text-xs text-slate-500">Largeur</span>
      <select id="width-selector" class="bg-[#1e1e35] border border-[#2a2a45] text-slate-200 text-xs rounded-lg px-2 py-1.5 outline-none cursor-pointer">
        <option value="600">Étroit</option>
        <option value="800" selected>Normal</option>
        <option value="1000">Large</option>
        <option value="9999">Plein</option>
      </select>
    </div>
  </div>
</div>`;

  // Chap selector navigation
  document.getElementById('chap-selector')?.addEventListener('change', e => {
    window.location.href = `/lecteur.html?id=${oeuvreId}&ch=${e.target.value}`;
  });
  document.getElementById('width-selector')?.addEventListener('change', e => {
    document.querySelectorAll('.reader-page').forEach(p => {
      p.style.maxWidth = e.target.value === '9999' ? '100%' : `${e.target.value}px`;
    });
    localStorage.setItem('sa_reader_width', e.target.value);
  });

  // Restaurer largeur
  const savedWidth = localStorage.getItem('sa_reader_width') || '800';
  const widthSel = document.getElementById('width-selector');
  if (widthSel) widthSel.value = savedWidth;

  // ── Rendu pages ──────────────────────────────────────────────
  const maxW = savedWidth === '9999' ? '100%' : `${savedWidth}px`;
  let pagesHtml = '';
  for (let i = 1; i <= chapitre.pages; i++) {
    const url = App.demoPageUrl(oeuvre, chapitre.numero, i);
    pagesHtml += `
<div class="reader-page" style="max-width:${maxW}">
  <img src="${url}" alt="Page ${i}" loading="${i <= 3 ? 'eager' : 'lazy'}"
       style="width:100%;height:auto;display:block"
       onerror="this.style.background='#${oeuvre.couleur||'131320'}';this.alt='Page ${i} — image non disponible'">
</div>`;
  }
  pagesEl.innerHTML = pagesHtml;

  // ── Navigation fin de chapitre ────────────────────────────────
  const endNavHtml = nextChap ? `
<div class="flex flex-col items-center gap-4 py-12 px-4 bg-[#0c0c18] border-t border-[#1e1e35]">
  <p class="text-slate-400 text-sm">Chapitre terminé !</p>
  <a href="/lecteur.html?id=${oeuvreId}&ch=${nextChap.numero}"
     class="flex items-center gap-2 px-6 py-3 bg-purple-700 hover:bg-purple-600 text-white rounded-xl font-bold transition-colors">
     Chapitre suivant · Ch.${nextChap.numero} <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M9 18l6-6-6-6"/></svg>
  </a>
  <a href="/oeuvre.html?id=${oeuvreId}" class="text-sm text-slate-500 hover:text-purple-400 transition-colors">Retour à la fiche</a>
</div>` : `
<div class="flex flex-col items-center gap-4 py-12 px-4 bg-[#0c0c18] border-t border-[#1e1e35]">
  <p class="text-2xl">🎉</p>
  <p class="font-bold text-slate-200">Vous avez lu le dernier chapitre disponible !</p>
  <p class="text-sm text-slate-500">Revenez bientôt pour la suite.</p>
  <a href="/oeuvre.html?id=${oeuvreId}"
     class="px-5 py-2.5 bg-purple-700 hover:bg-purple-600 text-white rounded-xl font-semibold text-sm transition-colors">
     Retour à la fiche
  </a>
</div>`;

  // Commentaires chapitre
  const comKey = `chap_${oeuvreId}_${chapitre.numero}`;
  const comments = App.LS.getComments(comKey);

  const commentsHtml = `
<div class="max-w-3xl mx-auto px-4 py-10">
  <h3 class="font-bold text-lg text-slate-100 mb-5">Commentaires du chapitre ${chapitre.numero}</h3>
  <div class="bg-[#111120] rounded-2xl p-5 border border-[#1e1e35] mb-6">
    <div class="flex flex-col gap-3">
      <input id="chap-com-author" class="form-input" placeholder="Pseudo (optionnel)" maxlength="30">
      <textarea id="chap-com-text" class="form-input resize-none" rows="3"
                placeholder="Votre avis sur ce chapitre..." maxlength="500"></textarea>
      <div class="flex justify-end">
        <button onclick="postChapComment('${comKey}')"
                class="px-5 py-2 bg-purple-700 hover:bg-purple-600 text-white rounded-xl text-sm font-semibold transition-colors">
          Publier
        </button>
      </div>
    </div>
  </div>
  <div id="chap-comments-list"></div>
</div>`;

  document.getElementById('reader-end').innerHTML = endNavHtml + commentsHtml;
  renderChapComments(comKey);

  // ── Progress bar ──────────────────────────────────────────────
  const bar = document.getElementById('reader-progress-bar');
  const onScroll = () => {
    const docH = document.documentElement.scrollHeight - window.innerHeight;
    const pct  = docH > 0 ? (window.scrollY / docH * 100) : 0;
    if (bar) bar.style.width = pct + '%';
  };
  window.addEventListener('scroll', onScroll, { passive: true });

  // ── Raccourcis clavier ────────────────────────────────────────
  document.addEventListener('keydown', e => {
    if (e.target.matches('input,textarea')) return;
    if (e.key === 'ArrowLeft' && prevChap)  window.location.href = `/lecteur.html?id=${oeuvreId}&ch=${prevChap.numero}`;
    if (e.key === 'ArrowRight' && nextChap) window.location.href = `/lecteur.html?id=${oeuvreId}&ch=${nextChap.numero}`;
  });
});

// ── Commentaires chapitre ─────────────────────────────────────
function renderChapComments(key) {
  const el   = document.getElementById('chap-comments-list');
  if (!el) return;
  const list = App.LS.getComments(key);
  if (!list.length) {
    el.innerHTML = `<div class="empty-state py-8"><div class="empty-state-icon">💬</div><p>Soyez le premier à commenter ce chapitre !</p></div>`;
    return;
  }
  el.innerHTML = list.map(c => `
<div class="comment-card mb-3">
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
    <button onclick="deleteChapComment('${key}', ${c.id})"
            class="text-xs text-slate-600 hover:text-red-400 transition-colors" title="Supprimer">✕</button>
  </div>
  <p class="mt-2 text-sm text-slate-300 leading-relaxed pl-10">${escHtml(c.text)}</p>
</div>`).join('');
}

function postChapComment(key) {
  const author = document.getElementById('chap-com-author')?.value || '';
  const text   = document.getElementById('chap-com-text')?.value || '';
  if (!text.trim()) { App.toast('Écrivez quelque chose !', 'warn'); return; }
  App.LS.addComment(key, author, text);
  document.getElementById('chap-com-text').value = '';
  renderChapComments(key);
  App.toast('Commentaire publié !', 'success');
}

function deleteChapComment(key, id) {
  App.LS.deleteComment(key, id);
  renderChapComments(key);
}

function escHtml(str) {
  return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
