# AI Lab Tracker

A lightweight GitHub Pages dashboard that tracks official Anthropic, Claude, OpenAI, Google Gemini, and Thinking Machines posts. The site is now maintained in manual Codex mode because the previous OpenAI-compatible model key is no longer reliable.

Live site after GitHub Pages is enabled:

```text
https://crash-zwt.github.io/anthropic-tracker/
```

## What It Tracks

- Anthropic News: model releases, company updates, policy, safety.
- Anthropic Alignment: alignment research posts.
- Claude Blog Agents: agent product updates and guides.
- Claude Blog Claude Code: Claude Code updates and workflows.
- OpenAI Model: GPT/model/capability release posts from the official OpenAI RSS feed.
- OpenAI Agents: agent architecture, Responses API, orchestration, and workflow posts from the official OpenAI RSS feed.
- OpenAI Code: Codex product and engineering posts from the official OpenAI RSS feed.
- Google Gemini: Gemini-related posts from Google's official AI blog RSS feed.
- Thinking Machines: official Thinking Machines blog and news posts discovered through its sitemap.

Sources are configured in `config/sources.json`.

The main dashboard is lab-first: left navigation links to institution pages such as OpenAI, Google, and Thinking Machines. Each lab page then groups posts into internal topics such as Model, Alignment, Agents, Code, Gemini, or Methods & Research.

## Summary Mode

The default maintenance path is manual Codex mode:

1. Ask Codex to update the tracker.
2. Codex checks the configured sources, reads new articles, writes bilingual summaries with personal judgment, renders the site, verifies navigation, and pushes the update.

The old GitHub Actions API summarizer is kept only as a legacy fallback for a future valid OpenAI-compatible key. It is no longer scheduled automatically.

If you intentionally re-enable API summarization, add this repository secret in GitHub:

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

## Running Locally With A Model API

```bash
export XF_MAAS_API_KEY="your-key"
python scripts/check_and_summarize.py
python scripts/render_site.py
```

Open `docs/index.html` in a browser.

## Manual Updates

There is no automatic daily schedule at the moment. This is intentional: the old third-party API key stopped being reliable, and GitHub Actions cannot use the local Codex subscription.

Manual legacy API runs are still available from `Actions -> Daily AI Lab Tracker -> Run workflow`, but use them only after configuring a working `XF_MAAS_API_KEY`.

For historical backfill in legacy API mode, run the workflow manually with:

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
