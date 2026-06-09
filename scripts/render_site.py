#!/usr/bin/env python3
"""Render the static GitHub Pages dashboard."""

from __future__ import annotations

import datetime as dt
import html
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
DOCS_DIR = ROOT / "docs"

CATEGORY_LABELS = {
    "model": "Model",
    "alignment": "Alignment",
    "agents": "Agents",
    "claude_code": "Claude Code",
}


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def esc(value: Any) -> str:
    if value is None:
        return ""
    return html.escape(str(value), quote=True)


def render_badge(category: str) -> str:
    label = CATEGORY_LABELS.get(category, category)
    return f'<span class="badge badge-{esc(category)}">{esc(label)}</span>'


def article_date(article: dict[str, Any]) -> str:
    raw = article.get("published_at") or article.get("added_at") or ""
    if len(raw) >= 10 and raw[:4].isdigit():
        return raw[:10]
    for fmt in ("%b %d, %Y", "%B %d, %Y"):
        try:
            return dt.datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return "undated"


def archive_label(date_key: str) -> str:
    if date_key == "undated":
        return "Undated"
    return date_key


def date_anchor(date_key: str) -> str:
    return f"date-{date_key}"


def main() -> int:
    articles = load_json(DATA_DIR / "articles.json", [])
    runs = load_json(DATA_DIR / "daily_runs.json", [])
    sources = load_json(ROOT / "config" / "sources.json", {"sources": []})["sources"]
    latest_run = runs[0] if runs else {}
    last_checked = latest_run.get("checked_at_display", "Never")

    total_by_category = {key: 0 for key in CATEGORY_LABELS}
    for article in articles:
        total_by_category[article.get("category")] = total_by_category.get(article.get("category"), 0) + 1

    source_rows = []
    for source in sources:
        count = latest_run.get("source_counts", {}).get(source["id"], 0)
        source_rows.append(
            f"""
            <li>
              <span>{esc(source["name"])}</span>
              <strong>{count} new</strong>
            </li>
            """
        )

    archive_counts: dict[str, int] = {}
    for article in articles:
        date_key = article_date(article)
        archive_counts[date_key] = archive_counts.get(date_key, 0) + 1

    archive_buttons = "\n".join(
        f'<a href="#{esc(date_anchor(date_key))}"><span>{esc(archive_label(date_key))}</span><strong>{count}</strong></a>'
        for date_key, count in sorted(archive_counts.items(), reverse=True)
    )

    cards = render_article_groups(articles[:120])
    if not cards:
        cards = """
        <article class="empty-state">
          <h2>No articles yet</h2>
          <p>After the first scheduled run, new posts will appear here with bilingual summaries and personal takes.</p>
        </article>
        """

    error_count = len(latest_run.get("errors", []))
    generated_at = dt.datetime.now(dt.timezone.utc).astimezone(dt.timezone(dt.timedelta(hours=8))).strftime("%Y-%m-%d %H:%M Asia/Shanghai")

    html_text = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Anthropic Tracker</title>
  <link rel="stylesheet" href="styles.css">
</head>
<body>
  <main class="layout" id="top">
    <aside class="sidebar">
      <header>
        <p class="eyebrow">AI Lab Watch</p>
        <h1>Anthropic Tracker</h1>
      </header>

      <section class="panel">
        <h2>Status</h2>
        <dl class="stats">
          <div>
            <dt>Last checked</dt>
            <dd>{esc(last_checked)}</dd>
          </div>
          <div>
            <dt>Today new</dt>
            <dd>{esc(latest_run.get("new_count", 0))}</dd>
          </div>
          <div>
            <dt>Tracked posts</dt>
            <dd>{len(articles)}</dd>
          </div>
          <div>
            <dt>Errors</dt>
            <dd>{error_count}</dd>
          </div>
        </dl>
      </section>

      <section class="panel">
        <h2>Sources</h2>
        <ul class="source-list">
          {"".join(source_rows)}
        </ul>
      </section>

      <section class="panel">
        <h2>Categories</h2>
        <div class="category-grid">
          {render_category_stat("model", total_by_category.get("model", 0))}
          {render_category_stat("alignment", total_by_category.get("alignment", 0))}
          {render_category_stat("agents", total_by_category.get("agents", 0))}
          {render_category_stat("claude_code", total_by_category.get("claude_code", 0))}
        </div>
      </section>

      <section class="panel">
        <h2>Archive</h2>
        <nav class="archive-list" aria-label="Article archive by publish date">
          {archive_buttons}
        </nav>
      </section>

      <footer>
        Generated: {esc(generated_at)}
      </footer>
    </aside>

    <section class="feed">
      <div class="feed-header">
        <div>
          <p class="eyebrow">Latest Briefs</p>
          <h2>New Anthropic and Claude posts</h2>
        </div>
        <a class="repo-link" href="https://github.com/crash-zwt/anthropic-tracker">GitHub</a>
      </div>
      {cards}
    </section>
  </main>
</body>
</html>
"""
    DOCS_DIR.mkdir(exist_ok=True)
    (DOCS_DIR / "index.html").write_text(html_text, encoding="utf-8")
    return 0


def render_category_stat(category: str, count: int) -> str:
    return f"""
    <div class="category-stat category-{esc(category)}">
      <span>{esc(CATEGORY_LABELS.get(category, category))}</span>
      <strong>{count}</strong>
    </div>
    """


def render_article_groups(articles: list[dict[str, Any]]) -> str:
    groups: dict[str, list[dict[str, Any]]] = {}
    for article in articles:
        groups.setdefault(article_date(article), []).append(article)

    sections = []
    for date_key in sorted(groups, reverse=True):
        articles_html = "\n".join(render_article(article) for article in groups[date_key])
        sections.append(
            f"""
            <section class="date-section" id="{esc(date_anchor(date_key))}">
              <div class="date-heading">
                <h3>{esc(archive_label(date_key))}</h3>
                <a href="#top">Back to top</a>
              </div>
              {articles_html}
            </section>
            """
        )
    return "\n".join(sections)


def render_article(article: dict[str, Any]) -> str:
    summary = article.get("summary", {})
    key_points = summary.get("key_points", [])
    points = "".join(f"<li>{esc(point)}</li>" for point in key_points)
    tags = "".join(f"<span>{esc(tag)}</span>" for tag in summary.get("tags", []))
    published = article.get("published_at") or "Unknown date"
    added = article.get("added_at", "")
    added_short = added[:10] if added else ""

    return f"""
    <article class="article-card">
      <div class="article-meta">
        {render_badge(article.get("category", ""))}
        <span>{esc(article.get("source_name"))}</span>
        <span>{esc(published)}</span>
        <span>Added {esc(added_short)}</span>
      </div>
      <h2>{esc(article.get("title"))}</h2>
      <a class="original-link" href="{esc(article.get("url"))}" target="_blank" rel="noreferrer">Original Link</a>
      <section>
        <h3>TL;DR</h3>
        <p>{esc(summary.get("tldr"))}</p>
      </section>
      <section>
        <h3>Key Points</h3>
        <ul>{points}</ul>
      </section>
      <section>
        <h3>Why It Matters</h3>
        <p>{esc(summary.get("why_it_matters"))}</p>
      </section>
      <section>
        <h3>My Take</h3>
        <p>{esc(summary.get("my_take"))}</p>
      </section>
      <div class="tags">{tags}</div>
    </article>
    """


if __name__ == "__main__":
    raise SystemExit(main())
