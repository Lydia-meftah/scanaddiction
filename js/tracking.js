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
  var GTM_ID = 'GTM-MRHG47Z5';   // ← Remplace ICI
  var GA4_ID = 'G-NQRMX2MT72';  // ← Remplace ICI
