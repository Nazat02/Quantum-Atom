#!/usr/bin/env python3
"""Quantum Atom — SEO layer.  Single source of truth for all search/share metadata.

Idempotent: every run first removes what a previous run wrote, then writes it again,
so the output only ever depends on the CONFIG below.  Safe to re-run after the
i18n engine regenerates the pages (our block lives *outside* the generated
`qa-i18n:start … qa-i18n:end` region).

What it manages
  * <head> block per page   description, robots, canonical, Open Graph, Twitter,
                            manifest/touch-icon, preconnects, JSON-LD, English i18n overrides
  * crawlable internal links   landing footer + Nucleus Explorer section
  * text alternative for the canvas apps (h1 + summary + nav) — real, accurate copy
  * sitemap.xml, robots.txt, 404.html, site.webmanifest, llms.txt

Usage:  python3 tools/seo/apply_seo.py [--base https://example.com/path/] [--lastmod YYYY-MM-DD]
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# ───────────────────────────── CONFIG ─────────────────────────────
BASE = "https://nazat02.github.io/Quantum-Atom/"       # public URL of the site root (trailing slash!)
REPO = "https://github.com/nazat02/Quantum-Atom"
SITE_NAME = "Quantum Atom"
AUTHOR_NAME = "Md. Shaikhul Hadis Nazat"
AUTHOR_URL = "https://github.com/nazat02"
LANGS = ["en", "ar", "bn", "zh-Hans", "ko", "ja", "it", "fr", "el"]
OG_LOCALES = ["ar_AR", "bn_BD", "zh_CN", "ko_KR", "ja_JP", "it_IT", "fr_FR", "el_GR"]
OG_IMAGE = "images/og-image.jpg"
OG_IMAGE_ALT = "Quantum Atom: 3D electron orbitals, molecules and nuclei running in the browser"
# Large mockups (real Diffuse-mode captures). Each one is shown in the landing-page gallery as a real <img>
# (Google Images only indexes pictures that are embedded in a page), listed in sitemap.xml and in the JSON-LD.
# (file, width, height, alt text, visible caption).  A "-1200" sibling of every file is used in srcset.
G = "images/quantum-atom-simulator-"
GALLERY = [
    (G + "3d-electron-cloud.jpg", 2400, 1350,
     "Quantum Atom Simulator showing a carbon atom as a glowing 3D electron cloud on desktop and a neon atom on a phone",
     "Quantum Atom Simulator on desktop and phone: the atom drawn as one soft probability cloud."),
    (G + "carbon-atom-diffuse-mode.jpg", 2400, 1600,
     "Carbon atom in the Quantum Atom Simulator, Diffuse mode: 2p electron cloud lobes in two colours around a glowing nucleus",
     "Carbon (Z = 6) in Diffuse mode. The two colours are the + and − signs of the wavefunction."),
    (G + "neon-atom-electron-orbitals.jpg", 2400, 1600,
     "Neon atom electron orbitals rendered as a 3D probability cloud in the Quantum Atom Simulator",
     "Neon, 1s² 2s² 2p⁶: a full second shell."),
    (G + "water-molecule-h2o.jpg", 2400, 1600,
     "Water molecule H2O in the Quantum Atom Simulator with its bent 104.5 degree geometry, shown on desktop and mobile",
     "Water, H₂O: the bent 104.5° shape with its electron cloud."),
    (G + "methane-molecule-ch4.jpg", 2400, 1600,
     "Methane molecule CH4 with tetrahedral geometry rendered as an electron cloud in the Quantum Atom Simulator",
     "Methane, CH₄: tetrahedral, 109.5°."),
    (G + "iron-atom-d-orbitals.jpg", 2400, 1600,
     "Iron atom with 26 electrons and its d orbitals shown as a dense 3D electron cloud in the Quantum Atom Simulator",
     "Iron, 26 electrons: the 3d orbitals fill in."),
    (G + "cloud-studio-controls.jpg", 2400, 1600,
     "Cloud Studio controls in the Quantum Atom Simulator: sliders for density, spread, dot size, brightness and glow of the electron cloud",
     "Cloud Studio: tune density, spread, glow and jitter of the cloud live."),
    (G + "mobile-app-screens.jpg", 2400, 1800,
     "Quantum Atom Simulator on mobile: carbon atom, Cloud Studio controls and a water molecule on three phone screens",
     "The simulator on a phone. No install needed."),
    (G + "dark-and-light-themes.jpg", 2400, 1350,
     "Quantum Atom Simulator in dark theme and light theme showing the same neon atom",
     "Dark and light themes, same atom."),
]
SQUARE_IMAGE = (G + "app-square.jpg", 1600, 1600)
# Gallery texts in every language the app ships: {lang: {key: text}}. Keys: landing.gallery.eyebrow / .title / .body / .c1 … .c9
# (c1…c9 are the captions, in GALLERY order). Registered with QA_I18N.add() from the head block, so they switch with the
# language picker like the rest of the page. Alt texts stay English: they describe the picture for search engines.
GALLERY_I18N = json.loads((Path(__file__).resolve().parent / "gallery_i18n.json").read_text(encoding="utf-8"))
assert all(GALLERY_I18N["en"][f"landing.gallery.c{i + 1}"] == g[4] for i, g in enumerate(GALLERY)), "gallery_i18n.json: English captions differ from GALLERY"
SCREENSHOTS = [g[0] for g in GALLERY]
ROBOTS = "index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1"

DESC_SPLASH = ("Quantum Atom is a free 3D simulator of real electron orbitals for all 118 elements, "
               "molecules and nuclei. Runs in your browser, no install needed.")
DESC_LANDING = ("Free 3D atom simulator: see real electron orbitals for all 118 elements, molecule "
                "geometry and a nucleus zoom down to quarks. No install, in your browser.")
DESC_SIM = ("Explore real electron orbitals for all 118 elements, VSEPR molecule shapes, excited "
            "states and antimatter in a free interactive 3D simulator. No install.")
DESC_NUC = ("Zoom from a nucleus to its protons, neutrons, quarks and gluons in 3D. Toggle pion "
            "exchange and gluon fields for any element. Free in your browser.")

# kind: splash | landing | simulator | nucleus.   canonical: page this URL consolidates to.
# title_key / desc_key: existing i18n keys bound to <title>/<meta description> (None = static).
PAGES = {
    "index.html": dict(kind="splash", theme="dark", canonical="index_dark.html",
                       title="Quantum Atom — Free 3D Atom, Molecule & Nucleus Simulator",
                       title_key="landing.meta.quantum_atom", desc=DESC_SPLASH, desc_key="landing.meta.quantum_atom_built_by_md",
                       fonts=True),
    "index_dark.html": dict(kind="landing", theme="dark", canonical="index_dark.html",
                            title=None, title_key="landing.meta.quantum_atom_simulator_atoms_molecules",
                            desc=DESC_LANDING, desc_key="landing.meta.a_free_browser_based_3d", fonts=True),
    "index_light.html": dict(kind="landing", theme="light", canonical="index_dark.html",
                             title=None, title_key=None, desc=DESC_LANDING, desc_key=None, fonts=True),
    "simulator_dark.html": dict(kind="simulator", theme="dark", canonical="simulator_dark.html",
                                title="Quantum Atom Simulator — 3D Orbitals for All 118 Elements",
                                title_key="sim.meta.quantum_atom_simulator", desc=DESC_SIM, desc_key=None, cdn=True),
    "simulator_light.html": dict(kind="simulator", theme="light", canonical="simulator_dark.html",
                                 title="Quantum Atom Simulator — 3D Orbitals for All 118 Elements",
                                 title_key="sim.meta.quantum_atom_simulator", desc=DESC_SIM, desc_key=None, cdn=True),
    "nucleus_explorer.html": dict(kind="nucleus", theme="dark", canonical="nucleus_explorer.html",
                                  title="Nucleus Explorer — Zoom to Quarks in 3D | Quantum Atom",
                                  title_key="nucleus.meta.nucleus_explorer_quantum_atom", desc=DESC_NUC,
                                  desc_key=None, fonts=True),
    "nucleus_explorer_light.html": dict(kind="nucleus", theme="light", canonical="nucleus_explorer.html",
                                        title="Nucleus Explorer — Zoom to Quarks in 3D | Quantum Atom",
                                        title_key="nucleus.meta.nucleus_explorer_quantum_atom", desc=DESC_NUC,
                                        desc_key=None, fonts=True),
}
# ──────────────────────────── /CONFIG ─────────────────────────────

# javascript: hrefs are invisible to crawlers; give each a real URL and keep the JS behaviour via onclick.
LINK_FIXES = {
    "index_dark.html":      ("goLight()",    "index_light.html"),
    "index_light.html":     ("goDark()",     "index_dark.html"),
    "simulator_dark.html":  ("goLightSim()", "simulator_light.html"),
    "simulator_light.html": ("goDarkSim()",  "simulator_dark.html"),
}

GOOGLE_VERIFICATION = "80WZs4sna8xwVlGZO4XBKbq9D4BDc8HNBHKhvFKA_B0"  # Search Console ownership
E = lambda s: html.escape(s, quote=True)
SEO_BLOCK_RE = re.compile(r"\n<!-- qa-seo:start.*?<!-- qa-seo:end -->", re.S)
SR_RE = re.compile(r"\n<!-- qa-seo:sr:start -->.*?<!-- qa-seo:sr:end -->", re.S)
INS_RE = re.compile(r"<!-- qa-seo:ins:(\w+) -->.*?<!-- /qa-seo:ins -->", re.S)
I18N_END_RE = re.compile(r"<!--\s*qa-i18n:end\s*-->")
HEAD_TAG_RE = re.compile(
    r'<meta\b(?:[^>"]|"[^"]*")*\b(?:name|property)="(?:description|robots|og:[^"]+|twitter:[^"]+)"(?:[^>"]|"[^"]*")*>[ \t]*\n?')
CANON_RE = re.compile(r'<link\b[^>]*\brel="canonical"[^>]*>[ \t]*\n?')
SCRIPT_STYLE_RE = re.compile(r"(<script\b.*?</script>|<style\b.*?</style>)", re.S)


def url(rel: str) -> str:
    return BASE + rel


def sub_outside_code(text: str, pattern: re.Pattern, repl: str = "") -> str:
    """Apply a regex only to markup, never inside <script>/<style> bodies."""
    parts = SCRIPT_STYLE_RE.split(text)
    for i in range(0, len(parts), 2):
        parts[i] = pattern.sub(repl, parts[i])
    return "".join(parts)


def ld(obj: dict) -> str:
    s = json.dumps(obj, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return f'<script type="application/ld+json">{s}</script>'


# ───────────────────────── structured data ─────────────────────────
def g_person():
    return {"@type": "Person", "@id": BASE + "#author", "name": AUTHOR_NAME, "url": AUTHOR_URL, "sameAs": [AUTHOR_URL]}


def g_website():
    return {"@type": "WebSite", "@id": BASE + "#website", "url": url("index_dark.html"), "name": SITE_NAME,
            "description": DESC_LANDING, "inLanguage": "en", "publisher": {"@id": BASE + "#author"}}


def g_image():
    return {"@type": "ImageObject", "@id": BASE + "#og-image", "url": url(OG_IMAGE), "contentUrl": url(OG_IMAGE),
            "width": 1200, "height": 630, "caption": OG_IMAGE_ALT}


def g_gallery():
    return [{"@type": "ImageObject", "@id": url(f) + "#image", "url": url(f), "contentUrl": url(f), "width": w, "height": h,
             "name": cap, "caption": alt, "representativeOfPage": i == 0,
             "creator": {"@id": BASE + "#author"}, "creditText": AUTHOR_NAME,
             "copyrightNotice": "© " + AUTHOR_NAME, "license": REPO + "/blob/main/LICENSE",
             "acquireLicensePage": REPO} for i, (f, w, h, alt, cap) in enumerate(GALLERY)]


def g_simulator():
    return {"@type": "WebApplication", "@id": BASE + "#simulator", "name": "Quantum Atom Simulator",
            "url": url("simulator_dark.html"), "description": DESC_SIM,
            "applicationCategory": "EducationalApplication", "operatingSystem": "Any (web browser)",
            "browserRequirements": "Requires a modern browser with JavaScript and WebGL",
            "isAccessibleForFree": True, "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
            "image": [url(GALLERY[0][0]), url(GALLERY[7][0]), url(SQUARE_IMAGE[0])],      # 16:9, 4:3, 1:1
            "screenshot": [url(p) for p in SCREENSHOTS],
            "inLanguage": LANGS, "author": {"@id": BASE + "#author"}, "sameAs": [REPO],
            "audience": {"@type": "EducationalAudience", "educationalRole": ["student", "teacher"]},
            "featureList": [
                "3D electron orbitals for all 118 elements",
                "Molecule geometry from VSEPR theory, plus a build mode for other compounds",
                "Guided lessons on covalent bonds, VSEPR and the periodic table",
                "Excited states and antimatter mode",
                "Nucleus Explorer: zoom from nucleus to quarks",
                "Light and dark themes, colorblind-safe palette, 9 languages"]}


def g_nucleus():
    return {"@type": "WebApplication", "@id": BASE + "#nucleus-explorer", "name": "Nucleus Explorer",
            "url": url("nucleus_explorer.html"), "description": DESC_NUC,
            "applicationCategory": "EducationalApplication", "operatingSystem": "Any (web browser)",
            "browserRequirements": "Requires a modern browser with JavaScript and WebGL",
            "isAccessibleForFree": True, "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
            "image": url(OG_IMAGE), "inLanguage": LANGS, "author": {"@id": BASE + "#author"},
            "isPartOf": {"@id": BASE + "#simulator"},
            "featureList": ["Continuous zoom from nucleus to quarks", "Pion exchange overlay",
                            "Gluon field overlay", "All 118 elements"]}


def g_webpage(cfg, title, canonical_rel, about_id, crumbs):
    pid = url(canonical_rel) + "#webpage"
    node = {"@type": "WebPage", "@id": pid, "url": url(canonical_rel), "name": title, "description": cfg["desc"],
            "inLanguage": "en", "isPartOf": {"@id": BASE + "#website"}, "primaryImageOfPage": {"@id": BASE + "#og-image"},
            "about": {"@id": about_id}}
    if crumbs:
        node["breadcrumb"] = {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": n, "item": url(r)} for i, (n, r) in enumerate(crumbs)]}
    return node


def jsonld_for(name, cfg, title):
    if cfg["kind"] == "landing":
        page = g_webpage(cfg, title, "index_dark.html", BASE + "#simulator", None)
        page["image"] = [{"@id": url(f[0]) + "#image"} for f in GALLERY]
        g = [g_website(), g_person(), g_image(), g_simulator(), g_nucleus(), page] + g_gallery()
    elif cfg["kind"] == "simulator":
        g = [g_website(), g_person(), g_image(), g_simulator(),
             g_webpage(cfg, title, "simulator_dark.html", BASE + "#simulator",
                       [("Quantum Atom", "index_dark.html"), ("Simulator", "simulator_dark.html")])]
    elif cfg["kind"] == "nucleus":
        g = [g_website(), g_person(), g_image(), g_simulator(), g_nucleus(),
             g_webpage(cfg, title, "nucleus_explorer.html", BASE + "#nucleus-explorer",
                       [("Quantum Atom", "index_dark.html"), ("Nucleus Explorer", "nucleus_explorer.html")])]
    else:
        return ""
    # Only the canonical variant carries structured data; duplicates just point at it.
    if cfg["canonical"] != name:
        return ""
    return ld({"@context": "https://schema.org", "@graph": g})


# ───────────────────────── text alternative (apps) ─────────────────────────
def sr_section(name, cfg):
    th = cfg["theme"]
    home = "index_light.html" if th == "light" else "index_dark.html"
    sim = "simulator_light.html" if th == "light" else "simulator_dark.html"
    nuc = "nucleus_explorer_light.html" if th == "light" else "nucleus_explorer.html"
    nav = (f'<nav aria-label="Quantum Atom pages"><a href="{home}" tabindex="-1">Quantum Atom home</a> · '
           f'<a href="{sim}" tabindex="-1">Simulator</a> · <a href="{nuc}" tabindex="-1">Nucleus Explorer</a> · '
           f'<a href="{REPO}" tabindex="-1" rel="noopener">GitHub</a></nav>')
    if cfg["kind"] == "simulator":
        body = (
            "<h1>Quantum Atom Simulator: 3D Atoms, Molecules and Nuclei</h1>"
            "<p>Quantum Atom is a free, browser-based 3D simulator that draws electron orbitals as real probability "
            "clouds instead of dots on rails. Pick any of the 118 elements, explore molecules, promote electrons to "
            "excited states, switch to antimatter, or dive into the nucleus. No install and no account.</p>"
            "<h2>What you can explore</h2><ul>"
            "<li>All 118 elements from hydrogen to oganesson, with their s, p and d orbitals in 3D.</li>"
            "<li>Molecules such as water, ammonia and benzene with VSEPR geometry, plus a build mode for other compounds.</li>"
            "<li>Guided lessons on covalent bonds, VSEPR shapes and how the periodic table fills up.</li>"
            "<li>Side-by-side element comparison and a Bohr model versus quantum model view.</li>"
            "<li>Excited states, antimatter mode, light and dark themes and a colorblind-safe palette.</li></ul>")
    else:
        body = (
            "<h1>Nucleus Explorer: Zoom from the Nucleus to Quarks in 3D</h1>"
            "<p>The Nucleus Explorer is a free 3D tool from Quantum Atom. Choose any of the 118 elements and zoom "
            "continuously from the whole nucleus down to individual protons, neutrons and the quarks inside them. "
            "Toggle pion exchange and gluon field overlays, read the colour legend, and step through the periodic "
            "table with the arrow keys.</p>")
    return ("\n<!-- qa-seo:sr:start -->\n"
            f'<div class="qa-seo-sr" id="qa-seo-about" lang="en">{body}{nav}</div>\n'
            "<!-- qa-seo:sr:end -->")


# ───────────────────────── landing gallery ─────────────────────────
# Layout only; type and colours come from the page's own .section-* classes, so it follows both themes.
# Spacing uses the site's golden-ratio steps (8 / 13 / 21 / 34 px).
GALLERY_CSS = ("<style>#gallery{position:relative;z-index:1}"
               ".qa-gal{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:21px;margin-top:34px}"
               ".qa-gal figure{margin:0;display:flex;flex-direction:column;gap:13px}"
               ".qa-gal figure:first-child{grid-column:1/-1}"
               ".qa-gal a{display:block;border-radius:21px;overflow:hidden;background:#060403;"
               "border:1px solid color-mix(in srgb,currentColor 18%,transparent);"
               "box-shadow:0 13px 34px rgba(0,0,0,.28);transition:transform .22s}"
               ".qa-gal a:hover{transform:translateY(-3px)}"
               ".qa-gal img{display:block;width:100%;height:auto}"
               ".qa-gal figcaption{font-size:.85rem;line-height:1.6;opacity:.82;padding:0 8px}"
               "@media(max-width:820px){.qa-gal{grid-template-columns:1fr;gap:21px;margin-top:21px}}"
               "@media(prefers-reduced-motion:reduce){.qa-gal a{transition:none}.qa-gal a:hover{transform:none}}</style>")


def gallery_section():
    T = GALLERY_I18N["en"]
    figs = []
    for i, (f, w, h, alt, cap) in enumerate(GALLERY):
        small = f.replace(".jpg", "-1200.jpg")
        sizes = "(max-width:820px) 100vw, 1200px" if i == 0 else "(max-width:820px) 100vw, 600px"
        lazy = "" if i == 0 else ' loading="lazy"'
        k = f"landing.gallery.c{i + 1}"
        figs.append(f'<figure><a href="{f}" title="{E(cap)}" data-i18n-attr="title:{k}">'
                    f'<img src="{f}" srcset="{small} 1200w, {f} {w}w" sizes="{sizes}" width="{w}" height="{h}" '
                    f'alt="{E(alt)}"{lazy} decoding="async"></a><figcaption data-i18n="{k}">{E(cap)}</figcaption></figure>')
    return ('<!-- qa-seo:ins:gallery --><section id="gallery"><div class="section-inner">'
            f'<p class="section-eyebrow" data-i18n="landing.gallery.eyebrow">{E(T["landing.gallery.eyebrow"])}</p>'
            f'<h2 class="section-title" data-i18n="landing.gallery.title">{E(T["landing.gallery.title"])}</h2>'
            f'<p class="section-body" data-i18n="landing.gallery.body">{E(T["landing.gallery.body"])}</p>'
            f'<div class="qa-gal">{"".join(figs)}</div></div></section>\n\n<!-- /qa-seo:ins -->')


# ───────────────────────── head block ─────────────────────────
def head_block(name, cfg, title, overrides):
    canon = url(cfg["canonical"])
    d = cfg["desc"]
    dattr = f' data-i18n-attr="content:{cfg["desc_key"]}"' if cfg.get("desc_key") else ""
    L = ["<!-- qa-seo:start (generated by tools/seo/apply_seo.py — edit the config there, not this block) -->",
         f'<meta name="description"{dattr} content="{E(d)}">',
         f'<meta name="robots" content="{ROBOTS}">',
         f'<meta name="google-site-verification" content="{GOOGLE_VERIFICATION}">',
         f'<link rel="canonical" href="{canon}">',
         *([f'<link rel="icon" href="{url("favicon.ico")}" sizes="48x48">',
            f'<link rel="icon" type="image/png" href="{url("images/icon-192.png")}" sizes="192x192">']
           if cfg["canonical"] == name or cfg["kind"] == "splash" else []),
         '<meta property="og:type" content="website">',
         f'<meta property="og:site_name" content="{E(SITE_NAME)}">',
         f'<meta property="og:title" content="{E(title)}">',
         f'<meta property="og:description" content="{E(d)}">',
         f'<meta property="og:url" content="{canon}">',
         f'<meta property="og:image" content="{url(OG_IMAGE)}">',
         '<meta property="og:image:type" content="image/jpeg">',
         '<meta property="og:image:width" content="1200">',
         '<meta property="og:image:height" content="630">',
         f'<meta property="og:image:alt" content="{E(OG_IMAGE_ALT)}">',
         '<meta property="og:locale" content="en_US">']
    L += [f'<meta property="og:locale:alternate" content="{c}">' for c in OG_LOCALES]
    L += ['<meta name="twitter:card" content="summary_large_image">',
          f'<meta name="twitter:title" content="{E(title)}">',
          f'<meta name="twitter:description" content="{E(d)}">',
          f'<meta name="twitter:image" content="{url(OG_IMAGE)}">',
          f'<meta name="twitter:image:alt" content="{E(OG_IMAGE_ALT)}">',
          f'<meta name="author" content="{E(AUTHOR_NAME)}">',
          '<link rel="manifest" href="site.webmanifest">',
          '<link rel="apple-touch-icon" href="images/apple-touch-icon.png">']
    if cfg.get("fonts"):
        L.append('<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>')
    if cfg.get("cdn"):
        L.append('<link rel="preconnect" href="https://cdnjs.cloudflare.com" crossorigin>')
    if overrides:
        L.append("<script>window.QA_I18N&&QA_I18N.add('en'," + json.dumps(overrides, ensure_ascii=False) + ");</script>")
    j = jsonld_for(name, cfg, title)
    if j:
        L.append(j)
    if cfg["kind"] in ("simulator", "nucleus"):
        L.append("<style>.qa-seo-sr{position:absolute!important;width:1px;height:1px;margin:-1px;padding:0;border:0;"
                 "overflow:hidden;clip:rect(0 0 0 0);clip-path:inset(50%);white-space:nowrap}</style>")
    if cfg["kind"] == "landing":
        L.append("<style>.qa-seo-cta{margin-top:.9rem}.qa-seo-cta a{color:inherit;font-weight:600;"
                 "text-decoration:underline;text-underline-offset:3px}</style>")
        L.append(GALLERY_CSS)
        L.append("<script>window.QA_I18N&&(function(d){for(var k in d)QA_I18N.add(k,d[k]);})("
                 + json.dumps(GALLERY_I18N, ensure_ascii=False, separators=(",", ":")) + ");</script>")
    L.append("<!-- qa-seo:end -->")
    return "\n" + "\n".join(L)


# ───────────────────────── per-page transform ─────────────────────────
def process(name: str, cfg: dict) -> dict:
    path = ROOT / name
    with open(path, encoding="utf-8", newline="") as fh:
        s = fh.read()
    # 1. undo previous run
    s = SEO_BLOCK_RE.sub("", s)
    s = SR_RE.sub("", s)
    s = INS_RE.sub("", s)
    m = I18N_END_RE.search(s)
    hend = s.find("</head>")
    assert m and hend > m.end(), f"{name}: i18n end marker / </head> not found"
    head_start, head_end = m.end(), hend

    # 2. strip conflicting head tags (markup only, never inside scripts)
    head = s[head_start:head_end]
    head = sub_outside_code(head, HEAD_TAG_RE)
    head = sub_outside_code(head, CANON_RE)
    s = s[:head_start] + head + s[head_end:]
    hend = s.find("</head>")

    # 3. <title> handling + English overrides for keys bound to it / the description
    tm = re.search(r"<title\b([^>]*)>(.*?)</title>", s, re.S)
    assert tm, f"{name}: <title> missing"
    cur_title = html.unescape(tm.group(2).strip())
    title = cfg["title"] or cur_title
    body_html = s[s.find("<body"):]
    overrides = {}

    def used_elsewhere(key):
        return body_html.count(f'data-i18n="{key}"') > 0 or body_html.count(f"content:{key}") > 0

    attrs = tm.group(1)
    key = cfg.get("title_key")
    if key and cfg["title"] is not None:                               # config-driven, so re-runs are stable
        if used_elsewhere(key):
            attrs = re.sub(r'\s*data-i18n="[^"]*"', "", attrs)       # key also labels visible UI -> unbind <title>
        else:
            overrides[key] = title                                     # English only; other languages keep theirs
    s = s[:tm.start()] + f"<title{attrs}>{E(title).replace('&#x27;', chr(39))}</title>" + s[tm.end():]
    dk = cfg.get("desc_key")
    if dk:
        if used_elsewhere(dk):
            cfg = dict(cfg, desc_key=None)
        else:
            overrides[dk] = cfg["desc"]

    # 4. insert head block right after the generated i18n block
    m = I18N_END_RE.search(s)
    s = s[:m.end()] + head_block(name, cfg, title, overrides) + s[m.end():]

    # 5. body: text alternative for canvas apps
    if cfg["kind"] in ("simulator", "nucleus"):
        bm = re.compile(r"<body\b[^>]*>").search(s, s.find("</head>"))
        s = s[:bm.end()] + sr_section(name, cfg) + s[bm.end():]

    # 5b. theme toggles: javascript: href -> real href + onclick (idempotent: no match once fixed)
    if name in LINK_FIXES:
        fn, target = LINK_FIXES[name]
        s = s.replace(f'href="javascript:{fn}"', f'href="{target}" onclick="{fn};return false;"')

    # 6. landing: crawlable links to the Nucleus Explorer
    if cfg["kind"] == "landing":
        nuc = "nucleus_explorer_light.html" if cfg["theme"] == "light" else "nucleus_explorer.html"
        fm = re.search(r'<a\b[^>]*class="footer-link"[^>]*href="[^"]*simulator_(?:dark|light)\.html"[^>]*>.*?</a>|'
                       r'<a\b[^>]*href="[^"]*simulator_(?:dark|light)\.html"[^>]*class="footer-link"[^>]*>.*?</a>', s, re.S)
        assert fm, f"{name}: footer simulator link not found"
        neighbour = re.sub(r"<[^>]+>", "", fm.group(0)).strip()          # match the footer's casing (light theme is uppercase)
        label = "NUCLEUS EXPLORER" if neighbour.isupper() else "Nucleus Explorer"
        link = (f'<!-- qa-seo:ins:footer --><a href="{nuc}" class="footer-link">{label}</a>'
                f"<!-- /qa-seo:ins -->")
        s = s[:fm.end()] + link + s[fm.end():]
        pm = re.search(r'<p\b[^>]*data-i18n="landing\.section_body\.the_nucleus_explorer_does_one"[^>]*>.*?</p>', s, re.S)
        assert pm, f"{name}: nucleus section paragraph not found"
        cta = (f'<!-- qa-seo:ins:cta --><p class="section-body qa-seo-cta"><a href="{nuc}">Nucleus Explorer →</a></p>'
               f"<!-- /qa-seo:ins -->")
        s = s[:pm.end()] + cta + s[pm.end():]
        gi = s.find('<section id="cta">')
        assert gi > 0, f"{name}: CTA section not found"
        s = s[:gi] + gallery_section() + s[gi:]

    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(s)
    return {"file": name, "title": title, "desc_len": len(cfg["desc"]), "title_len": len(title), "overrides": sorted(overrides)}


# ───────────────────────── static files ─────────────────────────
def write_static(lastmod: str):
    canon_pages = [("index_dark.html", "1.0", "monthly", [g[0] for g in GALLERY] + [SQUARE_IMAGE[0], OG_IMAGE]),
                   ("simulator_dark.html", "0.9", "monthly", []),          # canvas app: no <img> on the page
                   ("nucleus_explorer.html", "0.8", "monthly", [])]
    x = ['<?xml version="1.0" encoding="UTF-8"?>',
         '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">']
    for rel, pri, freq, imgs in canon_pages:
        x += ["  <url>", f"    <loc>{url(rel)}</loc>", f"    <lastmod>{lastmod}</lastmod>",
              f"    <changefreq>{freq}</changefreq>", f"    <priority>{pri}</priority>"]
        x += [f"    <image:image><image:loc>{url(i)}</image:loc></image:image>" for i in imgs]
        x.append("  </url>")
    x.append("</urlset>")
    (ROOT / "sitemap.xml").write_text("\n".join(x) + "\n", encoding="utf-8")

    (ROOT / "robots.txt").write_text(
        "# Quantum Atom — crawl policy.  NOTE: crawlers only read robots.txt at the HOST root. On a GitHub\n"
        "# Pages *project* site this file is not discovered; submit sitemap.xml in Search Console / Bing\n"
        "# Webmaster Tools instead, or serve the site from a custom domain root.\n"
        "User-agent: *\nAllow: /\n\n"
        f"Sitemap: {url('sitemap.xml')}\n", encoding="utf-8")

    (ROOT / "site.webmanifest").write_text(json.dumps({
        "name": "Quantum Atom — 3D Atom, Molecule & Nucleus Simulator", "short_name": "Quantum Atom",
        "description": DESC_LANDING, "start_url": "./index_dark.html", "scope": "./", "display": "standalone",
        "background_color": "#090605", "theme_color": "#090605", "lang": "en", "categories": ["education", "science"],
        "icons": [{"src": "images/icon-192.png", "sizes": "192x192", "type": "image/png"},
                  {"src": "images/icon-512.png", "sizes": "512x512", "type": "image/png"},
                  {"src": "images/icon-512-maskable.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"}]},
        ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    (ROOT / "404.html").write_text(f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" media="(prefers-color-scheme: dark)" content="#090605">
<meta name="theme-color" media="(prefers-color-scheme: light)" content="#ffffff">
<title>Page not found — Quantum Atom</title>
<meta name="robots" content="noindex,follow">
<meta name="color-scheme" content="dark light">
<link rel="icon" href="{url('images/icon-192.png')}">
<style>
:root{{--bg:#fff;--fg:#1c1740;--mut:#5b5680;--acc:#6952e0}}
@media (prefers-color-scheme:dark){{:root{{--bg:#050302;--fg:#fff;--mut:#cdbfb6;--acc:#ff5b14}}}}
*{{box-sizing:border-box}}html,body{{height:100%;margin:0}}
body{{display:grid;place-items:center;padding:24px;background:var(--bg);color:var(--fg);font:16px/1.6 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}}
main{{max-width:34rem;text-align:center}}h1{{font-size:clamp(2rem,6vw,3rem);margin:.2em 0}}p{{color:var(--mut)}}
nav{{display:flex;flex-wrap:wrap;gap:12px;justify-content:center;margin-top:1.5rem}}
a{{color:#fff;background:var(--acc);padding:.65em 1.2em;border-radius:999px;text-decoration:none;font-weight:600}}
a.alt{{background:transparent;color:var(--fg);box-shadow:inset 0 0 0 2px var(--acc)}}
</style>
</head>
<body>
<main>
<p aria-hidden="true" style="font-size:3rem;margin:0">⚛️</p>
<h1>404 — this orbital is empty</h1>
<p>The page you asked for doesn’t exist, but there are 118 elements waiting to be explored.</p>
<nav>
<a href="{url('index_dark.html')}">Quantum Atom home</a>
<a class="alt" href="{url('simulator_dark.html')}">Open the simulator</a>
<a class="alt" href="{url('nucleus_explorer.html')}">Nucleus Explorer</a>
</nav>
</main>
</body>
</html>
""", encoding="utf-8")

    (ROOT / "llms.txt").write_text(f"""# Quantum Atom

> Free, browser-based 3D simulator of atomic orbitals, molecules and nuclei. All 118 elements, real probability-cloud orbitals, VSEPR molecule geometry, antimatter mode and a Nucleus Explorer that zooms from the nucleus to quarks. No install, no account. Built by {AUTHOR_NAME}.

## Pages
- [Home]({url('index_dark.html')}): the story of the atom, from Democritus to quantum mechanics, and what the simulator shows.
- [Simulator]({url('simulator_dark.html')}): atoms, molecules, build mode, lessons, compare, excited states, antimatter.
- [Nucleus Explorer]({url('nucleus_explorer.html')}): continuous zoom from nucleus to quarks with pion exchange and gluon overlays.

## Source
- [GitHub repository]({REPO}): README with controls, languages and project structure.
""", encoding="utf-8")


def main():
    global BASE
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=BASE)
    ap.add_argument("--lastmod", default=dt.date.today().isoformat())
    a = ap.parse_args()
    BASE = a.base if a.base.endswith("/") else a.base + "/"
    for name, cfg in PAGES.items():
        r = process(name, dict(cfg))
        print(f"{name:30s} title={r['title_len']:>3} desc={r['desc_len']:>3} i18n-overrides={r['overrides']}")
    write_static(a.lastmod)
    print("wrote sitemap.xml robots.txt site.webmanifest 404.html llms.txt")


if __name__ == "__main__":
    main()
