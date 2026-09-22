// Booking flow for a pre-selected counsellor: mode → date → time → confirm.
// Availability comes from /book/availability/ (server-authoritative). Submit
// is a normal form POST.
(function () {
  const form = document.getElementById("bookingForm");
  const dataEl = document.getElementById("counsellors-data");
  if (!form || !dataEl) return;

  const counsellors = JSON.parse(dataEl.textContent);
  const bySlug = {};
  counsellors.forEach((c) => {
    bySlug[c.slug] = c;
  });

  const WEEKDAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
  const windowDays = parseInt(form.dataset.windowDays, 10) || 21;
  const serverHorizon = form.dataset.bookingHorizon
    ? new Date(form.dataset.bookingHorizon)
    : null;

  const counsellorSlugInput = document.getElementById("counsellorSlugInput");
  const dateInput = document.getElementById("dateInput");
  const timeInput = document.getElementById("timeInput");
  const modeInput = document.getElementById("modeInput");

  const calPrev = document.getElementById("calPrev");
  const calNext = document.getElementById("calNext");
  const calMonthLabel = document.getElementById("calMonthLabel");
  const calGrid = document.getElementById("calGrid");
  const slotGrid = document.getElementById("slotGrid");
  const slotEmpty = document.getElementById("slotEmpty");
  const modeFilter = document.getElementById("modeFilter");
  const summaryCounsellor = document.getElementById("summaryCounsellor");
  const summaryDate = document.getElementById("summaryDate");
  const summaryTime = document.getElementById("summaryTime");
  const summaryMode = document.getElementById("summaryMode");
  const confirmBtn = document.getElementById("confirmBtn");

  let selectedSlug = counsellorSlugInput.value || form.dataset.preselected || "";
  let selectedDate = dateInput.value || "";
  let selectedTime = timeInput.value || "";
  let selectedMode = modeInput.value || "";
  let currentMonth = null;

  const counsellor = bySlug[selectedSlug];
  if (!counsellor) return;

  const pad2 = (n) => String(n).padStart(2, "0");
  const isoDate = (d) =>
    `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`;
  const startOfDay = (d) => new Date(d.getFullYear(), d.getMonth(), d.getDate());
  const firstOfMonth = (d) => new Date(d.getFullYear(), d.getMonth(), 1);
  const addDays = (d, n) => {
    const copy = new Date(d);
    copy.setDate(copy.getDate() + n);
    return copy;
  };
  const sameMonth = (a, b) =>
    a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth();

  const formatTime = (hhmmss) => {
    const [hStr, mStr] = hhmmss.split(":");
    let h = parseInt(hStr, 10);
    const suffix = h >= 12 ? "PM" : "AM";
    h = h % 12 || 12;
    return `${h}:${mStr} ${suffix}`;
  };

  const formatDateFull = (iso) => {
    const d = new Date(`${iso}T00:00:00`);
    return d.toLocaleDateString("en-GB", {
      day: "numeric",
      month: "long",
      year: "numeric",
    });
  };

  const today = startOfDay(new Date());
  const horizon = serverHorizon ? startOfDay(serverHorizon) : addDays(today, windowDays);
  const minMonth = firstOfMonth(today);
  const maxMonth = firstOfMonth(horizon);

  function renderModeChips() {
    modeFilter.replaceChildren();

    counsellor.modes.forEach((m) => {
      const chip = document.createElement("button");
      chip.type = "button";
      chip.className = "mode-chip" + (m === selectedMode ? " is-active" : "");
      chip.dataset.mode = m;
      chip.textContent = m === "in-person" ? "In person" : "Online";
      chip.addEventListener("click", () => {
        selectedMode = m;
        modeInput.value = m;
        modeFilter.querySelectorAll(".mode-chip").forEach((el) => {
          el.classList.toggle("is-active", el.dataset.mode === m);
        });
        updateSummary();
      });
      modeFilter.appendChild(chip);
    });

    if (selectedMode && !counsellor.modes.includes(selectedMode)) {
      selectedMode = "";
      modeInput.value = "";
    }

    // Default to the first offered mode so the flow has one less tap when
    // the counsellor only offers one option (or as a sensible start).
    if (!selectedMode && counsellor.modes.length === 1) {
      selectedMode = counsellor.modes[0];
      modeInput.value = selectedMode;
      modeFilter
        .querySelector(`.mode-chip[data-mode="${selectedMode}"]`)
        ?.classList.add("is-active");
    }
  }

  function renderCalendar() {
    calGrid.replaceChildren();
    calMonthLabel.textContent = currentMonth.toLocaleDateString("en-GB", {
      month: "long",
      year: "numeric",
    });
    calPrev.disabled = sameMonth(currentMonth, minMonth) || currentMonth < minMonth;
    calNext.disabled = sameMonth(currentMonth, maxMonth);

    WEEKDAY_LABELS.forEach((label) => {
      const cell = document.createElement("span");
      cell.className = "cal-day is-label";
      cell.textContent = label;
      calGrid.appendChild(cell);
    });

    const firstDay = new Date(currentMonth);
    const leadingBlanks = (firstDay.getDay() + 6) % 7;
    for (let i = 0; i < leadingBlanks; i++) {
      calGrid.appendChild(document.createElement("span"));
    }

    const daysInMonth = new Date(
      currentMonth.getFullYear(),
      currentMonth.getMonth() + 1,
      0
    ).getDate();

    for (let day = 1; day <= daysInMonth; day++) {
      const date = new Date(currentMonth.getFullYear(), currentMonth.getMonth(), day);
      const iso = isoDate(date);
      const pyWeekday = (date.getDay() + 6) % 7;
      const hasHours = (counsellor.working_hours[String(pyWeekday)] || []).length > 0;
      const inWindow = date >= today && date <= horizon;

      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "cal-day";
      btn.textContent = String(day);

      if (!hasHours || !inWindow) {
        btn.classList.add("is-disabled");
        btn.disabled = true;
      } else {
        if (iso === selectedDate) btn.classList.add("is-selected");
        btn.addEventListener("click", () => {
          calGrid.querySelectorAll(".cal-day").forEach((el) => el.classList.remove("is-selected"));
          btn.classList.add("is-selected");
          fetchAvailability(iso, { preserveSelection: false });
        });
      }
      calGrid.appendChild(btn);
    }
  }

  function fetchAvailability(iso, opts) {
    selectedDate = iso;
    dateInput.value = iso;
    if (!opts.preserveSelection) {
      selectedTime = "";
      timeInput.value = "";
    }
    slotGrid.replaceChildren();
    slotEmpty.hidden = false;
    slotEmpty.textContent = "Loading available times…";
    updateSummary();

    fetch(
      `/book/availability/?counsellor=${encodeURIComponent(counsellor.slug)}&date=${iso}`
    )
      .then((res) => {
        if (!res.ok) throw new Error(`availability ${res.status}`);
        return res.json();
      })
      .then((data) => renderSlots(data.slots || []))
      .catch(() => {
        slotEmpty.hidden = false;
        slotEmpty.textContent = "Couldn't load times — please try again.";
      });
  }

  function renderSlots(slots) {
    slotGrid.replaceChildren();
    if (slots.length === 0) {
      slotEmpty.hidden = false;
      slotEmpty.textContent = "No times available that day — try another date.";
      return;
    }
    slotEmpty.hidden = true;

    slots.forEach((iso) => {
      const timePart = iso.slice(11, 19);
      const chip = document.createElement("button");
      chip.type = "button";
      chip.className =
        "slot-chip" +
        (timePart.slice(0, 5) === selectedTime.slice(0, 5) ? " is-selected" : "");
      chip.textContent = formatTime(timePart);
      chip.addEventListener("click", () => {
        selectedTime = timePart;
        timeInput.value = timePart;
        slotGrid.querySelectorAll(".slot-chip").forEach((el) => el.classList.remove("is-selected"));
        chip.classList.add("is-selected");
        updateSummary();
      });
      slotGrid.appendChild(chip);
    });
  }

  function updateSummary() {
    summaryCounsellor.textContent = counsellor.name;
    summaryMode.textContent =
      selectedMode === "in-person"
        ? "In person"
        : selectedMode === "online"
          ? "Online"
          : "—";
    summaryDate.textContent = selectedDate ? formatDateFull(selectedDate) : "—";
    summaryTime.textContent = selectedTime ? formatTime(selectedTime) : "—";

    const ready = Boolean(selectedDate && selectedTime && selectedMode);
    confirmBtn.disabled = !ready;
  }

  calPrev.addEventListener("click", () => {
    if (calPrev.disabled) return;
    currentMonth = new Date(currentMonth.getFullYear(), currentMonth.getMonth() - 1, 1);
    renderCalendar();
  });

  calNext.addEventListener("click", () => {
    if (calNext.disabled) return;
    currentMonth = new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1, 1);
    renderCalendar();
  });

  counsellorSlugInput.value = counsellor.slug;
  renderModeChips();
  currentMonth = selectedDate
    ? firstOfMonth(new Date(`${selectedDate}T00:00:00`))
    : minMonth;
  renderCalendar();
  if (selectedDate) {
    fetchAvailability(selectedDate, { preserveSelection: true });
  }
  updateSummary();
})();
