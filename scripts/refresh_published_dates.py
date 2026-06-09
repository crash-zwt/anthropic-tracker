#!/usr/bin/env python3
"""Refresh published_at for existing articles without re-summarizing."""

from __future__ import annotations

import json

import check_and_summarize as tracker


def main() -> int:
    articles = tracker.load_json(tracker.ARTICLES_PATH, [])
    updated = []
    errors = []

    for article in articles:
        url = article.get("url", "")
        if not url or not tracker.allowed_article_url(url):
            continue
        try:
            extracted = tracker.extract_article(url)
        except Exception as exc:
            errors.append({"url": url, "error": str(exc)})
            continue

        published_at = extracted.get("published_at", "")
        if published_at and published_at != article.get("published_at", ""):
            article["published_at"] = published_at
            updated.append({"title": article.get("title", ""), "published_at": published_at})

    tracker.save_json(tracker.ARTICLES_PATH, articles)
    print(json.dumps({"updated": updated, "errors": errors}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
