#!/usr/bin/env python3
"""Recalibrate the Relay fiction from the live board counter. Idempotent + re-runnable.

Why this exists as a script and not hand edits:
  - the counter moves ~3,000 messages/day, so any kHz figure in the site is stale within hours;
  - hand-chained replaces already broke the tuner scale once (42.000 ... 38.000);
  - the fixed band 36-44 was a real bug: home = counter/1000 sat at 95% of the scale at
    43,595 and would leave the band within a day. The band is now DERIVED from home.

Method: read the CURRENT home frequency out of index.html, compute each station's OFFSET
from it, then re-place every station at new_home + offset. Running it again is safe.

Usage: python recalibrate.py [COUNTER]     (omit COUNTER to scrape the live board)
"""
import re, os, sys, json, math, subprocess

D = r"D:\Media\тесты\Tools\Aisite"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126.0 Safari/537.36"
BAND_HALF = 4            # half-width of the tuning band in kHz (keeps the current 8 kHz feel)
LABEL_STEP = 2           # scale labels every N kHz


def live_counter():
    out = os.path.join(os.environ.get("LOCALAPPDATA", "/tmp"), "recal_live.html")
    subprocess.run(["curl", "-sSL", "--max-time", "25", "-A", UA,
                    "-o", out, "https://getpostingboard.dev/"], check=True)
    html = open(out, encoding="utf-8", errors="replace").read()
    m = re.search(r"([\d,]+)\s*MESSAGES", html)
    if not m:
        raise SystemExit("could not read the live counter")
    return int(m.group(1).replace(",", ""))


def load(p):  return open(os.path.join(D, p), encoding="utf-8").read()
def save(p, s): open(os.path.join(D, p), "w", encoding="utf-8").write(s)


def main():
    counter = int(sys.argv[1]) if len(sys.argv) > 1 else live_counter()
    home = counter / 1000.0
    fmin = int(math.floor(home)) - BAND_HALF
    fmax = fmin + 2 * BAND_HALF

    idx = load("index.html")
    m = re.search(r'aria-valuenow="([\d.]+)"', idx)
    old_home = float(m.group(1))
    print("live counter : %s" % f"{counter:,}")
    print("old home kHz : %.3f (band 36-44 -> home was at %.0f%% of the scale)" % (
        old_home, (old_home - 36) / 8 * 100))
    print("new home kHz : %.3f | new band %d-%d (home sits at %.0f%%)" % (
        home, fmin, fmax, (home - fmin) / (fmax - fmin) * 100))

    # ---- station offsets, read from the JS band plan so nothing is hand-typed ----
    js = load("js/relay-ether.js")
    old_st = [(float(a), b) for a, b in re.findall(r"\{ f:([\d.]+), call:\"([^\"]+)\"", js)]
    offsets = [(call, round(f - old_home, 3)) for f, call in old_st]
    new_st = {call: round(home + off, 3) for call, off in offsets}
    print("\nstation re-placement (offset from home preserved):")
    for call, off in offsets:
        print("   %-26s %+6.3f -> %.3f kHz" % (call, off, new_st[call]))

    # dispatch marks: freq(No. N) = home + (N-1) * 0.001 kHz
    dispatch_nos = sorted({int(n) for n in re.findall(r'No\. (\d+)</span>', load("meatproxy.html"))})
    new_dispatch = {n: round(home + (n - 1) * 0.001, 3) for n in dispatch_nos}
    print("\ndispatch marks:", ", ".join("No.%d -> %.3f" % (n, f) for n, f in sorted(new_dispatch.items())))

    # ================= apply =================
    changed = {}

    def sub_count(s, old, new):
        n = s.count(old)
        changed[old] = changed.get(old, 0) + n
        return s.replace(old, new)

    # --- js/relay-ether.js ---
    js2 = js
    js2 = sub_count(js2, "var FMIN = %s, FMAX = %s;" % (
        re.search(r"var FMIN = (\d+), FMAX = (\d+);", js).group(1),
        re.search(r"var FMIN = (\d+), FMAX = (\d+);", js).group(2)),
        "var FMIN = %d, FMAX = %d;" % (fmin, fmax))
    for call, newf in new_st.items():
        oldf = dict((c, f) for f, c in old_st)[call]
        js2 = sub_count(js2, "{ f:%.3f, call:\"%s\"" % (oldf, call), "{ f:%.3f, call:\"%s\"" % (newf, call))
    js2 = sub_count(js2, "%.3f" % old_home, "%.3f" % home)          # home constant everywhere
    js2 = sub_count(js2, "%s" % f"{int(round(old_home*1000)):,}", "%s" % f"{counter:,}")
    save("js/relay-ether.js", js2)

    # --- index.html ---
    i2 = idx
    i2 = sub_count(i2, 'aria-valuemin="%d"' % 36, 'aria-valuemin="%d"' % fmin)
    i2 = sub_count(i2, 'aria-valuemax="%d"' % 44, 'aria-valuemax="%d"' % fmax)
    i2 = sub_count(i2, 'aria-valuenow="%.3f"' % old_home, 'aria-valuenow="%.3f"' % home)
    i2 = sub_count(i2, 'aria-valuetext="%.3f kilohertz' % old_home, 'aria-valuetext="%.3f kilohertz' % home)
    # the four scale labels, replaced as one block so order can never collide
    old_row = re.search(r'<div class="tuner-row"[^>]*>.*?</div>', i2, re.S).group(0)
    new_row = ('<div class="tuner-row" aria-hidden="true">\n'
               '      <span>%d.000</span><span>%d.000</span>\n'
               '      <span class="tuner-hint">drag the needle — seven stations on the band</span>\n'
               '      <span>%d.000</span><span>%d.000</span>\n'
               '    </div>' % (fmin, fmin + LABEL_STEP, fmax - LABEL_STEP, fmax))
    changed["tuner-row"] = 1 if old_row != new_row else 0
    i2 = i2.replace(old_row, new_row)
    # station fallback list + ticker counters
    for call, newf in new_st.items():
        oldf = dict((c, f) for f, c in old_st)[call]
        i2 = sub_count(i2, "<b>%.3f kHz</b> · %s" % (oldf, call), "<b>%.3f kHz</b> · %s" % (newf, call))
    i2 = sub_count(i2, "%.3f kHz" % old_home, "%.3f kHz" % home)
    # the tuner readout shows the bare number (no unit) inside <span class="ro-freq">
    i2 = sub_count(i2, 'id="ro-freq">%.3f<' % old_home, 'id="ro-freq">%.3f<' % home)
    i2 = sub_count(i2, "%s transmissions logged" % f"{int(round(old_home*1000)):,}",
                   "%s transmissions logged" % f"{counter:,}")
    save("index.html", i2)

    # --- meatproxy.html ---
    mp = load("meatproxy.html"); mp2 = mp
    for n, f in re.findall(r'No\. (\d+)</span><span class="freq">· ([\d.]+) kHz', mp):
        mp2 = sub_count(mp2, 'No. %s</span><span class="freq">· %s kHz' % (n, f),
                        'No. %s</span><span class="freq">· %.3f kHz' % (n, new_dispatch[int(n)]))
    mp2 = sub_count(mp2, "Out of %s transmissions" % f"{int(round(old_home*1000)):,}",
                    "Out of %s transmissions" % f"{counter:,}")
    save("meatproxy.html", mp2)

    # --- article.html ---
    ar = load("article.html"); ar2 = ar
    for m2 in re.finditer(r'No\. (\d+) · ([\d.]+) kHz', ar):
        ar2 = sub_count(ar2, "No. %s · %s kHz" % (m2.group(1), m2.group(2)),
                        "No. %s · %.3f kHz" % (m2.group(1), new_dispatch[int(m2.group(1))]))
    save("article.html", ar2)

    # --- og.svg (the share card: it still printed 21.637 kHz from v1) ---
    og = load("assets/og.svg"); og2 = og
    old_og_khz = re.search(r'>([\d.]+) kHz ON AIR<', og).group(1)
    old_lo = re.search(r'<text x="330" y="580"[^>]*>([\d.]+)</text>', og).group(1)
    old_hi = re.search(r'<text x="870" y="580"[^>]*>([\d.]+)</text>', og).group(1)
    og2 = sub_count(og2, "%s kHz ON AIR" % old_og_khz, "%.3f kHz ON AIR" % home)
    og2 = sub_count(og2, ">%s</text>" % old_lo, ">%d.000</text>" % fmin)
    og2 = sub_count(og2, ">%s</text>" % old_hi, ">%d.000</text>" % fmax)
    save("assets/og.svg", og2)
    print("\nog.svg share card: %s kHz / band %s-%s  ->  %.3f kHz / band %d-%d" % (
        old_og_khz, old_lo, old_hi, home, fmin, fmax))

    # --- README.md ---
    rd = load("README.md"); rd2 = rd
    rd2 = sub_count(rd2, f"{int(round(old_home*1000)):,}", f"{counter:,}")
    rd2 = sub_count(rd2, "%.3f" % old_home, "%.3f" % home)
    rd2 = sub_count(rd2, "band 36–44", "band %d–%d" % (fmin, fmax))
    for n, f in sorted(new_dispatch.items()):
        rd2 = re.sub(r"No\. %d → [\d.]+ kHz" % n, "No. %d → %.3f kHz" % (n, f), rd2)
    save("README.md", rd2)

    json.dump({"counter": counter, "home": round(home, 3), "fmin": fmin, "fmax": fmax,
               "stations": new_st, "dispatch": new_dispatch},
              open(os.path.join(D, "_build_freqs.json"), "w", encoding="utf-8"), indent=1)
    print("\nwrote _build_freqs.json")


main()
