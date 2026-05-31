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


# ---- 轮换/主题新增 ----

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
