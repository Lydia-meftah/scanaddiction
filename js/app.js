'use strict';
// ============================================================
//  app.js — Utilitaires globaux · Scanaddiction
// ============================================================

const App = (() => {

  // ─── Config ────────────────────────────────────────────────
  const CFG = {
    siteName : 'Scanaddiction',
    discord  : 'https://discord.gg/scanaddiction',
    kofi     : 'https://ko-fi.com/scanaddiction',
    email    : 'contact@scanaddiction.fr',
    dataPath : '/data/oeuvres.json'
  };

  // ─── LocalStorage helpers ───────────────────────────────────
  const LS = {
    get(key, fb = null) {
      try { const v = localStorage.getItem(key); return v !== null ? JSON.parse(v) : fb; }
      catch { return fb; }
    },
    set(key, val) { try { localStorage.setItem(key, JSON.stringify(val)); } catch {} },

    // Favoris
    getFavoris()     { return this.get('sa_favoris', []); },
    isFavori(id)     { return this.getFavoris().includes(id); },
    toggleFavori(id) {
      const f = this.getFavoris(), i = f.indexOf(id);
      if (i === -1) f.push(id); else f.splice(i, 1);
      this.set('sa_favoris', f);
      return i === -1; // true = ajouté
    },

    // Bookmark (dernier chapitre lu)
    getBookmark(id)      { return this.get(`sa_bm_${id}`, null); },
    setBookmark(id, num) { this.set(`sa_bm_${id}`, num); },

    // Notes personnelles
    getRating(id)        { return this.get(`sa_note_${id}`, 0); },
    setRating(id, note)  { this.set(`sa_note_${id}`, note); },

    // Commentaires (key = "oeuvre_ID" ou "chap_ID_NUM")
    getComments(key)  { return this.get(`sa_com_${key}`, []); },
    addComment(key, author, text) {
      const list = this.getComments(key);
      const com = {
        id: Date.now(),
        author: (author || '').trim() || 'Anonyme',
        text: text.trim(),
        date: new Date().toISOString()
      };
      list.unshift(com);
      this.set(`sa_com_${key}`, list);
      return com;
    },
    deleteComment(key, id) {
      const list = this.getComments(key).filter(c => c.id !== id);
      this.set(`sa_com_${key}`, list);
      return list;
    },

    // Suggestions
    getSuggestions()     { return this.get('sa_suggestions', []); },
    addSuggestion(data)  {
      const list = this.getSuggestions();
      const s = { id: Date.now(), date: new Date().toISOString(), statut: 'en_attente', ...data };
      list.unshift(s);
      this.set('sa_suggestions', list);
      return s;
    },
    updateSuggestionStatut(id, statut) {
      const list = this.getSuggestions().map(s => s.id === id ? { ...s, statut } : s);
      this.set('sa_suggestions', list);
      return list;
    }
  };

  // ─── Toast notifications ────────────────────────────────────
  let _toastEl = null;
  function toast(msg, type = 'info', dur = 3200) {
    if (!_toastEl) {
      _toastEl = document.createElement('div');
      _toastEl.className = 'fixed bottom-5 right-5 z-[9999] flex flex-col gap-2 pointer-events-none';
      document.body.appendChild(_toastEl);
    }
    const colors = { success:'bg-green-700', error:'bg-red-700', info:'bg-purple-700', warn:'bg-amber-600' };
    const icons  = { success:'✓', error:'✕', info:'ℹ', warn:'⚠' };
    const el = document.createElement('div');
    el.className = `pointer-events-auto flex items-center gap-3 px-4 py-3 rounded-xl shadow-xl text-white text-sm font-medium ${colors[type]||colors.info} opacity-0 translate-y-3 transition-all duration-300`;
    el.innerHTML = `<span class="font-bold">${icons[type]||icons.info}</span><span>${msg}</span>`;
    _toastEl.appendChild(el);
    requestAnimationFrame(() => {
      el.classList.remove('opacity-0','translate-y-3');
    });
    setTimeout(() => {
      el.classList.add('opacity-0','translate-y-3');
      setTimeout(() => el.remove(), 300);
    }, dur);
  }

  // ─── Navigation ─────────────────────────────────────────────
  function initNav() {
    const path = window.location.pathname;
    const active = href => {
      const h = href.replace('.html','');
      if (h === '/index' || h === '/') return path === '/' || path === '/index.html';
      return path.includes(h.replace('/', ''));
    };
    const lk = href => `transition-colors duration-200 ${active(href) ? 'text-purple-400 font-semibold' : 'text-slate-300 hover:text-white'}`;

    const html = `
<nav class="sticky top-0 z-50 bg-[#080810]/95 backdrop-blur-md border-b border-[#1e1e35]" id="main-nav">
  <div class="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between gap-4">
    <a href="/index.html" class="flex items-center gap-2.5 font-black text-xl tracking-tight shrink-0 hover:opacity-90 transition-opacity">
      <svg width="26" height="26" viewBox="0 0 28 28" fill="none"><polygon points="14,2 26,8 26,20 14,26 2,20 2,8" fill="#7c3aed" opacity="0.95"/><polygon points="14,7 21,11 21,18 14,22 7,18 7,11" fill="#a78bfa" opacity="0.5"/><circle cx="14" cy="14" r="3" fill="#fff"/></svg>
      <span>Scan<span class="text-purple-400">addiction</span></span>
    </a>
    <div class="hidden md:flex items-center gap-7 text-sm font-medium">
      <a href="/index.html" class="${lk('/index.html')}">Accueil</a>
      <a href="/catalogue.html" class="${lk('/catalogue.html')}">Catalogue</a>
      <a href="/suggestions.html" class="${lk('/suggestions.html')}">Suggestions</a>
      <a href="/apropos.html" class="${lk('/apropos.html')}">À propos</a>
    </div>
    <div class="hidden md:flex items-center gap-2.5">
      <a href="${CFG.discord}" target="_blank" rel="noopener noreferrer"
         class="flex items-center gap-1.5 px-3 py-1.5 bg-[#5865F2] hover:bg-[#4752c4] text-white rounded-lg text-xs font-bold transition-colors">
        <svg width="13" height="13" fill="currentColor" viewBox="0 0 24 24"><path d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.25.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057.1 18.08.105 18.1.12 18.112a19.9 19.9 0 0 0 5.993 3.03.078.078 0 0 0 .084-.028c.462-.63.874-1.295 1.226-1.994a.076.076 0 0 0-.041-.106 13.107 13.107 0 0 1-1.872-.892.077.077 0 0 1-.008-.128 10.2 10.2 0 0 0 .372-.292.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127 12.299 12.299 0 0 1-1.873.892.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028 19.839 19.839 0 0 0 6.002-3.03.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03z"/></svg>
        Discord
      </a>
      <a href="${CFG.kofi}" target="_blank" rel="noopener noreferrer"
         class="flex items-center gap-1.5 px-3 py-1.5 bg-[#FF5E5B] hover:bg-[#e04f4c] text-white rounded-lg text-xs font-bold transition-colors">
        ☕ Ko-fi
      </a>
    </div>
    <button id="nav-toggle" class="md:hidden p-2 text-slate-400 hover:text-white transition-colors" aria-label="Menu">
      <svg id="icon-menu" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M4 6h16M4 12h16M4 18h16"/></svg>
      <svg id="icon-close" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" class="hidden"><path d="M6 18L18 6M6 6l12 12"/></svg>
    </button>
  </div>
  <div id="nav-mobile" class="hidden md:hidden bg-[#0b0b16] border-t border-[#1e1e35] px-5 py-5 flex flex-col gap-1">
    <a href="/index.html" class="py-3 text-sm font-medium border-b border-[#1e1e35] ${lk('/index.html')}">Accueil</a>
    <a href="/catalogue.html" class="py-3 text-sm font-medium border-b border-[#1e1e35] ${lk('/catalogue.html')}">Catalogue</a>
    <a href="/suggestions.html" class="py-3 text-sm font-medium border-b border-[#1e1e35] ${lk('/suggestions.html')}">Suggestions</a>
    <a href="/apropos.html" class="py-3 text-sm font-medium border-b border-[#1e1e35] ${lk('/apropos.html')}">À propos</a>
    <div class="flex gap-3 pt-3">
      <a href="${CFG.discord}" target="_blank" rel="noopener noreferrer" class="flex-1 text-center py-2.5 bg-[#5865F2] text-white rounded-lg text-sm font-bold">Discord</a>
      <a href="${CFG.kofi}" target="_blank" rel="noopener noreferrer" class="flex-1 text-center py-2.5 bg-[#FF5E5B] text-white rounded-lg text-sm font-bold">☕ Ko-fi</a>
    </div>
  </div>
</nav>`;

    const ph = document.getElementById('nav-placeholder');
    if (ph) ph.outerHTML = html;

    // Mobile toggle
    document.addEventListener('click', e => {
      const toggle = document.getElementById('nav-toggle');
      const mobile = document.getElementById('nav-mobile');
      if (!toggle || !mobile) return;
      if (toggle.contains(e.target)) {
        const open = !mobile.classList.contains('hidden');
        mobile.classList.toggle('hidden', open);
        document.getElementById('icon-menu')?.classList.toggle('hidden', !open);
        document.getElementById('icon-close')?.classList.toggle('hidden', open);
      }
    });
  }

  // ─── Footer ──────────────────────────────────────────────────
  function initFooter() {
    const ph = document.getElementById('footer-placeholder');
    if (!ph) return;
    ph.outerHTML = `
<footer class="mt-20 border-t border-[#1e1e35] bg-[#060610]">
  <div class="max-w-7xl mx-auto px-4 sm:px-6 py-12">
    <div class="flex flex-col md:flex-row gap-10 justify-between">
      <div class="max-w-xs">
        <a href="/index.html" class="flex items-center gap-2 font-black text-lg mb-3">
          <svg width="22" height="22" viewBox="0 0 28 28" fill="none"><polygon points="14,2 26,8 26,20 14,26 2,20 2,8" fill="#7c3aed" opacity="0.9"/><circle cx="14" cy="14" r="3" fill="#fff"/></svg>
          <span>Scan<span class="text-purple-400">addiction</span></span>
        </a>
        <p class="text-sm text-slate-400 leading-relaxed">Plateforme communautaire de scantrad amateur francophone. Qualité, découverte, passion partagée.</p>
        <p class="text-xs text-slate-600 mt-4">Projet solo · non commercial</p>
      </div>
      <div class="grid grid-cols-2 sm:grid-cols-3 gap-8 text-sm">
        <div>
          <p class="font-semibold text-slate-200 mb-3 uppercase text-xs tracking-wider">Site</p>
          <ul class="space-y-2.5 text-slate-400">
            <li><a href="/index.html" class="hover:text-purple-400 transition-colors">Accueil</a></li>
            <li><a href="/catalogue.html" class="hover:text-purple-400 transition-colors">Catalogue</a></li>
            <li><a href="/suggestions.html" class="hover:text-purple-400 transition-colors">Suggestions</a></li>
          </ul>
        </div>
        <div>
          <p class="font-semibold text-slate-200 mb-3 uppercase text-xs tracking-wider">Communauté</p>
          <ul class="space-y-2.5 text-slate-400">
            <li><a href="${CFG.discord}" target="_blank" rel="noopener" class="hover:text-purple-400 transition-colors">Discord</a></li>
            <li><a href="${CFG.kofi}" target="_blank" rel="noopener" class="hover:text-purple-400 transition-colors">Ko-fi</a></li>
            <li><a href="/contact.html" class="hover:text-purple-400 transition-colors">Contact</a></li>
          </ul>
        </div>
        <div>
          <p class="font-semibold text-slate-200 mb-3 uppercase text-xs tracking-wider">Infos</p>
          <ul class="space-y-2.5 text-slate-400">
            <li><a href="/apropos.html" class="hover:text-purple-400 transition-colors">À propos</a></li>
            <li><a href="/soutien.html" class="hover:text-purple-400 transition-colors">Soutenir</a></li>
            <li><a href="/mentions-legales.html" class="hover:text-purple-400 transition-colors">Mentions légales</a></li>
          </ul>
        </div>
      </div>
    </div>
    <div class="mt-10 pt-6 border-t border-[#1e1e35] flex flex-col sm:flex-row gap-2 justify-between items-center text-xs text-slate-600">
      <p>© ${new Date().getFullYear()} Scanaddiction · Projet amateur non commercial · Les œuvres restent la propriété de leurs auteurs.</p>
      <a href="/mentions-legales.html" class="hover:text-slate-400 transition-colors">Mentions légales</a>
    </div>
  </div>
</footer>`;
  }

  // ─── Back to top ─────────────────────────────────────────────
  function initBackToTop() {
    const btn = document.createElement('button');
    btn.id = 'back-to-top';
    btn.setAttribute('aria-label', 'Retour en haut');
    btn.className = 'fixed bottom-6 left-5 z-40 p-3 bg-purple-700/80 hover:bg-purple-600 text-white rounded-full shadow-lg shadow-purple-900/40 opacity-0 pointer-events-none transition-all duration-300';
    btn.innerHTML = '<svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"><path d="M18 15l-6-6-6 6"/></svg>';
    document.body.appendChild(btn);
    window.addEventListener('scroll', () => {
      const show = window.scrollY > 500;
      btn.style.opacity = show ? '1' : '0';
      btn.style.pointerEvents = show ? 'auto' : 'none';
    }, { passive: true });
    btn.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));
  }

  // ─── Data cache ───────────────────────────────────────────────
  let _cache = null;
  async function getOeuvres() {
    if (_cache) return _cache;
    const r = await fetch(CFG.dataPath);
    if (!r.ok) throw new Error('Impossible de charger les données');
    _cache = await r.json();
    return _cache;
  }

  // ─── Utils ────────────────────────────────────────────────────
  const getParam = name => new URLSearchParams(window.location.search).get(name);

  function formatDate(iso) {
    if (!iso) return '';
    return new Date(iso).toLocaleDateString('fr-FR', { day: 'numeric', month: 'short', year: 'numeric' });
  }

  function timeAgo(iso) {
    const diff = Date.now() - new Date(iso).getTime();
    const m = Math.floor(diff / 60000);
    if (m < 1)  return 'À l\'instant';
    if (m < 60) return `Il y a ${m} min`;
    const h = Math.floor(m / 60);
    if (h < 24) return `Il y a ${h}h`;
    const d = Math.floor(h / 24);
    if (d < 7)  return `Il y a ${d}j`;
    return formatDate(iso);
  }

  function starHTML(note, max = 5) {
    let s = '';
    for (let i = 0; i < max; i++) {
      if (i < Math.floor(note)) s += '<span class="text-amber-400">★</span>';
      else if (i === Math.floor(note) && note % 1 >= 0.5) s += '<span class="text-amber-300 opacity-50">★</span>';
      else s += '<span class="text-slate-700">★</span>';
    }
    return s;
  }

  function statutBadge(statut) {
    const map = {
      'en cours': 'bg-emerald-900/40 text-emerald-400 border border-emerald-800/50',
      'terminé'  : 'bg-slate-800/60 text-slate-400 border border-slate-700/50',
      'pause'    : 'bg-amber-900/40 text-amber-400 border border-amber-800/50'
    };
    return `<span class="px-2 py-0.5 rounded-md text-xs font-semibold ${map[statut] || map['terminé']}">${statut}</span>`;
  }

  function typeBadge(type) {
    const map = {
      'manga'  : 'bg-purple-900/40 text-purple-400 border border-purple-800/50',
      'manhwa' : 'bg-blue-900/40 text-blue-400 border border-blue-800/50',
      'manhua' : 'bg-orange-900/40 text-orange-400 border border-orange-800/50',
      'webtoon': 'bg-teal-900/40 text-teal-400 border border-teal-800/50'
    };
    return `<span class="px-2 py-0.5 rounded-md text-xs font-semibold ${map[type] || 'bg-slate-800 text-slate-400'}">${type}</span>`;
  }

  // Génère des URLs d'images de démo pour le lecteur
  function demoPageUrl(oeuvre, chapNum, pageNum) {
    const c = oeuvre.couleur || '131320';
    return `https://placehold.co/800x1200/${c}/7c3aed?text=${encodeURIComponent(oeuvre.titre)}%0ACh.${chapNum}+·+Page+${pageNum}`;
  }

  // ─── Init ─────────────────────────────────────────────────────
  function init() {
    initNav();
    initFooter();
    initBackToTop();
  }

  document.addEventListener('DOMContentLoaded', init);

  // API publique
  return { LS, toast, getParam, formatDate, timeAgo, starHTML, statutBadge, typeBadge, getOeuvres, demoPageUrl, CFG };

})();
