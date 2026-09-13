#!/usr/bin/env python3
"""Rebuild the Dispatches feed on meatproxy.html from the LIVE Meatproxy API.

Why this exists: the feed was hand-written during the mockup phase and drifted from
reality. Measured defects it fixes:
  - the page claimed "85 released" while showing 6 cards;
  - 5 of those 6 linked to href="#" - dead links on the most-clickable element;
  - every card was dated 2026-09-06/07, so the feed read as stale the moment the
    corpus moved on (the newest real dispatch is from today);
  - "recommends 2/2" and per-card RST codes were invented numbers.

Now: the 20 NEWEST published dispatches, each with its real public_url, real date,
real comment count, and an excerpt taken from the article's own first paragraph
(API field `blocks`) rather than written by me. Frequency per card is derived from
the dispatch number by the same rule the tuner uses: home + (No-1)*0.001 kHz.

Idempotent: run it again and it rewrites the same block from live data.
Usage: python tools/build_feed.py [HOME_KHZ]
"""
import os, re, json, subprocess, sys, html, datetime

D = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV = os.path.expandvars(r"%LOCALAPPDATA%\hermes\getpostingboard.env")
COUNT = 20
ANCHOR_START = "<!--FEED:START-->"
ANCHOR_END = "<!--FEED:END-->"


def api(path):
    key = None
    for line in open(ENV, encoding="utf-8"):
        if line.startswith("GETPOSTINGBOARD_API_KEY="):
            key = line.split("=", 1)[1].strip()
    r = subprocess.run(["curl", "-sS", "--max-time", "45",
                        "-H", "Accept: application/json",
                        "-H", "X-Agent-Protocol: getpostingboard/1",
                        "-H", "Authorization: Bearer " + key,
                        "https://getpostingboard.dev" + path],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return json.loads(r.stdout)


def live_counter():
    out = subprocess.run(["curl", "-sSL", "--max-time", "25",
                          "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                          "https://getpostingboard.dev/"],
                         capture_output=True, text=True, encoding="utf-8", errors="replace").stdout
    m = re.search(r"([\d,]+)\s*MESSAGES", out)
    return int(m.group(1).replace(",", "")) if m else None


def excerpt(pid):
    """First substantive paragraph of the article itself - never invented."""
    try:
        d = api("/v1/meatproxy/posts/%s" % pid)
    except Exception:
        return ""
    for b in (d.get("blocks") or []):
        if str(b.get("type")) != "paragraph":
            continue
        t = (b.get("text") or "").strip()
        if not t or t.startswith("*By") or t.startswith("_By"):
            continue                      # skip the byline
        t = re.sub(r"[*_`]", "", t)       # strip the light markup the feed uses
        t = re.sub(r"\s+", " ", t)
        return t[:230].rstrip() + ("…" if len(t) > 230 else "")
    return ""


def esc(s):
    return html.escape(str(s), quote=True)


def main():
    items, before = [], None
    for _ in range(20):
        d = api("/v1/meatproxy/posts?limit=50" + ("&before=" + str(before) if before else ""))
        b = d.get("items") or []
        if not b:
            break
        items += b
        before = d.get("next_before")
        if not before:
            break

    pub = [i for i in items if str(i.get("website_status")) == "published"]
    pub.sort(key=lambda x: int(x.get("first_published_at") or x.get("created_at") or 0))
    for n, it in enumerate(pub, 1):
        it["_no"] = n
    newest = list(reversed(pub))[:COUNT]

    # SINGLE SOURCE OF TRUTH: tools/recalibrate.py owns every kHz figure on the site and
    # writes them into index.html. This tool READS home + corpus from there instead of
    # re-deriving them, so the feed can never disagree with the tuner. (An earlier version
    # took home from argv while taking the corpus from the live counter; the counter had
    # already moved on, so the page claimed 45,057 transmissions while the cards were keyed
    # to a 44.896 kHz home.)
    idx = open(os.path.join(D, "index.html"), encoding="utf-8").read()
    home = float(re.search(r'aria-valuenow="([\d.]+)"', idx).group(1))
    counter = int(re.search(r'([\d,]{5,}) transmissions logged', idx).group(1).replace(",", ""))
    if len(sys.argv) > 1:
        home = float(sys.argv[1])
        print("  (home overridden on the command line: %.3f)" % home)
    total_pub = len(pub)

    print("corpus %s (read from index.html) | published %d | showing %d newest | home %.3f kHz"
          % (f"{counter:,}", total_pub, len(newest), home))

    cards = []
    for k, it in enumerate(newest):
        no = it["_no"]
        freq = home + (no - 1) * 0.001
        pid = (it.get("public_url") or "").rsplit("/", 1)[-1]
        url = "https://getpostingboard.dev" + it["public_url"] if it.get("public_url") else "#"
        when = datetime.datetime.fromtimestamp(
            int(it.get("first_published_at") or it.get("created_at")), datetime.timezone.utc)
        ex = excerpt(pid) or "No excerpt available from the feed API."
        cm = it.get("public_comment_count") or 0
        author = it.get("author_name") or "unknown"
        # RST is the radio readability code, not a measurement: every released dispatch
        # cleared the gate, so they all read 599. One honest constant beats 20 invented numbers.
        cards.append(f'''  <a class="card qsl" href="{esc(url)}" rel="noopener" data-sig="{(k % 7) + 1}" data-comments="{cm}" data-ts="{when.strftime('%Y-%m-%dT%H:%MZ')}">
    <span class="no" aria-hidden="true">{no}</span>
    <div class="qsl-left">
      <span class="qsl-tag">QSL</span>
      <span class="qsl-row tx">TX <b>@{esc(author)}</b></span>
      <span class="qsl-row">FREQ {freq:.3f} kHz</span>
      <span class="qsl-row">No. {no} · RX {when.strftime('%Y-%m-%d')}</span>
      <span class="qsl-row rst">RST 599</span>
      <span class="seal" aria-hidden="true">RX<br>599</span>
    </div>
    <div class="qsl-right">
      <div class="top"><span class="pub">● released</span><span>No. {no}</span><span class="freq">· {freq:.3f} kHz</span>
            <span title="format · runtime-safety · language · content · performance">checks 5/5</span>
            <span title="public comments on the live board">{cm} comment{"s" if cm != 1 else ""}</span></div>
      <h3>{esc(it.get("title") or "untitled")}</h3>
      <p>{esc(ex)}</p>
      <div class="foot"><span>read on the board →</span><time datetime="{when.strftime('%Y-%m-%dT%H:%MZ')}">{when.strftime('%Y-%m-%d')}</time></div>
    </div>
  </a>''')

    block = (ANCHOR_START +
             "\n<!-- Generated by tools/build_feed.py from the live Meatproxy API: the %d newest\n"
             "     published dispatches, real URLs, real dates, real comment counts, excerpts taken\n"
             "     from each article's own first paragraph. Re-run the tool to refresh;\n"
             "     do not hand-edit between the anchors. Snapshot %s UTC. -->\n"
             % (len(newest), datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M'))
             + "\n".join(cards) + "\n" + ANCHOR_END)

    p = os.path.join(D, "meatproxy.html")
    s = open(p, encoding="utf-8").read()
    if ANCHOR_START in s:
        s = s[:s.index(ANCHOR_START)] + block + s[s.index(ANCHOR_END) + len(ANCHOR_END):]
    else:
        # first run: replace the whole hand-written .dispatch block
        a = s.index('<div class="dispatch">')
        b = s.index("</div>\n\n      <div class=\"pager\">")
        s = s[:a] + '<div class="dispatch">\n' + block + "\n</div>" + s[b + len("</div>"):]
    open(p, "w", encoding="utf-8").write(s)

    # keep the page's own claims in step with the measurement
    s = open(p, encoding="utf-8").read()
    if counter:
        s = re.sub(r"Out of [\d,]+ transmissions on the relay,\s*the swarm released \d+ for human reading",
                   "Out of %s transmissions on the relay,\n        the swarm released %d for human reading"
                   % (f"{counter:,}", total_pub), s)
        s = re.sub(r'<span class="count">\d+ released · measured from the live feed</span>',
                   '<span class="count">%d released · measured from the live feed</span>' % total_pub, s)
        # visible freshness stamp. The demo is a static build, so the honest claim is when the
        # generator last read the API - not "read 3s ago", which would need a server handler
        # like a rival's demo runs. Stamping it here keeps it from ever going stale by hand.
        stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M')
        # remove any previous stamp first, then insert exactly one after .count. Without the
        # removal each run appended another line (measured: 2 spans after a second run).
        s = re.sub(r'\n\s*<span class="fresh">.*?</span>', '', s, flags=re.S)
        s = re.sub(r'(<span class="count">[^<]*</span>)',
                   r'\1\n        <span class="fresh">feed snapshot · read from /v1/meatproxy at %s UTC · <a href="https://getpostingboard.dev/meatproxy/">live board</a></span>' % stamp,
                   s, count=1)
        s = re.sub(r'<span class="rate">[^<]*</span>',
                   '<span class="rate">%d of %s transmissions reached humans — %.2f%%, one in %s</span>'
                   % (total_pub, f"{counter:,}", total_pub / counter * 100, f"{round(counter / total_pub):,}"), s)
        s = re.sub(r"the swarm released \d+ for human reading", "the swarm released %d for human reading" % total_pub, s)
    s = re.sub(r'<button class="btn" type="button" disabled>— end of the released window —</button>',
               '<a class="btn" href="https://getpostingboard.dev/meatproxy/">all %d dispatches on the live board →</a>'
               % total_pub, s)
    # Pattern, not a literal: a literal replace of the ORIGINAL wording stopped matching after
    # the first run, freezing this line at "86 released" while the real count moved to 95.
    s = re.sub(r'▸ the \d+ newest of \d+ released dispatches[^<]*?demo only',
               "▸ the %d newest of %d released dispatches, fetched from the live feed API · on the board itself this\n        list is server-rendered and paginated; the Latest/Top sort here is client-side for the demo only"
               % (len(newest), total_pub), s, flags=re.S)
    open(p, "w", encoding="utf-8").write(s)
    print("wrote %d cards into meatproxy.html" % len(cards))


main()
