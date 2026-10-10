(() => {
    const root = document.querySelector("[data-statements]");
    if (!root) return;
  
    root.querySelectorAll(".statement-panel").forEach((panel) => {
      const marks = [...panel.querySelectorAll("mark[data-note]")];
      const note = panel.querySelector(".note");
      const progress = panel.querySelector(".keyword-progress");
      const fill = panel.querySelector(".keyword-progress-fill");
      if (!marks.length || !note) return;
  
      let index = 0;
  
      function show(i) {
        index = i;
        marks.forEach((mark, n) => {
          mark.classList.toggle("is-lit", n === i);
          mark.classList.toggle("is-dim", n !== i);
        });
  
        note.textContent = marks[i].dataset.note;
        note.classList.remove("is-changing");
        void note.offsetWidth; // restart the animation
        note.classList.add("is-changing");
  
        if (progress) {
          progress.classList.remove("is-ticking");
          void progress.offsetWidth;
          progress.classList.add("is-ticking");
        }
      }
  
      // The progress bar drives the cycle, so the bar and the text never drift apart.
      // With reduced motion the bar never animates, so nothing auto-advances.
      fill?.addEventListener("animationend", () => show((index + 1) % marks.length));
  
      show(0);
    });
  })();
