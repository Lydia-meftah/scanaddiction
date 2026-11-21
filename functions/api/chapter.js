/**
 * functions/api/chapter.js — Cloudflare Pages Function
 *
 * Proxy côté serveur pour extraire les images et chapitres
 * des sites Madara (Sushiscan, Raijin-Scans, Crunchyscan…)
 * en contournant CORS.
 *
 * GET /api/chapter?url={chapter_page_url}&mode=chapter   → { images: [...] }
 * GET /api/chapter?url={series_page_url}&mode=chapters   → { chapters: [...] }
 */

// Le proxy ne sert que le site lui-même (même origine) : plus d'en-tête
// Access-Control-Allow-Origin: * qui permettait à n'importe quel site
// d'utiliser ce proxy (et le quota Cloudflare) à sa place.
const HEADERS = {
  'Content-Type': 'application/json',
  'X-Content-Type-Options': 'nosniff',
};

// Projets Cloudflare Pages du site (prod + previews <hash>.<projet>.pages.dev)
const PAGES_PROJECTS = ['scanaddiction.pages.dev', 'scanaddiction-pages.pages.dev'];

// Origines autorisées à appeler /api/chapter :
// - le domaine qui sert la Function elle-même (quel qu'il soit : pages.dev, domaine perso…)
// - les projets Pages ci-dessus et leurs previews
// - le développement local
function isAllowedOrigin(origin, selfHost) {
  if (!origin) return true; // navigation directe / même origine sans en-tête Origin
  try {
    const { protocol, hostname } = new URL(origin);
    if (hostname === selfHost) return true;
    if (hostname === 'localhost' || hostname === '127.0.0.1') return true;
    return protocol === 'https:' &&
      PAGES_PROJECTS.some(p => hostname === p || hostname.endsWith('.' + p));
  } catch {
    return false;
  }
}

const MODES = new Set(['chapter', 'chapters']);

// Domaines autorisés (whitelist de sécurité)
const ALLOWED = [
  'sushiscan.net',
  'raijin-scans.fr',
  'crunchyscan.fr',
  'www.scan-manga.com',
  'scan-manga.com',
];

// Un hostname est autorisé s'il correspond à un domaine de la whitelist
// (ou un de ses sous-domaines). Centralisé ici pour que la validation de
// l'URL initiale ET de l'URL finale (après redirection) partagent la même règle.
function hostAllowed(hostname) {
  const host = hostname.replace(/^www\./, '');
  return ALLOWED.some(h => host === h || host.endsWith('.' + h));
}

// Garde-fous réseau du proxy
const FETCH_TIMEOUT_MS = 10000;        // coupe une source qui ne répond pas
const MAX_BYTES = 3 * 1024 * 1024;     // 3 Mo max lus par page (anti-abus mémoire)

function ok(data) {
  return new Response(JSON.stringify(data), { headers: HEADERS });
}
function err(msg, status = 400) {
  return new Response(JSON.stringify({ error: msg }), { status, headers: HEADERS });
}

async function getHtml(url) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);
  try {
    const res = await fetch(url, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8',
        'Referer': new URL(url).origin + '/',
        'Cache-Control': 'no-cache',
      },
      redirect: 'follow',
      signal: controller.signal,
      cf: { cacheTtl: 300, cacheEverything: false },
    });

    // Anti-SSRF : la whitelist ne valide que l'URL de départ. `fetch` suivant
    // les redirections, un site autorisé (ou compromis) pouvait rediriger le
    // proxy vers une cible arbitraire. On revérifie donc l'URL finale : elle
    // doit rester en https ET sur un domaine autorisé.
    let finalUrl;
    try { finalUrl = new URL(res.url); } catch { throw new Error('URL finale invalide'); }
    if (finalUrl.protocol !== 'https:' || !hostAllowed(finalUrl.hostname)) {
      throw new Error(`Redirection non autorisee: ${finalUrl.hostname}`);
    }

    if (!res.ok) throw new Error(`HTTP ${res.status} — ${url}`);

    // Lecture bornée en taille pour éviter qu'une page géante épuise la mémoire.
    if (!res.body) return await res.text();
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let out = '';
    let total = 0;
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      total += value.byteLength;
      if (total > MAX_BYTES) { try { await reader.cancel(); } catch {} break; }
      out += decoder.decode(value, { stream: true });
    }
    out += decoder.decode();
    return out;
  } finally {
    clearTimeout(timer);
  }
}

// ── Extraction images depuis une page chapitre ────────────────────────────
function extractImages(html) {
  // 1. ts_reader.run({sources:[{images:[...]}]}) — Madara standard
  const tsMatch = html.match(/ts_reader\.run\s*\(\s*(\{[\s\S]*?\})\s*\)/);
  if (tsMatch) {
    try {
      const data = JSON.parse(tsMatch[1]);
      const imgs = data.sources?.[0]?.images ?? [];
      if (imgs.length) return imgs;
    } catch {}
  }

  // 2. JSON embedé: "chapter_preloaded_images":["url",...]
  const preMatch = html.match(/"chapter_preloaded_images"\s*:\s*(\[[^\]]+\])/);
  if (preMatch) {
    try {
      const imgs = JSON.parse(preMatch[1]);
      if (imgs.length) return imgs;
    } catch {}
  }

  // 3. <img data-src="..."> dans .reading-content
  const block = html.match(/class="reading-content"([\s\S]*?)(?:<\/div>\s*<\/div>|id="manga-reading-nav)/)?.[1] ?? html;
  const dataSrcs = [...block.matchAll(/data-src="(https?:\/\/[^"]+\.(?:jpg|jpeg|png|webp)[^"]*)"/gi)]
    .map(m => m[1].trim())
    .filter(u => !u.includes('placeholder'));
  if (dataSrcs.length) return [...new Set(dataSrcs)];

  // 4. <img src="..."> dans .reading-content (fallback)
  const srcs = [...block.matchAll(/\bsrc="(https?:\/\/[^"]+\.(?:jpg|jpeg|png|webp)[^"]*)"/gi)]
    .map(m => m[1].trim())
    .filter(u => !u.includes('placeholder') && !u.includes('logo') && !u.includes('icon'));
  return [...new Set(srcs)];
}

// ── Extraction liste de chapitres depuis une page série ───────────────────
function extractChapters(html, origin) {
  const chapters = [];
  const seen = new Set();

  // Pattern Madara: <li class="wp-manga-chapter ..."><a href="...">Chapitre X</a>
  const liRegex = /<li[^>]*class="[^"]*wp-manga-chapter[^"]*"[^>]*>([\s\S]*?)<\/li>/gi;
  let liMatch;
  while ((liMatch = liRegex.exec(html)) !== null) {
    const li = liMatch[1];
    const hrefM = li.match(/href="([^"]+)"/);
    const textM = li.match(/<a[^>]+>([\s\S]*?)<\/a>/);
    if (!hrefM) continue;
    const url = hrefM[1].trim();
    if (seen.has(url)) continue;
    seen.add(url);
    const rawText = (textM?.[1] ?? '').replace(/<[^>]+>/g, '').trim();
    const numM = url.match(/(?:chapter|chapitre)[- _]([\d.]+)/i)
               ?? rawText.match(/([\d]+(?:\.\d+)?)/);
    const num = numM ? parseFloat(numM[1]) : 0;
    chapters.push({ url, num, title: rawText.substring(0, 80) });
  }

  // Fallback: tous les liens contenant "chapter" ou "chapitre"
  if (!chapters.length) {
    const aRegex = /href="(https?:\/\/[^"]*(?:chapter|chapitre)[^"]*)"/gi;
    let aMatch;
    while ((aMatch = aRegex.exec(html)) !== null) {
      const url = aMatch[1].trim();
      if (seen.has(url)) continue;
      seen.add(url);
      const numM = url.match(/(?:chapter|chapitre)[- _]([\d.]+)/i);
      const num = numM ? parseFloat(numM[1]) : 0;
      chapters.push({ url, num, title: `Chapitre ${num}` });
    }
  }

  // Tri croissant par numéro
  chapters.sort((a, b) => a.num - b.num);
  return chapters;
}

// ── Handler principal ─────────────────────────────────────────────────────
export async function onRequest(context) {
  const { request } = context;

  if (request.method !== 'GET') return err('Méthode non autorisée', 405);

  // Bloque les appels venant d'autres sites (Origin, sinon Referer)
  const reqUrl  = new URL(request.url);
  const caller = request.headers.get('Origin') ?? request.headers.get('Referer');
  if (!isAllowedOrigin(caller, reqUrl.hostname)) return err('Origine non autorisée', 403);

  const target  = reqUrl.searchParams.get('url');
  const mode    = reqUrl.searchParams.get('mode') ?? 'chapter';

  if (!target) return err('Paramètre ?url= manquant');
  if (!MODES.has(mode)) return err('Paramètre ?mode= invalide');

  let parsed;
  try { parsed = new URL(target); }
  catch { return err('URL invalide'); }
  if (parsed.protocol !== 'https:') return err('Seules les URL https sont acceptées');

  if (!hostAllowed(parsed.hostname)) {
    return err(`Domaine non autorisé: ${parsed.hostname.replace(/^www\./, '')}`, 403);
  }

  try {
    const html = await getHtml(target);

    if (mode === 'chapters') {
      const chapters = extractChapters(html, parsed.origin);
      return ok({ chapters, count: chapters.length, source: target });
    } else {
      const images = extractImages(html);
      return ok({ images, count: images.length, source: target });
    }
  } catch (e) {
    console.error('[api/chapter]', e.message);
    return err('Source injoignable', 502);
  }
}
