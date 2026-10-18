# Basketball widget rebuild brief

Build a self-contained plain HTML, CSS, and JavaScript basketball shooting widget for the existing Django homepage.

- Keep the HTML in `core/templates/game.html`, included from the homepage. Do not replace Django navigation, crisis information, footer, or unrelated homepage content.
- Use scoped CSS in `static/css/game.css` and interaction code in `static/js/game.js`. Do not change global `body`, site typography, or Django buttons.
- Visual direction: a pale blue-grey stage (`#EAF0F4`), one large white dashed shooting surface, orange-red rim, thin grey net, compact score pill, and a small decorative coupon card.
- Interaction: pointer/mouse/touch drag on the ball, a visible aim guide, release-to-shoot physics, reliable downward rim-crossing score detection, no duplicate scores, and input locked during a shot.
- Progression: start at 0 baskets and 5 shots; a completed shot consumes one attempt; only five made baskets within five attempts unlock a coupon; include miss, completion, and replay states.
- Accessibility: clear labels, focus-visible controls, keyboard alternative, live status feedback, no horizontal overflow, and reduced-motion support.
- Coupon: keep reward/code values in one configuration object; reveal only after 5/5; provide copy and replay buttons; label it as a browser-only demo unless server-side issuance/validation exists.
- Load the CSS and JavaScript through Django's `{% static %}` template tag. Run Django checks and test the homepage after each implementation pass.
