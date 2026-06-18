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
    "openai_model": "OpenAI Model",
    "openai_agents": "OpenAI Agents",
    "openai_code": "OpenAI Code",
    "google_gemini": "Google Gemini",
    "thinking_machines": "Thinking Machines",
}

CATEGORY_SLUGS = {
    "model": "model",
    "alignment": "alignment",
    "agents": "agents",
    "claude_code": "claude-code",
    "openai_model": "openai-model",
    "openai_agents": "openai-agents",
    "openai_code": "openai-code",
    "google_gemini": "google-gemini",
    "thinking_machines": "thinking-machines",
}

CATEGORY_ORDER = list(CATEGORY_LABELS)

LAB_LABELS = {
    "anthropic": "Anthropic / Claude",
    "openai": "OpenAI",
    "google": "Google",
    "thinking_machines": "Thinking Machines",
}

LAB_SLUGS = {
    "anthropic": "anthropic",
    "openai": "openai",
    "google": "google",
    "thinking_machines": "thinking-machines",
}

LAB_ORDER = list(LAB_LABELS)

TOPIC_LABELS = {
    "model": "Model",
    "alignment": "Alignment",
    "agents": "Agents",
    "code": "Code",
    "gemini": "Gemini",
    "methods": "Methods & Research",
}

TOPIC_ORDER = ["model", "alignment", "agents", "code", "gemini", "methods"]


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


def category_href(category: str, current_category: str | None = None) -> str:
    slug = CATEGORY_SLUGS.get(category, category)
    if current_category == category:
        return "#top"
    if current_category:
        return f"{slug}.html"
    return f"categories/{slug}.html"


def lab_href(lab: str, current_lab: str | None = None, nested: bool = False) -> str:
    slug = LAB_SLUGS.get(lab, lab)
    if current_lab == lab:
        return "#top"
    prefix = "../" if nested else ""
    return f"{prefix}labs/{slug}.html"


def home_href(nested: bool = False) -> str:
    return "../index.html" if nested else "index.html"


def article_lab(article: dict[str, Any]) -> str:
    vendor = article.get("vendor", "")
    if vendor == "OpenAI":
        return "openai"
    if vendor == "Google":
        return "google"
    if vendor == "Thinking Machines":
        return "thinking_machines"
    return "anthropic"


def source_lab(source: dict[str, Any]) -> str:
    vendor = source.get("vendor", "")
    if vendor == "OpenAI":
        return "openai"
    if vendor == "Google":
        return "google"
    if vendor == "Thinking Machines":
        return "thinking_machines"
    return "anthropic"


def article_topic(article: dict[str, Any]) -> str:
    category = article.get("category", "")
    text = " ".join(
        [
            str(article.get("title", "")),
            str(article.get("summary", {}).get("tldr", "")),
            " ".join(str(tag) for tag in article.get("summary", {}).get("tags", [])),
        ]
    ).lower()
    if article_lab(article) == "openai":
        if any(keyword in text for keyword in ("codex", "coding", "code generation")):
            return "code"
        if any(keyword in text for keyword in ("agent", "agents", "responses api", "agents sdk", "computer use", "tool use")):
            return "agents"
        if any(keyword in text for keyword in ("alignment", "safety", "model spec", "privacy", "teen", "policy", "bio defense", "cyber defense", "trusted access")):
            return "alignment"
        if any(keyword in text for keyword in ("method", "research", "latency", "inference", "architecture", "evaluation", "benchmark")):
            return "methods"
        return "model"
    if category in {"model", "openai_model"}:
        return "model"
    if category == "alignment":
        return "alignment"
    if category in {"agents", "openai_agents"}:
        return "agents"
    if category in {"claude_code", "openai_code"}:
        return "code"
    if category == "google_gemini":
        return "gemini"
    if category == "thinking_machines":
        return "methods"
    return category or "methods"


def topic_anchor(topic: str) -> str:
    return f"topic-{topic}"


def main() -> int:
    articles = load_json(DATA_DIR / "articles.json", [])
    runs = load_json(DATA_DIR / "daily_runs.json", [])
    sources = load_json(ROOT / "config" / "sources.json", {"sources": []})["sources"]
    latest_run = runs[0] if runs else {}
    last_checked = latest_run.get("checked_at_display", "Never")
    generated_at = dt.datetime.now(dt.timezone.utc).astimezone(dt.timezone(dt.timedelta(hours=8))).strftime("%Y-%m-%d %H:%M Asia/Shanghai")

    total_by_category = {key: 0 for key in CATEGORY_LABELS}
    total_by_lab = {key: 0 for key in LAB_LABELS}
    for article in articles:
        total_by_category[article.get("category")] = total_by_category.get(article.get("category"), 0) + 1
        lab = article_lab(article)
        total_by_lab[lab] = total_by_lab.get(lab, 0) + 1

    DOCS_DIR.mkdir(exist_ok=True)
    category_dir = DOCS_DIR / "categories"
    category_dir.mkdir(exist_ok=True)
    lab_dir = DOCS_DIR / "labs"
    lab_dir.mkdir(exist_ok=True)

    index_html = render_page(
        articles=articles,
        all_articles=articles,
        sources=sources,
        latest_run=latest_run,
        last_checked=last_checked,
        total_by_category=total_by_category,
        total_by_lab=total_by_lab,
        generated_at=generated_at,
        current_category=None,
        current_lab=None,
    )
    (DOCS_DIR / "index.html").write_text(index_html, encoding="utf-8")

    for category in CATEGORY_ORDER:
        category_articles = [article for article in articles if article.get("category") == category]
        category_html = render_page(
            articles=category_articles,
            all_articles=articles,
            sources=sources,
            latest_run=latest_run,
            last_checked=last_checked,
            total_by_category=total_by_category,
            total_by_lab=total_by_lab,
            generated_at=generated_at,
            current_category=category,
            current_lab=None,
        )
        (category_dir / f"{CATEGORY_SLUGS[category]}.html").write_text(category_html, encoding="utf-8")
    for lab in LAB_ORDER:
        lab_articles = [article for article in articles if article_lab(article) == lab]
        lab_html = render_page(
            articles=lab_articles,
            all_articles=articles,
            sources=sources,
            latest_run=latest_run,
            last_checked=last_checked,
            total_by_category=total_by_category,
            total_by_lab=total_by_lab,
            generated_at=generated_at,
            current_category=None,
            current_lab=lab,
        )
        (lab_dir / f"{LAB_SLUGS[lab]}.html").write_text(lab_html, encoding="utf-8")
    return 0


def render_page(
    *,
    articles: list[dict[str, Any]],
    all_articles: list[dict[str, Any]],
    sources: list[dict[str, Any]],
    latest_run: dict[str, Any],
    last_checked: str,
    total_by_category: dict[str, int],
    total_by_lab: dict[str, int],
    generated_at: str,
    current_category: str | None,
    current_lab: str | None,
) -> str:
    lab_run_counts = {lab: 0 for lab in LAB_ORDER}
    for source in sources:
        count = latest_run.get("source_counts", {}).get(source["id"], 0)
        lab = source_lab(source)
        lab_run_counts[lab] = lab_run_counts.get(lab, 0) + count
    source_rows = []
    for lab in LAB_ORDER:
        count = lab_run_counts.get(lab, 0)
        source_rows.append(
            f"""
            <li>
              <span>{esc(LAB_LABELS[lab])}</span>
              <strong>{count} new</strong>
            </li>
            """
        )

    if current_lab:
        nav_heading = "Topics"
        topic_counts = count_topics(articles)
        archive_buttons = "\n".join(
            f'<a href="#{esc(topic_anchor(topic))}"><span>{esc(TOPIC_LABELS.get(topic, topic))}</span><strong>{count}</strong></a>'
            for topic, count in topic_counts.items()
        )
        cards = render_lab_article_groups(articles)
    else:
        nav_heading = "Archive"
        archive_counts: dict[str, int] = {}
        for article in articles:
            date_key = article_date(article)
            archive_counts[date_key] = archive_counts.get(date_key, 0) + 1

        archive_buttons = "\n".join(
            f'<a href="#{esc(date_anchor(date_key))}"><span>{esc(archive_label(date_key))}</span><strong>{count}</strong></a>'
            for date_key, count in sorted(archive_counts.items(), reverse=True)
        )
        cards = render_article_groups(articles)
    if not cards:
        cards = """
        <article class="empty-state">
          <h2>No articles yet</h2>
          <p>After the first scheduled run, new posts will appear here with bilingual summaries and personal takes.</p>
        </article>
        """

    error_count = len(latest_run.get("errors", []))
    title = "AI Lab Tracker"
    feed_title = "New AI lab posts"
    eyebrow = "Latest Briefs"
    if current_category:
        title = f"{CATEGORY_LABELS[current_category]} - AI Lab Tracker"
        feed_title = f"{CATEGORY_LABELS[current_category]} Posts"
        eyebrow = "Category Briefs"
    if current_lab:
        title = f"{LAB_LABELS[current_lab]} - AI Lab Tracker"
        feed_title = f"{LAB_LABELS[current_lab]} Posts"
        eyebrow = "Lab Briefs"
    nested = bool(current_category or current_lab)
    stylesheet = "../styles.css" if nested else "styles.css"
    repo_href = "https://github.com/crash-zwt/anthropic-tracker"

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(title)}</title>
  <link rel="stylesheet" href="{stylesheet}">
</head>
<body>
  <main class="layout" id="top">
    <aside class="sidebar">
      <header>
        <p class="eyebrow">AI Lab Watch</p>
        <h1><a class="site-title" href="{home_href(nested)}">AI Lab Tracker</a></h1>
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
            <dd>{len(all_articles)}</dd>
          </div>
          <div>
            <dt>Errors</dt>
            <dd>{error_count}</dd>
          </div>
        </dl>
      </section>

      <section class="panel">
        <h2>Run Activity</h2>
        <ul class="source-list">
          {"".join(source_rows)}
        </ul>
      </section>

      <section class="panel">
        <h2>Labs</h2>
        <div class="lab-grid">
          {render_lab_stats(total_by_lab, current_lab, nested)}
        </div>
      </section>

      <section class="panel">
        <h2>{esc(nav_heading)}</h2>
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
          <p class="eyebrow">{esc(eyebrow)}</p>
          <h2>{esc(feed_title)}</h2>
        </div>
        <div class="header-actions">
          {render_all_posts_link(nested)}
          <a class="repo-link" href="{repo_href}">GitHub</a>
        </div>
      </div>
      {cards}
    </section>
  </main>
</body>
</html>
"""


def render_all_posts_link(nested: bool) -> str:
    if not nested:
        return ""
    return f'<a class="repo-link" href="{home_href(True)}">All Posts</a>'


def render_category_stat(category: str, count: int, current_category: str | None = None) -> str:
    active = " is-active" if current_category == category else ""
    return f"""
    <a class="category-stat category-{esc(category)}{active}" href="{esc(category_href(category, current_category))}">
      <span>{esc(CATEGORY_LABELS.get(category, category))}</span>
      <strong>{count}</strong>
    </a>
    """


def render_category_stats(total_by_category: dict[str, int], current_category: str | None = None) -> str:
    return "\n".join(
        render_category_stat(category, total_by_category.get(category, 0), current_category)
        for category in CATEGORY_ORDER
    )


def render_lab_stat(lab: str, count: int, current_lab: str | None = None, nested: bool = False) -> str:
    active = " is-active" if current_lab == lab else ""
    return f"""
    <a class="lab-stat lab-{esc(lab)}{active}" href="{esc(lab_href(lab, current_lab, nested))}">
      <span>{esc(LAB_LABELS.get(lab, lab))}</span>
      <strong>{count}</strong>
    </a>
    """


def render_lab_stats(total_by_lab: dict[str, int], current_lab: str | None = None, nested: bool = False) -> str:
    return "\n".join(
        render_lab_stat(lab, total_by_lab.get(lab, 0), current_lab, nested)
        for lab in LAB_ORDER
    )


def count_topics(articles: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for article in articles:
        topic = article_topic(article)
        counts[topic] = counts.get(topic, 0) + 1
    return {
        topic: counts[topic]
        for topic in TOPIC_ORDER
        if counts.get(topic, 0)
    }


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


def render_lab_article_groups(articles: list[dict[str, Any]]) -> str:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for article in articles:
        grouped.setdefault(article_topic(article), []).append(article)

    sections = []
    for topic in TOPIC_ORDER:
        topic_articles = grouped.get(topic, [])
        if not topic_articles:
            continue
        sections.append(
            f"""
            <section class="topic-section" id="{esc(topic_anchor(topic))}">
              <div class="topic-heading">
                <h3>{esc(TOPIC_LABELS.get(topic, topic))}</h3>
                <span>{len(topic_articles)} posts</span>
              </div>
              {render_article_groups(topic_articles)}
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
