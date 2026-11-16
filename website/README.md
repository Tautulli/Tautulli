# Tautulli docs

The Tautulli documentation site, built with Docusaurus 3. It needs Node 20+ and Python 3.11+.

## Run it locally

```
cd website
npm ci
npm start
```

The site opens at http://localhost:3000. Search works only in a production build.

## Build

Run `npm run build`, then `npm run serve` to preview it. `build/` holds the static site. `DOCS_URL` and `DOCS_BASE_URL` set the site URL and base path. Give `serve` the same values as `build`.

## API reference page

`api-reference.py` writes `docs/api-reference.md` from the docstrings in `plexpy/api2.py` and `plexpy/webserve.py` before every start and build. Git ignores the generated file. Edit the docstrings to change the page.
