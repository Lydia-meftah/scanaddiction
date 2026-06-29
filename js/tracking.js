/**
 * tracking.js — Scanaddiction Analytics
 * ───────────────────────────────────────────────────────────────
 * ⚠️  CONFIGURATION REQUISE
 *   1. Remplace GTM_ID  par ton Container ID  (ex: GTM-AB12CD3)
 *   2. Remplace GA4_ID  par ton Measurement ID (ex: G-ABCDE12345)
 *   Crée tes comptes sur :
 *     https://tagmanager.google.com  (GTM)
 *     https://analytics.google.com  (GA4)
 * ───────────────────────────────────────────────────────────────
 *
 * PLAN D'EVENTS IMPLEMENTÉS
 * ┌────────────────────────┬─────────────────────────────────────┐
 * │ EVENT                  │ PARAMÈTRES CLÉS                     │
 * ├────────────────────────┼─────────────────────────────────────┤
 * │ page_view              │ (auto GA4)                          │
 * │ search                 │ search_term, results_count          │
 * │ filter_apply           │ filter_type, filter_value           │
 * │ sort_apply             │ sort_by                             │
 * │ manga_click            │ title, source, type, reader_mode    │
 * │ reader_open            │ title, source_site, reader_mode     │
 * │ chapter_loaded         │ title, source, chapter_num, imgs    │
 * │ chapter_navigate       │ direction, chapter_num, title       │
 * │ scroll_milestone       │ depth_percent, title, chapter       │
 * │ chapter_complete       │ title, source_site, chapter_num     │
 * │ chapter_error          │ title, source, error_type           │
 * │ source_performance     │ source_site, success, latency_ms    │
 * └────────────────────────┴─────────────────────────────────────┘
 */

(function () {
  'use strict';

  /* ── IDs à configurer ──────────────────────────────────────── */
  var GTM_ID = 'GTM-XXXXXXX';   // ← Remplace ICI
  var GA4_ID = 'G-XXXXXXXXXX';  // ← Remplace ICI

  /* ── 1. dataLayer (partagé GTM + GA4) ─────────────────────── */
  window.dataLayer = window.dataLayer || [];

  /* ── 2. GTM — snippet head ─────────────────────────────────── */
  (function (w, d, s, l, i) {
    w[l] = w[l] || [];
    w[l].push({ 'gtm.start': new Date().getTime(), event: 'gtm.js' });
    var f = d.getElementsByTagName(s)[0];
    var j = d.createElement(s);
    var dl = l !== 'dataLayer' ? '&l=' + l : '';
    j.async = true;
    j.src = 'https://www.googletagmanager.com/gtm.js?id=' + i + dl;
    f.parentNode.insertBefore(j, f);
  })(window, document, 'script', 'dataLayer', GTM_ID);

  /* ── 3. GA4 — gtag.js ──────────────────────────────────────── */
  var gScript = document.createElement('script');
  gScript.async = true;
  gScript.src = 'https://www.googletagmanager.com/gtag/js?id=' + GA4_ID;
  document.head.appendChild(gScript);

  function gtag() { window.dataLayer.push(arguments); }
  window.gtag = gtag;
  gtag('js', new Date());
  gtag('config', GA4_ID, {
    send_page_view: true,
    page_title: document.title,
    page_location: window.location.href,
    /* Paramètres custom qui apparaîtront dans les rapports GA4 */
    custom_map: {
      dimension1: 'manga_source',
      dimension2: 'reader_mode',
      dimension3: 'manga_type',
    },
  });

  /* ── 4. GTM noscript (fallback) ────────────────────────────── */
  document.addEventListener('DOMContentLoaded', function () {
    var ns = document.createElement('noscript');
    var iframe = document.createElement('iframe');
    iframe.src = 'https://www.googletagmanager.com/ns.html?id=' + GTM_ID;
    iframe.height = '0';
    iframe.width = '0';
    iframe.style.cssText = 'display:none;visibility:hidden';
    ns.appendChild(iframe);
    document.body.insertBefore(ns, document.body.firstChild);
  });

  /* ═══════════════════════════════════════════════════════════
     SA_TRACK — API de tracking centralisée
     Usage : SA_TRACK.search("naruto", 42)
  ═══════════════════════════════════════════════════════════ */
  var SA_TRACK = {

    /* Interne — envoie vers GA4 + dataLayer GTM */
    _push: function (eventName, params) {
      var payload = Object.assign({
        event_category: 'engagement',
        non_interaction: false,
      }, params);

      /* GA4 */
      if (typeof window.gtag === 'function') {
        window.gtag('event', eventName, payload);
      }
      /* GTM dataLayer */
      window.dataLayer.push(Object.assign({ event: 'sa_' + eventName }, payload));

      /* Debug console (retiré en prod si GTM_ID est valide) */
      if (GTM_ID === 'GTM-XXXXXXX') {
        console.debug('[SA_TRACK]', eventName, payload);
      }
    },

    /* ── CATALOGUE ──────────────────────────────────────────── */

    /**
     * Recherche dans le catalogue
     * @param {string} term - Terme saisi
     * @param {number} count - Nombre de résultats
     */
    search: function (term, count) {
      if (!term || term.length < 2) return;
      this._push('search', {
        search_term:    term.trim().toLowerCase(),
        results_count:  count,
        event_category: 'catalogue',
      });
    },

    /**
     * Filtre appliqué (type/statut/source)
     * @param {string} filterType  - "type" | "statut" | "source"
     * @param {string} filterValue - Valeur sélectionnée
     */
    filterApply: function (filterType, filterValue) {
      if (!filterValue) return; // Ignorer "Tous les..."
      this._push('filter_apply', {
        filter_type:    filterType,
        filter_value:   filterValue,
        event_category: 'catalogue',
      });
    },

    /**
     * Changement de tri
     * @param {string} sortBy - "titre" | "note" | "chapitres"
     */
    sortApply: function (sortBy) {
      this._push('sort_apply', {
        sort_by:        sortBy,
        event_category: 'catalogue',
      });
    },

    /**
     * Clic sur une carte manga
     * @param {Object} oeuvre     - Objet oeuvre du catalogue
     * @param {string} readerType - "mangadex" | "proxy" | "external"
     */
    mangaClick: function (oeuvre, readerType) {
      this._push('manga_click', {
        manga_title:    oeuvre.titre,
        manga_source:   oeuvre.sourceNom,
        manga_type:     oeuvre.type,
        manga_statut:   oeuvre.statut,
        reader_mode:    readerType,
        event_category: 'catalogue',
        /* select_item compatible GA4 e-commerce (pour funnel analysis) */
        items: [{
          item_id:       oeuvre.id,
          item_name:     oeuvre.titre,
          item_category: oeuvre.sourceNom,
          item_variant:  oeuvre.type,
        }],
      });
    },

    /* ── LECTEUR ────────────────────────────────────────────── */

    /**
     * Ouverture du lecteur
     */
    readerOpen: function (mangaTitle, sourceSite, readerMode) {
      this._sourceSite  = sourceSite;
      this._mangaTitle  = mangaTitle;
      this._readerMode  = readerMode;
      this._chapterNum  = 0;
      this._scrollFired = new Set();
      this._startTime   = Date.now();

      this._push('reader_open', {
        manga_title:    mangaTitle,
        source_site:    sourceSite,
        reader_mode:    readerMode,
        event_category: 'reader',
      });
    },

    /**
     * Chapitre chargé avec succès
     */
    chapterLoaded: function (chapterNum, imageCount) {
      var latency = this._startTime ? Date.now() - this._startTime : 0;
      this._chapterNum  = chapterNum;
      this._scrollFired = new Set();
      this._startTime   = Date.now();

      this._push('chapter_loaded', {
        manga_title:    this._mangaTitle || '',
        source_site:    this._sourceSite || '',
        reader_mode:    this._readerMode || '',
        chapter_num:    chapterNum,
        image_count:    imageCount,
        latency_ms:     latency,
        event_category: 'reader',
      });

      /* Démarrer le tracker de scroll pour ce chapitre */
      this._initScrollTracker();
    },

    /**
     * Erreur de chargement
     */
    chapterError: function (errorType, errorMsg) {
      this._push('chapter_error', {
        manga_title:    this._mangaTitle || '',
        source_site:    this._sourceSite || '',
        reader_mode:    this._readerMode || '',
        error_type:     errorType,    // "chapters_load" | "images_load"
        error_message:  String(errorMsg).substring(0, 150),
        event_category: 'reader',
        non_interaction: true,
      });
    },

    /**
     * Navigation prev/next
     */
    chapterNavigate: function (direction, chapterNum) {
      this._push('chapter_navigate', {
        manga_title:    this._mangaTitle || '',
        source_site:    this._sourceSite || '',
        direction:      direction,   // "prev" | "next" | "select"
        chapter_num:    chapterNum,
        event_category: 'reader',
      });
    },

    /**
     * Jalons de scroll (25/50/75/100 %)
     */
    scrollMilestone: function (depthPercent) {
      this._push('scroll_milestone', {
        manga_title:    this._mangaTitle || '',
        source_site:    this._sourceSite || '',
        chapter_num:    this._chapterNum || 0,
        depth_percent:  depthPercent,
        event_category: 'reader',
        non_interaction: true,
      });
    },

    /**
     * Chapitre terminé (scroll 100 %)
     */
    chapterComplete: function () {
      this._push('chapter_complete', {
        manga_title:    this._mangaTitle || '',
        source_site:    this._sourceSite || '',
        reader_mode:    this._readerMode || '',
        chapter_num:    this._chapterNum || 0,
        time_spent_s:   this._startTime ? Math.round((Date.now() - this._startTime) / 1000) : 0,
        event_category: 'reader',
        non_interaction: true,
      });
    },

    /**
     * Performance de la source (succès/échec + latence)
     */
    sourcePerformance: function (sourceSite, success, latencyMs) {
      this._push('source_performance', {
        source_site:    sourceSite,
        success:        success,
        latency_ms:     latencyMs,
        event_category: 'performance',
        non_interaction: true,
      });
    },

    /* ── Interne : tracker de profondeur de scroll ─────────── */
    _initScrollTracker: function () {
      var self = this;
      var milestones = [25, 50, 75, 100];

      /* Supprimer l'ancien listener si existe */
      if (this._scrollHandler) {
        window.removeEventListener('scroll', this._scrollHandler);
      }

      this._scrollHandler = function () {
        var el  = document.documentElement;
        var scrolled = window.scrollY + window.innerHeight;
        var total = el.scrollHeight;
        if (total <= window.innerHeight) return; // page courte
        var pct = Math.round((scrolled / total) * 100);
        milestones.forEach(function (m) {
          if (pct >= m && !self._scrollFired.has(m)) {
            self._scrollFired.add(m);
            self.scrollMilestone(m);
            if (m === 100) self.chapterComplete();
          }
        });
      };

      window.addEventListener('scroll', this._scrollHandler, { passive: true });
    },
  };

  /* Exposer globalement */
  window.SA_TRACK = SA_TRACK;

})();
