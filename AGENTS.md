# Agent Maintenance Guide

This repo is designed to be easy for coding agents to extend safely.

## Core Workflow

1. Read `config/sources.json`.
2. Run `python scripts/check_and_summarize.py`.
3. Run `python scripts/render_site.py`.
4. Review changes in `data/*.json` and `docs/index.html`.

## Adding A New Source

Add an entry to `config/sources.json`:

```json
{
  "id": "openai_news",
  "name": "OpenAI News",
  "url": "https://openai.com/news/",
  "category": "model",
  "vendor": "OpenAI",
  "description": "OpenAI model and product announcements."
}
```

Use stable, lowercase `id` values. Supported current categories:

- `model`
- `alignment`
- `agents`
- `claude_code`

If adding a category, also update `CATEGORY_LABELS` and styles in `scripts/render_site.py` and `docs/styles.css`.

Sources can define `include_keywords` and `exclude_keywords`. Use these for broad landing pages such as Anthropic News where only a subset of posts should be tracked.

If filters change after data has already been collected, run `python scripts/prune_filtered_sources.py` to remove records that no longer match.

## Changing Model Provider

Edit `config/model.json`. Prefer OpenAI-compatible providers that expose:

```text
POST {base_url}/chat/completions
Authorization: Bearer $API_KEY
```

Do not commit secrets. Use GitHub Secrets and reference the secret name through `api_key_env`.

## Data Files

- `data/seen_articles.json`: URL-level dedupe state.
- `data/articles.json`: summarized article records.
- `data/daily_runs.json`: run history and source-level counts.

Do not manually delete entries unless intentionally reprocessing articles.

## Run Limit

`scripts/check_and_summarize.py` caps processing with `MAX_NEW_ARTICLES_PER_RUN`, defaulting to 6. Keep this guard unless the user explicitly wants a historical backfill.

## Bootstrap Existing Posts

Use `python scripts/bootstrap_seen.py` after the initial run if the user wants to follow only future posts. It marks currently discoverable source links as seen without creating article summaries.

If the user later wants those historical posts summarized, run `scripts/check_and_summarize.py` with `BACKFILL_BOOTSTRAP=1`. In GitHub Actions, use workflow dispatch inputs `backfill_bootstrap=true` and a larger `max_new_articles`.

## Design Rules

Keep the site a quiet dashboard:

- Summary/status on the left.
- Article feed on the right.
- Category colors for quick scanning.
- Keep every article card tied to an `Original Link`.

## Change Log

When changing behavior, update `CHANGELOG.md` so future agents know what changed and why.
