#!/usr/bin/env python3
"""Mark currently discoverable source links as seen without summarizing them."""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import check_and_summarize as tracker


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    sources = tracker.load_json(tracker.SOURCE_PATH, {"sources": []})["sources"]
    seen = tracker.load_json(tracker.SEEN_PATH, {})
    articles = tracker.load_json(tracker.ARTICLES_PATH, [])
    article_urls = {article["url"] for article in articles}
    now = dt.datetime.now(dt.timezone.utc).isoformat()

    added = 0
    for source in sources:
        for candidate in tracker.discover_articles(source):
            url = candidate["url"]
            if url in seen or url in article_urls:
                continue
            seen[url] = {
                "title": candidate["title"],
                "source_id": source["id"],
                "first_seen_at": now,
                "bootstrap_only": True
            }
            added += 1

    tracker.save_json(tracker.SEEN_PATH, seen)
    print(json.dumps({"bootstrap_seen_added": added}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
