# Tautulli docs

The Tautulli documentation site, built with Docusaurus 3. It needs Node 20+ and Python 3.11+.

## Run it locally

```
cd website
npm ci
npm start
```

The site opens at http://localhost:3000. Search works only in a production build.

## Build and publish

Run `npm run build`, then `npm run serve` to preview it. `build/` holds the static site. `DOCS_URL` and `DOCS_BASE_URL` set the site URL and base path. Give `serve` the same values as `build`.
Cloudflare Pages builds this directory when a push changes the docs. `master` publishes https://docs.tautulli.com. `nightly` publishes https://docs-nightly.tautulli.com with a notice bar and `noindex`. Other branches get a preview URL with `noindex`. `.nvmrc` sets the Node version for that build. `static/_redirects` maps the old GitBook paths.

## Generated pages

`generate-docs.py` writes two pages before every start and build. Git ignores both.

- `docs/api-reference.md` comes from the docstrings in `plexpy/api2.py` and `plexpy/webserve.py`.
- `docs/exporter-guide.md` is `docs/_exporter-guide.md` with the field tables from `build_export_docs()` in `plexpy/exporter.py`. Edit the prose in `docs/_exporter-guide.md`.
