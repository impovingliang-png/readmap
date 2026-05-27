#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NATIONS_DIR = ROOT / "nations"
DATA_DIR = ROOT / "data"


@dataclass(frozen=True)
class CountryMeta:
  slug: str
  name_en: str
  name_zh: str
  css_components_href: str
  css_theme_href: str

  @property
  def page_url(self) -> str:
    return f"https://readmap.idv.tw/country/nations/{self.slug}/"

  @property
  def title(self) -> str:
    return f"{self.name_zh} {self.name_en} | 國家地理數據與事實 - ReadMap"

  @property
  def description(self) -> str:
    return (
      f"探索{self.name_zh} ({self.name_en}) 的核心事實：包含最新人口數據、國土面積、"
      "地理位置地圖以及詳細的國家文化總覽。"
    )

  @property
  def twitter_description(self) -> str:
    return (
      f"探索{self.name_zh} ({self.name_en}) 的核心事實：包含最新人口數據、國土面積、"
      "地理位置地圖與詳細總覽。"
    )

  @property
  def og_url(self) -> str:
    return self.page_url


def _load_country_meta(slug: str, components_href: str, theme_href: str) -> CountryMeta:
  data_path = DATA_DIR / f"{slug}.json"
  if not data_path.exists():
    raise FileNotFoundError(f"Missing data file: {data_path}")

  data = json.loads(data_path.read_text(encoding="utf-8"))
  name_en = (data.get("name") or {}).get("en") or slug.replace("-", " ").title()
  name_zh = (data.get("name") or {}).get("zh") or name_en

  return CountryMeta(
    slug=slug,
    name_en=str(name_en),
    name_zh=str(name_zh),
    css_components_href=components_href,
    css_theme_href=theme_href,
  )


def _extract_head_preamble(head_inner: str) -> tuple[str, str, str]:
  """
  Returns (charset_line, viewport_line, styles_links_block).
  Falls back to defaults if missing.
  """
  charset = re.search(r'^\s*<meta\s+charset="[^"]+"\s*/?>\s*$', head_inner, re.M)
  viewport = re.search(
    r'^\s*<meta\s+name="viewport"\s+content="[^"]+"\s*/?>\s*$', head_inner, re.M
  )
  links = re.findall(r'^\s*<link\s+rel="stylesheet"\s+href="[^"]+"\s*/>\s*$', head_inner, re.M)

  charset_line = charset.group(0).strip() if charset else '<meta charset="utf-8" />'
  viewport_line = viewport.group(0).strip() if viewport else '<meta name="viewport" content="width=device-width, initial-scale=1" />'
  links_block = "\n  ".join(l.strip() for l in links)
  return charset_line, viewport_line, links_block


def _build_head_inner(meta: CountryMeta, existing_head_inner: str) -> str:
  charset_line, viewport_line, links_block = _extract_head_preamble(existing_head_inner)
  if not links_block:
    links_block = (
      f'<link rel="stylesheet" href="{meta.css_components_href}" />\n'
      f'  <link rel="stylesheet" href="{meta.css_theme_href}" />'
    ).strip()

  return (
    "  <link rel=\"icon\" href=\"https://readmap.idv.tw/favicon.png\" type=\"image/png\" sizes=\"1024x1024\" />\n"
    "  <link rel=\"apple-touch-icon\" href=\"https://readmap.idv.tw/readmap.png\" />\n"
    "\n"
    f"  <link rel=\"canonical\" href=\"{meta.page_url}\" />\n"
    "\n"
    f"  <link rel=\"alternate\" hreflang=\"zh-TW\" href=\"{meta.page_url}?lang=zh\" />\n"
    f"  <link rel=\"alternate\" hreflang=\"en\" href=\"{meta.page_url}?lang=en\" />\n"
    f"  <link rel=\"alternate\" hreflang=\"x-default\" href=\"{meta.page_url}\" />\n"
    "\n"
    f"  {charset_line}\n"
    f"  {viewport_line}\n"
    f"  {links_block}\n"
    f"  \n"
    f"  <title>{meta.title}</title>\n"
    f"  <meta name=\"description\" content=\"{meta.description}\" />\n"
    f"\n"
    f"  <meta property=\"og:title\" content=\"{meta.title}\" />\n"
    f"  <meta property=\"og:description\" content=\"{meta.description}\" />\n"
    f"  <meta property=\"og:url\" content=\"{meta.og_url}\" />\n"
    f"  <meta property=\"og:type\" content=\"article\" />\n"
    f"  <meta property=\"og:image\" content=\"https://readmap.idv.tw/readmap.png\" />\n"
    f"  <meta property=\"og:image:width\" content=\"1200\" />\n"
    f"  <meta property=\"og:image:height\" content=\"630\" />\n"
    f"  \n"
    f"  <meta name=\"twitter:card\" content=\"summary_large_image\" />\n"
    f"  <meta name=\"twitter:title\" content=\"{meta.title}\" />\n"
    f"  <meta name=\"twitter:description\" content=\"{meta.twitter_description}\" />\n"
    f"  <meta name=\"twitter:image\" content=\"https://readmap.idv.tw/readmap.png\" />\n"
  )


def _update_country_index_html(path: Path) -> bool:
  original = path.read_text(encoding="utf-8")

  m = re.search(r"<head>(?P<inner>[\s\S]*?)</head>", original, re.I)
  if not m:
    raise ValueError(f"Missing <head> in {path}")

  inner = m.group("inner")
  slug = path.parent.name

  # Keep original hrefs (including cache-busting query params)
  href_components = re.search(r'href="(?P<h>../../components\.css[^"]*)"', inner)
  href_theme = re.search(r'href="(?P<h>\./theme\.css[^"]*)"', inner)
  components_href = href_components.group("h") if href_components else "../../components.css"
  theme_href = href_theme.group("h") if href_theme else "./theme.css"

  meta = _load_country_meta(slug, components_href, theme_href)
  new_inner = "\n" + _build_head_inner(meta, inner) + "\n"

  updated = original[: m.start("inner")] + new_inner + original[m.end("inner") :]
  if updated == original:
    return False

  path.write_text(updated, encoding="utf-8")
  return True


def main() -> None:
  index_files = sorted(NATIONS_DIR.glob("*/index.html"))
  if not index_files:
    raise SystemExit(f"No nation pages found under: {NATIONS_DIR}")

  changed = 0
  for path in index_files:
    if _update_country_index_html(path):
      changed += 1

  print(f"Updated meta tags: {changed}/{len(index_files)} files")


if __name__ == "__main__":
  main()
