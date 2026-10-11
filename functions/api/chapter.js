/**
 * functions/api/chapter.js — Cloudflare Pages Function (proxy durci)
 *
 * Extrait images / liste de chapitres des sites Madara en contournant CORS.
 *   GET /api/chapter?url={page_chapitre}&mode=chapter   → { images:  [...] }
 *   GET /api/chapter?url={page_serie}&mode=chapters      → { chapters:[...] }
 *
 * Durcissement anti-SSRF (réf. OWASP SSRF Prevention Cheat Sheet) :
 *   - méthode GET uniquement ;
 *   - schéma https:// imposé, pas d'identifiants dans l'URL, port standard ;
 *   - allowlist d'hôtes en correspondance exacte ;
 *   - redirections NON suivies (redirect:'manual') — une URL autorisée ne peut
 *     pas rebondir vers une cible interne/bloquée après validation ;
 *   - délai max (AbortController) et plafond de taille de réponse ;
 *   - CORS restreint aux origines du site.
 */

const ALLOWED_HOSTS = new Set([
  'sushiscan.net',
  'raijin-scans.fr',
  'crunchyscan.fr',
  'scan-manga.com',
  'www.scan-manga.com',
]);

const ALLOWED_ORIGINS = new Set([
  'https://scanaddiction-pages.pages.dev',
  'http://localhost:8788',
  'http://localhost:3000',
]);

const MAX_BYTES = 5 * 1024 * 1024;   // 5 Mo
const FETCH_TIMEOUT_MS = 15000;

function corsHeaders(origin) {
  const h = {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Methods': 'GET, OPTIONS',
    'Cache-Control': 'public, max-age=300',
  };
  if (origin && ALLOWED_ORIGINS.has(origin)) h['Access-Control-Allow-Origin'] = origin;
  return h;
}
const ok  = (data, origin) => new Response(JSON.stringify(data), { headers: corsHeaders(origin) });
const err = (msg, status, origin) => new Response(JSON.stringify({ error: msg }), { status, headers: corsHeaders(origin) });

/** Valide l'URL cible contre les règles anti-SSRF. Renvoie {url} ou {error,status}. */
function validateTarget(raw) {
  let u;
  try { u = new URL(raw); } catch { return { error: 'URL invalide', status: 400 }; }
  if (u.protocol !== 'https:')             return { error: 'Schéma non autorisé (https requis)', status: 400 };
  if (u.username || u.password)            return { error: 'Identifiants interdits dans l’URL', status: 400 };
  if (u.port && u.port !== '443')          return { error: 'Port non autorisé', status: 400 };
  if (!ALLOWED_HOSTS.has(u.hostname))      return { error: `Domaine non autorisé: ${u.hostname}`, status: 403 };
  return { url: u };
}

async function getHtml(url) {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), FETCH_TIMEOUT_MS);
  try {
    const res = await fetch(url, {
      method: 'GET',
      redirect: 'manual',               // ne jamais suivre une redirection (anti-SSRF)
      signal: ctrl.signal,
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8',
        'Referer': new URL(url).origin + '/',
      },
    });
    if (res.status >= 300 && res.status < 400) throw new Error('Redirection refusée');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);

    // Plafond de taille : lecture bornée du flux.
    const reader = res.body.getReader();
    const chunks = [];
    let size = 0;
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      size += value.length;
      if (size > MAX_BYTES) { reader.cancel(); throw new Error('Réponse trop volumineuse'); }
      chunks.push(value);
    }
    return new TextDecoder('utf-8').decode(await new Blob(chunks).arrayBuffer());
  } finally {
    clearTimeout(timer);
  }
}

// ── Extraction images (page chapitre) ───────────────────────────────────────
function extractImages(html) {
  const tsMatch = html.match(/ts_reader\.run\s*\(\s*(\{[\s\S]*?\})\s*\)/);
  if (tsMatch) { try { const d = JSON.parse(tsMatch[1]); const i = d.sources?.[0]?.images ?? []; if (i.length) return i; } catch {} }
  const preMatch = html.match(/"chapter_preloaded_images"\s*:\s*(\[[^\]]+\])/);
  if (preMatch) { try { const i = JSON.parse(preMatch[1]); if (i.length) return i; } catch {} }
  const block = html.match(/class="reading-content"([\s\S]*?)(?:<\/div>\s*<\/div>|id="manga-reading-nav)/)?.[1] ?? html;
  const dataSrcs = [...block.matchAll(/data-src="(https?:\/\/[^"]+\.(?:jpg|jpeg|png|webp)[^"]*)"/gi)]
    .map(m => m[1].trim()).filter(u => !u.includes('placeholder'));
  if (dataSrcs.length) return [...new Set(dataSrcs)];
  const srcs = [...block.matchAll(/\bsrc="(https?:\/\/[^"]+\.(?:jpg|jpeg|png|webp)[^"]*)"/gi)]
    .map(m => m[1].trim()).filter(u => !u.includes('placeholder') && !u.includes('logo') && !u.includes('icon'));
  return [...new Set(srcs)];
}

// ── Extraction liste de chapitres (page série) ───────────────────────────────
function extractChapters(html) {
  const chapters = [], seen = new Set();
  const liRegex = /<li[^>]*class="[^"]*wp-manga-chapter[^"]*"[^>]*>([\s\S]*?)<\/li>/gi;
  let m;
  while ((m = liRegex.exec(html)) !== null) {
    const li = m[1];
    const href = li.match(/href="([^"]+)"/);
    const text = li.match(/<a[^>]+>([\s\S]*?)<\/a>/);
    if (!href || seen.has(href[1])) continue;
    seen.add(href[1]);
    const raw = (text?.[1] ?? '').replace(/<[^>]+>/g, '').trim();
    const numM = href[1].match(/(?:chapter|chapitre)[- _]([\d.]+)/i) ?? raw.match(/([\d]+(?:\.\d+)?)/);
    chapters.push({ url: href[1].trim(), num: numM ? parseFloat(numM[1]) : 0, title: raw.substring(0, 80) });
  }
  if (!chapters.length) {
    const aRegex = /href="(https?:\/\/[^"]*(?:chapter|chapitre)[^"]*)"/gi;
    while ((m = aRegex.exec(html)) !== null) {
      if (seen.has(m[1])) continue;
      seen.add(m[1]);
      const numM = m[1].match(/(?:chapter|chapitre)[- _]([\d.]+)/i);
      const num = numM ? parseFloat(numM[1]) : 0;
      chapters.push({ url: m[1].trim(), num, title: `Chapitre ${num}` });
    }
  }
  chapters.sort((a, b) => a.num - b.num);
  return chapters;
}

export async function onRequest(context) {
  const { request } = context;
  const origin = request.headers.get('Origin');

  if (request.method === 'OPTIONS') return new Response(null, { headers: corsHeaders(origin) });
  if (request.method !== 'GET')     return err('Méthode non autorisée', 405, origin);

  const reqUrl = new URL(request.url);
  const target = reqUrl.searchParams.get('url');
  const mode   = reqUrl.searchParams.get('mode') ?? 'chapter';
  if (!target)                             return err('Paramètre ?url= manquant', 400, origin);
  if (mode !== 'chapter' && mode !== 'chapters') return err('mode invalide', 400, origin);

  const v = validateTarget(target);
  if (v.error) return err(v.error, v.status, origin);

  try {
    const html = await getHtml(v.url.href);
    const payload = mode === 'chapters'
      ? { chapters: extractChapters(html) }
      : { images: extractImages(html) };
    payload.count = (payload.chapters ?? payload.images).length;
    return ok(payload, origin);
  } catch (e) {
    return err(String(e.message || e), 502, origin);
  }
}
