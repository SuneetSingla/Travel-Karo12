// Public site: mobile menu toggle + lightweight click tracking.
(function () {
  // Mobile menu
  var mb = document.getElementById("menuBtn");
  var nl = document.getElementById("navlinks");
  if (mb && nl) {
    mb.addEventListener("click", function () { nl.classList.toggle("open"); });
    nl.querySelectorAll("a").forEach(function (a) {
      a.addEventListener("click", function () { nl.classList.remove("open"); });
    });
  }

  // Click tracking: any element with data-track sends a small beacon to /track.
  // Used for the admin "website performance" insights. No personal data.
  function track(kind, label) {
    try {
      var body = JSON.stringify({ kind: kind, label: label || "" });
      if (navigator.sendBeacon) {
        navigator.sendBeacon("/track", new Blob([body], { type: "application/json" }));
      } else {
        fetch("/track", { method: "POST", headers: { "Content-Type": "application/json" }, body: body, keepalive: true });
      }
    } catch (e) { /* never block navigation */ }
  }
  document.addEventListener("click", function (e) {
    var el = e.target.closest("[data-track]");
    if (el) track(el.getAttribute("data-track"), el.getAttribute("data-label"));
  });
})();
