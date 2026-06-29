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

const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, OPTIONS',
  'Content-Type': 'application/json',
};

// Domaines autorisés (whitelist de sécurité)
const ALLOWED = [
  'sushiscan.net',
  'raijin-scans.fr',
  'crunchyscan.fr',
  'www.scan-manga.com',
  'scan-manga.com',
];

function ok(data) {
  return new Response(JSON.stringify(data), { headers: CORS });
}
function err(msg, status = 400) {
  return new Response(JSON.stringify({ error: msg }), { status, headers: CORS });
}

async function getHtml(url) {
  const res = await fetch(url, {
    headers: {
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
      'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
      'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8',
      'Referer': new URL(url).origin + '/',
      'Cache-Control': 'no-cache',
    },
    redirect: 'follow',
    cf: { cacheTtl: 300, cacheEverything: false },
  });
  if (!res.ok) throw new Error(`HTTP ${res.status} — ${url}`);
  return res.text();
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

  if (request.method === 'OPTIONS') {
    return new Response(null, { headers: CORS });
  }

  const reqUrl  = new URL(request.url);
  const target  = reqUrl.searchParams.get('url');
  const mode    = reqUrl.searchParams.get('mode') ?? 'chapter';

  if (!target) return err('Paramètre ?url= manquant');

  let parsed;
  try { parsed = new URL(target); }
  catch { return err('URL invalide'); }

  const host = parsed.hostname.replace(/^www\./, '');
  if (!ALLOWED.some(h => host === h || host.endsWith('.' + h))) {
    return err(`Domaine non autorisé: ${host}`, 403);
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
    return err(e.message, 502);
  }
}
