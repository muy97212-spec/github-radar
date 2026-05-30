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
    assert repos[0]["stars"] == 99  # 保留 star 更高的那份

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

def test_main_writes_report_to_vault_and_saves_snapshot(tmp_path, monkeypatch):
    # 全程不碰真实网络/真实 vault:patch 掉 client、config、HERE(快照目录)。
    vault = tmp_path / "vault"
    vault.mkdir()
    cfg = {"github_token": None, "pool_min_stars": 50, "fetch_cap_per_keyword": 10,
           "domains": {"自动化": ["k"]}, "weights": {"stock": 0.4, "velocity": 0.6},
           "top_k": 5, "burst_min_delta": 20,
           "vault_path": str(vault), "report_folder": "GitHub雷达"}
    monkeypatch.setattr(radar, "HERE", str(tmp_path))
    monkeypatch.setattr(radar, "load_config", lambda path: cfg)
    monkeypatch.setattr(radar, "GitHubClient", lambda token=None: FakeClient([_repo("a/b", 100)]))
    radar.main()
    reports = list((vault / "GitHub雷达").glob("*.md"))
    assert len(reports) == 1                      # 报告写进了 vault
    assert "a/b" in reports[0].read_text(encoding="utf-8")
    assert (tmp_path / "snapshot.json").exists()  # 快照在写报告之后落盘
