#!/usr/bin/env python3
"""Publish a BayAreaDailySync brief to the BADS static site (https://bamedia.agency/bads/).

Usage:
  python3 publish.py <brief.md> [<brief.md> ...] [--archive-only] [--no-push]
  python3 publish.py --rebuild [--no-push]   # re-render every page + feed from briefs/

Also writes feed.xml (RSS 2.0, last 20 briefs) and offline.html. Every page links
the PWA manifest, service worker (assets/app.js) and the install hint.
Email signup: set "signup.form_action" in site.json to the provider's form URL
(Buttondown / follow.it / MailerLite / Kit). While it is empty the form is not shown.

Layout: the repo root is the BAMedia company site (/ and /law/, static, not touched
here). BADS lives in the "out_dir" from site.json (default "bads", served at /bads/).
For each brief: copies the source to briefs/<basename>.md (repo root) and renders
bads/archive/<basename>.html. Then (unless --archive-only) rewrites bads/index.html
with the LAST brief given, regenerates bads/archive/index.html (newest first),
bads/feed.xml (+ a copy at /feed.xml for old subscribers), redirect stubs at the old
root URLs (/archive/...), and runs git add / commit / push to main (unless --no-push).
"""
import argparse, html, json, os, re, shutil, subprocess, sys
from datetime import datetime, timezone
from email.utils import format_datetime
from zoneinfo import ZoneInfo

try:
    import markdown
except ImportError:
    sys.exit("python-markdown missing: pip install --user --break-system-packages markdown")

ROOT = os.path.dirname(os.path.abspath(__file__))
SITE_TITLE = "BADS: Bay Area Daily Sync"
TAGLINE = "Your SF Bay Area brief, refreshed every 8 hours."
FOOTER = "Built from public sources. Snapshot, not real-time; check official links before you go."
CONFIG = json.load(open(os.path.join(ROOT, "site.json"), encoding="utf-8"))
SITE_URL = CONFIG.get("site_url", "https://bamedia.agency/bads/").rstrip("/") + "/"
OUT = os.path.join(ROOT, CONFIG.get("out_dir", "bads"))  # where BADS pages/feed are written
BRIEFS = os.path.join(ROOT, "briefs")                     # markdown sources stay at repo root
FEED_ITEMS = 20
TZ = ZoneInfo("America/Los_Angeles")

URL_RE = re.compile(r'(?<![(<\["\'=])(https?://[^\s<>()\[\]"]+)')

def autolink(text):
    out = []
    for line in text.split("\n"):
        def rep(m):
            url = m.group(1)
            trail = ""
            while url and url[-1] in ".,;:!?*_":
                trail = url[-1] + trail
                url = url[:-1]
            return f"<{url}>{trail}"
        out.append(URL_RE.sub(rep, line))
    return "\n".join(out)

LIST_RE = re.compile(r'^\s*([-*+]|\d+[.)])\s+')

def fix_lists(text):
    """Python-markdown needs a blank line before a list that follows a paragraph."""
    lines, out = text.split("\n"), []
    for i, line in enumerate(lines):
        if LIST_RE.match(line) and out and out[-1].strip() and not LIST_RE.match(out[-1]) \
                and not out[-1].startswith("#") and not out[-1].startswith("    "):
            out.append("")
        out.append(line)
    return "\n".join(out)

def render_md(text):
    text = fix_lists(autolink(text))
    body = markdown.markdown(text, extensions=["extra", "sane_lists", "nl2br"])
    # open external links in a new tab
    body = re.sub(r'<a href="(https?://[^"]+)"', r'<a href="\1" target="_blank" rel="noopener"', body)
    return body

def meta(md_text, basename):
    lines = [l.strip() for l in md_text.splitlines() if l.strip()]
    title = next((l.lstrip("# ").strip() for l in lines if l.startswith("# ")), basename)
    sub = ""
    for l in lines:
        if not l.startswith("#"):
            sub = re.sub(r"[*_]", "", l)
            break
    return title, sub

def signup_html(prefix):
    """Follow section: RSS always; email form only once site.json signup.form_action is set."""
    su = CONFIG.get("signup", {}) or {}
    action = (su.get("form_action") or "").strip()
    rss = f'<a href="{prefix}feed.xml">RSS feed</a>'
    if action:
        field = html.escape(su.get("email_field") or "email")
        hidden = "".join(f'<input type="hidden" name="{html.escape(k)}" value="{html.escape(str(v))}">'
                         for k, v in (su.get("hidden_fields") or {}).items())
        prov = html.escape(su.get("provider_name") or "our email provider")
        form = f"""<div class="signup">
  <p>Get each new brief by email. You'll get a confirmation email first; unsubscribe any time.</p>
  <form action="{html.escape(action)}" method="post" target="_blank">
    <label class="fine" for="bads-email">Email address</label>
    <input id="bads-email" type="email" name="{field}" placeholder="you@example.com" required autocomplete="email">{hidden}
    <button type="submit">Subscribe</button>
  </form>
  <p class="fine">Emails are sent by {prov}. Prefer a reader app? Use the {rss}.</p>
</div>"""
    else:
        # EMAIL SIGNUP PLACEHOLDER: hidden until site.json "signup.form_action" is set.
        form = f"""<!-- email signup placeholder: set signup.form_action in site.json, then run publish.py --rebuild -->
<p>Follow new briefs in any reader app with the {rss}, or install BADS on your phone (see the tip at the top).</p>"""
    return f'<section class="follow" id="follow"><h2>Get updates</h2>{form}</section>'

def page(title, body, prefix, active):
    nav_home = "current" if active == "home" else ""
    nav_arch = "current" if active == "archive" else ""
    return f"""<!doctype html>
<html lang="en" data-root="{prefix or './'}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(TAGLINE)}">
<meta name="theme-color" content="#0b6e99" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#121417" media="(prefers-color-scheme: dark)">
<link rel="manifest" href="{prefix}manifest.webmanifest">
<link rel="icon" type="image/png" sizes="32x32" href="{prefix}assets/icons/favicon-32.png">
<link rel="apple-touch-icon" href="{prefix}assets/icons/apple-touch-icon.png">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="BADS">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<link rel="alternate" type="application/rss+xml" title="{html.escape(SITE_TITLE)}" href="{SITE_URL}feed.xml">
<link rel="stylesheet" href="{prefix}assets/style.css">
<script src="{prefix}assets/app.js" defer></script>
</head>
<body>
<header class="site">
  <div class="wrap">
    <a class="brand" href="{prefix}index.html">{html.escape(SITE_TITLE)}</a>
    <p class="tagline">{html.escape(TAGLINE)}</p>
    <nav><a class="{nav_home}" href="{prefix}index.html">Latest</a> <a class="{nav_arch}" href="{prefix}archive/index.html">Archive</a> <a href="{prefix}index.html#follow">Get updates</a> <a href="{prefix}feed.xml">RSS</a></nav>
  </div>
</header>
<main class="wrap">
<div class="install-hint" id="install-hint" hidden><span class="install-text"></span><button class="install-btn" type="button" hidden>Install</button><button class="install-close" type="button" aria-label="Dismiss">&times;</button></div>
{body}
{signup_html(prefix)}
</main>
<footer class="site"><div class="wrap"><p>{html.escape(FOOTER)}</p><p class="fine">BADS is a brand of <a href="{prefix}../">Bay Area Media</a>.</p></div></footer>
</body>
</html>
"""

def build_brief(src):
    base = os.path.splitext(os.path.basename(src))[0]
    dst_md = os.path.join(BRIEFS, base + ".md")
    if os.path.abspath(src) != os.path.abspath(dst_md):
        shutil.copyfile(src, dst_md)
    text = open(dst_md, encoding="utf-8").read()
    title, sub = meta(text, base)
    body = '<article class="brief">' + render_md(text) + "</article>"
    archive_body = body + '<p class="back"><a href="index.html">&larr; All briefs</a></p>'
    with open(os.path.join(OUT, "archive", base + ".html"), "w", encoding="utf-8") as f:
        f.write(page(f"{title} · {sub[:60]} · BADS", archive_body, "../", "archive"))
    return base, title, sub, body

def write_index(base, title, sub, body):
    note = f'<p class="stamp">Latest brief · <a href="archive/{base}.html">permalink</a> · <a href="archive/index.html">past briefs</a></p>'
    with open(os.path.join(OUT, "index.html"), "w", encoding="utf-8") as f:
        f.write(page(SITE_TITLE, note + body, "", "home"))

def write_archive_index():
    items = []
    for fn in sorted(os.listdir(BRIEFS), reverse=True):
        if not fn.endswith(".md"):
            continue
        base = fn[:-3]
        if not os.path.exists(os.path.join(OUT, "archive", base + ".html")):
            continue
        title, sub = meta(open(os.path.join(BRIEFS, fn), encoding="utf-8").read(), base)
        items.append(f'<li><a href="{base}.html">{html.escape(sub or title)}</a><span class="fn">{html.escape(base)}</span></li>')
    body = "<h1>Archive</h1><p>Every published brief, newest first.</p><ul class=\"archive\">" + "\n".join(items) + "</ul>"
    with open(os.path.join(OUT, "archive", "index.html"), "w", encoding="utf-8") as f:
        f.write(page("Archive · BADS", body, "../", "archive"))

def brief_time(base):
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})-(\d{2})(\d{2})$", base)
    if m:
        y, mo, d, h, mi = map(int, m.groups())
        return datetime(y, mo, d, h, mi, tzinfo=TZ)
    return datetime.fromtimestamp(os.path.getmtime(os.path.join(BRIEFS, base + ".md")), timezone.utc)

def cdata(s):
    return "<![CDATA[" + s.replace("]]>", "]]]]><![CDATA[>") + "]]>"

def write_feed():
    bases = sorted((fn[:-3] for fn in os.listdir(BRIEFS) if fn.endswith(".md")), reverse=True)
    bases = [b for b in bases if os.path.exists(os.path.join(OUT, "archive", b + ".html"))][:FEED_ITEMS]
    items = []
    for b in bases:
        text = open(os.path.join(BRIEFS, b + ".md"), encoding="utf-8").read()
        title, sub = meta(text, b)
        link = f"{SITE_URL}archive/{b}.html"
        body = render_md(text)
        body = re.sub(r'(href|src)="(?!https?:|mailto:|#)([^"]+)"', lambda m: f'{m.group(1)}="{SITE_URL}{m.group(2).lstrip("./")}"', body)
        items.append(f"""  <item>
    <title>{html.escape(title + (" · " + sub if sub else ""))}</title>
    <link>{link}</link>
    <guid isPermaLink="true">{link}</guid>
    <pubDate>{format_datetime(brief_time(b))}</pubDate>
    <description>{html.escape(sub or title)}</description>
    <content:encoded>{cdata(body)}</content:encoded>
  </item>""")
    last = format_datetime(brief_time(bases[0])) if bases else format_datetime(datetime.now(timezone.utc))
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/" xmlns:atom="http://www.w3.org/2005/Atom">
<channel>
  <title>{html.escape(SITE_TITLE)}</title>
  <link>{SITE_URL}</link>
  <atom:link href="{SITE_URL}feed.xml" rel="self" type="application/rss+xml"/>
  <description>{html.escape(TAGLINE)}</description>
  <language>en-us</language>
  <lastBuildDate>{last}</lastBuildDate>
  <ttl>60</ttl>
  <image><url>{SITE_URL}assets/icons/icon-192.png</url><title>{html.escape(SITE_TITLE)}</title><link>{SITE_URL}</link></image>
{chr(10).join(items)}
</channel>
</rss>
"""
    with open(os.path.join(OUT, "feed.xml"), "w", encoding="utf-8") as f:
        f.write(xml)
    print(f"feed.xml -> {len(items)} items")

def write_offline():
    body = '<h1>You are offline</h1><p>This page has not been saved on this device yet. Briefs you have opened before still work offline. Try the <a href="index.html">latest brief</a> or the <a href="archive/index.html">archive</a>.</p>'
    with open(os.path.join(OUT, "offline.html"), "w", encoding="utf-8") as f:
        f.write(page("Offline · BADS", body, "", "home"))

LEGACY_STUB = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>Moved · BADS</title>
<meta name="robots" content="noindex">
<link rel="canonical" href="{url}">
<meta http-equiv="refresh" content="0; url={url}">
<script>location.replace("{url}" + location.hash);</script>
</head><body><p>BADS has moved to <a href="{url}">{url}</a>.</p></body></html>
"""

def write_legacy():
    """BADS used to live at the site root. Keep old URLs working: redirect stubs for
    /archive/*.html and /offline.html, and a copy of the feed at /feed.xml."""
    if os.path.abspath(OUT) == os.path.abspath(ROOT):
        return
    rel = os.path.relpath(OUT, ROOT).replace(os.sep, "/") + "/"
    legacy_arch = os.path.join(ROOT, "archive")
    os.makedirs(legacy_arch, exist_ok=True)
    for fn in os.listdir(os.path.join(OUT, "archive")):
        if fn.endswith(".html"):
            target = SITE_URL + "archive/" + fn
            with open(os.path.join(legacy_arch, fn), "w", encoding="utf-8") as f:
                f.write(LEGACY_STUB.format(url=target))
    with open(os.path.join(ROOT, "offline.html"), "w", encoding="utf-8") as f:
        f.write(LEGACY_STUB.format(url=SITE_URL + "offline.html"))
    shutil.copyfile(os.path.join(OUT, "feed.xml"), os.path.join(ROOT, "feed.xml"))
    print(f"legacy redirects -> /archive/*.html, /offline.html, /feed.xml copy (BADS at /{rel})")

def git(*args):
    print("+ git", " ".join(args))
    subprocess.run(["git", "-C", ROOT, *args], check=True)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("briefs", nargs="*")
    ap.add_argument("--rebuild", action="store_true", help="re-render every brief in briefs/ (newest becomes index.html)")
    ap.add_argument("--archive-only", action="store_true", help="add to archive without changing index.html")
    ap.add_argument("--no-push", action="store_true")
    a = ap.parse_args()
    if a.rebuild:
        a.briefs = [os.path.join(BRIEFS, fn) for fn in sorted(os.listdir(BRIEFS)) if fn.endswith(".md")]
    if not a.briefs:
        ap.error("give at least one brief, or --rebuild")
    built = None
    for src in a.briefs:
        if not os.path.isfile(src):
            sys.exit(f"not found: {src}")
        built = build_brief(src)
        print("rendered archive/%s.html" % built[0])
    if not a.archive_only:
        write_index(*built)
        print("index.html ->", built[0])
    write_archive_index()
    write_feed()
    write_offline()
    write_legacy()
    if a.no_push:
        return
    git("add", "-A")
    if subprocess.run(["git", "-C", ROOT, "diff", "--cached", "--quiet"]).returncode == 0:
        print("nothing to commit")
        return
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    git("commit", "-q", "-m", ("Rebuild site" if a.rebuild else f"Publish {built[0]}") + f" ({stamp})")
    git("push", "-q", "origin", "HEAD:main")
    print("pushed to main")

if __name__ == "__main__":
    main()
