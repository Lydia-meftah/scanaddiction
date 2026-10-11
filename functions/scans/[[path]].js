/**
 * functions/scans/[[path]].js — sert les chapitres traduits par Scanaddiction depuis Cloudflare R2.
 *
 *   GET /scans/index.json                    catalogue des séries hébergées
 *   GET /scans/<slug>/series.json            fiche série + chapitres
 *   GET /scans/<slug>/<chapitre>/<page>.webp page traduite
 *
 * Binding R2 requis : SCANS (voir wrangler.toml / réglages Pages → Functions → R2 bindings).
 * Lecture seule : aucune écriture possible depuis le site.
 */

const TYPES = {
  json: 'application/json; charset=utf-8',
  webp: 'image/webp',
  jpg: 'image/jpeg',
  jpeg: 'image/jpeg',
  png: 'image/png',
};
const SAFE = /^[a-z0-9][a-z0-9._-]*(\/[a-z0-9][a-z0-9._-]*)*$/i;

export async function onRequest({ request, env, params }) {
  if (request.method !== 'GET' && request.method !== 'HEAD') {
    return new Response('Méthode non autorisée', { status: 405 });
  }
  if (!env.SCANS) {
    return new Response(JSON.stringify({ error: 'Binding R2 SCANS non configuré' }), {
      status: 503, headers: { 'Content-Type': TYPES.json },
    });
  }
  const key = (Array.isArray(params.path) ? params.path.join('/') : String(params.path || ''));
  if (!key || !SAFE.test(key) || key.includes('..')) return new Response('Introuvable', { status: 404 });

  const ext = key.split('.').pop().toLowerCase();
  if (!TYPES[ext]) return new Response('Introuvable', { status: 404 });

  const obj = await env.SCANS.get(key, { onlyIf: request.headers, range: request.headers });
  if (!obj) return new Response('Introuvable', { status: 404 });

  const headers = new Headers();
  obj.writeHttpMetadata(headers);
  headers.set('ETag', obj.httpEtag);
  headers.set('Content-Type', TYPES[ext]);
  headers.set('X-Content-Type-Options', 'nosniff');
  if (!headers.has('Cache-Control')) {
    headers.set('Cache-Control', ext === 'json' ? 'public, max-age=120' : 'public, max-age=31536000, immutable');
  }
  if (!('body' in obj) || !obj.body) return new Response(null, { status: 304, headers });
  return new Response(request.method === 'HEAD' ? null : obj.body, { headers });
}
