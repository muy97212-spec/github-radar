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
