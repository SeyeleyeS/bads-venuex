#!/usr/bin/env python3
"""Publish a BayAreaDailySync brief to the BADS static site (bads.venuex.net).

Usage:
  python3 publish.py <brief.md> [<brief.md> ...] [--archive-only] [--no-push]

For each brief: copies the source to briefs/<basename>.md and renders
archive/<basename>.html. Then (unless --archive-only) rewrites index.html with
the LAST brief given, regenerates archive/index.html (newest first), and runs
git add / commit / push to main (unless --no-push).
"""
import argparse, html, os, re, shutil, subprocess, sys
from datetime import datetime, timezone

try:
    import markdown
except ImportError:
    sys.exit("python-markdown missing: pip install --user --break-system-packages markdown")

ROOT = os.path.dirname(os.path.abspath(__file__))
SITE_TITLE = "BADS: Bay Area Daily Sync"
TAGLINE = "Your SF Bay Area brief, refreshed every 8 hours."
FOOTER = "Built from public sources. Snapshot, not real-time; check official links before you go."

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

def page(title, body, prefix, active):
    nav_home = "current" if active == "home" else ""
    nav_arch = "current" if active == "archive" else ""
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(TAGLINE)}">
<link rel="stylesheet" href="{prefix}assets/style.css">
</head>
<body>
<header class="site">
  <div class="wrap">
    <a class="brand" href="{prefix}index.html">{html.escape(SITE_TITLE)}</a>
    <p class="tagline">{html.escape(TAGLINE)}</p>
    <nav><a class="{nav_home}" href="{prefix}index.html">Latest</a> <a class="{nav_arch}" href="{prefix}archive/index.html">Archive</a></nav>
  </div>
</header>
<main class="wrap">
{body}
</main>
<footer class="site"><div class="wrap"><p>{html.escape(FOOTER)}</p></div></footer>
</body>
</html>
"""

def build_brief(src):
    base = os.path.splitext(os.path.basename(src))[0]
    dst_md = os.path.join(ROOT, "briefs", base + ".md")
    if os.path.abspath(src) != os.path.abspath(dst_md):
        shutil.copyfile(src, dst_md)
    text = open(dst_md, encoding="utf-8").read()
    title, sub = meta(text, base)
    body = '<article class="brief">' + render_md(text) + "</article>"
    archive_body = body + '<p class="back"><a href="index.html">&larr; All briefs</a></p>'
    with open(os.path.join(ROOT, "archive", base + ".html"), "w", encoding="utf-8") as f:
        f.write(page(f"{title} · {sub[:60]} · BADS", archive_body, "../", "archive"))
    return base, title, sub, body

def write_index(base, title, sub, body):
    note = f'<p class="stamp">Latest brief · <a href="archive/{base}.html">permalink</a> · <a href="archive/index.html">past briefs</a></p>'
    with open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8") as f:
        f.write(page(SITE_TITLE, note + body, "", "home"))

def write_archive_index():
    items = []
    for fn in sorted(os.listdir(os.path.join(ROOT, "briefs")), reverse=True):
        if not fn.endswith(".md"):
            continue
        base = fn[:-3]
        if not os.path.exists(os.path.join(ROOT, "archive", base + ".html")):
            continue
        title, sub = meta(open(os.path.join(ROOT, "briefs", fn), encoding="utf-8").read(), base)
        items.append(f'<li><a href="{base}.html">{html.escape(sub or title)}</a><span class="fn">{html.escape(base)}</span></li>')
    body = "<h1>Archive</h1><p>Every published brief, newest first.</p><ul class=\"archive\">" + "\n".join(items) + "</ul>"
    with open(os.path.join(ROOT, "archive", "index.html"), "w", encoding="utf-8") as f:
        f.write(page("Archive · BADS", body, "../", "archive"))

def git(*args):
    print("+ git", " ".join(args))
    subprocess.run(["git", "-C", ROOT, *args], check=True)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("briefs", nargs="+")
    ap.add_argument("--archive-only", action="store_true", help="add to archive without changing index.html")
    ap.add_argument("--no-push", action="store_true")
    a = ap.parse_args()
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
    if a.no_push:
        return
    git("add", "-A")
    if subprocess.run(["git", "-C", ROOT, "diff", "--cached", "--quiet"]).returncode == 0:
        print("nothing to commit")
        return
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    git("commit", "-q", "-m", f"Publish {built[0]} ({stamp})")
    git("push", "-q", "origin", "HEAD:main")
    print("pushed to main")

if __name__ == "__main__":
    main()
