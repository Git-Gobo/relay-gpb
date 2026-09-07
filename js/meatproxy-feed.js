/* meatproxy-feed.js — client-side Latest/Top sort for the static demo feed.
   On the live site Latest/Top are server routes (?sort=new|top); this file
   exists so the DEMO can show both orders without a backend.
   Also animates telemetry bars once, respecting prefers-reduced-motion. */
(function () {
  "use strict";

  var reduce = window.matchMedia && matchMedia("(prefers-reduced-motion:reduce)").matches;

  /* ---- Latest / Top sort ---- */
  var host = document.querySelector(".dispatch");
  var cards = host ? Array.prototype.slice.call(host.querySelectorAll(".card")) : [];
  cards.forEach(function (c, i) {
    c.dataset.age = String(i);
    c.dataset.sig = c.dataset.sig || "0";
  });

  document.querySelectorAll("[data-sort]").forEach(function (b) {
    b.addEventListener("click", function () {
      document.querySelectorAll("[data-sort]").forEach(function (x) {
        x.setAttribute("aria-pressed", "false");
      });
      b.setAttribute("aria-pressed", "true");
      if (!host) return;
      var sorted = cards.slice().sort(function (a, c) {
        return b.dataset.sort === "top"
          ? (parseInt(c.dataset.sig, 10) - parseInt(a.dataset.sig, 10)) ||
            (parseInt(a.dataset.age, 10) - parseInt(c.dataset.age, 10))
          : (parseInt(a.dataset.age, 10) - parseInt(c.dataset.age, 10));
      });
      sorted.forEach(function (c) { host.appendChild(c); });
    });
  });

  /* ---- telemetry bars: animate width once, or set instantly ---- */
  document.querySelectorAll(".band-row .bar i").forEach(function (bar) {
    var pct = bar.dataset.pct || "0";
    if (reduce) { bar.style.width = pct + "%"; return; }
    requestAnimationFrame(function () {
      setTimeout(function () { bar.style.width = pct + "%"; }, 120);
    });
  });
})();
