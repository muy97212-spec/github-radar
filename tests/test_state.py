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
