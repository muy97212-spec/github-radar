# GitHub 雷达(GitHub Radar)Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 一个本地 Python CLI,扫描固定关注领域的 GitHub 项目,产出"综合/标杆/爆发"三榜 Markdown 报告并写入 Obsidian vault。

**Architecture:** 用 GitHub REST Search API 按领域关键词抓宽候选池(低 star 门槛);读本地 JSON 快照算真实增速(无历史则用"年龄均速"代理);存量与增速作为**两个独立排名**(前 5% 只管标杆榜,不淘汰黑马);渲染 Markdown 写入 vault,同时覆盖快照供下次对比。

**Tech Stack:** Python 3.12 · `requests` · `pyyaml` · `pytest`。包名 `ghradar/`(避免与入口 `radar.py` 同名冲突),入口 `python radar.py`。

**关键设计依据(来自调研):** 官方 GitHub Trending 不在 API 里、只能按语言筛,所以不爬 trending 页,改用 Search API + 本地快照算领域内真增速。详见 spec `docs/superpowers/specs/2026-05-30-github-radar-design.md`。

**所有命令均在项目根目录 `/Users/jenson/github-radar/` 下执行。** 每次 commit 消息结尾加
`Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`(为简洁,下文示例从略)。

**数据结构约定:**

仓库 dict(由 API 归一化得到):
```python
{
  "full_name": "owner/repo",
  "html_url": "https://github.com/owner/repo",
  "stars": 12340,            # int
  "language": "Python",      # str | None
  "description": "...",      # str(可空)
  "topics": ["a", "b"],      # list[str]
  "created_at": "2024-01-01T00:00:00Z",  # ISO8601 | None
}
```

快照 JSON:
```json
{ "generated_at": "2026-05-30T01:00:00+00:00", "repos": { "owner/repo": 12000 } }
```

`build_rankings(...)` 返回:
```python
{
  "first_run": bool,
  "pool_size": int,
  "combined": [enriched, ...],   # 已按综合分降序、截 top_k
  "landmark": [enriched, ...],   # 存量前 5%、截 top_k
  "burst":    [enriched, ...],   # 增速降序、截 top_k
}
```
enriched = 仓库 dict 追加:`delta`(int|None,真实涨幅)、`velocity_value`(float,每日均速)、
`velocity_per_day`(=velocity_value)、`is_estimated`(bool)、`stock_score`、`velocity_score`、`combined_score`。

---

## File Structure

```
github-radar/
  radar.py                  # CLI 入口(python radar.py)
  conftest.py               # 空文件,让 pytest 把项目根加入 sys.path
  config.yaml               # 领域关键词与阈值
  requirements.txt
  ghradar/
    __init__.py
    config.py               # load_config / all_keywords
    github_client.py        # GitHubClient.search_repos
    snapshot.py             # load_snapshot / save_snapshot
    scoring.py              # build_rankings(纯函数,无 IO)
    report.py               # render_markdown
  tests/
    test_config.py
    test_snapshot.py
    test_scoring.py
    test_github_client.py
    test_report.py
  snapshot.json             # 运行时生成(已 gitignore)
  reports/                  # vault 不可用时降级输出(已 gitignore)
```

---

## Task 1: 项目骨架与依赖

**Files:**
- Create: `requirements.txt`
- Create: `conftest.py`
- Create: `ghradar/__init__.py`
- Create: `config.yaml`

- [ ] **Step 1: 写 `requirements.txt`**

```
requests>=2.31
PyYAML>=6.0
pytest>=8.0
```

- [ ] **Step 2: 创建空的 `conftest.py` 与 `ghradar/__init__.py`**

```bash
: > conftest.py
: > ghradar/__init__.py
```

(`conftest.py` 留空即可;它的存在让 pytest 把项目根目录加入 `sys.path`,从而能 `import ghradar`。)

- [ ] **Step 3: 写 `config.yaml`(关键词已预填两个领域)**

```yaml
domains:
  自动化与工作流: [workflow automation, RPA, browser automation, playwright, n8n, scraping]
  内容创作与分发: [content automation, social media automation, video generation,
                  auto upload, multi-platform publish, AIGC content]
pool_min_stars: 50
fetch_cap_per_keyword: 300
top_k: 15
burst_min_delta: 20
weights: { stock: 0.4, velocity: 0.6 }
vault_path: "/Users/jenson/Documents/Obsidian Vault"
report_folder: "GitHub雷达"
```

- [ ] **Step 4: 安装依赖并确认 pytest 可运行**

Run: `python3 -m pip install -r requirements.txt && python3 -m pytest -q`
Expected: pytest 启动,输出 `no tests ran`(还没有测试)。

- [ ] **Step 5: Commit**

```bash
git add requirements.txt conftest.py ghradar/__init__.py config.yaml
git commit -m "chore: project scaffold, deps and config"
```

---

## Task 2: `config.py` — 读取与校验配置

**Files:**
- Create: `ghradar/config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_config.py
import textwrap
import pytest
from ghradar.config import load_config, all_keywords

def _write(tmp_path, body):
    p = tmp_path / "config.yaml"
    p.write_text(textwrap.dedent(body), encoding="utf-8")
    return str(p)

def test_defaults_filled(tmp_path, monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    path = _write(tmp_path, """
        domains: {A: [x]}
        vault_path: /tmp/vault
    """)
    cfg = load_config(path)
    assert cfg["pool_min_stars"] == 50
    assert cfg["top_k"] == 15
    assert cfg["weights"] == {"stock": 0.4, "velocity": 0.6}
    assert cfg["report_folder"] == "GitHub雷达"
    assert cfg["github_token"] is None

def test_partial_weights_merge(tmp_path):
    path = _write(tmp_path, """
        domains: {A: [x]}
        vault_path: /tmp/vault
        weights: {velocity: 0.7}
    """)
    cfg = load_config(path)
    assert cfg["weights"] == {"stock": 0.4, "velocity": 0.7}

def test_missing_domains_raises(tmp_path):
    path = _write(tmp_path, "vault_path: /tmp/vault\n")
    with pytest.raises(ValueError):
        load_config(path)

def test_token_from_env(tmp_path, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "tok123")
    path = _write(tmp_path, "domains: {A: [x]}\nvault_path: /tmp/vault\n")
    assert load_config(path)["github_token"] == "tok123"

def test_all_keywords_dedupes_preserving_order(tmp_path):
    path = _write(tmp_path, """
        domains:
          A: [x, y]
          B: [y, z]
        vault_path: /tmp/vault
    """)
    cfg = load_config(path)
    assert all_keywords(cfg) == ["x", "y", "z"]
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python3 -m pytest tests/test_config.py -q`
Expected: FAIL（`ModuleNotFoundError: No module named 'ghradar.config'`)

- [ ] **Step 3: 实现 `ghradar/config.py`**

```python
import os
import yaml

DEFAULTS = {
    "pool_min_stars": 50,
    "fetch_cap_per_keyword": 300,
    "top_k": 15,
    "burst_min_delta": 20,
    "weights": {"stock": 0.4, "velocity": 0.6},
    "report_folder": "GitHub雷达",
}

def load_config(path):
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    cfg = dict(DEFAULTS)
    cfg.update(raw)
    weights = dict(DEFAULTS["weights"])
    weights.update(raw.get("weights") or {})
    cfg["weights"] = weights
    if not cfg.get("domains"):
        raise ValueError("config 缺少 domains")
    if not cfg.get("vault_path"):
        raise ValueError("config 缺少 vault_path")
    cfg["github_token"] = os.environ.get("GITHUB_TOKEN")
    return cfg

def all_keywords(cfg):
    seen, out = set(), []
    for kw_list in cfg["domains"].values():
        for k in kw_list:
            if k not in seen:
                seen.add(k)
                out.append(k)
    return out
```

- [ ] **Step 4: 跑测试确认通过**

Run: `python3 -m pytest tests/test_config.py -q`
Expected: PASS（5 passed)

- [ ] **Step 5: Commit**

```bash
git add ghradar/config.py tests/test_config.py
git commit -m "feat(config): load/validate config with defaults and env token"
```

---

## Task 3: `snapshot.py` — 本地快照读写

**Files:**
- Create: `ghradar/snapshot.py`
- Test: `tests/test_snapshot.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_snapshot.py
from ghradar.snapshot import load_snapshot, save_snapshot

def test_load_missing_returns_empty(tmp_path):
    snap = load_snapshot(str(tmp_path / "nope.json"))
    assert snap == {"generated_at": None, "repos": {}}

def test_save_then_load_roundtrip(tmp_path):
    path = str(tmp_path / "snap.json")
    repos = [
        {"full_name": "a/b", "stars": 100},
        {"full_name": "c/d", "stars": 200},
    ]
    saved = save_snapshot(path, repos, generated_at="2026-05-30T00:00:00+00:00")
    assert saved["repos"] == {"a/b": 100, "c/d": 200}
    loaded = load_snapshot(path)
    assert loaded["generated_at"] == "2026-05-30T00:00:00+00:00"
    assert loaded["repos"]["a/b"] == 100
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python3 -m pytest tests/test_snapshot.py -q`
Expected: FAIL（`No module named 'ghradar.snapshot'`)

- [ ] **Step 3: 实现 `ghradar/snapshot.py`**

```python
import json
import os
from datetime import datetime, timezone

def load_snapshot(path):
    if not os.path.exists(path):
        return {"generated_at": None, "repos": {}}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_snapshot(path, repos, generated_at=None):
    generated_at = generated_at or datetime.now(timezone.utc).isoformat()
    data = {
        "generated_at": generated_at,
        "repos": {r["full_name"]: r["stars"] for r in repos},
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return data
```

- [ ] **Step 4: 跑测试确认通过**

Run: `python3 -m pytest tests/test_snapshot.py -q`
Expected: PASS（2 passed)

- [ ] **Step 5: Commit**

```bash
git add ghradar/snapshot.py tests/test_snapshot.py
git commit -m "feat(snapshot): json star snapshot load/save"
```

---

## Task 4: `scoring.py` — 三榜打分(核心,纯函数)

**Files:**
- Create: `ghradar/scoring.py`
- Test: `tests/test_scoring.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_scoring.py
from datetime import datetime, timezone
from ghradar.scoring import build_rankings, _minmax

CFG = {"top_k": 15, "burst_min_delta": 20, "weights": {"stock": 0.4, "velocity": 0.6}}
NOW = datetime(2026, 5, 30, tzinfo=timezone.utc)

def _repo(name, stars, created="2024-01-01T00:00:00Z"):
    return {"full_name": name, "html_url": f"https://github.com/{name}",
            "stars": stars, "language": "Python", "description": "", "topics": [],
            "created_at": created}

def test_minmax_basic():
    assert _minmax([0, 5, 10]) == [0.0, 0.5, 1.0]

def test_minmax_all_equal_returns_ones():
    assert _minmax([7, 7, 7]) == [1.0, 1.0, 1.0]

def test_minmax_single_and_empty():
    assert _minmax([3]) == [1.0]
    assert _minmax([]) == []

def test_first_run_marks_estimated_and_uses_proxy():
    repos = [_repo("a/b", 100), _repo("c/d", 200)]
    r = build_rankings(repos, {"generated_at": None, "repos": {}}, CFG, now=NOW)
    assert r["first_run"] is True
    for e in r["combined"]:
        assert e["is_estimated"] is True
        assert e["delta"] is None
        assert e["velocity_value"] > 0  # stars / age_days

def test_velocity_uses_real_delta_when_history():
    repos = [_repo("a/b", 150), _repo("c/d", 205)]
    prev = {"generated_at": "2026-05-20T00:00:00+00:00", "repos": {"a/b": 50, "c/d": 200}}
    r = build_rankings(repos, prev, CFG, now=NOW)
    assert r["first_run"] is False
    by_name = {e["full_name"]: e for e in r["combined"]}
    assert by_name["a/b"]["delta"] == 100       # 150 - 50
    assert by_name["a/b"]["is_estimated"] is False
    # 10 天涨 100 → 10/天
    assert round(by_name["a/b"]["velocity_per_day"], 1) == 10.0

def test_burst_filters_below_min_delta():
    repos = [_repo("big/slow", 9000), _repo("small/fast", 300)]
    prev = {"generated_at": "2026-05-29T00:00:00+00:00",
            "repos": {"big/slow": 8995, "small/fast": 200}}  # +5 vs +100
    r = build_rankings(repos, prev, CFG, now=NOW)
    names = [e["full_name"] for e in r["burst"]]
    assert "small/fast" in names      # +100 >= 20
    assert "big/slow" not in names    # +5 < 20

def test_burst_includes_estimated_on_first_run():
    repos = [_repo("a/b", 100)]
    r = build_rankings(repos, {"generated_at": None, "repos": {}}, CFG, now=NOW)
    assert [e["full_name"] for e in r["burst"]] == ["a/b"]

def test_landmark_takes_top_5_percent():
    repos = [_repo(f"o/r{i}", stars=i) for i in range(1, 101)]  # 100 个,star 1..100
    r = build_rankings(repos, {"generated_at": None, "repos": {}}, CFG, now=NOW)
    # 5% of 100 = 5 个,且都是 star 最高的
    assert len(r["landmark"]) == 5
    assert [e["stars"] for e in r["landmark"]] == [100, 99, 98, 97, 96]

def test_combined_weighting_orders_results():
    # 一个超高星低增速,一个低星超高增速;权重偏增速 → 高增速应排前
    repos = [_repo("big/x", 100000), _repo("rocket/y", 500)]
    prev = {"generated_at": "2026-05-29T00:00:00+00:00",
            "repos": {"big/x": 99990, "rocket/y": 100}}  # +10 vs +400
    r = build_rankings(repos, prev, CFG, now=NOW)
    assert r["combined"][0]["full_name"] == "rocket/y"
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python3 -m pytest tests/test_scoring.py -q`
Expected: FAIL（`No module named 'ghradar.scoring'`)

- [ ] **Step 3: 实现 `ghradar/scoring.py`**

```python
import math
from datetime import datetime, timezone

def _parse_iso(s):
    if not s:
        return None
    return datetime.fromisoformat(s.replace("Z", "+00:00"))

def _minmax(values):
    if not values:
        return []
    lo, hi = min(values), max(values)
    if hi == lo:
        return [1.0 for _ in values]
    return [(v - lo) / (hi - lo) for v in values]

def _age_days(created_at, now):
    created = _parse_iso(created_at)
    if not created:
        return 1.0
    return max((now - created).total_seconds() / 86400.0, 1.0)

def build_rankings(repos, prev_snapshot, config, now=None):
    now = now or datetime.now(timezone.utc)
    prev_repos = (prev_snapshot or {}).get("repos") or {}
    first_run = len(prev_repos) == 0
    prev_time = _parse_iso((prev_snapshot or {}).get("generated_at"))
    elapsed_days = max((now - prev_time).total_seconds() / 86400.0, 1.0) if prev_time else 1.0

    enriched = []
    for r in repos:
        name, stars = r["full_name"], r["stars"]
        has_prev = (not first_run) and (name in prev_repos)
        if has_prev:
            delta = max(stars - prev_repos[name], 0)
            velocity_value = delta / elapsed_days
            is_estimated = False
        else:
            delta = None
            velocity_value = stars / _age_days(r.get("created_at"), now)
            is_estimated = True
        e = dict(r)
        e.update(delta=delta, velocity_value=velocity_value,
                 velocity_per_day=velocity_value, is_estimated=is_estimated)
        enriched.append(e)

    stock_scores = _minmax([math.log(e["stars"] + 1) for e in enriched])
    velocity_scores = _minmax([e["velocity_value"] for e in enriched])
    w = config["weights"]
    for e, ss, vs in zip(enriched, stock_scores, velocity_scores):
        e["stock_score"] = ss
        e["velocity_score"] = vs
        e["combined_score"] = w["stock"] * ss + w["velocity"] * vs

    top_k = config["top_k"]
    combined = sorted(enriched, key=lambda e: e["combined_score"], reverse=True)[:top_k]

    by_stars = sorted(enriched, key=lambda e: e["stars"], reverse=True)
    cutoff = max(1, math.ceil(len(by_stars) * 0.05))
    landmark = by_stars[:cutoff][:top_k]

    burst_min = config["burst_min_delta"]
    burst_candidates = [
        e for e in enriched
        if e["is_estimated"] or (e["delta"] is not None and e["delta"] >= burst_min)
    ]
    burst = sorted(burst_candidates, key=lambda e: e["velocity_value"], reverse=True)[:top_k]

    return {"first_run": first_run, "pool_size": len(enriched),
            "combined": combined, "landmark": landmark, "burst": burst}
```

- [ ] **Step 4: 跑测试确认通过**

Run: `python3 -m pytest tests/test_scoring.py -q`
Expected: PASS（9 passed)

- [ ] **Step 5: Commit**

```bash
git add ghradar/scoring.py tests/test_scoring.py
git commit -m "feat(scoring): combined/landmark/burst rankings with snapshot velocity"
```

---

## Task 5: `github_client.py` — Search API 封装

**Files:**
- Create: `ghradar/github_client.py`
- Test: `tests/test_github_client.py`

- [ ] **Step 1: 写失败测试(用假 session,不发真实请求)**

```python
# tests/test_github_client.py
from ghradar.github_client import GitHubClient

class FakeResp:
    def __init__(self, status=200, headers=None, payload=None):
        self.status_code = status
        self.headers = headers or {}
        self._payload = payload or {}
    def json(self):
        return self._payload
    def raise_for_status(self):
        if self.status_code >= 400:
            raise AssertionError(f"HTTP {self.status_code}")

class FakeSession:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []
    def get(self, url, headers=None, params=None, timeout=None):
        self.calls.append(params)
        return self._responses.pop(0)

def _item(name, stars):
    return {"full_name": name, "html_url": f"https://github.com/{name}",
            "stargazers_count": stars, "language": "Python",
            "description": "d", "topics": ["t"], "created_at": "2024-01-01T00:00:00Z"}

def test_normalize_maps_fields():
    sess = FakeSession([FakeResp(payload={"items": [_item("a/b", 42)]})])
    client = GitHubClient(token="x", session=sess)
    repos = client.search_repos("kw", min_stars=50, cap=100)
    assert repos[0] == {
        "full_name": "a/b", "html_url": "https://github.com/a/b", "stars": 42,
        "language": "Python", "description": "d", "topics": ["t"],
        "created_at": "2024-01-01T00:00:00Z"}

def test_pagination_stops_on_short_page():
    sess = FakeSession([FakeResp(payload={"items": [_item("a/b", 10)]})])  # <100 → 停
    client = GitHubClient(token="x", session=sess)
    repos = client.search_repos("kw", min_stars=50, cap=300)
    assert len(repos) == 1
    assert len(sess.calls) == 1  # 没翻第二页

def test_rate_limit_retry_then_success():
    slept = []
    limited = FakeResp(status=403, headers={"X-RateLimit-Remaining": "0",
                                            "X-RateLimit-Reset": "0"})
    ok = FakeResp(payload={"items": [_item("a/b", 10)]})
    sess = FakeSession([limited, ok])
    client = GitHubClient(token="x", session=sess, sleep=lambda s: slept.append(s))
    repos = client.search_repos("kw", min_stars=50, cap=100)
    assert len(repos) == 1
    assert slept  # 限流后睡过
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python3 -m pytest tests/test_github_client.py -q`
Expected: FAIL（`No module named 'ghradar.github_client'`)

- [ ] **Step 3: 实现 `ghradar/github_client.py`**

```python
import time
import requests

API = "https://api.github.com/search/repositories"

class GitHubClient:
    def __init__(self, token=None, session=None, sleep=time.sleep):
        self.token = token
        self.session = session or requests.Session()
        self.sleep = sleep

    def _headers(self):
        h = {"Accept": "application/vnd.github+json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def _get(self, params):
        for _ in range(5):
            resp = self.session.get(API, headers=self._headers(), params=params, timeout=30)
            if resp.status_code in (403, 429):
                retry_after = resp.headers.get("Retry-After")
                if retry_after:
                    self.sleep(int(retry_after))
                    continue
                if resp.headers.get("X-RateLimit-Remaining") == "0":
                    reset = int(resp.headers.get("X-RateLimit-Reset", "0"))
                    self.sleep(max(reset - int(time.time()), 1))
                    continue
            resp.raise_for_status()
            return resp.json()
        resp.raise_for_status()
        return resp.json()

    def search_repos(self, keyword, min_stars, cap):
        per_page = 100
        pages = max(1, -(-cap // per_page))  # ceil(cap/per_page)
        items = []
        for page in range(1, pages + 1):
            data = self._get({
                "q": f"{keyword} stars:>={min_stars}",
                "sort": "stars", "order": "desc",
                "per_page": per_page, "page": page,
            })
            page_items = data.get("items", [])
            if not page_items:
                break
            items.extend(page_items)
            if len(page_items) < per_page:
                break
        return [self._normalize(it) for it in items[:cap]]

    @staticmethod
    def _normalize(it):
        return {
            "full_name": it["full_name"],
            "html_url": it["html_url"],
            "stars": it.get("stargazers_count", 0),
            "language": it.get("language"),
            "description": it.get("description") or "",
            "topics": it.get("topics") or [],
            "created_at": it.get("created_at"),
        }
```

- [ ] **Step 4: 跑测试确认通过**

Run: `python3 -m pytest tests/test_github_client.py -q`
Expected: PASS（3 passed)

- [ ] **Step 5: Commit**

```bash
git add ghradar/github_client.py tests/test_github_client.py
git commit -m "feat(client): github search api with pagination and rate-limit backoff"
```

---

## Task 6: `report.py` — 渲染 Markdown

**Files:**
- Create: `ghradar/report.py`
- Test: `tests/test_report.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_report.py
from ghradar.report import render_markdown

def _enriched(name, stars, delta, vpd, estimated):
    return {"full_name": name, "html_url": f"https://github.com/{name}",
            "stars": stars, "language": "Python", "description": "一句话",
            "topics": ["ai", "cli"], "delta": delta,
            "velocity_per_day": vpd, "is_estimated": estimated}

def _rankings(first_run):
    e = _enriched("a/b", 1234, None if first_run else 100, 10.0, first_run)
    return {"first_run": first_run, "pool_size": 7,
            "combined": [e], "landmark": [e], "burst": [e]}

def test_frontmatter_and_title_present():
    md = render_markdown(_rankings(False), "2026-05-30", ["自动化与工作流"])
    assert md.startswith("---\n")
    assert "tags: [github雷达]" in md
    assert "date: 2026-05-30" in md
    assert "# GitHub 雷达 · 2026-05-30" in md

def test_repo_link_and_sections():
    md = render_markdown(_rankings(False), "2026-05-30", ["A", "B"])
    assert "[a/b](https://github.com/a/b)" in md
    assert "🥇 综合榜" in md and "🏆 标杆榜" in md and "🚀 爆发榜" in md
    assert "+100" in md  # 真实涨幅

def test_first_run_note_and_estimated_growth():
    md = render_markdown(_rankings(True), "2026-05-30", ["A"])
    assert "首跑" in md
    assert "估算" in md

def test_empty_section_renders_placeholder():
    r = {"first_run": False, "pool_size": 0, "combined": [], "landmark": [], "burst": []}
    md = render_markdown(r, "2026-05-30", ["A"])
    assert "本期无" in md
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python3 -m pytest tests/test_report.py -q`
Expected: FAIL（`No module named 'ghradar.report'`)

- [ ] **Step 3: 实现 `ghradar/report.py`**

```python
def _fmt_entry(i, e):
    stars = f"{e['stars']:,}"
    if e.get("delta") is None:
        growth = f"📈 ~{e['velocity_per_day']:.0f}/天(估算)"
    else:
        growth = f"📈 +{e['delta']} ({e['velocity_per_day']:.0f}/天)"
    lang = f"`{e['language']}`" if e.get("language") else ""
    topics = " ".join(f"`{t}`" for t in (e.get("topics") or [])[:5])
    desc = (e.get("description") or "").strip()
    line1 = f"{i}. **[{e['full_name']}]({e['html_url']})** · ⭐ {stars} · {growth} · {lang}"
    line1 = line1.rstrip(" ·")
    parts = [line1]
    if desc:
        parts.append(f"   {desc}")
    if topics:
        parts.append(f"   {topics}")
    return "\n".join(parts)

def _section(title, entries):
    if not entries:
        return f"## {title}\n\n_(本期无)_\n"
    body = "\n".join(_fmt_entry(i, e) for i, e in enumerate(entries, 1))
    return f"## {title}\n\n{body}\n"

def render_markdown(rankings, date_str, domains):
    domain_str = " / ".join(domains)
    note = " · ⚠️ 首跑 · 增速为估算" if rankings["first_run"] else ""
    lines = [
        "---",
        "tags: [github雷达]",
        f"date: {date_str}",
        "generated_by: github-radar",
        "---",
        "",
        f"# GitHub 雷达 · {date_str}",
        "",
        f"> 候选池 {rankings['pool_size']} 个仓库 · 领域:{domain_str}{note}",
        "",
        _section("🥇 综合榜", rankings["combined"]),
        _section("🏆 标杆榜(存量前 5%)", rankings["landmark"]),
        _section("🚀 爆发榜(增速)", rankings["burst"]),
    ]
    return "\n".join(lines)
```

- [ ] **Step 4: 跑测试确认通过**

Run: `python3 -m pytest tests/test_report.py -q`
Expected: PASS（4 passed)

- [ ] **Step 5: Commit**

```bash
git add ghradar/report.py tests/test_report.py
git commit -m "feat(report): render three-list markdown with frontmatter"
```

---

## Task 7: `radar.py` — CLI 串联与输出落盘

**Files:**
- Create: `radar.py`
- Test: `tests/test_radar.py`

- [ ] **Step 1: 写失败测试(mock 掉网络,验证落盘与降级)**

```python
# tests/test_radar.py
import radar

class FakeClient:
    def __init__(self, repos):
        self._repos = repos
    def search_repos(self, keyword, min_stars, cap):
        return self._repos

def _repo(name, stars):
    return {"full_name": name, "html_url": f"https://github.com/{name}",
            "stars": stars, "language": "Python", "description": "d",
            "topics": [], "created_at": "2024-01-01T00:00:00Z"}

def test_collect_repos_dedupes_by_name():
    client = FakeClient([_repo("a/b", 10), _repo("a/b", 99)])
    repos = radar.collect_repos(client, ["k1", "k2"], 50, 100)
    assert len(repos) == 1
    assert repos[0]["stars"] == 99  # 后写覆盖

def test_collect_repos_skips_failing_keyword(capsys):
    class Boom:
        def search_repos(self, *a):
            raise RuntimeError("boom")
    repos = radar.collect_repos(Boom(), ["k"], 50, 100)
    assert repos == []
    assert "失败" in capsys.readouterr().err

def test_output_path_falls_back_when_vault_missing(tmp_path):
    cfg = {"vault_path": str(tmp_path / "does-not-exist"),
           "report_folder": "GitHub雷达"}
    p = radar.output_path(cfg, "2026-05-30")
    assert p.endswith("reports/2026-05-30.md")

def test_output_path_uses_vault_when_present(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    cfg = {"vault_path": str(vault), "report_folder": "GitHub雷达"}
    p = radar.output_path(cfg, "2026-05-30")
    assert str(vault) in p and p.endswith("GitHub雷达/2026-05-30.md")
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python3 -m pytest tests/test_radar.py -q`
Expected: FAIL（`No module named 'radar'` 或函数缺失)

- [ ] **Step 3: 实现 `radar.py`**

```python
import os
import sys
from datetime import datetime, timezone

from ghradar.config import load_config, all_keywords
from ghradar.github_client import GitHubClient
from ghradar.snapshot import load_snapshot, save_snapshot
from ghradar.scoring import build_rankings
from ghradar.report import render_markdown

HERE = os.path.dirname(os.path.abspath(__file__))

def collect_repos(client, keywords, min_stars, cap):
    seen = {}
    for kw in keywords:
        try:
            for r in client.search_repos(kw, min_stars, cap):
                seen[r["full_name"]] = r
        except Exception as ex:
            print(f"⚠️ 关键词 '{kw}' 查询失败,跳过:{ex}", file=sys.stderr)
    return list(seen.values())

def output_path(cfg, date_str):
    folder = os.path.join(cfg["vault_path"], cfg["report_folder"])
    if not os.path.isdir(cfg["vault_path"]):
        folder = os.path.join(HERE, "reports")
        print(f"⚠️ vault 路径不存在,改写本地 {folder}", file=sys.stderr)
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, f"{date_str}.md")

def main():
    cfg = load_config(os.path.join(HERE, "config.yaml"))
    if not cfg["github_token"]:
        print("⚠️ 未设置 GITHUB_TOKEN,降速运行(限流更严)", file=sys.stderr)
    client = GitHubClient(token=cfg["github_token"])
    repos = collect_repos(client, all_keywords(cfg),
                          cfg["pool_min_stars"], cfg["fetch_cap_per_keyword"])
    snap_path = os.path.join(HERE, "snapshot.json")
    prev = load_snapshot(snap_path)
    now = datetime.now(timezone.utc)
    rankings = build_rankings(repos, prev, cfg, now=now)
    date_str = now.strftime("%Y-%m-%d")
    md = render_markdown(rankings, date_str, list(cfg["domains"].keys()))
    out = output_path(cfg, date_str)
    with open(out, "w", encoding="utf-8") as f:
        f.write(md)
    save_snapshot(snap_path, repos, generated_at=now.isoformat())
    print(f"✅ 报告已写入 {out}(候选池 {rankings['pool_size']} 个)")

if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 跑测试确认通过**

Run: `python3 -m pytest tests/test_radar.py -q`
Expected: PASS（4 passed)

- [ ] **Step 5: 全量测试 + Commit**

Run: `python3 -m pytest -q`
Expected: 全部 PASS（约 27 passed)

```bash
git add radar.py tests/test_radar.py
git commit -m "feat(cli): wire pipeline, write report to vault with fallback"
```

---

## Task 8: 真实联调与文档

**Files:**
- Create: `README.md`

- [ ] **Step 1: 真跑一次(冷启动,会标"首跑·估算")**

Run:
```bash
export GITHUB_TOKEN="$(gh auth token)"
python3 radar.py
```
Expected: 打印 `✅ 报告已写入 .../GitHub雷达/<日期>.md(候选池 N 个)`,N 为正数。

- [ ] **Step 2: 人工检查报告**

Run: `open "/Users/jenson/Documents/Obsidian Vault/GitHub雷达/"`
确认:三个榜都有内容、链接可点、顶部有"首跑·估算"提示。

- [ ] **Step 3: 写 `README.md`**

```markdown
# GitHub 雷达

扫描固定关注领域的 GitHub 项目,产出「综合 / 标杆(前5%) / 爆发(增速)」三榜
Markdown 报告并写入 Obsidian vault。

## 用法
```bash
pip install -r requirements.txt
export GITHUB_TOKEN="$(gh auth token)"   # 提升限流额度
python3 radar.py
```

报告输出到 `config.yaml` 里 `vault_path/report_folder` 指定的目录(默认你的 Obsidian vault)。
首次运行无历史快照,增速为「年龄均速」估算;之后每跑一次存一份 `snapshot.json`,
下次即按真实涨幅算增速。

## 配置
编辑 `config.yaml`:领域关键词、`pool_min_stars`、`top_k`、`burst_min_delta`、
`weights`(stock/velocity 权重)、`vault_path`、`report_folder`。

## 定时
可挂 cron,例如每天 9 点:
`0 9 * * * cd /Users/jenson/github-radar && GITHUB_TOKEN=$(gh auth token) python3 radar.py`
```

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: add README with usage and scheduling"
```

---

## Self-Review(写完计划后的自检结果)

- **Spec 覆盖:** 领域监控→Task 1 config.yaml;宽候选池+去重→Task 5/7;前5%标杆→Task 4
  `landmark`;快照真增速+代理→Task 3/4;三榜加权→Task 4;Obsidian Markdown→Task 6/7;
  限流/无 token/vault 缺失/首跑→Task 5/7 + scoring;TDD→各任务。无遗漏。
- **占位符扫描:** 无 TBD/TODO;每个代码步骤均为完整可运行代码。
- **类型/命名一致性:** `build_rankings`/`search_repos`/`render_markdown`/`load_config`/
  `all_keywords`/`load_snapshot`/`save_snapshot`/`collect_repos`/`output_path` 在定义与调用处一致;
  enriched 字段(`delta`/`velocity_per_day`/`is_estimated`/`*_score`)在 scoring 产出、report 消费,键名一致。
- **已知偏离 spec:** 包名用 `ghradar/` 而非 `radar/`,以避免与入口 `radar.py` 文件同名冲突
  (spec §11 写的是 `radar/`,此处为修复导入冲突的合理调整)。
