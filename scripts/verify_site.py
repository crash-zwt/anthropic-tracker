#!/usr/bin/env python3
"""Verify generated static pages have working local navigation."""

from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urldefrag


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
EXPECTED_CATEGORY_PAGES = {
    "categories/model.html",
    "categories/alignment.html",
    "categories/agents.html",
    "categories/claude-code.html",
    "categories/openai-model.html",
    "categories/openai-agents.html",
    "categories/openai-code.html",
}


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: set[str] = set()
        self.hrefs: list[str] = []
        self.archive_hrefs: list[str] = []
        self.category_hrefs: list[str] = []
        self._in_archive = False
        self._archive_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = dict(attrs)
        if "id" in attr:
            self.ids.add(attr["id"] or "")
        if tag == "nav" and "archive-list" in (attr.get("class") or ""):
            self._in_archive = True
            self._archive_depth = 1
        elif self._in_archive:
            self._archive_depth += 1

        href = attr.get("href")
        if tag == "a" and href:
            self.hrefs.append(href)
            if self._in_archive:
                self.archive_hrefs.append(href)
            if "category-stat" in (attr.get("class") or ""):
                self.category_hrefs.append(href)

    def handle_endtag(self, tag: str) -> None:
        if self._in_archive:
            self._archive_depth -= 1
            if self._archive_depth <= 0:
                self._in_archive = False


def parse(path: Path) -> PageParser:
    parser = PageParser()
    parser.feed(path.read_text(encoding="utf-8"))
    return parser


def resolve(page: Path, href: str) -> Path:
    target, _fragment = urldefrag(href)
    if not target:
        return page
    return (page.parent / target).resolve()


def main() -> int:
    pages = [DOCS / "index.html", *sorted((DOCS / "categories").glob("*.html"))]
    failures: list[str] = []

    if {str(path.relative_to(DOCS)) for path in pages if path.parent.name == "categories"} != EXPECTED_CATEGORY_PAGES:
        failures.append("Category pages are missing or unexpected.")

    for page in pages:
        page_html = page.read_text(encoding="utf-8")
        parser = PageParser()
        parser.feed(page_html)
        label = str(page.relative_to(DOCS))
        if "top" not in parser.ids:
            failures.append(f"{label}: missing #top")
        if not parser.archive_hrefs and "empty-state" not in page_html:
            failures.append(f"{label}: missing archive links")

        for href in parser.archive_hrefs:
            target, fragment = urldefrag(href)
            if target:
                failures.append(f"{label}: archive link should be page-local: {href}")
            elif fragment not in parser.ids:
                failures.append(f"{label}: archive target missing: #{fragment}")

        for href in parser.hrefs:
            target, fragment = urldefrag(href)
            if href.startswith("http") or href.startswith("#") or not target:
                continue
            target_path = resolve(page, href)
            if not target_path.exists():
                failures.append(f"{label}: broken href {href}")
                continue
            if fragment:
                target_parser = parse(target_path)
                if fragment not in target_parser.ids:
                    failures.append(f"{label}: broken href fragment {href}")

    if failures:
        print("\n".join(failures))
        return 1
    print(f"Verified {len(pages)} pages: archive links, category links, and local hrefs are valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
