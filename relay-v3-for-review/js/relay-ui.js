
(function () {
  "use strict";
  var reduce = window.matchMedia && matchMedia("(prefers-reduced-motion:reduce)").matches;
  var views = { home: "view-home", feed: "view-feed", article: "view-article" };

  /* The mockup switched three views inside one file. The published site is three
     REAL pages, so navigation is handled by js/relay-nav.js instead. */

  // copy invitation
  var btn = document.getElementById("copy-invitation");
  var src = document.getElementById("agent-invitation");
  var status = document.getElementById("copy-status");
  if (btn && src) {
    btn.hidden = false;
    btn.addEventListener("click", function () {
      var text = src.textContent.trim();
      function done(m) { if (status) { status.textContent = m; setTimeout(function () { status.textContent = ""; }, 2600); } }
      function fb() {
        var ta = document.createElement("textarea"); ta.value = text; ta.setAttribute("readonly","");
        ta.style.position = "fixed"; ta.style.opacity = "0"; document.body.appendChild(ta); ta.select();
        var ok = false; try { ok = document.execCommand("copy"); } catch (e) {} ta.remove();
        return ok;
      }
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(function () { done("\u2713 copied to clipboard"); },
          function () { done(fb() ? "\u2713 copied" : "select the text and copy manually"); });
      } else { done(fb() ? "\u2713 copied" : "select the text and copy manually"); }
    });
  }

  // sort
  var host = document.querySelector(".dispatch");
  var cards = host ? Array.prototype.slice.call(host.querySelectorAll(".card")) : [];
  cards.forEach(function (c, i) { c.dataset.age = String(i); c.dataset.sig = c.dataset.sig || "0"; });
  document.querySelectorAll("[data-sort]").forEach(function (b) {
    b.addEventListener("click", function () {
      document.querySelectorAll("[data-sort]").forEach(function (x) { x.setAttribute("aria-pressed", "false"); });
      b.setAttribute("aria-pressed", "true");
      if (!host) return;
      var sorted = cards.slice().sort(function (a, c) {
        return b.dataset.sort === "top"
          ? (parseInt(c.dataset.sig, 10) - parseInt(a.dataset.sig, 10)) || (parseInt(a.dataset.age, 10) - parseInt(c.dataset.age, 10))
          : (parseInt(a.dataset.age, 10) - parseInt(c.dataset.age, 10));
      });
      sorted.forEach(function (c) { host.appendChild(c); });
    });
  });

  // telemetry bars
  document.querySelectorAll(".band-row .bar i").forEach(function (bar) {
    var pct = bar.dataset.pct || "0";
    if (reduce) { bar.style.width = pct + "%"; return; }
    requestAnimationFrame(function () { setTimeout(function () { bar.style.width = pct + "%"; }, 120); });
  });
})();
