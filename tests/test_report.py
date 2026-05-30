# tests/test_report.py
from ghradar.report import render_markdown

def _enriched(name, stars, delta, vpd, estimated):
    return {"full_name": name, "html_url": f"https://github.com/{name}",
            "stars": stars, "language": "Python", "description": "一句话",
            "topics": ["ai", "cli"], "delta": delta,
            "velocity_per_day": vpd, "is_estimated": estimated}

def _rankings(first_run):
    e = _enriched("a/b", 1234, None if first_run else 100, 10.0, first_run)
    return {"first_run": first_run, "pool_size": 7,
            "combined": [e], "landmark": [e], "burst": [e]}

def test_frontmatter_and_title_present():
    md = render_markdown(_rankings(False), "2026-05-30", ["自动化与工作流"])
    assert md.startswith("---\n")
    assert "tags: [github雷达]" in md
    assert "date: 2026-05-30" in md
    assert "# GitHub 雷达 · 2026-05-30" in md

def test_repo_link_and_sections():
    md = render_markdown(_rankings(False), "2026-05-30", ["A", "B"])
    assert "[a/b](https://github.com/a/b)" in md
    assert "🥇 综合榜" in md and "🏆 标杆榜" in md and "🚀 爆发榜" in md
    assert "+100" in md  # 真实涨幅

def test_first_run_note_and_estimated_growth():
    md = render_markdown(_rankings(True), "2026-05-30", ["A"])
    assert "首跑" in md
    assert "估算" in md

def test_empty_section_renders_placeholder():
    r = {"first_run": False, "pool_size": 0, "combined": [], "landmark": [], "burst": []}
    md = render_markdown(r, "2026-05-30", ["A"])
    assert "本期无" in md
