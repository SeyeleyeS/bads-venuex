# BADS: Bay Area Daily Sync

Static site for **bads.venuex.net**: the SF Bay Area Urban Concierge brief, refreshed every 8 hours.
Plain HTML/CSS, no build step, served by GitHub Pages from `main` at `/`.

Publish a new brief (renders it, updates `index.html` and `archive/`, commits and pushes):

    python3 publish.py /path/to/bayareadailysync-YYYY-MM-DD-HHMM.md

Requires `python-markdown` (`pip install --user markdown`). Sources are kept in `briefs/`.
Built from public sources. Snapshot, not real-time; check official links before you go.
