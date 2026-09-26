// Focus-area picker:
// Select topics, filter by consultation mode,
// and rank counsellors by specialty relevance.

(function () {
  const grid = document.getElementById("topicGrid");
  const dataEl = document.getElementById("counsellors-data");
  const matchesEmpty = document.getElementById("matchesEmpty");
  const matchesGrid = document.getElementById("matchesGrid");
  const modeFilter = document.querySelector(".mode-filter");

  if (!grid || !dataEl || !matchesEmpty || !matchesGrid) return;

  // --------------------------------------------------
  // DATA
  // --------------------------------------------------

  let counsellors = [];

  try {
    counsellors = JSON.parse(dataEl.textContent);
  } catch (error) {
    console.error("Unable to parse counsellor data:", error);
    return;
  }

  const chips = Array.from(grid.querySelectorAll(".topic-chip"));

  // Map topic slugs -> human-readable labels
  const labelBySlug = Object.fromEntries(
    chips.map((chip) => [chip.dataset.topic, chip.textContent.trim()])
  );

  // --------------------------------------------------
  // CONFIG
  // --------------------------------------------------

  const MAX_TOPICS = 5;
  const MAX_MATCHES = 3;

  // --------------------------------------------------
  // STATE
  // --------------------------------------------------

  const selected = new Set();
  let mode = "any";

  // --------------------------------------------------
  // TOPIC SELECTION
  // --------------------------------------------------

  chips.forEach((chip) => {
    chip.addEventListener("click", () => {
      const topic = chip.dataset.topic;

      if (!topic) return;

      if (selected.has(topic)) {
        selected.delete(topic);
        chip.classList.remove("is-selected");
        chip.setAttribute("aria-pressed", "false");
      } else {
        if (selected.size >= MAX_TOPICS) {
          showSelectionLimit();
          return;
        }

        selected.add(topic);
        chip.classList.add("is-selected");
        chip.setAttribute("aria-pressed", "true");
      }

      renderMatches();
    });
  });

  // --------------------------------------------------
  // MODE FILTER
  // --------------------------------------------------

  if (modeFilter) {
    const modeChips = Array.from(
      modeFilter.querySelectorAll(".mode-chip")
    );

    modeChips.forEach((chip) => {
      chip.addEventListener("click", () => {
        modeChips.forEach((item) => {
          item.classList.remove("is-active");
          item.setAttribute("aria-pressed", "false");
        });

        chip.classList.add("is-active");
        chip.setAttribute("aria-pressed", "true");

        mode = chip.dataset.mode || "any";

        renderMatches();
      });
    });
  }

  // --------------------------------------------------
  // MATCHING
  // --------------------------------------------------

  /**
   * Calculate meaningful matching metrics.
   *
   * specialty weight:
   * 2 = primary
   * 1 = secondary
   * 0 = no match
   */
  const getMatchMetrics = (counsellor) => {
    let strength = 0;
    let coverage = 0;
    let primaryMatches = 0;

    selected.forEach((topic) => {
      const weight = counsellor.specialties?.[topic] || 0;

      if (weight > 0) {
        coverage += 1;
        strength += weight;

        if (weight === 2) {
          primaryMatches += 1;
        }
      }
    });

    return {
      strength,
      coverage,
      primaryMatches,
    };
  };

  /**
   * Consultation mode is treated as an eligibility
   * condition rather than another specialty score.
   */
  const matchesMode = (counsellor) => {
    if (mode === "any") return true;

    return counsellor.modes?.includes(mode) ?? false;
  };

  // --------------------------------------------------
  // BEST-FOR LABELS
  // --------------------------------------------------

  const bestForLabels = (counsellor) =>
    Array.from(selected)
      .filter((topic) => (counsellor.specialties?.[topic] || 0) > 0)
      .sort(
        (a, b) =>
          (counsellor.specialties?.[b] || 0) -
          (counsellor.specialties?.[a] || 0)
      )
      .slice(0, 3)
      .map((topic) => labelBySlug[topic] || topic);

  // --------------------------------------------------
  // CARD RENDERING
  // --------------------------------------------------

  const renderCard = (counsellor) => {
    const card = document.createElement("article");
    card.className = "match-card";

    // Photo
    const img = document.createElement("img");
    img.src = counsellor.photo_thumb || counsellor.photo || "";
    img.width = 84;
    img.height = 48;
    img.loading = "lazy";
    img.decoding = "async";
    img.alt = "";
    img.setAttribute("aria-hidden", "true");

    card.appendChild(img);

    // Name
    const name = document.createElement("h3");
    name.textContent = counsellor.name;

    card.appendChild(name);

    // Credentials
    if (counsellor.credentials) {
      const credentials = document.createElement("p");
      credentials.className = "credentials";
      credentials.textContent = counsellor.credentials;

      card.appendChild(credentials);
    }

    // Best-for topics
    const bestFor = bestForLabels(counsellor);

    if (bestFor.length > 0) {
      const bestForEl = document.createElement("p");
      bestForEl.className = "best-for";
      bestForEl.textContent = `Best for: ${bestFor.join(", ")}`;

      card.appendChild(bestForEl);
    }

    // Mode + languages
    const details = [];

    if (Array.isArray(counsellor.modes)) {
      const modeLabels = counsellor.modes.map((item) =>
        item === "in-person" ? "In person" : "Online"
      );

      if (modeLabels.length) {
        details.push(modeLabels.join(" · "));
      }
    }

    if (
      Array.isArray(counsellor.languages) &&
      counsellor.languages.length
    ) {
      details.push(counsellor.languages.join(", "));
    }

    if (details.length) {
      const modes = document.createElement("p");
      modes.className = "modes";
      modes.textContent = details.join(" · ");

      card.appendChild(modes);
    }

    // Booking CTA
    const cta = document.createElement("a");
    cta.className = "btn btn-dark";
    cta.href = `/book/?counsellor=${encodeURIComponent(
      counsellor.slug
    )}`;
    cta.textContent = `Book with ${counsellor.name}`;

    card.appendChild(cta);

    return card;
  };

  // --------------------------------------------------
  // EMPTY / STATUS STATES
  // --------------------------------------------------

  const showEmptyMessage = (message) => {
    matchesEmpty.hidden = false;
    matchesEmpty.textContent = message;

    matchesGrid.hidden = true;
    matchesGrid.replaceChildren();
  };

  const showSelectionLimit = () => {
    matchesEmpty.hidden = false;
    matchesEmpty.textContent =
      `You can select up to ${MAX_TOPICS} focus areas.`;
  };

  // --------------------------------------------------
  // MAIN MATCHING PIPELINE
  // --------------------------------------------------

  const renderMatches = () => {
    if (selected.size === 0) {
      showEmptyMessage(
        "Select a focus area above to see your best-fit counsellors."
      );

      return;
    }

    const ranked = counsellors
      // Step 1: calculate specialty metrics
      .map((counsellor) => ({
        counsellor,
        ...getMatchMetrics(counsellor),
      }))

      // Step 2: counsellor must match at least one selected topic
      .filter(({ coverage }) => coverage > 0)

      // Step 3: apply consultation mode as a real filter
      .filter(({ counsellor }) => matchesMode(counsellor))

      // Step 4: rank
      .sort((a, b) => {
        // Prefer counsellors with more PRIMARY matches
        if (b.primaryMatches !== a.primaryMatches) {
          return b.primaryMatches - a.primaryMatches;
        }

        // Then prefer broader coverage
        if (b.coverage !== a.coverage) {
          return b.coverage - a.coverage;
        }

        // Then prefer stronger total expertise
        if (b.strength !== a.strength) {
          return b.strength - a.strength;
        }

        // Stable/deterministic final tie-break
        return (a.counsellor.name || "").localeCompare(
          b.counsellor.name || ""
        );
      })

      // Step 5: show only the top matches
      .slice(0, MAX_MATCHES);

    if (ranked.length === 0) {
      const message =
        mode === "any"
          ? "No close matches yet — try selecting a different focus area."
          : "No counsellors currently match both your selected focus areas and consultation mode.";

      showEmptyMessage(message);

      return;
    }

    matchesEmpty.hidden = true;
    matchesGrid.hidden = false;

    const cards = ranked.map(({ counsellor }) =>
      renderCard(counsellor)
    );

    matchesGrid.replaceChildren(...cards);
  };
})();