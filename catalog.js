import { qs } from "./app.js";
import { getState, toggleFavorite, getBookmark } from "./storage.js";

async function loadWorks() {
  const res = await fetch("/data/works.json", { cache: "no-store" });
  return await res.json();
}

function badge(txt) {
  return `<span class="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-white/70">${txt}</span>`;
}

export async function initCatalog() {
  const works = await loadWorks();
  const grid = qs("#grid");
  const tagsWrap = qs("#tags");
  const qInput = qs("#q");
  const clear = qs("#clear");

  const allTags = [...new Set(works.flatMap(w => w.tags))].sort();
  let activeTag = null;

  tagsWrap.innerHTML = `
    <div class="flex flex-wrap gap-2">
      <button data-tag="" class="rounded-full border border-white/15 bg-white/5 px-3 py-1 text-xs hover:bg-white/10">Tous</button>
      ${allTags.map(t => `<button data-tag="${t}" class="rounded-full border border-white/15 bg-white/5 px-3 py-1 text-xs hover:bg-white/10">${t}</button>`).join("")}
    </div>
  `;

  function render() {
    const q = qInput.value.trim().toLowerCase();
    const state = getState();
    const filtered = works.filter(w => {
      const okQ = !q || w.title.toLowerCase().includes(q);
      const okTag = !activeTag || w.tags.includes(activeTag);
      return okQ && okTag;
    });

    grid.innerHTML = filtered.map(w => {
      const fav = !!state.favorites[w.id];
      const bm = getBookmark(w.id);
      const resume = bm ? `Reprendre: ${bm.chapterId}` : "Aucun bookmark";
      return `
      <article class="group rounded-2xl border border-white/10 bg-white/5 p-4">
        <div class="flex gap-4">
          <img src="${w.cover}" alt="" class="h-24 w-20 rounded-xl object-cover border border-white/10" />
          <div class="min-w-0 flex-1">
            <div class="flex items-start justify-between gap-2">
              <a href="work.html?id=${encodeURIComponent(w.id)}" class="font-semibold hover:underline">${w.title}</a>
              <button data-fav="${w.id}" class="rounded-xl border border-white/15 bg-white/5 px-2 py-1 text-xs hover:bg-white/10">
                ${fav ? "★" : "☆"} Favori
              </button>
            </div>
            <div class="mt-1 text-xs text-white/60">${w.type.toUpperCase()} • ${w.status}</div>
            <div class="mt-2 flex flex-wrap gap-1">${w.tags.slice(0,4).map(badge).join("")}</div>
            <div class="mt-3 text-xs text-white/60">${resume}</div>
          </div>
        </div>
      </article>`;
    }).join("");

    grid.querySelectorAll("[data-fav]").forEach(btn => {
      btn.addEventListener("click", () => {
        toggleFavorite(btn.dataset.fav);
        render();
      });
    });
  }

  tagsWrap.querySelectorAll("[data-tag]").forEach(btn => {
    btn.addEventListener("click", () => {
      const t = btn.dataset.tag;
      activeTag = t || null;
      render();
    });
  });

  qInput.addEventListener("input", render);
  clear.addEventListener("click", () => { qInput.value = ""; activeTag = null; render(); });

  render();
}
