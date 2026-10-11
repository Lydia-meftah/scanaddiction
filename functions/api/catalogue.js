/**
 * functions/api/catalogue.js — API lecture du catalogue depuis D1.
 *   GET /api/catalogue?type=manhwa&statut=en%20cours&source=mangadex&q=blue&limit=60&offset=0
 * Toutes les entrées utilisateur passent par des requêtes préparées (.bind) —
 * aucune concaténation SQL, donc pas d'injection.
 */
const CORS = { 'Content-Type': 'application/json', 'Cache-Control': 'public, max-age=300' };
const TYPES = new Set(['manga', 'manhwa', 'manhua']);
const STATUTS = new Set(['en cours', 'terminé', 'pause', 'annulé']);
const MAX_LIMIT = 100;

export async function onRequest(context) {
  const { request, env } = context;
  if (request.method === 'OPTIONS') return new Response(null, { headers: CORS });
  if (!env.DB) return new Response(JSON.stringify({ error: 'DB non configurée' }), { status: 503, headers: CORS });

  const p = new URL(request.url).searchParams;
  const where = [], binds = [];
  const type = p.get('type'); if (type && TYPES.has(type)) { where.push('type = ?'); binds.push(type); }
  const statut = p.get('statut'); if (statut && STATUTS.has(statut)) { where.push('statut = ?'); binds.push(statut); }
  const source = p.get('source'); if (source) { where.push('source_code = ?'); binds.push(source); }
  const q = (p.get('q') || '').trim(); if (q) { where.push('titre LIKE ?'); binds.push('%' + q.replace(/[%_]/g, '') + '%'); }

  const limit = Math.min(parseInt(p.get('limit') || '60', 10) || 60, MAX_LIMIT);
  const offset = Math.max(parseInt(p.get('offset') || '0', 10) || 0, 0);
  const clause = where.length ? 'WHERE ' + where.join(' AND ') : '';

  try {
    const countRow = await env.DB.prepare(`SELECT COUNT(*) AS n FROM series ${clause}`).bind(...binds).first();
    const rows = await env.DB.prepare(
      `SELECT id, source_code, mangadex_id, titre, url, cover, type, statut, synopsis,
              auteur, genres, note, dernier_chapitre, lecteur_integre
       FROM series ${clause} ORDER BY titre COLLATE NOCASE LIMIT ? OFFSET ?`
    ).bind(...binds, limit, offset).all();

    const oeuvres = (rows.results || []).map(r => ({
      ...r, genres: JSON.parse(r.genres || '[]'), lecteurIntegre: !!r.lecteur_integre,
    }));
    return new Response(JSON.stringify({ total: countRow?.n ?? 0, limit, offset, oeuvres }), { headers: CORS });
  } catch (e) {
    return new Response(JSON.stringify({ error: String(e.message || e) }), { status: 500, headers: CORS });
  }
}
