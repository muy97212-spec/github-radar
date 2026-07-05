# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A local CLI that scans fixed interest-domains on GitHub (via the **Search API**, not the un-filterable Trending page), then renders three ranked lists — **综合 / 标杆(top-5% by stars) / 爆发(by velocity)** — as themed HTML + Markdown reports written into the user's Obsidian vault. No LLM/AI is involved anywhere: "analysis" is pure arithmetic (sort + a weighted formula). Pure-Python, no paid dependencies.

## Commands

Uses a project venv — **requires Python 3.12** (system `python3` may lack deps).

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt   # one-time
cp config.example.yaml config.yaml                                   # then edit vault_path

.venv/bin/python -m pytest -q                                        # all tests
.venv/bin/python -m pytest tests/test_scoring.py -q                  # one file
.venv/bin/python -m pytest tests/test_scoring.py::test_name -q       # one test

export GITHUB_TOKEN="$(gh auth token)"   # raises Search rate limit; read from env only, never configured
.venv/bin/python radar.py                # rotation: run only TODAY's one board
.venv/bin/python radar.py --all          # warmup: run all boards in one pass (heavier)

.venv/bin/python scripts/make_previews.py   # regenerate web/_preview_*.html for eyeballing themes
```

Development is **TDD** (every `ghradar/*.py` has a matching `tests/test_*.py`). Running `radar.py` hits the GitHub API and writes into the configured vault path.

## Architecture (the cross-file picture)

**Pipeline** (`radar.py` orchestrates): `github_client.search_repos` (collect candidate pool per keyword) → `scoring.build_rankings` (enrich + rank) → `report.render_markdown`/`render_html` (per-board files) → `state.save_board_state` (cache) → `snapshot.save_snapshot` (merge star history) → `overview.render_*` (cross-board total view).

**Rotation is the central design.** `domains.select_domain(domains, when) = domains[when.toordinal() % len(domains)]` — stateless, date-keyed, picks ONE board per day (config order = cycle order, N boards = N-day cycle). `radar.main` branches on `--all` / `rotation` config. Because only one board runs per day, the dashboard/overview must reconstruct all boards from the **board-state cache**, not from a single run.

**Velocity is per-repo, never list-vs-list.** `snapshot.json` stores `{repos: {full_name: {stars, seen}}}` keyed by repo identity. `scoring.build_rankings` looks up each repo's own previous stars+date and computes `velocity = delta / days_since_that_repo_was_last_seen` — so rankings that completely change between rotations still compare correctly. First sighting → no history → velocity is **estimated** from repo age (`is_estimated=True`, labeled "估算"). `snapshot.save_snapshot(..., base=prev)` merges (updates today's repos, preserves the rest).

**Two output tiers, two storage locations:**
- Per-board reports → vault `GitHub雷达/<slug>/` (`<date>.md/.html` + stable `_latest.md/.html`). `slugify` turns `/`→`·`, strips spaces.
- Cross-board overview → vault root `_总览.md` (table, with `[[wikilinks]]` for Obsidian Graph) + `_仪表盘.html` (dashboard).
- `boards_state/<slug>.json` is a **trimmed** cache (only `combined[:5]` + `burst[:3]`, dropping landmark/first_run) kept in the project dir, NOT the vault. The dashboard/overview render from this cache, so they can refresh without re-hitting the API — but per-board reports **cannot** be regenerated from cache (they need full rankings).

**Single themed-HTML system.** All boards share ONE editorial newspaper layout; only the accent color + texture vary. `report._THEMES` is built by the `_ivory_theme(kicker, accent, deep, tex)` factory (shared warm-ivory base, CSS-variable-driven `_BASE_CSS`). `report.theme_accent(theme)` is the single source of accent color, so `overview.py` dashboard cards recolor in step. Adding a board = add a `domains` entry + a `themes` mapping (+ optionally a new `_ivory_theme`); the dashboard adapts to board count `n` dynamically (rotation track columns `--cols:n`, grid `--gcols`).

**Data-slot contract** (keep stable across `scoring`/`report`/`overview`/`state`): rankings dict = `{first_run, pool_size, combined, landmark, burst}`; each entry has `full_name, html_url, stars, velocity_per_day, delta, is_estimated, language, description, topics`. Scoring uses log-stock + linear-velocity min-max normalization, weighted by `config.weights` (default 0.4/0.6).

## Constraints

- `config.yaml` is **gitignored** (holds the user's real vault path); `config.example.yaml` is the shipped template. `load_config` requires `domains` and `vault_path`, reads `GITHUB_TOKEN` from env. If `vault_path` doesn't exist, `radar.base_folder` falls back to project `reports/`.
- Gitignored: `config.yaml`, `snapshot.json`, `boards_state/`, `reports/`, `web/`, `.venv/`, logs.
- Public repo `github.com/muy97212-spec/github-radar`. Design docs (the source of truth for intent) live in `docs/superpowers/{specs,plans}/`.
- Scheduling is OS-level: `scripts/run-radar.sh` (auto-resolves token) driven by `scripts/com.github-radar.plist` (launchd) — see README for cron/Windows.
