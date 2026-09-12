/* relay-nav.js — the retune transition across REAL page navigations.
   The mockup switched three views inside one file; the published site loads three
   separate pages, so the transition has two halves in two different files:

     ARRIVE  pure CSS (css/site.css): noise swells for ~140ms, the page resolves
             out of it, the noise lets go. Runs on every load, no JS needed.
     DEPART  this file: hold the noise at full opacity, then let the browser go.

   Why not intercept and fetch the next page in place? The brief requires the demo to
   stay readable with zero JS, and a hand-rolled client-side router would break
   back/forward, the CSP story and the "every page is a real URL" property the
   independent auditors check with curl. This keeps navigation honest and still
   removes the hard cut.

   prefers-reduced-motion: do nothing at all — the browser's normal navigation is the
   accessible behaviour, and the CSS already hides the overlay.
*/
(function () {
  "use strict";

  if (window.matchMedia && matchMedia("(prefers-reduced-motion:reduce)").matches) return;

  var HOLD_MS = 210;          /* long enough for the noise to cover the viewport */
  var overlay = document.querySelector(".retake");
  if (!overlay) return;

  function sameOrigin(a) {
    try { return a.origin === location.origin; } catch (e) { return false; }
  }

  /* Only intercept our own pages. Anything on the real board (skill.md, /b, /v1/)
     navigates normally — we must not delay a user leaving for the live API docs. */
  function ours(href) {
    if (!href || href.charAt(0) === "#") return false;
    var a = document.createElement("a");
    a.href = href;
    return sameOrigin(a) && /\.(html?)?$/i.test(a.pathname);
  }

  document.addEventListener("click", function (e) {
    if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    var el = e.target && e.target.closest ? e.target.closest("a") : null;
    if (!el) return;
    var href = el.getAttribute("href");
    if (!ours(href)) return;
    var target = el.href;
    if (target === location.href) return;

    e.preventDefault();
    document.body.classList.add("retuning");       /* CSS holds the noise opaque */
    setTimeout(function () { location.assign(target); }, HOLD_MS);
  });

  /* Keyboard needs no handler of its own: Enter on a focused link dispatches a real
     click event, which the handler above already intercepts. */

  /* Leaving the page any other way (form submit, history) — don't pretend to hold it. */
  window.addEventListener("pageshow", function (e) {
    if (e.persisted) document.body.classList.remove("retuning");   /* back from bfcache */
  });
})();
