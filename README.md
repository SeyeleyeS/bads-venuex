# BADS: Bay Area Daily Sync

Static site for **bamedia.agency**: the SF Bay Area Urban Concierge brief, refreshed every 8 hours.
Plain HTML/CSS, no build step, served by GitHub Pages from `main` at `/`.

Publish a new brief (renders it, updates `index.html` and `archive/`, commits and pushes):

    python3 publish.py /path/to/bayareadailysync-YYYY-MM-DD-HHMM.md

Requires `python-markdown` (`pip install --user markdown`). Sources are kept in `briefs/`.
Built from public sources. Snapshot, not real-time; check official links before you go.

## App (PWA), feed and email updates

- `manifest.webmanifest`, `sw.js`, `assets/app.js`, `assets/icons/`: installable app. The service worker is
  network-first for pages (new briefs show immediately) and keeps the shell + briefs you've opened for offline reading.
- `feed.xml`: RSS 2.0, last 20 briefs with full HTML in `content:encoded`. Rebuilt on every publish.
- Email signup: set `signup.form_action` in `site.json` to the provider's embed form URL (and `email_field` if the
  provider doesn't use `email`), then run `python3 publish.py --rebuild`. While it is empty, no form is shown.
- `python3 publish.py --rebuild` re-renders every page from `briefs/`.
