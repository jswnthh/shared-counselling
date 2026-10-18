const court = document.querySelector("[data-basketball-game]");
const ball = court?.querySelector("[data-game-ball]");
const hoop = court?.querySelector("[data-game-hoop]");
const aimLayer = court?.querySelector("[data-game-aim]");
const statusEl = court?.querySelector("[data-game-status]");
const streakEl = court?.querySelector("[data-game-streak]");
const coupon = court?.querySelector("[data-game-coupon]");
const couponCodeLabel = coupon?.querySelector("[data-coupon-code-label]");
const couponNote = coupon?.querySelector("[data-coupon-note]");

if (court && ball && hoop && aimLayer) {
  const DOT_COUNT = 10;
  // Circle centers in each 32×32 asset sit at (r, r), and r shrinks toward the rim.
  const AIM_RADII = [6, 5.8, 5.6, 5.4, 5.2, 5, 4.8, 4.6, 4.4, 4.2];
  const DOT_BOX = 46;
  const REST_POWER = 0.42;
  const STREAK_GOAL = 3;

  const dots = AIM_RADII.map((radius, index) => {
    const img = document.createElement("img");
    const n = index + 1;
    img.className = "basketball-game-aim-dot";
    img.alt = "";
    img.draggable = false;
    img.width = DOT_BOX;
    img.height = DOT_BOX;
    img.src = new URL(`../images/game-assets/aim-point-${n}.svg`, import.meta.url).href;
    img.style.width = `${DOT_BOX}px`;
    img.style.height = `${DOT_BOX}px`;
    aimLayer.append(img);
    return { img, radius };
  });

  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  let rest = null;
  let aim = { lateral: 0, power: REST_POWER };
  let dragging = false;
  let flying = false;
  let pullDistance = 0;
  let activePointer = null;
  let streak = 0;
  let couponShown = false;

  function clamp(value, min, max) {
    return Math.min(max, Math.max(min, value));
  }

  function courtPoint(clientX, clientY) {
    const rect = court.getBoundingClientRect();
    return { x: clientX - rect.left, y: clientY - rect.top };
  }

  // getBoundingClientRect is in viewport pixels. `zoom` on the game
  // makes those differ from the CSS pixels used by left/top.
  function cssPerVisual() {
    const width = court.getBoundingClientRect().width;
    return width ? court.offsetWidth / width : 1;
  }

  function elementCenter(el, yRatio = 0.5) {
    const courtRect = court.getBoundingClientRect();
    const rect = el.getBoundingClientRect();
    return {
      x: rect.left - courtRect.left + rect.width / 2,
      y: rect.top - courtRect.top + rect.height * yRatio,
    };
  }

  function measureRest() {
    rest = elementCenter(ball);
  }

  function measureRim() {
    const rim = hoop.querySelector(".basketball-game-rim-front");
    const courtRect = court.getBoundingClientRect();
    const rect = rim.getBoundingClientRect();
    return {
      x: rect.left - courtRect.left + rect.width / 2,
      y: rect.top - courtRect.top + rect.height * 0.5,
      half: rect.width * 0.38,
    };
  }

  function pullFromPointer(pointer) {
    const ballRect = ball.getBoundingClientRect();
    const courtRect = court.getBoundingClientRect();
    const minX = ballRect.width / 2 + 8;
    const maxX = courtRect.width - ballRect.width / 2 - 8;
    const minY = ballRect.height / 2 + 8;
    const maxY = courtRect.height - ballRect.height / 2 - 8;
    const x = clamp(pointer.x, minX, maxX);
    const y = clamp(pointer.y, minY, maxY);
    const dx = x - rest.x;
    const dy = y - rest.y;
    return {
      x: dx,
      y: dy,
      // Screen-right aims the arc at the right side of the ring.
      lateral: clamp(dx / 110, -1, 1),
      // Pulling down lofts the shot. Pulling up flattens it.
      power: clamp(0.36 + dy / 130, 0.08, 1),
    };
  }

  function ballCenter() {
    return elementCenter(ball);
  }

  function trajectoryFor(start, lateral, power) {
    const rim = measureRim();
    const end = {
      x: rim.x + lateral * rim.half * 0.82,
      y: rim.y,
    };
    const rise = 80 + power * 240;
    const control = {
      x: start.x + (end.x - start.x) * (0.4 + lateral * 0.1),
      y: rim.y - rise,
    };
    return { start, control, end };
  }

  function pointOnCurve(curve, t) {
    const u = 1 - t;
    return {
      x: u * u * curve.start.x + 2 * u * t * curve.control.x + t * t * curve.end.x,
      y: u * u * curve.start.y + 2 * u * t * curve.control.y + t * t * curve.end.y,
    };
  }

  function placeDot(dot, point) {
    const scale = cssPerVisual();
    const origin = (dot.radius / 32) * DOT_BOX;
    dot.img.style.left = `${point.x * scale - origin}px`;
    dot.img.style.top = `${point.y * scale - origin}px`;
  }

  function renderAim() {
    if (court.getBoundingClientRect().width < 8) return null;
    const start = ballCenter();
    const curve = trajectoryFor(start, aim.lateral, aim.power);
    dots.forEach((dot, index) => {
      const t = (index + 1) / DOT_COUNT;
      placeDot(dot, pointOnCurve(curve, t));
    });
    return curve;
  }

  function placeBall(center) {
    const scale = cssPerVisual();
    const width = ball.offsetWidth;
    const height = ball.offsetHeight;
    ball.style.left = `${center.x * scale - width / 2}px`;
    ball.style.top = `${center.y * scale - height / 2}px`;
    ball.style.bottom = "auto";
    ball.style.transform = "none";
  }

  function releaseBallStyles() {
    ball.style.left = "";
    ball.style.top = "";
    ball.style.bottom = "";
    ball.style.transform = "";
  }

  function setStatus(text) {
    if (statusEl) statusEl.textContent = text;
  }

  function updateScore() {
    if (streakEl) streakEl.textContent = `${Math.min(streak, STREAK_GOAL)}/${STREAK_GOAL}`;
  }

  function setBallDepth(depth) {
    ball.classList.toggle("is-behind-rim", depth === "behind");
    ball.classList.toggle("is-bouncing", depth === "bounce");
  }

  function revealCoupon() {
    if (!coupon || couponShown) return;
    couponShown = true;
    coupon.hidden = false;
    requestAnimationFrame(() => coupon.classList.add("is-visible"));
  }

  async function copyCoupon() {
    if (!coupon) return;
    const code = coupon.dataset.couponCode;
    if (!code) return;

    try {
      await navigator.clipboard.writeText(code);
      if (couponCodeLabel) couponCodeLabel.textContent = "COPIED!";
      if (couponNote) couponNote.textContent = "Coupon code copied to your clipboard.";
      setStatus("Coupon code copied.");
    } catch {
      if (couponNote) couponNote.textContent = "Take a screenshot to save your coupon.";
      setStatus("Copy is unavailable here — take a screenshot of the coupon.");
    }
  }

  function onPointerDown(event) {
    if (flying || event.button > 0) return;
    dragging = true;
    activePointer = event.pointerId;
    ball.classList.add("is-dragging");
    ball.setPointerCapture(event.pointerId);
    measureRest();
    applyDrag(courtPoint(event.clientX, event.clientY));
    setStatus("Release to shoot along the arc.");
    event.preventDefault();
  }

  function applyDrag(pointer) {
    const pull = pullFromPointer(pointer);
    aim = { lateral: pull.lateral, power: pull.power };
    pullDistance = Math.hypot(pull.x, pull.y);
    placeBall({ x: rest.x + pull.x, y: rest.y + pull.y });
    renderAim();
  }

  function onPointerMove(event) {
    if (!dragging || event.pointerId !== activePointer) return;
    applyDrag(courtPoint(event.clientX, event.clientY));
  }

  function finishDrag(event) {
    if (!dragging || (event && event.pointerId !== activePointer)) return;
    dragging = false;
    activePointer = null;
    ball.classList.remove("is-dragging");
    const curve = renderAim();
    if (pullDistance < 16) {
      aim = { lateral: 0, power: REST_POWER };
      releaseBallStyles();
      requestAnimationFrame(() => {
        measureRest();
        renderAim();
      });
      setStatus("Pull the ball back, then release.");
      return;
    }
    fly(curve);
  }

  function fly(curve) {
    if (!curve) return;
    flying = true;
    ball.disabled = true;
    aimLayer.hidden = true;
    const duration = reducedMotion ? 0 : 720;
    const started = performance.now();

    function frame(now) {
      const t = duration === 0 ? 1 : clamp((now - started) / duration, 0, 1);
      const eased = 1 - (1 - t) ** 2;
      placeBall(pointOnCurve(curve, eased));
      if (t < 1) {
        requestAnimationFrame(frame);
        return;
      }
      resolveShot(curve);
    }

    requestAnimationFrame(frame);
  }

  function isBasket(curve) {
    const rim = measureRim();
    const horizontalError = Math.abs(curve.end.x - rim.x) / rim.half;
    // The ball must arrive over the centre of the rim with enough, but not too
    // much, loft. Everything else visibly catches the rim and rebounds.
    return horizontalError < 0.58 && aim.power >= 0.24 && aim.power <= 0.9;
  }

  function animateCurve(curve, duration, onComplete, depthAt) {
    const started = performance.now();
    function frame(now) {
      const t = duration === 0 ? 1 : clamp((now - started) / duration, 0, 1);
      if (depthAt && t >= depthAt.t) setBallDepth(depthAt.depth);
      placeBall(pointOnCurve(curve, t));
      if (t < 1) {
        requestAnimationFrame(frame);
      } else {
        onComplete();
      }
    }
    requestAnimationFrame(frame);
  }

  function finishShot(made) {
    setBallDepth(null);
    aimLayer.hidden = false;
    if (made) {
      streak += 1;
      if (streak >= STREAK_GOAL) revealCoupon();
    } else {
      streak = 0;
    }
    updateScore();
    aim = { lateral: 0, power: REST_POWER };
    releaseBallStyles();
    requestAnimationFrame(() => {
      measureRest();
      renderAim();
    });

    ball.disabled = false;
    setStatus(couponShown && streak === STREAK_GOAL ? "Three in a row — your coupon is unlocked!" : made ? "Swish! Keep the streak going." : "Off the rim — the streak resets. Try again.");
    flying = false;
  }

  function resolveShot(curve) {
    const made = isBasket(curve);
    const rim = measureRim();

    if (made) {
      hoop.classList.remove("is-rim-hit");
      hoop.classList.add("is-scored");
      const drop = {
        start: curve.end,
        control: { x: rim.x + (curve.end.x - rim.x) * 0.3, y: rim.y + 42 },
        end: { x: rim.x, y: rim.y + 122 },
      };
      animateCurve(drop, reducedMotion ? 0 : 360, () => {
        hoop.classList.remove("is-scored");
        finishShot(true);
      }, { t: 0.12, depth: "behind" });
      return;
    }

    hoop.classList.remove("is-scored");
    hoop.classList.add("is-rim-hit");
    const side = curve.end.x < rim.x ? -1 : 1;
    const rebound = {
      start: curve.end,
      control: { x: curve.end.x + side * 70, y: rim.y - 52 },
      end: { x: curve.end.x + side * 130, y: rim.y + 118 },
    };
    setBallDepth("bounce");
    animateCurve(rebound, reducedMotion ? 0 : 430, () => {
      hoop.classList.remove("is-rim-hit");
      finishShot(false);
    });
  }

  ball.addEventListener("pointerdown", onPointerDown);
  ball.addEventListener("pointermove", onPointerMove);
  ball.addEventListener("pointerup", finishDrag);
  ball.addEventListener("pointercancel", finishDrag);
  coupon?.addEventListener("click", copyCoupon);

  ball.addEventListener("keydown", (event) => {
    if (flying) return;
    const step = event.shiftKey ? 0.2 : 0.1;
    if (event.key === "ArrowLeft") {
      aim.lateral = clamp(aim.lateral - step, -1, 1);
    } else if (event.key === "ArrowRight") {
      aim.lateral = clamp(aim.lateral + step, -1, 1);
    } else if (event.key === "ArrowDown") {
      aim.power = clamp(aim.power + step, 0.08, 1);
    } else if (event.key === "ArrowUp") {
      aim.power = clamp(aim.power - step, 0.08, 1);
    } else if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      fly(renderAim());
      return;
    } else {
      return;
    }
    event.preventDefault();
    renderAim();
    setStatus("Arrows bend the arc. Enter shoots.");
  });

  function layoutFromRest() {
    if (dragging || flying) return;
    releaseBallStyles();
    requestAnimationFrame(() => {
      measureRest();
      renderAim();
    });
  }

  window.addEventListener("resize", layoutFromRest);
  hoop.querySelector(".basketball-game-rim-front")?.addEventListener("load", layoutFromRest);

  measureRest();
  updateScore();
  renderAim();
}
