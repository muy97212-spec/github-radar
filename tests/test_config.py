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
