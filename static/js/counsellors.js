(() => {
  const deck = document.querySelector(".counsellors-deck");
  const overlay = document.getElementById("counsellor-overlay");
  const mount = document.getElementById("overlay-mount");
  const counter = document.getElementById("overlay-counter");
  if (!deck || !overlay || !mount) return;

  const cards = Array.from(deck.querySelectorAll(".counsellor-card"));
  if (!cards.length) return;

  const prevBtn = overlay.querySelector("[data-overlay-prev]");
  const nextBtn = overlay.querySelector("[data-overlay-next]");

  let index = 0;
  let lastFocus = null;

  function sourceFor(i) {
    return cards[i]?.querySelector(".profile-source");
  }

  function renderProfile(i) {
    const source = sourceFor(i);
    if (!source) return;

    index = i;
    mount.replaceChildren(source.content.cloneNode(true));

    const total = cards.length;
    if (counter) counter.textContent = `${i + 1} / ${total}`;

    if (prevBtn) prevBtn.disabled = total <= 1;
    if (nextBtn) nextBtn.disabled = total <= 1;

    const panel = mount.querySelector(".profile-panel");
    const heading = panel?.querySelector(".profile-name");
    if (heading) {
      heading.id = "overlay-live-title";
      overlay.setAttribute("aria-labelledby", "overlay-live-title");
    }

    const slug = panel?.dataset.slug;
    if (slug && history.replaceState) {
      history.replaceState(null, "", `#${slug}`);
    }

    overlay.querySelector(".overlay-scroll")?.scrollTo({ top: 0 });
  }

  function openAt(i) {
    if (i < 0 || i >= cards.length) return;
    lastFocus = document.activeElement;
    renderProfile(i);
    if (typeof overlay.showModal === "function") {
      if (!overlay.open) overlay.showModal();
    } else {
      overlay.setAttribute("open", "");
    }
    document.body.classList.add("overlay-open");
    overlay.querySelector(".overlay-close")?.focus();
  }

  function closeOverlay() {
    if (typeof overlay.close === "function") {
      if (overlay.open) overlay.close();
    } else {
      overlay.removeAttribute("open");
    }
    document.body.classList.remove("overlay-open");
    if (history.replaceState) {
      history.replaceState(null, "", window.location.pathname + window.location.search);
    }
    if (lastFocus && typeof lastFocus.focus === "function") {
      lastFocus.focus();
    }
  }

  function step(delta) {
    const next = (index + delta + cards.length) % cards.length;
    renderProfile(next);
  }

  deck.addEventListener("click", (event) => {
    const trigger = event.target.closest("[data-open-profile]");
    if (!trigger || !deck.contains(trigger)) return;
    const i = Number(trigger.getAttribute("data-open-profile"));
    if (Number.isNaN(i)) return;
    openAt(i);
  });

  overlay.addEventListener("click", (event) => {
    if (event.target.closest("[data-close-overlay]")) {
      closeOverlay();
      return;
    }
    if (event.target.closest("[data-overlay-prev]")) {
      step(-1);
      return;
    }
    if (event.target.closest("[data-overlay-next]")) {
      step(1);
      return;
    }
    // Click on the dialog backdrop (not the panel chrome).
    const rect = overlay.getBoundingClientRect();
    const clickedBackdrop =
      event.target === overlay &&
      (event.clientX < rect.left ||
        event.clientX > rect.right ||
        event.clientY < rect.top ||
        event.clientY > rect.bottom);
    if (clickedBackdrop) closeOverlay();
  });

  overlay.addEventListener("cancel", (event) => {
    event.preventDefault();
    closeOverlay();
  });

  document.addEventListener("keydown", (event) => {
    if (!overlay.open) return;
    if (event.key === "ArrowRight") {
      event.preventDefault();
      step(1);
    } else if (event.key === "ArrowLeft") {
      event.preventDefault();
      step(-1);
    }
  });

  const hash = window.location.hash.replace(/^#/, "");
  if (hash) {
    const hashIndex = cards.findIndex((card) => card.id === hash);
    if (hashIndex >= 0) openAt(hashIndex);
  }
})();
