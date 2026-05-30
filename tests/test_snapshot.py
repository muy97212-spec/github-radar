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
