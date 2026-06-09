#!/usr/bin/env python3
"""Remove article and seen records that no longer pass source filters."""

from __future__ import annotations

import json
from pathlib import Path

import check_and_summarize as tracker


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    sources = tracker.load_json(tracker.SOURCE_PATH, {"sources": []})["sources"]
    source_by_id = {source["id"]: source for source in sources}

    articles = tracker.load_json(tracker.ARTICLES_PATH, [])
    seen = tracker.load_json(tracker.SEEN_PATH, {})

    kept_articles = []
    removed_articles = []
    for article in articles:
        source = source_by_id.get(article.get("source_id"))
        title = article.get("title", "")
        url = article.get("url", "")
        if not tracker.allowed_article_url(url) or (source and not tracker.passes_source_filters(source, title, url)):
            removed_articles.append({"title": title, "url": url})
            continue
        kept_articles.append(article)

    kept_seen = {}
    removed_seen = []
    for url, entry in seen.items():
        source = source_by_id.get(entry.get("source_id"))
        title = entry.get("title", "")
        if not tracker.allowed_article_url(url) or (source and not tracker.passes_source_filters(source, title, url)):
            removed_seen.append({"title": title, "url": url})
            continue
        kept_seen[url] = entry

    tracker.save_json(tracker.ARTICLES_PATH, kept_articles)
    tracker.save_json(tracker.SEEN_PATH, kept_seen)

    print(json.dumps({
        "removed_articles": len(removed_articles),
        "removed_seen": len(removed_seen),
        "article_titles": [item["title"] for item in removed_articles],
        "seen_titles": [item["title"] for item in removed_seen[:20]]
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
