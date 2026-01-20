export const CONFIG = {
  siteName: "Scanaddiction",
  slogan: "Lire autrement. Découvrir vraiment.",
  discordInviteUrl: "https://discord.gg/TON_INVITE",
  kofiUrl: "https://ko-fi.com/TONKOFI",
  contactEmail: "tonmail@exemple.com",
};

export function qs(sel, root = document) { return root.querySelector(sel); }
export function qsa(sel, root = document) { return [...root.querySelectorAll(sel)]; }

export function setYear() {
  const el = qs("[data-year]");
  if (el) el.textContent = String(new Date().getFullYear());
}

export function setActiveNav() {
  const path = location.pathname.split("/").pop() || "index.html";
  qsa("[data-nav]").forEach(a => {
    if (a.getAttribute("href") === path) a.classList.add("text-white");
  });
}

export function mountShell() {
  const header = qs("#app-header");
  const footer = qs("#app-footer");
  if (header) header.innerHTML = `
  <header class="sticky top-0 z-40 border-b border-white/10 bg-black/70 backdrop-blur">
    <div class="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
      <a class="flex items-center gap-2" href="index.html">
        <span class="inline-flex h-9 w-9 items-center justify-center rounded-xl bg-white/10">SA</span>
        <div class="leading-tight">
          <div class="font-semibold">${CONFIG.siteName}</div>
          <div class="text-xs text-white/60">${CONFIG.slogan}</div>
        </div>
      </a>

      <nav class="hidden items-center gap-5 text-sm text-white/70 md:flex">
        <a data-nav href="catalog.html" class="hover:text-white">Catalogue</a>
        <a data-nav href="suggestions.html" class="hover:text-white">Suggestions</a>
        <a data-nav href="about.html" class="hover:text-white">À propos</a>
        <a data-nav href="support.html" class="hover:text-white">Soutenir</a>
        <a data-nav href="discord.html" class="hover:text-white">Discord</a>
      </nav>

      <div class="flex items-center gap-2">
        <a href="account.html" class="rounded-xl border border-white/15 bg-white/5 px-3 py-2 text-sm hover:bg-white/10">Compte</a>
      </div>
    </div>
  </header>`;

  if (footer) footer.innerHTML = `
  <footer class="mt-16 border-t border-white/10 bg-black/40">
    <div class="mx-auto grid max-w-6xl gap-8 px-4 py-10 md:grid-cols-3">
      <div>
        <div class="text-lg font-semibold">${CONFIG.siteName}</div>
        <p class="mt-2 text-sm text-white/70">
          Projet indépendant francophone. Sélection > quantité. Communauté > hype.
        </p>
      </div>
      <div class="text-sm text-white/70">
        <div class="font-semibold text-white">Liens</div>
        <ul class="mt-2 space-y-1">
          <li><a class="hover:text-white" href="catalog.html">Catalogue</a></li>
          <li><a class="hover:text-white" href="suggestions.html">Suggestions</a></li>
          <li><a class="hover:text-white" href="contact.html">Contact</a></li>
        </ul>
      </div>
      <div class="text-sm text-white/70">
        <div class="font-semibold text-white">Support</div>
        <p class="mt-2">Ko-fi : <a class="underline hover:text-white" href="${CONFIG.kofiUrl}" target="_blank" rel="noreferrer">ouvrir</a></p>
        <p class="mt-1">Discord : <a class="underline hover:text-white" href="${CONFIG.discordInviteUrl}" target="_blank" rel="noreferrer">rejoindre</a></p>
        <p class="mt-4 text-xs text-white/50">© <span data-year></span> ${CONFIG.siteName}</p>
      </div>
    </div>
  </footer>`;
}
