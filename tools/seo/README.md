# SEO tooling

Everything search- and share-related is generated from **one config** in `apply_seo.py`.
No build step is added to the site itself — these are maintainer scripts (Python 3, Pillow for images).

```bash
python3 tools/seo/apply_seo.py        # (re)write head blocks, links, sitemap, robots, manifest, 404, llms.txt
python3 tools/seo/validate_seo.py     # fail on any broken rule (titles, canonicals, JSON-LD, links, images…)
python3 tools/seo/make_assets.py      # regenerate og-image.jpg + app icons
```

The apply script is **idempotent** (byte-identical output on every run) and writes only
*outside* the generated `qa-i18n:start … qa-i18n:end` region, so it survives `tools/install-engine.js`.
Run it again after regenerating the pages.

## Images for Google Images

Google Images only indexes pictures that are embedded in a page with a real `<img>`. The site used to have none
(the previews were only in the GitHub README), so `apply_seo.py` now inserts a **Gallery** section into both landing
pages (before the CTA) from the `GALLERY` list in its config: descriptive file names, alt text, captions,
`width`/`height`, `srcset` with a 1200px variant, plus `ImageObject` JSON-LD and `<image:image>` sitemap entries.
To add a picture: put `name.jpg` and `name-1200.jpg` in `images/`, add a line to `GALLERY`, re-run the script.
The gallery texts are translated into all 13 app languages in `gallery_i18n.json` (alt texts stay English for search engines); a new picture needs a `landing.gallery.cN` caption there for each language.

## URL strategy

| Page | Canonical | Why |
|---|---|---|
| `index.html` (splash, JS redirect) | `index_dark.html` | the splash only redirects; consolidate on the real landing page |
| `index_dark.html` / `index_light.html` | `index_dark.html` | dark/light are the same content |
| `simulator_dark.html` / `_light` | `simulator_dark.html` | same app, two themes |
| `nucleus_explorer.html` / `_light` | `nucleus_explorer.html` | same app, two themes |

Only canonical pages are in `sitemap.xml` and only canonical pages carry JSON-LD.
Languages share one URL (chosen client-side), so **no `hreflang`** is emitted — hreflang requires one URL per language.

## What changed vs. the original pages

* Fixed: `og:image` pointed to a non-existent `images/preview.png`; `canonical`/`og:url` on the dark landing page pointed to a non-existent `index_dark_v4.html`.
* Added: unique title + meta description, canonical, robots, full Open Graph/Twitter cards (1200×630 image), JSON-LD (`WebSite`, `Person`, `WebApplication`, `ImageObject`, `BreadcrumbList`).
* Added: an accessible text alternative (`h1`, summary, links) to the canvas-only app pages, so they have real indexable text.
* Added: crawlable links (landing footer + Nucleus Explorer section → `nucleus_explorer.html`, which previously had no inbound link from the landing page); `javascript:` theme toggles now have real `href`s.
* Added: `preconnect` hints for fonts/CDN, web manifest + touch icons, `404.html` (noindex), `llms.txt`.

## i18n note

English title/description are bound to existing i18n keys. `apply_seo.py` registers the new English
values with `QA_I18N.add('en', …)` (outside the generated block). If you also edit `i18n/en.js`,
set these keys there and the override becomes a no-op:

`landing.meta.quantum_atom_built_by_md`, `landing.meta.a_free_browser_based_3d`,
`sim.meta.quantum_atom_simulator`, `nucleus.meta.nucleus_explorer_quantum_atom`.

## After deploying (one-time checklist)

1. **Search Console**: add the URL-prefix property `https://nazat02.github.io/Quantum-Atom/`, submit `sitemap.xml`, request indexing for the 3 canonical URLs.
2. **Bing Webmaster Tools**: import from Search Console.
3. **GitHub repo → About**: set a description (reuse the meta description) and topics, e.g. `quantum-mechanics`, `atomic-orbitals`, `chemistry`, `physics-simulation`, `webgl`, `threejs`, `education`, `vsepr`, `periodic-table`, `3d-visualization`.
4. Check share cards with the Facebook Sharing Debugger / LinkedIn Post Inspector; validate JSON-LD at validator.schema.org.
5. Running on a **custom domain root** is the single biggest SEO upgrade: `robots.txt` is only honoured at the host root, and GitHub *project* pages (`user.github.io/repo/`) cannot serve one there. Pass `--base https://your-domain/` to `apply_seo.py`.

## Known limits / next steps

* **Page weight is the main remaining SEO cost.** Every page inlines ~1.9 MB of translation data (all 9 languages), so each HTML file is 2–4 MB. Measured: the translation block is ~1.97 MB per page while the English dictionary alone is ~0.1 MB. Moving the other dictionaries to lazily-loaded `i18n/<lang>.js` files (the engine already has `loadScript`) would save about 1.8 MB per page and should improve Core Web Vitals. Not done here because it changes the generated engine, and `tools/install-engine.js` / `i18n/en.js` are not in this archive.
* three.js is a render-blocking `<script>` from cdnjs without SRI; pin a verified SRI hash once it can be checked.
* The landing copy says “140+ curated molecules”, the stats counter and README say 52. Pick one number; new SEO copy deliberately avoids it.
* The landing pages have no `<main>` landmark. Adding one means wrapping all sections, which I did not do without visual-regression coverage of the animated landing pages.
