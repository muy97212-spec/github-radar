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
    boards = [p for p in base.iterdir() if p.is_dir()]
    assert len(boards) == 1
    latest = boards[0] / "_latest.html"
    assert latest.read_text(encoding="utf-8").lstrip().startswith("<!DOCTYPE html>")
    assert "a/b" in latest.read_text(encoding="utf-8")
    assert list(boards[0].glob("*.md"))                          # 带日期 md
    assert (base / "_总览.md").exists()
    assert (base / "_仪表盘.html").read_text(encoding="utf-8").lstrip().startswith("<!DOCTYPE html>")
    assert (tmp_path / "snapshot.json").exists()                 # 快照落盘(新格式)
    assert (tmp_path / "boards_state").exists()                  # 板块状态缓存

def test_rotation_snapshot_merge_preserves_other_boards(tmp_path, monkeypatch):
    import json
    vault = tmp_path / "vault"; vault.mkdir()
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
