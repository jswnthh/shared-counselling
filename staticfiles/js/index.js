// Scroll reveal
const prefersReduced = window.matchMedia(
  "(prefers-reduced-motion: reduce)",
).matches;

if (!prefersReduced && "IntersectionObserver" in window) {
  const io = new IntersectionObserver(
    (entries) => {
      entries.forEach((e) => {
        if (e.isIntersecting) {
          e.target.classList.add("in");
          io.unobserve(e.target);
        }
      });
    },
    { threshold: 0.15 },
  );
  document.querySelectorAll(".reveal").forEach((el) => io.observe(el));
} else {
  document.querySelectorAll(".reveal").forEach((el) => el.classList.add("in"));
}

// Hero portrait carousel: photos shrink near the edges, swell at the centre
const facesViewport = document.querySelector(".hero-faces");
const facesTrack = document.getElementById("facesTrack");

if (facesViewport && facesTrack) {
  const photos = Array.from(facesTrack.querySelectorAll(".face-photo"));

  if (!prefersReduced) {
    const MIN_SCALE = 0.86;
    const MAX_SCALE = 1.08;

    const updateFaceScale = () => {
      const viewportRect = facesViewport.getBoundingClientRect();
      const center = viewportRect.left + viewportRect.width / 2;
      const halfWidth = viewportRect.width / 2;

      photos.forEach((photo) => {
        const rect = photo.getBoundingClientRect();
        const photoCenter = rect.left + rect.width / 2;
        const distance = Math.min(
          Math.abs(photoCenter - center) / halfWidth,
          1,
        );
        const closeness = Math.pow(1 - distance, 1.6);
        const scale = MIN_SCALE + (MAX_SCALE - MIN_SCALE) * closeness;
        photo.style.transform = `scale(${scale.toFixed(3)})`;
        photo.style.zIndex = Math.round(scale * 100);
      });

      requestAnimationFrame(updateFaceScale);
    };

    requestAnimationFrame(updateFaceScale);
  } else {
    photos.forEach((photo) => {
      photo.style.transform = "scale(1)";
    });
  }
}
