# Anthropic Tracker

A lightweight GitHub Pages dashboard that tracks official Anthropic and Claude posts, summarizes new articles with an OpenAI-compatible model API, and publishes the results daily.

Live site after GitHub Pages is enabled:

```text
https://crash-zwt.github.io/anthropic-tracker/
```

## What It Tracks

- Anthropic News: model releases, company updates, policy, safety.
- Anthropic Alignment: alignment research posts.
- Claude Blog Agents: agent product updates and guides.
- Claude Blog Claude Code: Claude Code updates and workflows.

Sources are configured in `config/sources.json`.

## Required Secret

Add this repository secret in GitHub:

```text
XF_MAAS_API_KEY
```

The model config lives in `config/model.json`:

```json
{
  "provider": "openai_compatible",
  "base_url": "https://maas-coding-api.cn-huabei-1.xf-yun.com/v2",
  "model": "astron-code-latest",
  "api_key_env": "XF_MAAS_API_KEY"
}
```

Never commit API keys.

## GitHub Pages Setup

In the GitHub repo:

1. Go to `Settings -> Pages`.
2. Set `Source` to `Deploy from a branch`.
3. Set `Branch` to `main`.
4. Set folder to `/docs`.
5. Save.

## Running Locally

```bash
export XF_MAAS_API_KEY="your-key"
python scripts/check_and_summarize.py
python scripts/render_site.py
```

Open `docs/index.html` in a browser.

## Daily Schedule

The workflow runs at `01:07`, `01:37`, `02:07`, and `02:37 UTC`, which are `09:07`, `09:37`, `10:07`, and `10:37 Asia/Shanghai`.
The later runs are reliability fallbacks because GitHub scheduled workflows are best-effort and can be delayed or skipped.

Manual runs are available from `Actions -> Daily Anthropic Tracker -> Run workflow`.

For historical backfill, run the workflow manually with:

```text
backfill_bootstrap=true
max_new_articles=60
```

## Safety Limit

By default, each run summarizes at most 6 new articles:

```text
MAX_NEW_ARTICLES_PER_RUN=6
```

This prevents the first run from treating a full historical archive as one huge daily update. Increase it temporarily only when intentionally backfilling old posts.
