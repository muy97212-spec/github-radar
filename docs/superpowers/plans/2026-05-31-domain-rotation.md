# 板块轮换 + 分主题展示 + 总览 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 GitHub 雷达按 5 天周期每天聚焦一个板块，输出到各自子文件夹（各带符合主题的视觉皮肤），并生成跨全部板块的总览表格与仪表盘，同时让「真实增速」在轮换下仍然准确。

**Architecture:** 用日期取模无状态地选当天板块；快照改为「每仓库记 `{stars, seen}`」且合并写入（只更新当天板块、其余保留），使增速按每仓库各自间隔计算；报告渲染按主题分发到各自 renderer（共用数据/转义/无障碍 helper，只换 chrome + CSS）；每板块跑完缓存精简 JSON，总览从这些缓存渲染表格 + 仪表盘。

**Tech Stack:** Python 3.12（项目 `.venv`）、pytest、PyYAML、requests；前端为服务端烘焙的单文件 HTML（无 `<script>`），视觉用 frontend-design 技能 + Claude Preview 验收。

**约定：**
- 所有命令用项目 venv：`/Users/jenson/github-radar/.venv/bin/python`、`/Users/jenson/github-radar/.venv/bin/pytest`。
- 每个 commit 结尾加：`Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`。
- 当前分支 `feat/domain-rotation`（已从 main 切出）。
- 参考规格：`docs/superpowers/specs/2026-05-31-domain-rotation-design.md`。

---

## 文件结构

| 文件 | 职责 | 动作 |
|------|------|------|
| `ghradar/domains.py` | 板块名→slug、按日期选当天/明日板块 | 新建 |
| `ghradar/snapshot.py` | 快照新格式 `{last_run, repos:{name:{stars,seen}}}`、兼容旧格式、合并写入 | 改 |
| `ghradar/scoring.py` | 每仓库各自间隔算增速、爆发榜按日增速门槛 | 改 |
| `ghradar/config.py` | 加 `rotation`/`themes` 默认、`burst_min_delta`→`burst_min_velocity` | 改 |
| `ghradar/state.py` | 每板块榜单精简缓存 JSON 读写 | 新建 |
| `ghradar/report.py` | `render_html` 按主题分发；Phase 2 增 4 套皮肤 | 改 |
| `ghradar/overview.py` | 总览表格(md) + 仪表盘(html) | 新建 |
| `radar.py` | 串联轮换：选板块→搜→写子文件夹→存 state→重生成总览→合并快照 | 改 |
| `.gitignore` | 加 `boards_state/` | 改 |
| `config.example.yaml` / `config.yaml` | 5 板块、rotation、themes、改键名 | 改 |
| `README.md` | 文档：轮换、目录结构、主题、查看方式 | 改 |
| `tests/test_domains.py` / `test_state.py` / `test_overview.py` | 新模块测试 | 新建 |
| `tests/test_snapshot.py` / `test_scoring.py` / `test_report.py` / `test_radar.py` | 适配新格式 + 新断言 | 改 |

---

# Phase 1 — 后端骨架（轮换 + 快照 + 增速 + 状态 + 总览表格）

完成后：轮换可跑、报告进子文件夹、`_总览.md` 可用、`_仪表盘.html` 为可用占位、测试全绿。

---

### Task 1: `ghradar/domains.py` — slug 与选板块

**Files:**
- Create: `ghradar/domains.py`
- Test: `tests/test_domains.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_domains.py
from datetime import datetime, timedelta, timezone
from ghradar.domains import slugify, select_domain, next_domain

def test_slugify_replaces_slash_and_spaces():
    assert slugify("AI/大模型应用与框架") == "AI·大模型应用与框架"
    assert slugify("开发者工具 / CLI") == "开发者工具·CLI"
    assert slugify("自动化与工作流") == "自动化与工作流"

def test_select_domain_cycles_and_covers_all():
    domains = ["A", "B", "C", "D", "E"]
    base = datetime(2026, 5, 31, tzinfo=timezone.utc)
    picks = [select_domain(domains, base + timedelta(days=i)) for i in range(6)]
    assert picks[5] == picks[0]            # 第 6 天回到第 1 个
    assert set(picks[:5]) == set(domains)  # 5 天覆盖全部

def test_select_domain_matches_ordinal_formula():
    domains = ["A", "B", "C", "D", "E"]
    d = datetime(2026, 5, 31, tzinfo=timezone.utc)
    assert select_domain(domains, d) == domains[d.toordinal() % 5]

def test_next_domain_is_following_day():
    domains = ["A", "B", "C", "D", "E"]
    base = datetime(2026, 5, 31, tzinfo=timezone.utc)
    assert next_domain(domains, base) == select_domain(domains, base + timedelta(days=1))
```

- [ ] **Step 2: 运行确认失败**

Run: `/Users/jenson/github-radar/.venv/bin/pytest tests/test_domains.py -v`
Expected: FAIL（`ModuleNotFoundError: ghradar.domains`）

- [ ] **Step 3: 实现**

```python
# ghradar/domains.py
"""板块名 → 文件夹安全 slug；按日期无状态地选当天/明日板块。"""


def slugify(name):
    """文件夹名不允许含 '/'，统一换成 '·' 并去空格。"""
    return name.replace("/", "·").replace(" ", "")


def select_domain(domains, when):
    """当天板块 = domains[日期序数 % 板块数]。无状态、可预测、漏跑不漂移。"""
    return domains[when.toordinal() % len(domains)]


def next_domain(domains, when):
    """明日板块，供仪表盘提示『接下来轮到谁』。"""
    return domains[(when.toordinal() + 1) % len(domains)]
```

- [ ] **Step 4: 运行确认通过**

Run: `/Users/jenson/github-radar/.venv/bin/pytest tests/test_domains.py -v`
Expected: PASS（4 项）

- [ ] **Step 5: 提交**

```bash
git add ghradar/domains.py tests/test_domains.py
git commit -m "feat(domains): slugify + date-mod board selection

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: `ghradar/snapshot.py` — 每仓库 `{stars,seen}` + 兼容旧格式 + 合并写入

**Files:**
- Modify: `ghradar/snapshot.py`（整体替换）
- Test: `tests/test_snapshot.py`（整体替换）

- [ ] **Step 1: 写失败测试（替换整个文件）**

```python
# tests/test_snapshot.py
import json
from datetime import datetime, timezone
from ghradar.snapshot import load_snapshot, save_snapshot

NOW = datetime(2026, 5, 31, tzinfo=timezone.utc)

def test_load_missing_returns_empty(tmp_path):
    snap = load_snapshot(str(tmp_path / "nope.json"))
    assert snap == {"last_run": None, "repos": {}}

def test_save_then_load_roundtrip(tmp_path):
    path = str(tmp_path / "snap.json")
    repos = [{"full_name": "a/b", "stars": 100}, {"full_name": "c/d", "stars": 200}]
    saved = save_snapshot(path, repos, now=NOW)
    assert saved["repos"]["a/b"]["stars"] == 100
    loaded = load_snapshot(path)
    assert loaded["repos"]["a/b"]["stars"] == 100
    assert loaded["repos"]["a/b"]["seen"].startswith("2026-05-31")
    assert loaded["last_run"].startswith("2026-05-31")

def test_save_merges_with_base_keeping_other_repos(tmp_path):
    path = str(tmp_path / "s.json")
    base = {"last_run": "2026-05-25T00:00:00+00:00",
            "repos": {"old/x": {"stars": 10, "seen": "2026-05-25T00:00:00+00:00"}}}
    save_snapshot(path, [{"full_name": "new/y", "stars": 50}], now=NOW, base=base)
    loaded = load_snapshot(path)
    assert loaded["repos"]["old/x"]["stars"] == 10               # 其他板块保留
    assert loaded["repos"]["old/x"]["seen"] == "2026-05-25T00:00:00+00:00"
    assert loaded["repos"]["new/y"]["stars"] == 50               # 今天更新/插入
    assert loaded["repos"]["new/y"]["seen"].startswith("2026-05-31")

def test_load_migrates_old_flat_format(tmp_path):
    path = str(tmp_path / "old.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"generated_at": "2026-05-30T00:00:00+00:00",
                   "repos": {"a/b": 100}}, f)
    loaded = load_snapshot(path)
    assert loaded["repos"]["a/b"] == {"stars": 100, "seen": "2026-05-30T00:00:00+00:00"}
    assert loaded["last_run"] == "2026-05-30T00:00:00+00:00"
```

- [ ] **Step 2: 运行确认失败**

Run: `/Users/jenson/github-radar/.venv/bin/pytest tests/test_snapshot.py -v`
Expected: FAIL（旧 save_snapshot 签名/返回结构不符）

- [ ] **Step 3: 实现（整体替换 `ghradar/snapshot.py`）**

```python
# ghradar/snapshot.py
import json
import os
from datetime import datetime, timezone


def _iso(now):
    return now.isoformat() if hasattr(now, "isoformat") else str(now)


def _normalize(data):
    """统一为 {last_run, repos:{name:{stars,seen}}}；兼容旧的裸 star 格式。"""
    if not data:
        return {"last_run": None, "repos": {}}
    last_run = data.get("last_run") or data.get("generated_at")
    norm = {}
    for name, v in (data.get("repos") or {}).items():
        if isinstance(v, dict):
            norm[name] = {"stars": v.get("stars", 0), "seen": v.get("seen") or last_run}
        else:                                  # 旧格式:裸 star → 用全局时间当 seen
            norm[name] = {"stars": v, "seen": last_run}
    return {"last_run": last_run, "repos": norm}


def load_snapshot(path):
    if not os.path.exists(path):
        return {"last_run": None, "repos": {}}
    with open(path, "r", encoding="utf-8") as f:
        return _normalize(json.load(f))


def save_snapshot(path, repos, now=None, base=None):
    """合并写入:以 base(上次快照)为底,更新/插入今天这批仓库,其余原样保留。"""
    now = now or datetime.now(timezone.utc)
    now_iso = _iso(now)
    merged = dict((base or {}).get("repos") or {})
    for r in repos:
        merged[r["full_name"]] = {"stars": r["stars"], "seen": now_iso}
    data = {"last_run": now_iso, "repos": merged}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return data
```

- [ ] **Step 4: 运行确认通过**

Run: `/Users/jenson/github-radar/.venv/bin/pytest tests/test_snapshot.py -v`
Expected: PASS（4 项）

- [ ] **Step 5: 提交**

```bash
git add ghradar/snapshot.py tests/test_snapshot.py
git commit -m "feat(snapshot): per-repo {stars,seen} + merge write + legacy migration

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: `ghradar/scoring.py` — 每仓库各自间隔 + 爆发榜按日增速

**Files:**
- Modify: `ghradar/scoring.py`（替换 `build_rankings`）
- Test: `tests/test_scoring.py`（更新 CFG 与 prev 夹具到新格式）

- [ ] **Step 1: 更新测试到新格式（替换整个文件）**

```python
# tests/test_scoring.py
from datetime import datetime, timezone
from ghradar.scoring import build_rankings, _minmax

CFG = {"top_k": 15, "burst_min_velocity": 20, "weights": {"stock": 0.4, "velocity": 0.6}}
NOW = datetime(2026, 5, 30, tzinfo=timezone.utc)

def _repo(name, stars, created="2024-01-01T00:00:00Z"):
    return {"full_name": name, "html_url": f"https://github.com/{name}",
            "stars": stars, "language": "Python", "description": "", "topics": [],
            "created_at": created}

def _prev(mapping):
    """mapping: {name: (stars, seen_iso)} → 新格式快照。"""
    return {"last_run": None,
            "repos": {n: {"stars": s, "seen": seen} for n, (s, seen) in mapping.items()}}

def test_minmax_basic():
    assert _minmax([0, 5, 10]) == [0.0, 0.5, 1.0]

def test_minmax_all_equal_returns_ones():
    assert _minmax([7, 7, 7]) == [1.0, 1.0, 1.0]

def test_minmax_single_and_empty():
    assert _minmax([3]) == [1.0]
    assert _minmax([]) == []

def test_first_run_marks_estimated_and_uses_proxy():
    repos = [_repo("a/b", 100), _repo("c/d", 200)]
    r = build_rankings(repos, {"last_run": None, "repos": {}}, CFG, now=NOW)
    assert r["first_run"] is True
    for e in r["combined"]:
        assert e["is_estimated"] is True
        assert e["delta"] is None
        assert e["velocity_per_day"] > 0

def test_velocity_uses_per_repo_elapsed():
    repos = [_repo("a/b", 150), _repo("c/d", 205)]
    prev = _prev({"a/b": (50, "2026-05-20T00:00:00+00:00"),    # 10 天前
                  "c/d": (200, "2026-05-25T00:00:00+00:00")})  # 5 天前
    r = build_rankings(repos, prev, CFG, now=NOW)
    assert r["first_run"] is False
    by = {e["full_name"]: e for e in r["combined"]}
    assert by["a/b"]["delta"] == 100
    assert by["a/b"]["is_estimated"] is False
    assert round(by["a/b"]["velocity_per_day"], 1) == 10.0      # 100 / 10 天
    assert round(by["c/d"]["velocity_per_day"], 1) == 1.0       # 5 / 5 天

def test_board_first_appearance_is_estimated_even_when_not_first_run():
    # 快照里有别的板块的仓库 → first_run=False;但本仓库没出现过 → 估算
    repos = [_repo("new/repo", 300)]
    prev = _prev({"other/board": (10, "2026-05-25T00:00:00+00:00")})
    r = build_rankings(repos, prev, CFG, now=NOW)
    assert r["first_run"] is False
    e = r["combined"][0]
    assert e["is_estimated"] is True and e["delta"] is None

def test_burst_filters_by_velocity_per_day():
    repos = [_repo("big/slow", 9000), _repo("small/fast", 300)]
    prev = _prev({"big/slow": (8995, "2026-05-29T00:00:00+00:00"),    # +5/天
                  "small/fast": (200, "2026-05-29T00:00:00+00:00")})  # +100/天
    r = build_rankings(repos, prev, CFG, now=NOW)
    names = [e["full_name"] for e in r["burst"]]
    assert "small/fast" in names      # 100/天 >= 20
    assert "big/slow" not in names    # 5/天 < 20

def test_burst_includes_estimated_on_first_run():
    repos = [_repo("a/b", 100)]
    r = build_rankings(repos, {"last_run": None, "repos": {}}, CFG, now=NOW)
    assert [e["full_name"] for e in r["burst"]] == ["a/b"]

def test_landmark_takes_top_5_percent():
    repos = [_repo(f"o/r{i}", stars=i) for i in range(1, 101)]
    r = build_rankings(repos, {"last_run": None, "repos": {}}, CFG, now=NOW)
    assert len(r["landmark"]) == 5
    assert [e["stars"] for e in r["landmark"]] == [100, 99, 98, 97, 96]

def test_combined_weighting_orders_results():
    repos = [_repo("big/x", 100000), _repo("rocket/y", 500)]
    prev = _prev({"big/x": (99990, "2026-05-29T00:00:00+00:00"),     # +10/天
                  "rocket/y": (100, "2026-05-29T00:00:00+00:00")})   # +400/天
    r = build_rankings(repos, prev, CFG, now=NOW)
    assert r["combined"][0]["full_name"] == "rocket/y"

def test_empty_repos_returns_empty_rankings():
    r = build_rankings([], None, CFG, now=NOW)
    assert r == {"first_run": True, "pool_size": 0,
                 "combined": [], "landmark": [], "burst": []}

def test_rankings_respect_top_k():
    cfg = {"top_k": 3, "burst_min_velocity": 20, "weights": {"stock": 0.4, "velocity": 0.6}}
    repos = [_repo(f"o/r{i}", stars=i) for i in range(1, 201)]
    r = build_rankings(repos, {"last_run": None, "repos": {}}, cfg, now=NOW)
    assert len(r["combined"]) == 3
    assert len(r["landmark"]) == 3
    assert len(r["burst"]) == 3
```

- [ ] **Step 2: 运行确认失败**

Run: `/Users/jenson/github-radar/.venv/bin/pytest tests/test_scoring.py -v`
Expected: FAIL（旧 build_rankings 用全局 `prev_time` 且读 `burst_min_delta`）

- [ ] **Step 3: 实现（替换 `build_rankings`，其余保持）**

```python
def build_rankings(repos, prev_snapshot, config, now=None):
    now = now or datetime.now(timezone.utc)
    prev_repos = (prev_snapshot or {}).get("repos") or {}
    first_run = len(prev_repos) == 0

    enriched = []
    for r in repos:
        name, stars = r["full_name"], r["stars"]
        prev = None if first_run else prev_repos.get(name)
        if prev is not None:
            prev_stars = prev["stars"] if isinstance(prev, dict) else prev
            seen = _parse_iso(prev.get("seen")) if isinstance(prev, dict) else None
            # 每仓库各自的间隔:轮换下某板块可能 5 天才见一次。
            elapsed = max((now - seen).total_seconds() / 86400.0, 1.0) if seen else 1.0
            delta = max(stars - prev_stars, 0)
            velocity_per_day = delta / elapsed
            is_estimated = False
        else:
            delta = None
            velocity_per_day = stars / _age_days(r.get("created_at"), now)
            is_estimated = True
        e = dict(r)
        e.update(delta=delta, velocity_per_day=velocity_per_day, is_estimated=is_estimated)
        enriched.append(e)

    stock_scores = _minmax([math.log(e["stars"] + 1) for e in enriched])
    velocity_scores = _minmax([e["velocity_per_day"] for e in enriched])
    w = config["weights"]
    for e, ss, vs in zip(enriched, stock_scores, velocity_scores):
        e["stock_score"] = ss
        e["velocity_score"] = vs
        e["combined_score"] = w["stock"] * ss + w["velocity"] * vs

    top_k = config["top_k"]
    combined = sorted(enriched, key=lambda e: e["combined_score"], reverse=True)[:top_k]

    by_stars = sorted(enriched, key=lambda e: e["stars"], reverse=True)
    cutoff = max(1, math.ceil(len(by_stars) * LANDMARK_FRACTION))
    landmark = by_stars[:cutoff][:top_k]

    # 爆发榜门槛按"日增速"而非原始增量:轮换下间隔不固定,日增速才同量纲。
    burst_min_v = config.get("burst_min_velocity", config.get("burst_min_delta", 20))
    burst_candidates = [
        e for e in enriched
        if e["is_estimated"] or e["velocity_per_day"] >= burst_min_v
    ]
    burst = sorted(burst_candidates, key=lambda e: e["velocity_per_day"], reverse=True)[:top_k]

    return {"first_run": first_run, "pool_size": len(enriched),
            "combined": combined, "landmark": landmark, "burst": burst}
```

- [ ] **Step 4: 运行确认通过**

Run: `/Users/jenson/github-radar/.venv/bin/pytest tests/test_scoring.py -v`
Expected: PASS（12 项）

- [ ] **Step 5: 提交**

```bash
git add ghradar/scoring.py tests/test_scoring.py
git commit -m "feat(scoring): per-repo elapsed velocity + burst by velocity/day

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: `ghradar/config.py` + config 文件 — rotation/themes + 改键名 + 5 板块

**Files:**
- Modify: `ghradar/config.py:4-11`（DEFAULTS）
- Modify: `config.example.yaml`（整体替换）
- Modify: `config.yaml`（本地、gitignored；整体替换为 5 板块）
- Test: `tests/test_config.py`（若不存在则新建）

- [ ] **Step 1: 写失败测试**

```python
# tests/test_config.py
from ghradar.config import load_config

def test_defaults_include_rotation_and_themes(tmp_path):
    p = tmp_path / "c.yaml"
    p.write_text("domains:\n  自动化: [k]\nvault_path: /tmp\n", encoding="utf-8")
    cfg = load_config(str(p))
    assert cfg["rotation"] is True
    assert cfg["themes"] == {}
    assert cfg["burst_min_velocity"] == 20

def test_user_can_override_rotation_and_themes(tmp_path):
    p = tmp_path / "c.yaml"
    p.write_text(
        "domains:\n  自动化: [k]\nvault_path: /tmp\n"
        "rotation: false\nthemes:\n  自动化: scope\n", encoding="utf-8")
    cfg = load_config(str(p))
    assert cfg["rotation"] is False
    assert cfg["themes"]["自动化"] == "scope"
```

- [ ] **Step 2: 运行确认失败**

Run: `/Users/jenson/github-radar/.venv/bin/pytest tests/test_config.py -v`
Expected: FAIL（DEFAULTS 无 rotation/themes/burst_min_velocity）

- [ ] **Step 3: 改 DEFAULTS（`ghradar/config.py` 第 4–11 行）**

```python
DEFAULTS = {
    "pool_min_stars": 50,
    "fetch_cap_per_keyword": 300,
    "top_k": 15,
    "burst_min_velocity": 20,
    "weights": {"stock": 0.4, "velocity": 0.6},
    "report_folder": "GitHub雷达",
    "rotation": True,
    "themes": {},
}
```

- [ ] **Step 4: 运行确认通过**

Run: `/Users/jenson/github-radar/.venv/bin/pytest tests/test_config.py -v`
Expected: PASS（2 项）

- [ ] **Step 5: 替换 `config.example.yaml`（5 板块 + rotation + themes）**

```yaml
# 加板块 = 复制 domains 下一段、改板块名与关键词；themes 缺省走 editorial。
domains:
  自动化与工作流: [workflow automation, RPA, browser automation, playwright, n8n, scraping]
  内容创作与分发: [content automation, social media automation, video generation,
                  auto upload, multi-platform publish, AIGC content]
  AI/大模型应用与框架: [LLM application, AI agent framework, RAG, LLM inference,
                       agentic workflow, prompt engineering]
  开发者工具 / CLI: [developer tool, CLI tool, terminal, productivity, editor plugin]
  自托管 / 效率应用: [self-hosted, knowledge management, note taking, kanban, dashboard]

rotation: true            # 每天按日期取模只跑一个板块;false = 跑全部(回退)
themes:                   # 板块 → 视觉主题(scope/editorial/console/terminal/homelab)
  自动化与工作流: scope
  内容创作与分发: editorial
  AI/大模型应用与框架: console
  开发者工具 / CLI: terminal
  自托管 / 效率应用: homelab

pool_min_stars: 50
fetch_cap_per_keyword: 300
top_k: 15
burst_min_velocity: 20    # 爆发榜门槛:日增速(星/天)
weights: { stock: 0.4, velocity: 0.6 }
vault_path: "/path/to/your/Obsidian Vault"
report_folder: "GitHub雷达"
```

- [ ] **Step 6: 替换本地 `config.yaml`（与 example 相同，但 `vault_path` 用真实路径）**

把上面内容复制到 `config.yaml`，并将 `vault_path` 改为 `"/Users/jenson/Documents/Obsidian Vault"`。（`config.yaml` 已被 gitignore，不会提交。）

- [ ] **Step 7: 提交（不含 config.yaml）**

```bash
git add ghradar/config.py tests/test_config.py config.example.yaml
git commit -m "feat(config): rotation + themes knobs, 5 boards, rename burst key

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: `ghradar/state.py` — 板块榜单精简缓存

**Files:**
- Create: `ghradar/state.py`
- Test: `tests/test_state.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_state.py
from datetime import datetime, timezone
from ghradar.state import save_board_state, load_all_board_states

NOW = datetime(2026, 5, 31, tzinfo=timezone.utc)

def _e(name, stars, delta, vpd, est=False):
    return {"full_name": name, "html_url": f"https://github.com/{name}", "stars": stars,
            "language": "Python", "description": "d", "topics": ["x"],
            "delta": delta, "velocity_per_day": vpd, "is_estimated": est}

def _rankings():
    items = [_e(f"o/r{i}", 1000 - i, 10 + i, float(i)) for i in range(8)]
    return {"first_run": False, "pool_size": 42,
            "combined": items, "landmark": items, "burst": items}

def test_save_and_load_roundtrip_trims_fields(tmp_path):
    d = str(tmp_path / "boards_state")
    save_board_state(d, "AI/大模型应用与框架", _rankings(), "2026-05-31", now=NOW)
    states = load_all_board_states(d, ["AI/大模型应用与框架", "自动化与工作流"])
    ai = states["AI/大模型应用与框架"]
    assert ai["pool_size"] == 42
    assert ai["date_str"] == "2026-05-31"
    assert ai["slug"] == "AI·大模型应用与框架"
    assert len(ai["combined"]) == 5          # combined 截到 5
    assert len(ai["burst"]) == 3             # burst 截到 3
    assert set(ai["combined"][0]) == {"full_name", "html_url", "stars",
                                      "velocity_per_day", "delta", "is_estimated"}
    assert states["自动化与工作流"] is None   # 未采集 → None
```

- [ ] **Step 2: 运行确认失败**

Run: `/Users/jenson/github-radar/.venv/bin/pytest tests/test_state.py -v`
Expected: FAIL（`ModuleNotFoundError: ghradar.state`）

- [ ] **Step 3: 实现**

```python
# ghradar/state.py
"""每板块跑完缓存一份精简榜单 JSON,供总览(表格/仪表盘)读取全部板块。
存项目目录 boards_state/<slug>.json,不进 vault。"""
import json
import os
from datetime import datetime, timezone

from ghradar.domains import slugify

_KEEP = ("full_name", "html_url", "stars", "velocity_per_day", "delta", "is_estimated")


def _trim(e):
    return {k: e.get(k) for k in _KEEP}


def save_board_state(dir_path, domain, rankings, date_str, now=None):
    now = now or datetime.now(timezone.utc)
    os.makedirs(dir_path, exist_ok=True)
    state = {
        "domain": domain,
        "slug": slugify(domain),
        "updated_at": now.isoformat() if hasattr(now, "isoformat") else str(now),
        "date_str": date_str,
        "pool_size": rankings["pool_size"],
        "combined": [_trim(e) for e in rankings["combined"][:5]],
        "burst": [_trim(e) for e in rankings["burst"][:3]],
    }
    path = os.path.join(dir_path, slugify(domain) + ".json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    return state


def load_all_board_states(dir_path, domains):
    out = {}
    for d in domains:
        path = os.path.join(dir_path, slugify(d) + ".json")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                out[d] = json.load(f)
        else:
            out[d] = None
    return out
```

- [ ] **Step 4: 运行确认通过**

Run: `/Users/jenson/github-radar/.venv/bin/pytest tests/test_state.py -v`
Expected: PASS（1 项）

- [ ] **Step 5: 提交**

```bash
git add ghradar/state.py tests/test_state.py
git commit -m "feat(state): per-board trimmed rankings cache

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: `ghradar/report.py` — `render_html` 按主题分发（仅 editorial，输出不变）

**Files:**
- Modify: `ghradar/report.py`（把现有 render_html 函数体抽成 `_render_editorial`，新增分发）
- Test: `tests/test_report.py`（补 2 个分发测试，其余不变）

- [ ] **Step 1: 补失败测试（在 `tests/test_report.py` 末尾追加）**

```python
def test_render_html_unknown_theme_falls_back_to_editorial():
    h = render_html(_rankings(False), "2026-05-30", ["A"], theme="does-not-exist")
    assert h.lstrip().startswith("<!DOCTYPE html>")
    assert "综合榜" in h

def test_render_html_editorial_theme_explicit():
    h = render_html(_rankings(False), "2026-05-30", ["A"], theme="editorial")
    assert "晨报" in h  # 编辑部 chrome 标志
```

- [ ] **Step 2: 运行确认失败**

Run: `/Users/jenson/github-radar/.venv/bin/pytest tests/test_report.py -v`
Expected: FAIL（render_html 不接受 `theme` 关键字）

- [ ] **Step 3: 重构（不改输出）**

把现有 `def render_html(rankings, date_str, domains):` 整段**改名**为
`def _render_editorial(rankings, date_str, domains):`（函数体一字不改）。
然后在文件末尾追加分发层：

```python
# 主题 → renderer。共用 _html_section/_html_entry/_vel_html/_esc/_date_cn 等数据 helper；
# 各 renderer 自带 chrome(masthead/lede/footer) + CSS + 字体。Phase 2 注册其余 4 套。
_THEME_RENDERERS = {
    "editorial": _render_editorial,
}


def render_html(rankings, date_str, domains, theme="editorial"):
    renderer = _THEME_RENDERERS.get(theme) or _THEME_RENDERERS["editorial"]
    return renderer(rankings, date_str, domains)
```

- [ ] **Step 4: 运行确认通过**

Run: `/Users/jenson/github-radar/.venv/bin/pytest tests/test_report.py -v`
Expected: PASS（旧 8 项 + 新 2 项）

- [ ] **Step 5: 提交**

```bash
git add ghradar/report.py tests/test_report.py
git commit -m "refactor(report): theme dispatch for render_html (editorial unchanged)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7: `ghradar/overview.py` — 总览表格(md) + 仪表盘占位(html)

**Files:**
- Create: `ghradar/overview.py`
- Test: `tests/test_overview.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_overview.py
from ghradar.overview import render_overview_md, render_dashboard_html

def _state(domain, date_str, top_name, delta):
    e = {"full_name": top_name, "html_url": f"https://github.com/{top_name}",
         "stars": 1234, "velocity_per_day": float(delta), "delta": delta, "is_estimated": False}
    return {"domain": domain, "slug": domain, "updated_at": "x", "date_str": date_str,
            "pool_size": 99, "combined": [e], "burst": [e]}

DOMAINS = ["自动化与工作流", "内容创作与分发", "AI/大模型应用与框架",
           "开发者工具 / CLI", "自托管 / 效率应用"]

def test_overview_md_has_row_per_board_and_marks_uncollected():
    states = {d: None for d in DOMAINS}
    states["自动化与工作流"] = _state("自动化与工作流", "2026-05-31", "D4Vinci/Scrapling", 293)
    md = render_overview_md(states, DOMAINS, today="自动化与工作流", today_str="2026-05-31")
    assert md.count("|") >= 6 * (len(DOMAINS) + 2)   # 表头 + 分隔 + 5 行
    assert "尚未采集" in md                            # 未采集板块
    assert "D4Vinci/Scrapling" in md                  # 已采集榜首
    assert "今天" in md                                # 今日板块标记/相对天数

def test_overview_md_relative_days():
    states = {d: None for d in DOMAINS}
    states["内容创作与分发"] = _state("内容创作与分发", "2026-05-26", "a/b", 10)
    md = render_overview_md(states, DOMAINS, today="自动化与工作流", today_str="2026-05-31")
    assert "5 天前" in md

def test_dashboard_html_is_full_doc_and_escapes():
    states = {d: None for d in DOMAINS}
    states["AI/大模型应用与框架"] = _state("AI/大模型应用与框架", "2026-05-31", "x<script>/y", 5)
    h = render_dashboard_html(states, DOMAINS, today="AI/大模型应用与框架",
                              nxt="开发者工具 / CLI", today_str="2026-05-31")
    assert h.lstrip().startswith("<!DOCTYPE html>")
    assert "<script>/y" not in h and "&lt;script&gt;" in h   # 转义
    assert "AI/大模型应用与框架" in h
    assert "prefers-reduced-motion" in h                     # 无障碍回退存在
```

- [ ] **Step 2: 运行确认失败**

Run: `/Users/jenson/github-radar/.venv/bin/pytest tests/test_overview.py -v`
Expected: FAIL（`ModuleNotFoundError: ghradar.overview`）

- [ ] **Step 3: 实现（Phase 1 仪表盘为可用占位，Phase 3 美化）**

```python
# ghradar/overview.py
"""跨全部板块的总览:_总览.md(表格) + _仪表盘.html(面板)。
只有当天板块真去搜,这里读 boards_state 缓存来展示全部 5 个板块的最新态。"""
import html as _html
from datetime import datetime


def _esc(s):
    return _html.escape(str(s) if s is not None else "")


def _rel_days(date_str, today_str):
    try:
        d0 = datetime.strptime(date_str, "%Y-%m-%d").date()
        d1 = datetime.strptime(today_str, "%Y-%m-%d").date()
        n = (d1 - d0).days
        return "今天" if n <= 0 else f"{n} 天前"
    except (ValueError, TypeError):
        return date_str or "—"


def _vel_text(e):
    if e is None:
        return "—"
    if e.get("is_estimated"):
        return f"约 +{e['velocity_per_day']:.0f}/天"
    if e.get("delta") == 0:
        return "持平"
    return f"+{e.get('delta')}/天"


def _top(state, board):
    items = (state or {}).get(board) or []
    return items[0] if items else None


def render_overview_md(states, domains, today, today_str):
    lines = [
        "---", "tags: [github雷达, 总览]", f"date: {today_str}", "---", "",
        "# GitHub 雷达 · 总览", "",
        f"> 今日板块：**{today}** · 5 天轮换 · 快照 {today_str}", "",
        "| 板块 | 上次更新 | 候选池 | 综合榜首 | 榜首增速 | 爆发榜首 |",
        "|------|---------|-------|---------|---------|---------|",
    ]
    for d in domains:
        st = states.get(d)
        mark = " ⬅️ 今天" if d == today else ""
        if not st:
            lines.append(f"| {d}{mark} | 尚未采集 | — | — | — | — |")
            continue
        c = _top(st, "combined")
        b = _top(st, "burst")
        lines.append(
            f"| {d}{mark} | {_rel_days(st.get('date_str'), today_str)} "
            f"| {st.get('pool_size', '—')} | {c['full_name'] if c else '—'} "
            f"| {_vel_text(c)} | {b['full_name'] if b else '—'} |"
        )
    return "\n".join(lines) + "\n"


# ---- 仪表盘(Phase 1 占位:可用 + 通过 smoke 测试;Phase 3 用 frontend-design 美化) ----
_DASH_CSS = """
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:ui-sans-serif,system-ui,"PingFang SC",sans-serif;background:#0f1115;color:#e6e6e6;padding:32px}
h1{font-size:22px;margin-bottom:4px}.sub{color:#9aa0a6;font-size:13px;margin-bottom:24px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:16px}
.card{background:#171a21;border:1px solid #262b34;border-radius:12px;padding:18px}
.card.today{border-color:#7cf03d;box-shadow:0 0 0 1px #7cf03d}
.card h2{font-size:15px;margin-bottom:8px}.card .meta{color:#9aa0a6;font-size:12px}
.card .top{margin-top:10px;font-size:13px}.tag{font-size:11px;color:#0f1115;background:#7cf03d;border-radius:4px;padding:1px 6px}
@media (prefers-reduced-motion: reduce){*{animation:none!important;transition:none!important}}
"""


def render_dashboard_html(states, domains, today, nxt, today_str):
    cards = []
    for d in domains:
        st = states.get(d)
        cls = "card today" if d == today else "card"
        tag = '<span class="tag">今天</span>' if d == today else (
            "（接下来）" if d == nxt else "")
        if not st:
            body = '<div class="meta">尚未采集</div>'
        else:
            c = _top(st, "combined")
            body = (f'<div class="meta">{_esc(_rel_days(st.get("date_str"), today_str))}'
                    f' · 池 {st.get("pool_size", "—")}</div>'
                    f'<div class="top">综合榜首：{_esc(c["full_name"]) if c else "—"}'
                    f' · {_esc(_vel_text(c))}</div>')
        cards.append(f'<div class="{cls}"><h2>{_esc(d)} {tag}</h2>{body}</div>')
    return (
        '<!DOCTYPE html>\n<html lang="zh-CN">\n<head>\n<meta charset="UTF-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        f"<title>GitHub 雷达 · 总览仪表盘 · {_esc(today_str)}</title>\n"
        f"<style>{_DASH_CSS}</style>\n</head>\n<body>\n"
        f"<h1>GitHub 雷达 · 总览仪表盘</h1>"
        f'<div class="sub">今日板块 {_esc(today)} · 接下来 {_esc(nxt)} · 快照 {_esc(today_str)}</div>'
        f'<div class="grid">{"".join(cards)}</div>\n</body>\n</html>\n'
    )
```

- [ ] **Step 4: 运行确认通过**

Run: `/Users/jenson/github-radar/.venv/bin/pytest tests/test_overview.py -v`
Expected: PASS（3 项）

- [ ] **Step 5: 提交**

```bash
git add ghradar/overview.py tests/test_overview.py
git commit -m "feat(overview): _总览.md table + dashboard placeholder

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 8: `radar.py` — 串联轮换 + 子文件夹 + 状态 + 总览

**Files:**
- Modify: `radar.py`（整体替换）
- Test: `tests/test_radar.py`（替换 main 相关测试）

- [ ] **Step 1: 整体替换 `tests/test_radar.py`**

（`output_path` 已被 `base_folder` 取代，故原 `test_output_path_*` 两个用例删除、改测 `base_folder`；保留 collect 工具测试。）

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
    assert repos[0]["stars"] == 99

def test_collect_repos_skips_failing_keyword(capsys):
    class Boom:
        def search_repos(self, *a):
            raise RuntimeError("boom")
    repos = radar.collect_repos(Boom(), ["k"], 50, 100)
    assert repos == []
    assert "失败" in capsys.readouterr().err

def test_base_folder_falls_back_when_vault_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(radar, "HERE", str(tmp_path))
    cfg = {"vault_path": str(tmp_path / "nope"), "report_folder": "GitHub雷达"}
    assert radar.base_folder(cfg) == str(tmp_path / "reports")

def test_base_folder_uses_vault_when_present(tmp_path):
    vault = tmp_path / "v"; vault.mkdir()
    cfg = {"vault_path": str(vault), "report_folder": "GitHub雷达"}
    assert radar.base_folder(cfg).endswith("GitHub雷达")

def _rotation_cfg(vault):
    return {"github_token": None, "pool_min_stars": 50, "fetch_cap_per_keyword": 10,
            "domains": {"自动化与工作流": ["k1"], "内容创作与分发": ["k2"]},
            "themes": {"自动化与工作流": "editorial"},
            "weights": {"stock": 0.4, "velocity": 0.6}, "top_k": 5,
            "burst_min_velocity": 20, "rotation": True,
            "vault_path": str(vault), "report_folder": "GitHub雷达"}

def test_rotation_writes_into_board_subfolder_and_overview(tmp_path, monkeypatch):
    vault = tmp_path / "vault"; vault.mkdir()
    monkeypatch.setattr(radar, "HERE", str(tmp_path))
    monkeypatch.setattr(radar, "load_config", lambda path: _rotation_cfg(vault))
    monkeypatch.setattr(radar, "GitHubClient", lambda token=None: FakeClient([_repo("a/b", 100)]))
    radar.main()
    base = vault / "GitHub雷达"
    # 当天板块写进了某个 slug 子文件夹(取决于日期),且根目录有两个总览
    boards = [p for p in base.iterdir() if p.is_dir()]
    assert len(boards) == 1
    latest = boards[0] / "_latest.html"
    assert latest.read_text(encoding="utf-8").lstrip().startswith("<!DOCTYPE html>")
    assert "a/b" in latest.read_text(encoding="utf-8")
    assert (boards[0]).glob("*.md")                              # 带日期 md
    assert (base / "_总览.md").exists()
    assert (base / "_仪表盘.html").read_text(encoding="utf-8").lstrip().startswith("<!DOCTYPE html>")
    assert (tmp_path / "snapshot.json").exists()                 # 快照落盘(新格式)
    assert (tmp_path / "boards_state").exists()                  # 板块状态缓存

def test_rotation_snapshot_merge_preserves_other_boards(tmp_path, monkeypatch):
    import json
    vault = tmp_path / "vault"; vault.mkdir()
    # 预置上次快照:含"别的板块"的仓库
    (tmp_path / "snapshot.json").write_text(json.dumps(
        {"last_run": "2026-05-25T00:00:00+00:00",
         "repos": {"old/board": {"stars": 10, "seen": "2026-05-25T00:00:00+00:00"}}}),
        encoding="utf-8")
    monkeypatch.setattr(radar, "HERE", str(tmp_path))
    monkeypatch.setattr(radar, "load_config", lambda path: _rotation_cfg(vault))
    monkeypatch.setattr(radar, "GitHubClient", lambda token=None: FakeClient([_repo("a/b", 100)]))
    radar.main()
    snap = json.loads((tmp_path / "snapshot.json").read_text(encoding="utf-8"))
    assert "old/board" in snap["repos"]      # 其他板块数据未被覆盖
    assert "a/b" in snap["repos"]            # 今天板块已更新
```

- [ ] **Step 2: 运行确认失败**

Run: `/Users/jenson/github-radar/.venv/bin/pytest tests/test_radar.py -v`
Expected: FAIL（radar.main 尚未支持轮换/子文件夹/总览）

- [ ] **Step 3: 实现（整体替换 `radar.py`）**

```python
import os
import sys
from datetime import datetime, timezone

from ghradar.config import load_config, all_keywords
from ghradar.github_client import GitHubClient
from ghradar.snapshot import load_snapshot, save_snapshot
from ghradar.scoring import build_rankings
from ghradar.report import render_markdown, render_html
from ghradar.domains import slugify, select_domain, next_domain
from ghradar.state import save_board_state, load_all_board_states
from ghradar.overview import render_overview_md, render_dashboard_html

HERE = os.path.dirname(os.path.abspath(__file__))


def collect_repos(client, keywords, min_stars, cap):
    seen = {}
    for kw in keywords:
        try:
            for r in client.search_repos(kw, min_stars, cap):
                cur = seen.get(r["full_name"])
                if cur is None or r["stars"] > cur["stars"]:
                    seen[r["full_name"]] = r
        except Exception as ex:
            print(f"⚠️ 关键词 '{kw}' 查询失败,跳过:{ex}", file=sys.stderr)
    return list(seen.values())


def base_folder(cfg):
    folder = os.path.join(cfg["vault_path"], cfg["report_folder"])
    if not os.path.isdir(cfg["vault_path"]):
        folder = os.path.join(HERE, "reports")
        print(f"⚠️ vault 路径不存在,改写本地 {folder}", file=sys.stderr)
    os.makedirs(folder, exist_ok=True)
    return folder


def _write(path, text):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def main():
    cfg = load_config(os.path.join(HERE, "config.yaml"))
    if not cfg["github_token"]:
        print("⚠️ 未设置 GITHUB_TOKEN,未认证搜索限流约 10 次/分钟", file=sys.stderr)
    client = GitHubClient(token=cfg["github_token"])
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d")
    domains = list(cfg["domains"].keys())
    snap_path = os.path.join(HERE, "snapshot.json")
    prev = load_snapshot(snap_path)
    base = base_folder(cfg)

    if cfg.get("rotation", True):
        today = select_domain(domains, now)
        keywords = cfg["domains"][today]
        repos = collect_repos(client, keywords, cfg["pool_min_stars"], cfg["fetch_cap_per_keyword"])
        rankings = build_rankings(repos, prev, cfg, now=now)
        theme = (cfg.get("themes") or {}).get(today, "editorial")

        folder = os.path.join(base, slugify(today))
        os.makedirs(folder, exist_ok=True)
        _write(os.path.join(folder, f"{date_str}.md"),
               render_markdown(rankings, date_str, [today]))
        html = render_html(rankings, date_str, [today], theme=theme)
        _write(os.path.join(folder, f"{date_str}.html"), html)
        _write(os.path.join(folder, "_latest.html"), html)

        state_dir = os.path.join(HERE, "boards_state")
        save_board_state(state_dir, today, rankings, date_str, now=now)
        save_snapshot(snap_path, repos, now=now, base=prev)

        states = load_all_board_states(state_dir, domains)
        nxt = next_domain(domains, now)
        _write(os.path.join(base, "_总览.md"),
               render_overview_md(states, domains, today, date_str))
        _write(os.path.join(base, "_仪表盘.html"),
               render_dashboard_html(states, domains, today, nxt, date_str))
        print(f"✅ 「{today}」板块报告 → {folder} · 总览已更新(候选池 {rankings['pool_size']})")
    else:
        # 回退:跑全部板块,写到主文件夹根(旧行为)
        repos = collect_repos(client, all_keywords(cfg),
                              cfg["pool_min_stars"], cfg["fetch_cap_per_keyword"])
        rankings = build_rankings(repos, prev, cfg, now=now)
        _write(os.path.join(base, f"{date_str}.md"), render_markdown(rankings, date_str, domains))
        html = render_html(rankings, date_str, domains)
        _write(os.path.join(base, f"{date_str}.html"), html)
        _write(os.path.join(base, "_latest.html"), html)
        save_snapshot(snap_path, repos, now=now, base=prev)
        print(f"✅ 报告(全板块)→ {base}(候选池 {rankings['pool_size']})")


if __name__ == "__main__":
    main()
```

> 注：原 `output_path` 函数已被 `base_folder` 取代；若 `tests/test_radar.py` 仍引用
> `radar.output_path`，相应的两个 `test_output_path_*` 用例在本任务 Step 1 已随文件替换移除。

- [ ] **Step 4: 运行确认通过**

Run: `/Users/jenson/github-radar/.venv/bin/pytest tests/test_radar.py -v`
Expected: PASS（collect ×2 + base_folder ×2 + rotation ×2 = 6）

- [ ] **Step 5: 提交**

```bash
git add radar.py tests/test_radar.py
git commit -m "feat(radar): rotation pipeline — per-board subfolder + state + overview

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 9: `.gitignore` + README + 全量测试 + 真实冒烟

**Files:**
- Modify: `.gitignore`
- Modify: `README.md`

- [ ] **Step 1: `.gitignore` 追加一行**

在 `snapshot.json` 同区追加：

```
boards_state/
```

- [ ] **Step 2: README 增「板块轮换」一节**

在 `README.md` 现有「网页版报告」节后追加（说明 5 板块、日期取模、目录结构、`_总览.md`/`_仪表盘.html`、各板块 `_latest.html` 的主题、`rotation: false` 回退）：

```markdown
## 板块轮换（5 天周期）

`rotation: true`（默认）时，每天按日期取模只跑**一个**板块（`config.yaml` 的
`domains` 顺序即循环序号），第 6 天回到第 1 个。输出结构：

​```
GitHub雷达/
├── _总览.md          # 全部板块一览表
├── _仪表盘.html      # 总览仪表盘（浏览器）
└── <板块名>/         # 每板块一个子文件夹
    ├── _latest.html  # 该板块最新一期（对应主题皮肤）
    ├── <日期>.html
    └── <日期>.md
​```

增速在轮换下仍准确：快照按「每仓库各自上次见到日期」计算（某板块 5 天轮一次→得
5 天平均日增速）。主题由 `themes:` 配置（scope/editorial/console/terminal/homelab）。
设 `rotation: false` 可回退为每天跑全部板块。
```

- [ ] **Step 3: 全量测试**

Run: `/Users/jenson/github-radar/.venv/bin/pytest -q`
Expected: PASS（全绿；约 30+ 项）

- [ ] **Step 4: 真实冒烟（可选，会调用 GitHub API）**

```bash
cd /Users/jenson/github-radar && GITHUB_TOKEN=$(gh auth token) ./.venv/bin/python radar.py
```
Expected: 打印 `✅ 「<板块>」板块报告 → …/GitHub雷达/<slug> · 总览已更新`；
检查 vault 下出现该板块子文件夹 + `_总览.md` + `_仪表盘.html`。
（若不想动真实 vault，可临时把 `config.yaml` 的 `vault_path` 指到一个临时目录。）

- [ ] **Step 5: 提交**

```bash
git add .gitignore README.md
git commit -m "chore: ignore boards_state + document rotation

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

**Phase 1 完成判据：** 全量 pytest 绿；真实/Fake 跑一次后 vault 出现 `<板块>/_latest.html`、
`_总览.md`、`_仪表盘.html`；snapshot 为新格式且合并保留旧板块。

---

# Phase 2 — 5 套主题皮肤

**共用契约（每个 `_render_<theme>` 必须遵守）：**
- 函数签名 `_render_<theme>(rankings, date_str, domains) -> str`，返回完整 HTML 文档。
- **复用** `_html_section(name, en, by, entries)` 渲染三榜（它内部调用 `_html_entry`/`_vel_html`/`_esc`，已含转义）。三榜元数据用现有 `_HTML_BOARDS_META`。
- 主题 CSS **必须定义** shared 行所用的 CSS 自定义属性，使共用的 `.entry/.rk/.e-name/.e-lang/.e-desc/.e-tags/.e-stat/.e-stars/.e-vel/.e-bar/.section/.sec-h` 被正确着色：至少 `--muted`、`--red`（增速色）、`--rule`（分隔/进度条底）、`--ink`、文本主色。
- 含 `@media (prefers-reduced-motion: reduce)` 回退（参考 editorial：`.entry{opacity:1!important;...}` 与 `.e-bar>i{transform:scaleX(var(--w))!important}`）。
- 无 `<script>`；所有外部文本经 `_esc`。
- **在 `<body>` 开头插入主题标记注释 `<!-- theme: <key> -->`**（如 `<!-- theme: scope -->`）。这是 smoke 测试用来区分主题的锚点——否则「未注册时回退到 editorial」会让只测结构的断言误判通过，破坏 TDD 的 RED。
- 在 `_THEME_RENDERERS` 注册键名。
- chrome（标题区/引语/页脚）自带，体现该板块主题语言（见各任务）。

**视觉实现方式：** 每个皮肤任务用 **frontend-design 技能** 驱动设计（先定一个鲜明方向，
再落 CSS），并用 **Claude Preview**（`.claude/launch.json` 已配 `python3 -m http.server 8765`）
渲染 + 截图验收。先写结构 smoke 测试（下方给全），再做视觉。

---

### Task 10: `scope` 主题（示波器/蓝图 · 深色）— 移植 `web/report.html`

**Files:**
- Modify: `ghradar/report.py`（新增 `_render_scope` 并注册）
- Read for reference: `web/report.html`（已存在的深色示波器 demo，取其视觉语言）
- Test: `tests/test_report.py`（追加 scope smoke 测试）

- [ ] **Step 1: 追加 smoke 测试**

```python
def test_render_scope_theme_smoke():
    h = render_html(_rankings(False), "2026-05-30", ["自动化与工作流"], theme="scope")
    assert h.lstrip().startswith("<!DOCTYPE html>")
    assert "<!-- theme: scope -->" in h            # 主题锚点(editorial 没有)
    assert "https://github.com/a/b" in h
    assert "综合榜" in h and "标杆榜" in h and "爆发榜" in h
    assert "+100" in h
    assert "prefers-reduced-motion" in h

def test_render_scope_escapes_untrusted():
    r = _rankings(False)
    r["combined"][0]["description"] = "x <script> & y"
    h = render_html(r, "2026-05-30", ["A"], theme="scope")
    assert "&lt;script&gt;" in h and "<script>" not in h.split("</head>")[1]
```

- [ ] **Step 2: 运行确认失败**

Run: `/Users/jenson/github-radar/.venv/bin/pytest tests/test_report.py -k scope -v`
Expected: FAIL（`_render_scope` 未注册 → 回退 editorial → 缺 `<!-- theme: scope -->` 标记）

- [ ] **Step 3: 实现 `_render_scope`（用 frontend-design + 参考 web/report.html）**

设计方向：深色「磷光示波器/工程蓝图」。要点：
- 字体 `Chakra Petch`（标题）+ `IBM Plex Mono`（数据），加对应 Google Fonts `<link>`。
- 背景近黑 + 细网格/扫描线；强调色磷光绿（如 `#7cf03d`）。chrome 用「雷达扫描」语汇
  （如标题区一条扫描线、英文副标 `OSCILLOSCOPE FEED / 自动化与工作流`）。
- 定义 `--muted/--red(此处为磷光绿)/--rule/--ink` 等，使三榜行被正确着色。
- 三榜用 `"".join(_html_section(name, en, by, rankings[key]) for name,en,by,key in _HTML_BOARDS_META)`。
- 末尾 `_THEME_RENDERERS["scope"] = _render_scope`。

实现后用 Claude Preview 渲染验收：

```bash
# 生成一份 scope 样张到可服务目录
cd /Users/jenson/github-radar && ./.venv/bin/python - <<'PY'
from ghradar.report import render_html
demo={"first_run":False,"pool_size":1605,"combined":[
 {"full_name":"D4Vinci/Scrapling","html_url":"https://github.com/D4Vinci/Scrapling",
  "stars":55653,"language":"Python","description":"An adaptive web scraping framework",
  "topics":["ai","crawler"],"delta":293,"velocity_per_day":293.0,"is_estimated":False}]*8,
 "landmark":[],"burst":[]}
demo["landmark"]=demo["combined"];demo["burst"]=demo["combined"]
open("web/_preview_scope.html","w").write(render_html(demo,"2026-05-31",["自动化与工作流"],theme="scope"))
print("written web/_preview_scope.html")
PY
```
然后用 Preview 打开 `http://localhost:8765/web/_preview_scope.html`，`preview_screenshot` 核对：
深色、磷光绿、网格/扫描线、三榜行可读、移动端不溢出。验收后删除 `web/_preview_scope.html`。

- [ ] **Step 4: 运行确认通过**

Run: `/Users/jenson/github-radar/.venv/bin/pytest tests/test_report.py -k scope -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add ghradar/report.py tests/test_report.py
git commit -m "feat(report): scope theme (oscilloscope/blueprint dark)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 11: `console` 主题（AI · 推理控制台 · 近黑）

**Files:**
- Modify: `ghradar/report.py`（新增 `_render_console` 并注册）
- Test: `tests/test_report.py`（追加 console smoke：同 Task 10 形式，主题改 `console`）

- [ ] **Step 1: 追加 smoke 测试**

```python
def test_render_console_theme_smoke():
    h = render_html(_rankings(False), "2026-05-30", ["AI/大模型应用与框架"], theme="console")
    assert h.lstrip().startswith("<!DOCTYPE html>")
    assert "<!-- theme: console -->" in h
    assert "综合榜" in h and "爆发榜" in h
    assert "prefers-reduced-motion" in h
    r = _rankings(False); r["combined"][0]["description"] = "x <script>"
    h2 = render_html(r, "2026-05-30", ["A"], theme="console")
    assert "&lt;script&gt;" in h2
```

- [ ] **Step 2: 运行确认失败**

Run: `/Users/jenson/github-radar/.venv/bin/pytest tests/test_report.py -k console -v`
Expected: FAIL

- [ ] **Step 3: 实现 `_render_console`（frontend-design）**

设计方向：「推理控制台 / model card」近黑。要点：
- **刻意避开 AI 紫**。近黑底（`#0b0d10`），电青（`#22d3ee`）+ 柠檬高光做强调；
  细等距网格背景；`IBM Plex Sans` + `IBM Plex Mono`。
- chrome：像一个推理面板/spec sheet，副标 `INFERENCE CONSOLE / AI·大模型应用与框架`，
  顶部一行「model card」式的统计条（候选池/快照日期）。
- 定义 shared CSS 变量，三榜行用青/灰阶；进度条 `--red` 用电青。
- 复用 `_html_section` + `_HTML_BOARDS_META`；含 reduced-motion 回退；注册 `console`。
- Preview 验收同 Task 10（样张写 `web/_preview_console.html`，截图核对后删除）。

- [ ] **Step 4: 运行确认通过**

Run: `/Users/jenson/github-radar/.venv/bin/pytest tests/test_report.py -k console -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add ghradar/report.py tests/test_report.py
git commit -m "feat(report): console theme (AI inference console, near-black)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 12: `terminal` 主题（开发者工具/CLI · TUI）

**Files:**
- Modify: `ghradar/report.py`（新增 `_render_terminal` 并注册）
- Test: `tests/test_report.py`（追加 terminal smoke）

- [ ] **Step 1: 追加 smoke 测试**

```python
def test_render_terminal_theme_smoke():
    h = render_html(_rankings(False), "2026-05-30", ["开发者工具 / CLI"], theme="terminal")
    assert h.lstrip().startswith("<!DOCTYPE html>")
    assert "<!-- theme: terminal -->" in h
    assert "综合榜" in h and "爆发榜" in h
    assert "prefers-reduced-motion" in h
    r = _rankings(False); r["combined"][0]["description"] = "x <script>"
    h2 = render_html(r, "2026-05-30", ["A"], theme="terminal")
    assert "&lt;script&gt;" in h2
```

- [ ] **Step 2: 运行确认失败**

Run: `/Users/jenson/github-radar/.venv/bin/pytest tests/test_report.py -k terminal -v`
Expected: FAIL

- [ ] **Step 3: 实现 `_render_terminal`（frontend-design）**

设计方向：终端 TUI。要点：
- 全等宽（`JetBrains Mono` 或 `IBM Plex Mono`），终端底 `#0c0c0c`，绿/琥珀提示符配色；
  chrome 用命令行语汇（标题如 `$ radar --board "开发者工具/CLI"`，分隔用 ASCII `───`/方框字符）。
- 三榜小标题前缀像 `▸` 或 `[combined]`；进度条用字符块或细线；定义 shared CSS 变量。
- 复用 `_html_section` + `_HTML_BOARDS_META`；reduced-motion 回退（可保留打字机式入场但回退要静止）；注册 `terminal`。
- Preview 验收（`web/_preview_terminal.html`，截图后删）。

- [ ] **Step 4: 运行确认通过**

Run: `/Users/jenson/github-radar/.venv/bin/pytest tests/test_report.py -k terminal -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add ghradar/report.py tests/test_report.py
git commit -m "feat(report): terminal theme (dev tools / CLI, TUI)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 13: `homelab` 主题（自托管/效率 · 浅色面板）

**Files:**
- Modify: `ghradar/report.py`（新增 `_render_homelab` 并注册）
- Test: `tests/test_report.py`（追加 homelab smoke）

- [ ] **Step 1: 追加 smoke 测试**

```python
def test_render_homelab_theme_smoke():
    h = render_html(_rankings(False), "2026-05-30", ["自托管 / 效率应用"], theme="homelab")
    assert h.lstrip().startswith("<!DOCTYPE html>")
    assert "<!-- theme: homelab -->" in h
    assert "综合榜" in h and "爆发榜" in h
    assert "prefers-reduced-motion" in h
    r = _rankings(False); r["combined"][0]["description"] = "x <script>"
    h2 = render_html(r, "2026-05-30", ["A"], theme="homelab")
    assert "&lt;script&gt;" in h2
```

- [ ] **Step 2: 运行确认失败**

Run: `/Users/jenson/github-radar/.venv/bin/pytest tests/test_report.py -k homelab -v`
Expected: FAIL

- [ ] **Step 3: 实现 `_render_homelab`（frontend-design）**

设计方向：「家庭实验室控制面板」浅色、干净现代。要点：
- `Space Grotesk`（标题）+ 系统无衬线/等宽（数据）；浅底（`#f6f8fa`）、大量留白、
  柔和卡片阴影、青绿点缀（`#0d9488`）。chrome 像一个 self-hosted 面板的总览页。
- 三榜做成带柔和分隔的卡片式列表；定义 shared CSS 变量（`--red` 用青绿）。
- 复用 `_html_section` + `_HTML_BOARDS_META`；reduced-motion 回退；注册 `homelab`。
- Preview 验收（`web/_preview_homelab.html`，截图后删）。

- [ ] **Step 4: 运行确认通过**

Run: `/Users/jenson/github-radar/.venv/bin/pytest tests/test_report.py -k homelab -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add ghradar/report.py tests/test_report.py
git commit -m "feat(report): homelab theme (self-hosted/productivity, light)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

# Phase 3 — 总览仪表盘（bespoke）

### Task 14: `_仪表盘.html` 升级为「指挥中心」

**Files:**
- Modify: `ghradar/overview.py`（重写 `render_dashboard_html` 与 `_DASH_CSS`）
- Test: `tests/test_overview.py`（已有的 `test_dashboard_html_is_full_doc_and_escapes` 必须仍绿；追加主色/今日标记断言）

- [ ] **Step 1: 追加断言（在 test_overview.py 末尾）**

```python
def test_dashboard_marks_today_and_next():
    states = {d: None for d in DOMAINS}
    h = render_dashboard_html(states, DOMAINS, today="自动化与工作流",
                              nxt="内容创作与分发", today_str="2026-05-31")
    assert "今天" in h
    assert "自动化与工作流" in h and "内容创作与分发" in h
    assert "尚未采集" in h            # 未采集板块仍显示
```

- [ ] **Step 2: 运行确认（现占位应已通过基本项；新断言可能需要微调）**

Run: `/Users/jenson/github-radar/.venv/bin/pytest tests/test_overview.py -v`
Expected: 基本项 PASS；`test_dashboard_marks_today_and_next` 视占位实现可能需 Step 3 后通过

- [ ] **Step 3: 重写 `render_dashboard_html`（frontend-design · 指挥中心）**

设计方向：「指挥中心 / mission control」。要点：
- 5 张板块卡片，**每张带该板块主题的主色**做色卡/边条（scope 磷光绿、editorial 朱红、
  console 电青、terminal 琥珀、homelab 青绿），让仪表盘把 5 个板块的视觉串起来。
- 每卡显示：板块名、上次更新（相对天数）、候选池、综合榜首（名+增速）、爆发榜首。
- 顶部状态条：今天是哪个板块（高亮）、接下来轮到谁、5 天循环的位置指示（如 5 个点）。
- 未采集板块显示「尚未采集」灰态。HTML 转义、无 `<script>`、`prefers-reduced-motion` 回退。
- 复用 `_rel_days`/`_vel_text`/`_top`/`_esc`。
- Preview 验收：

```bash
cd /Users/jenson/github-radar && ./.venv/bin/python - <<'PY'
from ghradar.overview import render_dashboard_html
def e(n,d): return {"full_name":n,"html_url":"#","stars":12345,"velocity_per_day":float(d),"delta":d,"is_estimated":False}
def st(dom,ds,n,d): return {"domain":dom,"slug":dom,"updated_at":"x","date_str":ds,"pool_size":1200,"combined":[e(n,d)],"burst":[e(n,d)]}
DOMAINS=["自动化与工作流","内容创作与分发","AI/大模型应用与框架","开发者工具 / CLI","自托管 / 效率应用"]
states={d:None for d in DOMAINS}
states["自动化与工作流"]=st("自动化与工作流","2026-05-31","D4Vinci/Scrapling",293)
states["内容创作与分发"]=st("内容创作与分发","2026-05-27","op7418/guizang-social-card-skill",251)
open("web/_preview_dash.html","w").write(render_dashboard_html(states,DOMAINS,"自动化与工作流","内容创作与分发","2026-05-31"))
print("written web/_preview_dash.html")
PY
```
用 Preview 打开 `http://localhost:8765/web/_preview_dash.html` 截图核对，验收后删除样张。

- [ ] **Step 4: 全量测试 + 真实冒烟**

Run: `/Users/jenson/github-radar/.venv/bin/pytest -q`
Expected: 全绿。
再跑一次真实/Fake `radar.py`，浏览器打开 vault 下 `_仪表盘.html` 与各板块 `_latest.html` 目检。

- [ ] **Step 5: 提交**

```bash
git add ghradar/overview.py tests/test_overview.py
git commit -m "feat(overview): mission-control dashboard with per-board accent colors

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## 收尾（全部 Phase 完成后）

- [ ] 全量 `pytest -q` 绿。
- [ ] 在 main 上 ff-merge：`git checkout main && git merge --ff-only feat/domain-rotation`。
- [ ] 推公开仓库前扫描 secrets/个人路径（`git diff` 检查无 token、无真实 `vault_path`、无 `config.yaml`）。
- [ ] 用户确认后 `git push origin main`。
- [ ] 更新记忆笔记 `github-radar-project.md`（轮换 + 5 主题 + 总览 + 仪表盘）。

## 范围之外（YAGNI）
不绑定星期几、不可配循环长度、不做板块差异化权重、不做历史趋势图。
