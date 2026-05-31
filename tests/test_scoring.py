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
