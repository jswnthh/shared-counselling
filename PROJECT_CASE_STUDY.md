# Shared Counselling — Project Case Study

**Audience for this document:** another AI (or a designer) building an **8–10 slide client presentation**.  
**Product:** Shared Counselling (working name “Common Ground”) — a marketing site plus a live, database-backed booking system for a shared counselling practice in India.  
**Stack:** Django 6 · Gunicorn · WhiteNoise · PostgreSQL (production) / SQLite (local) · Render · optional S3/R2 media · Resend/Anymail.

---

## How to turn this into slides

Use **one primary case-study beat per slide**: Problem → Requirement → Decision → What shipped → Client benefit.  
Do **not** dump file names. Speak in outcomes (trust, conversion, safety, operations).  
Suggested 10-slide arc is at the end.

**Brand in the UI:** “Shared Counselling” / “A Common Ground”.  
**Tone:** calm, professional, human — sage/teal palette, Space Grotesk + Karla, crisis-aware (not a wellness-app cliché).

---

## 1. The problem

A shared practice of qualified counsellors needed a **public face** and a **reliable first-session funnel**. Without a dedicated site they typically lose clients to:

- generic “contact us” forms and back-and-forth WhatsApp that never become an appointment;
- no way for a visitor to **self-select a counsellor** by focus area (anxiety, couples work, burnout, etc.);
- no shared **calendar of real availability**, so double-booking or “I’ll check and get back to you” delays;
- content locked in someone’s head or a spreadsheet — profiles and hours go stale;
- a website that looks like a brochure but cannot **take a booking**.

The client also needed **duty-of-care** on the public internet: people in distress may land here, so the site must signpost Indian crisis lines without pretending to be an emergency service.

---

## 2. Target users

| Persona | What they need | How the site serves them |
|---|---|---|
| **Prospective client** (individual, couple, family) | Safety, fit, a first session without a long email thread | Matching by topic + mode; directory; book in ~2 minutes; WhatsApp fallback |
| **HR / school coordinator** | Corporate or academic workshops, not DIY therapy | Dedicated service pages (corporate wellness, academic workshops) |
| **Practice coordinator / admin** | Edit profiles, hours, topics; see bookings; know when someone booked | Django admin; email notifications; `is_active` toggle |
| **Counsellor** (future) | Edit own bio/hours without seeing colleagues’ data | Admin row-level restriction already implemented; no public counsellor login yet |
| **Search engines / referrals** | Findable service pages | Per-page titles/descriptions, sitemap, robots.txt |

---

## 3. Requirement → design decision → implementation → benefit

Each block below is a **slide-ready story**. Use 6–8 of them as the body of the deck; keep the rest as speaker notes.

### 3.1 Marketing site + real bookings (not a brochure)

- **Problem:** A pretty site that still ends in “email us” does not convert anxious first-time clients.
- **Requirement:** Visitors must be able to pick a counsellor, see real slots, and confirm a session.
- **Decision:** One Django app: static-feeling marketing pages **and** a transactional `Booking` model. No separate booking SaaS (Calendly) so the practice owns data and UX.
- **Implementation:** Routes for home, four services, counsellor directory, `/book/`, JSON availability, confirmation. `BookingForm` + `get_available_slots()`. Submit is a **normal HTML POST** (not a fragile SPA).
- **Benefit:** The website **is** the front desk. The client can demonstrate a complete funnel in the presentation.

### 3.2 “Match me to a counsellor” instead of a staff list only

- **Problem:** Seven therapists look interchangeable to a new visitor; they bounce rather than guess.
- **Requirement:** Let people describe **what they want to work on** and get a shortlist.
- **Decision:** Topics live in the database, grouped by service. Each counsellor has **primary (weight 2)** and **secondary (weight 1)** specialties. Matching runs **in the browser** after one page load (no extra API).
- **Implementation:** Service pages render topic chips + `json_script` counsellor payload. `service.js` scores `sum(specialty weights) + 1 if mode matches`, caps **5 topics**, shows **top 3** with score > 0. CTA goes to `/book/?counsellor=<slug>`.
- **Benefit:** Feels personal and fast; specialty data is the same data that drives admin and booking — no duplicate CMS.

### 3.3 Directory as the booking gateway (choose a person first)

- **Problem:** A generic “book a session” page with a long counsellor dropdown is cold and error-prone.
- **Requirement:** People should meet the team, then book **that** person.
- **Decision:** Primary CTA “Book a session” goes to **`/counsellors/`**. `/book/` **redirects** to the directory unless `?counsellor=` is a valid **active** counsellor.
- **Implementation:** Card grid + profile overlay (`<dialog>`), hash URLs (`#slug`) for shareable profiles. Inactive counsellors show “Not accepting bookings”; WhatsApp remains available.
- **Benefit:** Conversion path is **human first**. Inactive staff stay visible for trust without taking phantom appointments.

### 3.4 Availability that cannot lie

- **Problem:** Showing slots the server will later reject destroys trust. Concurrent two-tab bookings can double-book.
- **Requirement:** Server is the source of truth; DB must still win races.
- **Decision:** Client calendar greys out non-working days as UX only. Real slots come from `GET /book/availability/`. POST re-checks `get_available_slots()`. A **conditional unique constraint** `(counsellor_slug, start_at)` for `status=confirmed` is the race guard (SQLite has no useful row locking).
- **Implementation:** 50-minute sessions, hourly starts (10-minute buffer), **21-day** horizon, **2-hour** lead time, Asia/Kolkata wall clock. `IntegrityError` → “that slot was just booked.” Email failure **does not** roll back the booking.
- **Benefit:** Honest calendar; no silent double-booking; booking survives mail outages.

### 3.5 Content in the database, stable shape for the frontend

- **Problem:** Hard-coded Python profiles require a developer for every bio/hours change.
- **Requirement:** Staff edit content in admin; site updates without a code change (except portraits in git — see photos).
- **Decision:** Keep the **old dict shape** (`slug`, `modes`, `specialties`, `working_hours[weekday] = [(start, end), ...]`) as a **query layer** (`core/data.py`). Views/JS never talk ORM.
- **Implementation:** Fresh queries each request (no import-time cache). Seed migration `0003` is a frozen copy of original content so deploys are replayable. Slug is **read-only after create** (bookings and URLs key on it).
- **Benefit:** Operational independence for copy/hours; engineers can change storage without rewriting templates.

### 3.6 Counsellor management as a practice OS

- **Problem:** Hours, languages, modes, photos, and “are they taking clients?” must stay consistent across matching, directory, and calendar.
- **Requirement:** One counsellor record to rule all surfaces.
- **Decision:** `Counsellor` + inlines for working windows (split shifts allowed) and specialty links. `is_active` is a first-class flag. Optional `user` FK for future self-serve.
- **Implementation:** Admin: list-editable `is_active`; portrait upload writes **WebP card (600px) + thumb (112px)** under `static/images/counsellors/`. Non-superuser staff tied to a counsellor **only see their row**; add/delete superuser-only (tested).
- **Benefit:** Practice can pause a counsellor overnight; matching and booking instantly respect it.

### 3.7 Crisis-aware, India-local product

- **Problem:** Mental-health sites that ignore crisis or look “US default” feel unsafe or irrelevant.
- **Requirement:** Visible helplines; India timezone; local contact paths.
- **Decision:** Fixed crisis bar (104 / Tele-MANAS 14416) with a **short mobile copy**. `TIME_ZONE = Asia/Kolkata` so `"09:00"` hours are IST, not UTC-shifted. WhatsApp (`wa.me`) as a parallel, culturally normal channel.
- **Implementation:** `tel:` links; compact bar under 600px; practice number in footer and enquire templates.
- **Benefit:** Demonstrates clinical responsibility and local fit in one glance — strong client-slide moment.

### 3.8 Production on a small budget without looking amateur

- **Problem:** Render free tier, ephemeral disks, blocked SMTP, hashed static files that 404’d.
- **Requirement:** HTTPS, Postgres, emails that actually send, CSS/JS that load.
- **Decision:** Blueprint: web service + Postgres. WhiteNoise **compressed but not filename-hashed** (hashing broke URLs). Email via **HTTPS APIs** (Resend preferred; Brevo/SendGrid fallbacks) because Render blocks 25/465/587. `SECRET_KEY` required. DEBUG off on Render.
- **Implementation:** `build.sh`: install → `collectstatic --clear` → **fail build if critical CSS/JS missing** → migrate. Gunicorn timeout 25s. SSL redirect, secure cookies, HSTS 1h, `CSRF_TRUSTED_ORIGINS` for onrender + custom domain env.
- **Benefit:** A credible live URL for the client demo; ops lessons already paid for.

---

## 4. Architecture (for one “how it works” slide)

```
Visitor browser
  ├── Marketing pages (server-rendered HTML + CSS)
  ├── Service matcher (JSON in page + service.js — no extra round trip)
  ├── Directory + overlay (HTML + counsellors.js)
  └── Booking UI (booking.js)
        ├── GET /book/availability/?counsellor=&date=   → JSON slots
        └── POST /book/  (CSRF) → validate → INSERT Booking
              ├── calendar_sync.create_calendar_event()  [stub]
              └── send_booking_emails()  [client + practice]
                    └── redirect /book/<id>/confirmed/

Django (core app)
  ├── data.py          dict API over ORM
  ├── scheduling.py    slot math + existing bookings + calendar busy
  ├── forms.py         never trust the chip list
  ├── admin.py         CMS for the practice
  └── images.py        portrait pipeline

Persist
  ├── Postgres (prod) / SQLite (dev)
  ├── WhiteNoise static (CSS/JS/WebP portraits)
  └── optional S3/R2 for leftover FileField media
```

**Important split:** `Booking` and `CalendarAccount` still key by **`counsellor_slug` string**, not a ForeignKey. That avoided rewriting the uniqueness constraint and scheduling queries when profiles moved into the DB. Historical bookings survive if a profile is later removed (confirmation page falls back to a title-cased slug).

**Calendar seam:** `CalendarAccount` + `calendar_sync.py` are the **only** place Google/Outlook would plug in. Callers already pass busy intervals and event IDs; today both functions no-op if not connected.

---

## 5. Pages and user journeys

### Public pages

| URL | Role | Journey |
|---|---|---|
| `/` | Trust + orientation | Hero team carousel → services → approach → counsellor teaser → book CTA. Crisis bar always on. |
| `/services/<slug>/` | Fit | Read intro → pick up to 5 topics → filter online/in-person → top 3 matches → Book or see all. |
| `/counsellors/` | Choose a person | Scan cards (status, specialties, location, languages) → overlay bio → Book or WhatsApp. Hash deep-link. |
| `/book/?counsellor=` | Convert | Mode → month calendar → fetch slots → name/email/phone → summary → confirm. |
| `/book/<id>/confirmed/` | Reassure | Summary + “email on the way”. |
| `/admin/` | Operate | Content + bookings. |
| `/sitemap.xml`, `/robots.txt` | Discover | Index marketing routes; disallow admin + availability API. |

### Primary conversion paths (draw these as 2–3 arrows on a slide)

1. **Home → Service → Match card → Book → Confirm → Email**  
2. **Home / nav → Directory → Profile → Book → Confirm**  
3. **Directory → WhatsApp** (enquire without committing to a slot)

Homepage “Book a first session” hits `/book/` **without** a counsellor and is redirected to the directory — by design.

### Four services (seeded)

1. Individual therapy  
2. Couples & family  
3. Corporate wellness  
4. Academic workshops  

Each has its own topic taxonomy (anxiety vs team conflict vs exam pressure, etc.).

---

## 6. Frontend features (what to show on a “product” slide)

- **Design system:** sage surface, slate/teal, large display type, rounded cards, ticker of specialisms, CTA marquee. Distinctive, not a Tailwind template.
- **Hero:** duplicated portrait track for seamless loop; `requestAnimationFrame` scale-by-distance from viewport centre; `fetchpriority="high"` on first image; lazy on the duplicate set.
- **Motion ethics:** `prefers-reduced-motion` disables carousel animation, ticker, orb, marquee, and skip-scroll-reveal.
- **Service matcher:** chip UI, live region for matches, lazy thumbs.
- **Directory overlay:** native `<dialog>`, focus restore, prev/next, keyboard, URL hash.
- **Booking widget:** custom month grid (not native date picker only), greys non-working weekdays and dates outside horizon; slot chips from API; live summary; hidden fields kept in sync.
- **Progressive enhancement:** booking is a real form; JS is additive.
- **XSS-safe data:** `json_script` not concatenated JS.
- **WhatsApp CTAs** with prefilled enquire text.
- **Crisis bar** full vs short copy.

**Accessibility notes for speaker notes:** `lang="en"`, viewport meta, `aria-label` on navs, `sr-only` headings, `:focus-visible` rings, `aria-live` on matches, `role="alert"` on form errors, decorative photos `alt=""` + `aria-hidden`. Native dialog semantics on the directory overlay.

---

## 7. Backend features

- Slot engine honouring hours, bookings, horizon, lead time, overlap with busy intervals.
- Server-side form: counsellor exists and is **bookable**, mode offered, phone ≥ 10 digits, slot still free.
- Atomic create + unique confirmed slot.
- Dual email: client confirmation (CC practice) + staff “new booking”.
- Availability JSON 404/400 for bad slug/date.
- Admin as CMS (services, topics, counsellors, bookings, calendar accounts).
- Portrait pipeline (Pillow, EXIF transpose, WebP).
- Tests covering availability exclusion, duplicate POST, inactive counsellor, email success/failure, admin isolation, sitemap/robots, photo resolution.

---

## 8. Models, views, important logic (for a technical appendix slide)

### Models

| Model | Why it exists |
|---|---|
| `ServiceCategory` | One marketing page + topic grouping |
| `Topic` | Matcher checkboxes |
| `Counsellor` | Public profile; `is_active`; JSON lists for languages/modes/modalities; `fee_note` reference-only; optional `user` |
| `CounsellorWorkingHours` | Split shifts; unique per counsellor/weekday/start |
| `CounsellorSpecialty` | Primary=2 / Secondary=1; unique per counsellor+topic |
| `Booking` | The transaction; modes online / in-person; cancelled vs confirmed; `client_phone`; `calendar_event_id` reserved |
| `CalendarAccount` | Future OAuth tokens + provider |

### Views (behaviour, not filenames)

- **index** — counsellor photo/name/active for hero + teaser dots.  
- **service_detail** — 404 unknown slug; bookable counsellors only in matcher JSON.  
- **counsellors** — all profiles (including inactive) with specialty labels, bio paragraphs, WhatsApp copy.  
- **book** — GET requires valid active counsellor; POST validates, creates, calendar stub, emails, redirect; IntegrityError friendly.  
- **booking_availability** — GET JSON.  
- **book_confirmed** — loads booking by id; name fallback if counsellor gone.  
- **robots_txt** — Allow `/`, Disallow admin + availability.

### Scheduling constants (say them on a slide if asked “how do hours work?”)

- Session **50** minutes, step **60** minutes.  
- Book **21** days ahead, minimum **2 hours** from now.  
- Display fee **₹1,500** — cosmetic; **no payments**.

---

## 9. Counsellor management (operations slide)

**Intake:** structured questionnaire (`docs/counsellor-content-intake.md`) maps to name, credentials, photo framing, location, modes, languages, intro, bio, modalities, specialty grid, weekly availability.

**Day-to-day:** Django admin. Toggle `is_active` from the list. Edit hours as rows (morning + evening). Attach specialties with level. Upload a JPEG/PNG/WebP → automatic WebP variants; **commit those static files** so the next Render deploy still has them (ephemeral disk).

**Governance already built:** slug immutable after create; counsellor staff cannot add/delete colleagues or open others’ change forms.

**Not built yet:** counsellor login portal, per-counsellor WhatsApp numbers, per-counsellor prices in the booking summary, live calendar OAuth.

---

## 10. Responsive / mobile

Breakpoints in CSS (not a JS layout engine):

- **≤600px:** crisis bar short copy (fixed height must not wrap).  
- **≤720px:** nav collapses to **Book only** (Services/Approach/Counsellors links hidden); approach rows stack; counsellor teaser column + View badge under faces.  
- **≤820px:** service cards single column.  
- **≤900px:** booking and service layouts stack; counsellor cards tighten; extra tweak **900–1099px**.

Also: `100svh` hero, `min(1200px, 92%)` wrap, `-webkit-tap-highlight` off, overflow-x hidden. An earlier mouse-follow “View” gimmick was **removed** because it failed on mobile — design decision: always-visible badge + hover scale on desktop.

Verify in a demo: phone-width homepage, directory overlay, booking calendar chips, crisis bar, WhatsApp button thumb reach.

---

## 11. SEO (honest: solid basics, not a content-marketing engine)

**Shipped**

- Unique `<title>` and `meta description` on home (default), each service (intro as description), directory, booking, confirmation.  
- Semantic headings, crawlable service and counsellor URLs.  
- `sitemap.xml`: home (1.0), counsellors (0.9), book (0.6), each service (0.8), weekly changefreq.  
- `robots.txt` points at sitemap; blocks `/admin/` and `/book/availability/`.  
- `django.contrib.sitemaps` in INSTALLED_APPS.  
- Fast-ish images (AVIF faces, WebP cards/thumbs, width/height attributes, lazy load).

**Not shipped (future / do not oversell)**

- Open Graph / Twitter cards  
- JSON-LD `LocalBusiness` / `Person` / `MedicalBusiness`  
- Canonical URLs, hreflang  
- Blog / resources for organic traffic  
- `noindex` on confirmation pages (IDs are sequential — see security)  
- Per-counsellor public URLs as first-class sitemap entries (hashes on `/counsellors/#slug` are weaker than `/counsellors/divya-shri/`)

---

## 12. Security considerations (be transparent with the client)

**In place**

- CSRF on booking POST; Django auth on admin; password validators.  
- `SECRET_KEY` from env; missing key fails boot.  
- Production: HTTPS redirect, secure session/CSRF cookies, HSTS, proxy SSL header.  
- `ALLOWED_HOSTS` + `.onrender.com`; extra CSRF origins via env for a custom domain.  
- Clickjacking middleware (Django default).  
- Availability and admin excluded from robots.  
- Server never trusts client slot list.  
- Email credentials not in git; `.env` loader does not overwrite existing env.  
- `json_script` for counsellor JSON.

**Gaps / risks to name if asked (maturity, not scare)**

- Confirmation URL `/book/<integer>/confirmed/` is **unguessable only by obscurity** — sequential IDs leak name, email, phone. Should be signed token or login.  
- No rate limit / captcha on booking or availability (spam / slot scraping).  
- `CalendarAccount` token fields would be **plaintext in DB** if OAuth is enabled without encryption.  
- Confirmation pages are **indexable** unless `noindex` added.  
- Media on local filesystem in production if S3 not configured (Render disk ephemeral + not ideal for PII photos).  
- HSTS is **1 hour** (good to start; raise after custom domain is stable).  
- Global `user-select: none` is a UX choice; not a security control.  
- No Content-Security-Policy, no 2FA documented for admin.

---

## 13. Deployment architecture

```
Git push → Render build (Python 3.13.7)
  pip install -r requirements.txt
  collectstatic --clear   # WhiteNoise CompressedStaticFilesStorage
  assert CSS/JS exist
  migrate --noinput

Runtime: gunicorn ProjectCounsellingSite.wsgi --bind 0.0.0.0:$PORT --timeout 25
DB: Render Postgres (DATABASE_URL, SSL, conn_max_age=600)
Static: WhiteNoise (WHITENOISE_USE_FINDERS=true as safety net)
Email: RESEND_API_KEY (or Brevo/SendGrid) via django-anymail
Optional media: AWS_* / R2-compatible endpoint
```

**Local:** SQLite, DEBUG on unless `RENDER` or explicit `DEBUG`. SMTP fallback if no API key.

**Blueprint:** `render.yaml` — free web + free Postgres; `SECRET_KEY` and `RESEND_API_KEY` dashboard secrets (needed at **build** time for collectstatic/Django).

---

## 14. Domain and HTTPS

- Render provides `*.onrender.com` with HTTPS; settings auto-allow that host and CSRF `https://*.onrender.com`.  
- Custom domain: set `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` (comma-separated env).  
- `SECURE_SSL_REDIRECT` + `SECURE_PROXY_SSL_HEADER` when `DEBUG` is false so Render’s TLS terminator is trusted.  
- Cookies marked Secure in production so session/CSRF never travel on HTTP.  
- **Client action:** point DNS (CNAME/ALIAS) at Render, add the domain in the dashboard, wait for cert, then raise HSTS.

There is no in-repo nginx/Caddy config; TLS is platform-managed.

---

## 15. Performance optimisations

- WhiteNoise compressed static; long-cache possible on S3 media (`immutable` Cache-Control).  
- Portraits: two sizes (card vs thumb); matcher and booking use **thumbs**.  
- AVIF for hero face assets; WebP for counsellor cards.  
- Google Fonts `preconnect`; `display=swap`.  
- Lazy-load below-fold images; first hero face high priority.  
- Matching is client-side after one HTML response (no N+1 APIs while clicking topics).  
- Availability fetched **once per selected date**, not per month paint.  
- ORM: `prefetch_related` hours and specialties.  
- DB connection pooling (`conn_max_age=600`) on Postgres.  
- Build fails rather than shipping a site with missing CSS.

**Tradeoff documented in code:** filename hashing was **turned off** after hashed URLs 404’d against unhashed files on disk. Compression remains.

**Not done:** CDN in front of HTML, Redis cache of counsellor dicts, HTTP/2 push, critical CSS inlining, image CDN.

---

## 16. Technical challenges solved (good “engineering” slide)

1. **Static content → CMS without rewriting the frontend** — dict adapter + data migration freeze.  
2. **Double-booking under SQLite and concurrent POSTs** — unique constraint + IntegrityError UX, not `select_for_update`.  
3. **Timezone correctness** — naive `"09:00"` strings made aware in IST so UTC default would not shift every diary by 5.5h.  
4. **Render SMTP blocked** — Anymail HTTPS providers; booking still succeeds if mail throws.  
5. **Hashed static 404s in production** — compressed-only storage + collectstatic smoke test.  
6. **Portraits vs ephemeral disk vs ImageField** — generate WebP into `static/`, resolve by **file existence** (`cards/<slug>.webp` beats stale `face_N` placeholders).  
7. **Mobile motion/nav** — dropped cursor-follow; crisis bar copy swap; nav collapse.  
8. **Trust vs conversion** — inactive counsellors visible but not bookable; server re-check if they were deactivated mid-form.

---

## 17. Design decisions visible from the code (taste + product)

- **Collective identity:** carousel of many faces, not a founder hero. Copy: “a team… every kind of mind.”  
- **Warm clinical, not startup purple:** sage, slate, teal; no stock gradients-as-product.  
- **Duty of care before marketing:** crisis bar is the topmost chrome.  
- **Person before calendar:** book URL requires a counsellor.  
- **Honesty about money:** one displayed fee, explicitly not a payment system; `fee_note` stored for later.  
- **WhatsApp is a first-class conversion**, not a footer afterthought.  
- **Progressive JS:** directory overlay and matcher enhance HTML; booking still posts.  
- **Admin as the product** for staff, not a second custom CMS.  
- **Seams over premature features:** calendar OAuth stubbed; counsellor `user` stubbed; Booking not FK’d yet.

---

## 18. Value to the client (close the deck on this)

What they can **use on Monday**:

- A live funnel from Google/referral → match or directory → booked session in the database.  
- Emails to the client and the practice inboxes.  
- WhatsApp with prefilled context.  
- Staff can change copy, hours, specialties, and “accepting clients” without waiting on a developer (portraits still need a deploy if new files).  
- Four service narratives (individual, couples/family, corporate, academic) for different buyers.  
- Crisis positioning that protects the practice’s reputation.  
- A path to Google/Outlook that does not require rewriting the site.  
- Tests around the money-path equivalent (the booking path).

---

## 19. Future improvements (roadmap slide — prioritize)

**High value, natural next steps**

1. **Custom domain + longer HSTS + Search Console** (sitemap already exists).  
2. **Signed/secret confirmation URLs** + `noindex`; optional client cancel/reschedule link.  
3. **Rate limiting + honeypot/captcha** on book and availability.  
4. **Real calendar sync** (fill `calendar_sync.py`; encrypt tokens).  
5. **Payment / deposits** or per-counsellor `fee_note` on the booking summary.  
6. **Open Graph + JSON-LD** for link previews and local SEO.  
7. **Counsellor self-serve** (the `user` FK and admin filters are ready).  
8. **Canonical counsellor pages** (`/counsellors/<slug>/`) for SEO and sharing.

**Medium**

- Online session: auto-generate Meet/Zoom link in the confirmation email.  
- SMS/WhatsApp booking confirmation (India).  
- Waitlist when a counsellor is inactive.  
- Caching `get_counsellors()` with invalidation on admin save.  
- CDN + restore hashed static **correctly**.  
- Persistent media (R2) for uploads without git.  
- Accessibility pass (overlay, calendar grid keyboard, contrast on crisis bar).  
- Analytics with privacy-respecting events (match → book → confirm).

**Later / larger**

- Recurring sessions, packages, sliding scale.  
- Client portal.  
- Multi-language UI (content already stores language **tags** per counsellor).  
- Corporate intake / workshop request form distinct from 1:1 booking.

---

## 20. Suggested 10-slide outline (for the presentation builder)

| # | Slide title | Use from this doc | Visual |
|---|---|---|---|
| 1 | **The brief** | §1 problem + practice name | One sentence + crisis bar screenshot |
| 2 | **Who it is for** | §2 table, 3 personas | Icons: client / HR / practice |
| 3 | **The journey** | §5 conversion paths | 3-arrow flow: Match / Directory / WhatsApp |
| 4 | **Find the right counsellor** | §3.2 matcher | Service page chips + 3 match cards |
| 5 | **Meet the team** | §3.3 directory | Card + overlay; active/inactive |
| 6 | **Book with confidence** | §3.4 slots + constraint | Calendar + “slot taken” story |
| 7 | **Run the practice** | §3.5–3.6 admin | `is_active`, hours, emails |
| 8 | **Built for India, built to last** | §3.7 + §13–14 | IST, helplines, WhatsApp, HTTPS |
| 9 | **Under the hood (light)** | §4 + §16 3 bullets | Architecture diagram, no file dump |
| 10 | **Live today / next** | §18 + §19 top 5 | Checklist + roadmap |

**Speaker-note extras (do not crowd slides):** SEO §11, security honesty §12, no payments, calendar stub, confirmation URL privacy, photo git deploy caveat.

---

## 21. Facts a presenter must not get wrong

- This is a **real booking database**, not a mock.  
- It is **not** a payments product. Fee is display-only (₹1,500).  
- Google Calendar is **prepared, not live**.  
- Seven seeded counsellor profiles; content is **admin-editable**.  
- Matching is **weighted specialties**, not AI.  
- Timezone is **India**. Helplines are **104** and **Tele-MANAS 14416**.  
- Hosting model: **Render + Postgres + WhiteNoise + Resend**.  
- “Book a session” in the header goes to the **directory**, not an empty calendar.

---

*Document generated from the codebase for client presentation use. It describes the product as implemented, including limitations.*
