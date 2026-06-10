# Changelog

## 2026-06-09

- Created the initial Anthropic Tracker repo structure.
- Added configurable sources for Anthropic News, Alignment, Claude Agents, and Claude Code.
- Added OpenAI-compatible model config for `astron-code-latest` through `XF_MAAS_API_KEY`.
- Added daily GitHub Actions workflow scheduled for 09:00 Asia/Shanghai.
- Added data files for seen URLs, summarized articles, and run history.
- Added static dashboard rendering into `docs/index.html` for GitHub Pages.
- Added `AGENTS.md` with maintenance instructions for future AI-assisted changes.
- Added a default `MAX_NEW_ARTICLES_PER_RUN=6` guard so first runs do not summarize an entire historical archive.
- Added `scripts/bootstrap_seen.py` so existing historical source links can be marked as seen after setup.
- Added manual workflow inputs for historical backfill of `bootstrap_only` links.
- Scoped Anthropic News to model release posts with source-level keyword filters.
- Added `scripts/prune_filtered_sources.py` to clean existing data after source filters change.
- Added publish-date archive navigation on the dashboard so readers can jump to articles from other dates.
- Improved publish-date extraction to support Chinese dates such as `2026年4月24日`, common meta tags, and ISO dates.
- Added `scripts/refresh_published_dates.py` and refreshed existing articles so the archive uses real article dates instead of run dates.
- Excluded category/team landing pages from article discovery and pruned existing landing-page records.
- Added static category pages under `docs/categories/` and made category cards link to their dedicated article columns.
- Made the sticky sidebar independently scrollable so Archive remains reachable on shorter screens.
- Added `scripts/verify_site.py` for local navigation checks across archive links and category pages.
- Added the site navigation verifier to the daily GitHub Actions workflow.
- Moved scheduled runs away from the top of the hour and added a second daily fallback run at 09:37 Asia/Shanghai.
