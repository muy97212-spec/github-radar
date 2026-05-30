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
