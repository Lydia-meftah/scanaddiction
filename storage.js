const KEY = "scanaddiction:v1";

function load() {
  try { return JSON.parse(localStorage.getItem(KEY)) ?? {}; }
  catch { return {}; }
}
function save(state) { localStorage.setItem(KEY, JSON.stringify(state)); }

export function getState() {
  const s = load();
  return {
    favorites: s.favorites ?? {},
    bookmarks: s.bookmarks ?? {},
    comments: s.comments ?? { work: {}, chapter: {} },
    suggestions: s.suggestions ?? [],
  };
}

export function toggleFavorite(workId) {
  const s = getState();
  s.favorites[workId] = !s.favorites[workId];
  const raw = load(); raw.favorites = s.favorites; save(raw);
  return s.favorites[workId];
}

export function setBookmark(workId, chapterId) {
  const raw = load();
  raw.bookmarks = raw.bookmarks ?? {};
  raw.bookmarks[workId] = { chapterId, at: new Date().toISOString() };
  save(raw);
}

export function getBookmark(workId) {
  return getState().bookmarks[workId] ?? null;
}

export function addComment(scope, key, author, text) {
  const raw = load();
  raw.comments = raw.comments ?? { work: {}, chapter: {} };
  raw.comments[scope] = raw.comments[scope] ?? {};
  raw.comments[scope][key] = raw.comments[scope][key] ?? [];
  raw.comments[scope][key].push({
    id: crypto.randomUUID?.() ?? String(Date.now()),
    author: author?.trim() || "Anonyme",
    text: text.trim(),
    at: new Date().toISOString()
  });
  save(raw);
}

export function listComments(scope, key) {
  const s = getState();
  return (s.comments?.[scope]?.[key] ?? []).slice().reverse();
}

export function addSuggestion(payload) {
  const raw = load();
  raw.suggestions = raw.suggestions ?? [];
  raw.suggestions.unshift({
    id: crypto.randomUUID?.() ?? String(Date.now()),
    status: "en_attente",
    createdAt: new Date().toISOString(),
    ...payload
  });
  save(raw);
}

export function listSuggestions() {
  return getState().suggestions ?? [];
}
