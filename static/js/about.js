(() => {
    const root = document.querySelector("[data-statements]");
    if (!root) return;
  
    const switcher = root.querySelector(".switch");
    const stage = root.querySelector(".statement-stage");
    const tabs = [...root.querySelectorAll('[role="tab"]')];
    const panels = [...root.querySelectorAll('[role="tabpanel"]')];
  
    /* ---------- Keyword highlighting inside each panel ---------- */
    function setupPanel(panel) {
      const marks = [...panel.querySelectorAll("mark[data-key]")];
      const chips = [...panel.querySelectorAll(".chip")];
      const note = panel.querySelector(".note");
      let activeKey = null;
  
      function say(text) {
        note.textContent = text;
        note.classList.remove("is-changing");
        void note.offsetWidth; // restart the animation
        note.classList.add("is-changing");
      }
  
      function apply(key) {
        activeKey = key;
        marks.forEach((m) => {
          m.classList.toggle("is-lit", key !== null && m.dataset.key === key);
          m.classList.toggle("is-dim", key !== null && m.dataset.key !== key);
        });
        chips.forEach((c) => {
          c.setAttribute("aria-pressed", String(c.dataset.key === key));
        });
        const chip = chips.find((c) => c.dataset.key === key);
        say(chip ? chip.dataset.note : note.dataset.default);
      }
  
      function toggle(key) {
        apply(activeKey === key ? null : key);
      }
  
      chips.forEach((c) => c.addEventListener("click", () => toggle(c.dataset.key)));
      marks.forEach((m) => m.addEventListener("click", () => toggle(m.dataset.key)));
  
      return { reset: () => apply(null) };
    }
  
    const panelApis = panels.map(setupPanel);
  
    /* ---------- Vision / Mission tabs ---------- */
    function select(index, moveFocus) {
      tabs.forEach((tab, i) => {
        const on = i === index;
        tab.setAttribute("aria-selected", String(on));
        tab.tabIndex = on ? 0 : -1;
        panels[i].hidden = !on;
        if (on && moveFocus) tab.focus();
      });
      switcher.dataset.active = index;
      stage.dataset.active = index;
      panelApis.forEach((p) => p.reset());
    }
  
    tabs.forEach((tab, i) => {
      tab.addEventListener("click", () => select(i, false));
      tab.addEventListener("keydown", (e) => {
        const last = tabs.length - 1;
        let next = null;
        if (e.key === "ArrowRight") next = i === last ? 0 : i + 1;
        if (e.key === "ArrowLeft") next = i === 0 ? last : i - 1;
        if (e.key === "Home") next = 0;
        if (e.key === "End") next = last;
        if (next !== null) {
          e.preventDefault();
          select(next, true);
        }
      });
    });
  })();