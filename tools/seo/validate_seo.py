#!/usr/bin/env python3
"""Quantum Atom — SEO validator (no dependencies except Pillow for image sizes).

Fails (exit 1) when any hard rule is broken; prints warnings for soft ones.
Usage:  python3 tools/seo/validate_seo.py
"""
from __future__ import annotations

import html
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
import apply_seo as cfgmod  # noqa: E402  (reuse BASE + page config: single source of truth)

BASE = cfgmod.BASE
errors: list[str] = []
warnings: list[str] = []
SCRIPT_STYLE = re.compile(r"<script\b.*?</script>|<style\b.*?</style>", re.S)


def err(page, msg): errors.append(f"[{page}] {msg}")
def warn(page, msg): warnings.append(f"[{page}] {msg}")


def local(urlstr: str):
    """Map an absolute URL under BASE (or a relative one) to a repo path; None if external."""
    if urlstr.startswith(BASE):
        rel = urlstr[len(BASE):].split("#")[0].split("?")[0] or "index.html"
        return ROOT / rel
    if re.match(r"^[a-z][a-z0-9+.-]*:", urlstr) or urlstr.startswith(("#", "//")):
        return None
    return ROOT / urlstr.split("#")[0].split("?")[0]


def meta(head, attr, val):
    return re.findall(rf'<meta\b(?:[^>"]|"[^"]*")*\b{attr}="{re.escape(val)}"(?:[^>"]|"[^"]*")*>', head)


def content_of(tag):
    m = re.search(r'\bcontent="([^"]*)"', tag)
    return html.unescape(m.group(1)) if m else ""


titles, descs = {}, {}
for name, cfg in cfgmod.PAGES.items():
    s = (ROOT / name).read_text(encoding="utf-8")
    head = s[: s.find("</head>")]
    head_nocode = SCRIPT_STYLE.sub("", head)
    body_nocode = SCRIPT_STYLE.sub("", s[s.find("<body"):])
    canon_rel = cfg["canonical"]
    canon = BASE + canon_rel

    # title
    tt = re.findall(r"<title\b[^>]*>(.*?)</title>", head_nocode, re.S)
    if len(tt) != 1: err(name, f"expected exactly 1 <title>, found {len(tt)}"); continue
    title = html.unescape(tt[0].strip())
    if not 20 <= len(title) <= 65: warn(name, f"title length {len(title)} (aim 20-65)")

    # description
    d = meta(head_nocode, "name", "description")
    if len(d) != 1: err(name, f"expected 1 meta description, found {len(d)}")
    else:
        dv = content_of(d[0])
        if not 70 <= len(dv) <= 160: err(name, f"description length {len(dv)} (need 70-160)")
        if dv != cfg["desc"]: err(name, "description differs from config (run apply_seo.py)")

    # canonical
    c = re.findall(r'<link\b[^>]*\brel="canonical"[^>]*\bhref="([^"]+)"', head_nocode)
    if len(c) != 1: err(name, f"expected 1 canonical, found {len(c)}")
    elif c[0] != canon: err(name, f"canonical {c[0]} != expected {canon}")
    if not local(canon) or not local(canon).exists(): err(name, f"canonical target missing: {canon}")

    # robots / OG / Twitter
    if len(meta(head_nocode, "name", "robots")) != 1: err(name, "need exactly 1 robots meta")
    for prop in ("og:title", "og:description", "og:url", "og:image", "og:image:width", "og:image:height",
                 "og:image:alt", "og:type", "og:site_name"):
        if len(meta(head_nocode, "property", prop)) != 1: err(name, f"need exactly 1 {prop}")
    for nm in ("twitter:card", "twitter:title", "twitter:description", "twitter:image"):
        if len(meta(head_nocode, "name", nm)) != 1: err(name, f"need exactly 1 {nm}")
    ou = meta(head_nocode, "property", "og:url")
    if ou and content_of(ou[0]) != canon: err(name, "og:url must equal canonical")
    oi = meta(head_nocode, "property", "og:image")
    if oi:
        p = local(content_of(oi[0]))
        if not p or not p.exists(): err(name, "og:image file missing")

    # viewport + lang
    if not meta(head_nocode, "name", "viewport"): err(name, "viewport meta missing")
    if not re.search(r"<html\b[^>]*\blang=", s[:400]): err(name, "<html lang> missing")

    # exactly one h1 in static markup
    h1 = len(re.findall(r"<h1\b", body_nocode))
    if h1 != 1: err(name, f"expected exactly 1 <h1> in static HTML, found {h1}")

    # JSON-LD: canonical pages must have valid graph; duplicates must have none
    blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', head, re.S)
    if cfg["kind"] in ("landing", "simulator", "nucleus") and cfg["canonical"] == name:
        if len(blocks) != 1: err(name, f"expected 1 JSON-LD block, found {len(blocks)}")
        for b in blocks:
            try:
                g = json.loads(b)["@graph"]
                ids = {n["@id"] for n in g}
                refs = {v["@id"] for n in g for v in n.values() if isinstance(v, dict) and "@id" in v and len(v) == 1}
                missing = refs - ids
                if missing: err(name, f"JSON-LD dangling @id refs: {sorted(missing)}")
                if not any(n["@type"] == "WebApplication" for n in g): err(name, "JSON-LD lacks WebApplication")
            except Exception as ex:  # noqa: BLE001
                err(name, f"JSON-LD invalid: {ex}")
    elif blocks:
        err(name, "non-canonical variant must not carry JSON-LD")

    # links
    for href in set(re.findall(r'<a\b[^>]*\bhref="([^"]+)"', body_nocode)):
        if href.startswith("javascript:"):
            warn(name, f"non-crawlable javascript: link kept ({href[:30]})"); continue
        p = local(href)
        if p is not None and not p.exists(): err(name, f"broken internal link: {href}")
    for lk in re.findall(r'<link\b[^>]*\bhref="([^"]+)"', head_nocode):
        p = local(lk)
        if p is not None and not p.exists() and not lk.startswith("data:"): err(name, f"missing head resource: {lk}")

    if cfg["canonical"] == name:
        if title in titles: err(name, f"duplicate title with {titles[title]}")
        titles[title] = name
        if cfg["desc"] in descs: err(name, f"duplicate description with {descs[cfg['desc']]}")
        descs[cfg["desc"]] = name
    print(f"ok  {name:30s} title={len(title):>2} h1={h1} canon→{canon_rel}")

# sitemap
try:
    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9", "i": "http://www.google.com/schemas/sitemap-image/1.1"}
    root = ET.parse(ROOT / "sitemap.xml").getroot()
    locs = [u.find("s:loc", ns).text for u in root.findall("s:url", ns)]
    for u in locs:
        p = local(u)
        if not p or not p.exists(): err("sitemap.xml", f"missing file for {u}")
        rel = Path(urlparse(u).path).name
        if rel in cfgmod.PAGES and cfgmod.PAGES[rel]["canonical"] != rel: err("sitemap.xml", f"non-canonical URL listed: {u}")
    for i in root.iter("{%s}loc" % ns["i"]):
        p = local(i.text)
        if not p or not p.exists(): err("sitemap.xml", f"missing image {i.text}")
    canon_pages = {BASE + v["canonical"] for v in cfgmod.PAGES.values()}
    if set(locs) != canon_pages: err("sitemap.xml", f"must list exactly the canonical pages; diff={set(locs) ^ canon_pages}")
    print(f"ok  sitemap.xml                   {len(locs)} URLs")
except Exception as ex:  # noqa: BLE001
    err("sitemap.xml", str(ex))

robots = (ROOT / "robots.txt").read_text()
if f"Sitemap: {BASE}sitemap.xml" not in robots: err("robots.txt", "Sitemap directive missing/wrong")
if re.search(r"(?im)^\s*disallow:\s*/\s*$", robots): err("robots.txt", "blocks entire site")

try:
    man = json.loads((ROOT / "site.webmanifest").read_text())
    for ic in man["icons"]:
        if not (ROOT / ic["src"]).exists(): err("site.webmanifest", f"icon missing {ic['src']}")
    print(f"ok  site.webmanifest              {len(man['icons'])} icons")
except Exception as ex:  # noqa: BLE001
    err("site.webmanifest", str(ex))

try:
    from PIL import Image
    im = Image.open(ROOT / cfgmod.OG_IMAGE)
    kb = (ROOT / cfgmod.OG_IMAGE).stat().st_size / 1024
    if im.size != (1200, 630): err("og-image", f"size {im.size}, need 1200x630")
    if kb > 300: err("og-image", f"{kb:.0f} KB > 300 KB (WhatsApp ignores larger)")
    print(f"ok  og-image.jpg                  {im.size[0]}x{im.size[1]} {kb:.0f} KB")
except ImportError:
    warn("og-image", "Pillow not installed; image size not checked")

print()
for w in warnings: print("WARN", w)
for e in errors: print("FAIL", e)
print(f"\n{len(errors)} error(s), {len(warnings)} warning(s)")
sys.exit(1 if errors else 0)
