// Enhance the booking phone field with an accessible country picker. The
// server remains authoritative: this only improves input and sends E.164 when
// the browser has loaded intl-tel-input successfully.
(function () {
  const input = document.getElementById("clientPhone");
  const form = document.getElementById("bookingForm");
  if (!input || !form || !window.intlTelInput) return;

  const phoneInput = window.intlTelInput(input, {
    initialCountry: "in",
    nationalMode: true,
    separateDialCode: true,
    formatAsYouType: true,
    utilsScript:
      "https://cdn.jsdelivr.net/npm/intl-tel-input@25.3.1/build/js/utils.js",
  });

  form.addEventListener("submit", function () {
    // getNumber returns an E.164 string. If client-side utilities have not
    // loaded or the value is invalid, keep the original value for Django to
    // validate and show its authoritative error message.
    if (input.value.trim() && phoneInput.isValidNumber()) {
      input.value = phoneInput.getNumber();
    }
  });
})();
