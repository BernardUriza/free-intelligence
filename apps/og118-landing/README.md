# og118.ai — coming soon

Static, self-contained "coming soon" landing for the domain **og118.ai**.

The whole page lives in a single file: `index.html` (HTML + inline CSS, no
JS, no build step, no external assets, no fonts, no CDNs). Point your static
host at this directory and serve `index.html`.

## Serve locally

```bash
python3 -m http.server 8080
# then open http://localhost:8080
```

Or just open `index.html` directly in a browser.

## Deploy

Drop `index.html` on any static host (Cloudflare Pages, Netlify, S3 +
CloudFront, GitHub Pages, plain nginx) and point the og118.ai DNS at it.
Nothing to install or compile.
