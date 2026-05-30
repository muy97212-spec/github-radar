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
