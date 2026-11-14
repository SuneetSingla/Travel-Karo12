// Public site: mobile nav toggle + sticky nav shadow on scroll.
(function () {
  var toggle = document.getElementById("navToggle");
  var links = document.getElementById("navLinks");
  var nav = document.getElementById("siteNav");

  if (toggle && links) {
    toggle.addEventListener("click", function () {
      var open = links.classList.toggle("open");
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
    });
    // Close menu when a link is tapped (mobile).
    links.querySelectorAll("a").forEach(function (a) {
      a.addEventListener("click", function () {
        links.classList.remove("open");
        toggle.setAttribute("aria-expanded", "false");
      });
    });
  }

  if (nav) {
    var onScroll = function () {
      if (window.scrollY > 10) nav.classList.add("scrolled");
      else nav.classList.remove("scrolled");
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
  }
})();
