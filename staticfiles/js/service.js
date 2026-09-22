// Focus-area picker: select topics, rank counsellors by specialty overlap.
(function () {
  const grid = document.getElementById("topicGrid");
  const dataEl = document.getElementById("counsellors-data");
  const matchesEmpty = document.getElementById("matchesEmpty");
  const matchesGrid = document.getElementById("matchesGrid");
  const modeFilter = document.querySelector(".mode-filter");

  if (!grid || !dataEl || !matchesEmpty || !matchesGrid) return;

  const counsellors = JSON.parse(dataEl.textContent);
  const chips = Array.from(grid.querySelectorAll(".topic-chip"));
  const labelBySlug = {};
  chips.forEach((chip) => {
    labelBySlug[chip.dataset.topic] = chip.textContent;
  });

  const MAX_TOPICS = 5;
  const MAX_MATCHES = 3;
  const selected = new Set();
  let mode = "any";

  chips.forEach((chip) => {
    chip.addEventListener("click", () => {
      const topic = chip.dataset.topic;
      if (selected.has(topic)) {
        selected.delete(topic);
        chip.classList.remove("is-selected");
      } else {
        if (selected.size >= MAX_TOPICS) return;
        selected.add(topic);
        chip.classList.add("is-selected");
      }
      renderMatches();
    });
  });

  if (modeFilter) {
    const modeChips = Array.from(modeFilter.querySelectorAll(".mode-chip"));
    modeChips.forEach((chip) => {
      chip.addEventListener("click", () => {
        modeChips.forEach((c) => c.classList.remove("is-active"));
        chip.classList.add("is-active");
        mode = chip.dataset.mode;
        renderMatches();
      });
    });
  }

  const scoreCounsellor = (counsellor) => {
    let score = 0;
    selected.forEach((topic) => {
      score += counsellor.specialties[topic] || 0;
    });
    if (mode !== "any" && counsellor.modes.includes(mode)) score += 1;
    return score;
  };

  const bestForLabels = (counsellor) =>
    Array.from(selected)
      .filter((topic) => counsellor.specialties[topic])
      .sort((a, b) => counsellor.specialties[b] - counsellor.specialties[a])
      .slice(0, 3)
      .map((topic) => labelBySlug[topic]);

  const renderCard = (counsellor) => {
    const card = document.createElement("article");
    card.className = "match-card";

    const img = document.createElement("img");
    img.src = counsellor.photo_thumb || counsellor.photo;
    img.width = 84;
    img.height = 84;
    img.loading = "lazy";
    img.decoding = "async";
    img.alt = "";
    img.setAttribute("aria-hidden", "true");
    card.appendChild(img);

    const name = document.createElement("h3");
    name.textContent = counsellor.name;
    card.appendChild(name);

    const credentials = document.createElement("p");
    credentials.className = "credentials";
    credentials.textContent = counsellor.credentials;
    card.appendChild(credentials);

    const bestFor = bestForLabels(counsellor);
    if (bestFor.length) {
      const bestForEl = document.createElement("p");
      bestForEl.className = "best-for";
      bestForEl.textContent = `Best for: ${bestFor.join(", ")}`;
      card.appendChild(bestForEl);
    }

    const modes = document.createElement("p");
    modes.className = "modes";
    const modeLabels = counsellor.modes.map((m) =>
      m === "in-person" ? "In person" : "Online",
    );
    modes.textContent = `${modeLabels.join(" · ")} · ${counsellor.languages.join(", ")}`;
    card.appendChild(modes);

    const cta = document.createElement("a");
    cta.className = "btn btn-dark";
    cta.href = `/book/?counsellor=${encodeURIComponent(counsellor.slug)}`;
    cta.textContent = `Book with ${counsellor.name}`;
    card.appendChild(cta);

    return card;
  };

  const renderMatches = () => {
    if (selected.size === 0) {
      matchesEmpty.hidden = false;
      matchesEmpty.textContent =
        "Select a focus area above to see your best-fit counsellors.";
      matchesGrid.hidden = true;
      matchesGrid.replaceChildren();
      return;
    }

    const ranked = counsellors
      .map((counsellor) => ({ counsellor, score: scoreCounsellor(counsellor) }))
      .filter((entry) => entry.score > 0)
      .sort((a, b) => b.score - a.score)
      .slice(0, MAX_MATCHES);

    if (ranked.length === 0) {
      matchesEmpty.hidden = false;
      matchesEmpty.textContent =
        "No close matches yet — try selecting a different focus area.";
      matchesGrid.hidden = true;
      matchesGrid.replaceChildren();
      return;
    }

    matchesEmpty.hidden = true;
    matchesGrid.hidden = false;
    matchesGrid.replaceChildren(...ranked.map((entry) => renderCard(entry.counsellor)));
  };
})();
