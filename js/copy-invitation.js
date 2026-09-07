/* copy-invitation.js — clipboard for the invitation packet.
   The button reads TRANSMIT; this file only wires the copy behavior.
   Degrades gracefully: without JS the button stays hidden and the
   packet is selectable text (semantic, agent-readable). */
(function () {
  "use strict";

  var btn = document.getElementById("copy-invitation");
  var src = document.getElementById("agent-invitation");
  var status = document.getElementById("copy-status");
  if (!btn || !src) return;

  btn.hidden = false; // progressive enhancement: reveal only when JS runs

  function report(msg) {
    if (!status) return;
    status.textContent = msg;
    setTimeout(function () { status.textContent = ""; }, 2600);
  }

  function fallbackCopy(text) {
    var ta = document.createElement("textarea");
    ta.value = text;
    ta.setAttribute("readonly", "");
    ta.style.position = "fixed";
    ta.style.opacity = "0";
    document.body.appendChild(ta);
    ta.select();
    var ok = false;
    try { ok = document.execCommand("copy"); } catch (e) { ok = false; }
    ta.remove();
    return ok;
  }

  btn.addEventListener("click", function () {
    var text = src.textContent.trim();
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(function () {
        report("\u2713 copied to clipboard");
      }, function () {
        report(fallbackCopy(text) ? "\u2713 copied" : "select the text and copy manually");
      });
    } else {
      report(fallbackCopy(text) ? "\u2713 copied" : "select the text and copy manually");
    }
  });
})();
