#!/usr/bin/env python3
"""Fetch configured sources, summarize new articles, and update tracker data."""

from __future__ import annotations

import datetime as dt
import email.utils
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "config"
DATA_DIR = ROOT / "data"

SOURCE_PATH = CONFIG_DIR / "sources.json"
MODEL_PATH = CONFIG_DIR / "model.json"
ARTICLES_PATH = DATA_DIR / "articles.json"
SEEN_PATH = DATA_DIR / "seen_articles.json"
RUNS_PATH = DATA_DIR / "daily_runs.json"

USER_AGENT = (
    "Mozilla/5.0 (compatible; anthropic-tracker/1.0; "
    "+https://github.com/crash-zwt/anthropic-tracker)"
)
MAX_ARTICLE_CHARS = 30000
MAX_NEW_ARTICLES_PER_RUN = int(os.getenv("MAX_NEW_ARTICLES_PER_RUN", "6"))
BACKFILL_BOOTSTRAP = os.getenv("BACKFILL_BOOTSTRAP", "").lower() in {"1", "true", "yes"}


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[dict[str, str]] = []
        self._current_href: str | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        attr_map = dict(attrs)
        href = attr_map.get("href")
        if href:
            self._current_href = href
            self._text = []

    def handle_data(self, data: str) -> None:
        if self._current_href is not None:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._current_href is not None:
            text = normalize_space(" ".join(self._text))
            self.links.append({"href": self._current_href, "text": text})
            self._current_href = None
            self._text = []


class TextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript", "svg"}:
            self.skip_depth += 1
        if tag in {"p", "h1", "h2", "h3", "li", "blockquote"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript", "svg"} and self.skip_depth:
            self.skip_depth -= 1
        if tag in {"p", "h1", "h2", "h3", "li", "blockquote"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.skip_depth:
            self.parts.append(data)

    def text(self) -> str:
        return normalize_space("\n".join(self.parts))


def normalize_space(value: str) -> str:
    value = html.unescape(value)
    value = re.sub(r"[ \t\r\f\v]+", " ", value)
    value = re.sub(r"\n\s+", "\n", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def fetch_url(url: str) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        raw = response.read()
        charset = response.headers.get_content_charset() or "utf-8"
        return raw.decode(charset, errors="replace")


def canonical_url(base_url: str, href: str) -> str:
    absolute = urllib.parse.urljoin(base_url, href)
    parsed = urllib.parse.urlparse(absolute)
    clean = parsed._replace(query="", fragment="")
    return urllib.parse.urlunparse(clean)


def allowed_article_url(url: str) -> bool:
    parsed = urllib.parse.urlparse(url)
    if parsed.netloc not in {"www.anthropic.com", "anthropic.com", "claude.com", "openai.com", "www.openai.com"}:
        return False
    path = parsed.path.rstrip("/")
    if path in {"", "/news", "/research", "/blog"}:
        return False
    if path.startswith("/blog/category/") or path.startswith("/research/team/"):
        return False
    if parsed.netloc in {"openai.com", "www.openai.com"} and path.startswith("/news/"):
        return False
    return (
        path.startswith("/news/")
        or path.startswith("/research/")
        or path.startswith("/blog/")
        or path.startswith("/index/")
    )


def discover_articles(source: dict[str, Any]) -> list[dict[str, str]]:
    if source["url"].endswith(".xml"):
        return discover_rss_articles(source)

    source_html = fetch_url(source["url"])
    parser = LinkParser()
    parser.feed(source_html)

    articles: dict[str, dict[str, str]] = {}
    for link in parser.links:
        url = canonical_url(source["url"], link["href"])
        title = link["text"]
        if not title or len(title) < 8:
            continue
        if not allowed_article_url(url):
            continue
        if url == source["url"].rstrip("/"):
            continue
        if not passes_source_filters(source, title, url):
            continue
        articles[url] = {
            "url": url,
            "title": title,
            "source_id": source["id"],
            "source_name": source["name"],
            "category": source["category"],
            "vendor": source["vendor"],
        }
    return list(articles.values())


def discover_rss_articles(source: dict[str, Any]) -> list[dict[str, str]]:
    source_xml = fetch_url(source["url"])
    root = ET.fromstring(source_xml)
    articles: dict[str, dict[str, str]] = {}
    for item in root.findall("./channel/item"):
        title = normalize_space(item.findtext("title") or "")
        url = canonical_url(source["url"], item.findtext("link") or "")
        description = normalize_space(item.findtext("description") or "")
        published = normalize_date(item.findtext("pubDate") or "")
        if not title or not allowed_article_url(url):
            continue
        if not passes_source_filters(source, title, url, description):
            continue
        articles[url] = {
            "url": url,
            "title": title,
            "source_id": source["id"],
            "source_name": source["name"],
            "category": source["category"],
            "vendor": source["vendor"],
            "published_at": published,
            "text": description,
        }
    return list(articles.values())


def passes_source_filters(source: dict[str, Any], title: str, url: str, extra_text: str = "") -> bool:
    haystack = f"{title} {url} {extra_text}".lower()
    include_keywords = [item.lower() for item in source.get("include_keywords", [])]
    exclude_keywords = [item.lower() for item in source.get("exclude_keywords", [])]
    if include_keywords and not any(keyword in haystack for keyword in include_keywords):
        return False
    if exclude_keywords and any(keyword in haystack for keyword in exclude_keywords):
        return False
    return True


def extract_article(url: str) -> dict[str, str]:
    page = fetch_url(url)
    title = first_match(page, r"<title[^>]*>(.*?)</title>") or ""
    title = re.sub(r"\s*[\\|]\s*(Anthropic|Claude).*$", "", normalize_space(title))

    parser = TextParser()
    parser.feed(page)
    text = parser.text()
    published = extract_published_date(page, text)
    return {
        "title": title,
        "published_at": published,
        "text": text[:MAX_ARTICLE_CHARS],
    }


def first_match(text: str, pattern: str) -> str | None:
    match = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    return normalize_space(match.group(1))


def extract_published_date(page: str, visible_text: str = "") -> str:
    candidates = [
        first_match(page, r'"datePublished"\s*:\s*"([^"]+)"'),
        first_match(page, r'"publishedAt"\s*:\s*"([^"]+)"'),
        first_match(page, r'"date"\s*:\s*"([^"]+)"'),
        first_match(page, r"<time[^>]+datetime=[\"']([^\"']+)"),
        first_match(page, r"<meta[^>]+property=[\"']article:published_time[\"'][^>]+content=[\"']([^\"']+)"),
        first_match(page, r"<meta[^>]+name=[\"']date[\"'][^>]+content=[\"']([^\"']+)"),
        first_match(page, r"<meta[^>]+name=[\"']publish_date[\"'][^>]+content=[\"']([^\"']+)"),
        first_match(page, r"(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日"),
        first_match(visible_text, r"(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日"),
        first_match(visible_text, r"\b([A-Z][a-z]{2,8}\s+\d{1,2},\s+\d{4})\b"),
    ]
    for candidate in candidates:
        parsed = normalize_date(candidate)
        if parsed:
            return parsed
    return ""


def normalize_date(value: str | None) -> str:
    if not value:
        return ""
    value = normalize_space(value)
    chinese = re.match(r"^(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日$", value)
    if chinese:
        year, month, day = chinese.groups()
        return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
    iso = re.match(r"^(\d{4}-\d{2}-\d{2})", value)
    if iso:
        return iso.group(1)
    for fmt in ("%b %d, %Y", "%B %d, %Y", "%b %d %Y", "%B %d %Y"):
        try:
            return dt.datetime.strptime(value, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    try:
        return email.utils.parsedate_to_datetime(value).date().isoformat()
    except (TypeError, ValueError):
        pass
    return value


def summarize_with_model(article: dict[str, Any], model_config: dict[str, Any]) -> dict[str, Any]:
    api_key_env = model_config["api_key_env"]
    api_key = os.getenv(api_key_env)
    if not api_key:
        raise RuntimeError(f"Missing required environment variable: {api_key_env}")

    endpoint = model_config["base_url"].rstrip("/") + "/chat/completions"
    prompt = build_prompt(article)
    payload = {
        "model": model_config["model"],
        "temperature": model_config.get("temperature", 0.2),
        "max_tokens": model_config.get("max_tokens", 1800),
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are an AI lab research and product analyst. "
                    "Return strict JSON only. No markdown fences."
                ),
            },
            {"role": "user", "content": prompt},
        ],
    }
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        endpoint,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=90) as response:
        result = json.loads(response.read().decode("utf-8"))

    content = result["choices"][0]["message"]["content"]
    return parse_json_object(content)


def build_prompt(article: dict[str, Any]) -> str:
    return f"""
Summarize this AI lab blog post for a Chinese reader who tracks model releases,
alignment, agents, Claude Code, OpenAI Codex, and OpenAI platform updates.

Style:
- Use Chinese-English mixed language.
- Keep it concise but useful.
- Include pragmatic personal judgment, not marketing language.
- Preserve key English technical terms.
- Be careful: if the article is thin or mostly an index page, say so.

Return strict JSON with this schema:
{{
  "tldr": "one paragraph",
  "key_points": ["3-6 bullets"],
  "why_it_matters": "one paragraph",
  "my_take": "one paragraph",
  "tags": ["2-6 short tags"],
  "importance": "low|medium|high"
}}

Metadata:
Title: {article.get("title")}
URL: {article.get("url")}
Category: {article.get("category")}
Source: {article.get("source_name")}

Article text:
{article.get("text", "")}
""".strip()


def parse_json_object(content: str) -> dict[str, Any]:
    content = content.strip()
    content = re.sub(r"^```(?:json)?", "", content).strip()
    content = re.sub(r"```$", "", content).strip()
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        start = content.find("{")
        end = content.rfind("}")
        if start == -1 or end == -1:
            raise
        data = json.loads(content[start : end + 1])
    return {
        "tldr": str(data.get("tldr", "")).strip(),
        "key_points": [str(item).strip() for item in data.get("key_points", []) if str(item).strip()],
        "why_it_matters": str(data.get("why_it_matters", "")).strip(),
        "my_take": str(data.get("my_take", "")).strip(),
        "tags": [str(item).strip() for item in data.get("tags", []) if str(item).strip()],
        "importance": str(data.get("importance", "medium")).strip().lower(),
    }


def main() -> int:
    sources = load_json(SOURCE_PATH, {"sources": []})["sources"]
    model_config = load_json(MODEL_PATH, {})
    api_key_env = model_config.get("api_key_env")
    if api_key_env and not os.getenv(api_key_env):
        print(f"Missing required environment variable: {api_key_env}", file=sys.stderr)
        return 1

    seen = load_json(SEEN_PATH, {})
    articles = load_json(ARTICLES_PATH, [])
    runs = load_json(RUNS_PATH, [])

    now = dt.datetime.now(dt.timezone.utc)
    run = {
        "checked_at": now.isoformat(),
        "checked_at_display": now.astimezone(dt.timezone(dt.timedelta(hours=8))).strftime("%Y-%m-%d %H:%M Asia/Shanghai"),
        "new_count": 0,
        "backfill_bootstrap": BACKFILL_BOOTSTRAP,
        "source_counts": {},
        "errors": [],
    }

    existing_urls = {item["url"] for item in articles}
    new_articles: list[dict[str, Any]] = []

    for source in sources:
        if len(new_articles) >= MAX_NEW_ARTICLES_PER_RUN:
            run["source_counts"][source["id"]] = 0
            continue
        try:
            candidates = discover_articles(source)
            source_new = 0
            for candidate in candidates:
                if len(new_articles) >= MAX_NEW_ARTICLES_PER_RUN:
                    break
                url = candidate["url"]
                seen_entry = seen.get(url)
                can_backfill = BACKFILL_BOOTSTRAP and seen_entry and seen_entry.get("bootstrap_only")
                if (seen_entry and not can_backfill) or url in existing_urls:
                    continue
                try:
                    if not candidate.get("text"):
                        extracted = extract_article(url)
                        candidate["title"] = extracted["title"] or candidate["title"]
                        candidate["published_at"] = extracted["published_at"]
                        candidate["text"] = extracted["text"]
                    try:
                        summary = summarize_with_model(candidate, model_config)
                    except Exception as exc:
                        run["errors"].append({"url": url, "error": str(exc)})
                        continue

                    record = {
                        "id": stable_id(url),
                        "url": url,
                        "title": candidate["title"],
                        "source_id": candidate["source_id"],
                        "source_name": candidate["source_name"],
                        "category": candidate["category"],
                        "vendor": candidate["vendor"],
                        "published_at": candidate.get("published_at", ""),
                        "added_at": now.isoformat(),
                        "summary": summary,
                    }
                    articles.insert(0, record)
                    new_articles.append(record)
                    seen[url] = {
                        "title": record["title"],
                        "source_id": record["source_id"],
                        "first_seen_at": now.isoformat(),
                    }
                    source_new += 1
                    time.sleep(1)
                except Exception as exc:
                    run["errors"].append({"url": url, "error": str(exc)})
            run["source_counts"][source["id"]] = source_new
        except Exception as exc:
            run["errors"].append({"source": source["id"], "error": str(exc)})
            run["source_counts"][source["id"]] = 0

    run["new_count"] = len(new_articles)
    runs.insert(0, run)
    runs = runs[:120]

    save_json(ARTICLES_PATH, articles)
    save_json(SEEN_PATH, seen)
    save_json(RUNS_PATH, runs)

    print(json.dumps({"new_count": len(new_articles), "errors": run["errors"]}, ensure_ascii=False))
    return 0


def stable_id(value: str) -> str:
    import hashlib

    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:12]


if __name__ == "__main__":
    sys.exit(main())
