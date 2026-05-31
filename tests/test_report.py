# tests/test_report.py
from ghradar.report import render_markdown, render_html

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


# ---- render_html (编辑部「晨报」风网页版) ----

def test_html_is_full_document_with_data():
    h = render_html(_rankings(False), "2026-05-30", ["自动化与工作流"])
    assert h.lstrip().startswith("<!DOCTYPE html>")
    assert "GitHub 雷达" in h
    assert "2026" in h
    assert "https://github.com/a/b" in h          # 仓库链接
    assert "综合榜" in h and "标杆榜" in h and "爆发榜" in h
    assert "+100" in h                             # 真实涨幅
    assert "1,234" in h                            # 千分位星数

def test_html_escapes_untrusted_text():
    r = _rankings(False)
    r["combined"][0]["description"] = "x <script> & y"
    h = render_html(r, "2026-05-30", ["A"])
    assert "&lt;script&gt;" in h                   # 转义后
    assert "<script>" not in h                     # 不出现裸标签

def test_html_first_run_marks_estimated():
    h = render_html(_rankings(True), "2026-05-30", ["A"])
    assert ("首跑" in h) or ("估算" in h)

def test_html_empty_boards_does_not_crash():
    r = {"first_run": False, "pool_size": 0, "combined": [], "landmark": [], "burst": []}
    h = render_html(r, "2026-05-30", ["A"])
    assert "<!DOCTYPE html>" in h

def test_render_html_unknown_theme_falls_back_to_editorial():
    h = render_html(_rankings(False), "2026-05-30", ["A"], theme="does-not-exist")
    assert h.lstrip().startswith("<!DOCTYPE html>")
    assert "综合榜" in h

def test_render_html_editorial_theme_explicit():
    h = render_html(_rankings(False), "2026-05-30", ["A"], theme="editorial")
    assert "晨报" in h  # 编辑部 chrome 标志


def test_render_scope_theme_smoke():
    h = render_html(_rankings(False), "2026-05-30", ["自动化与工作流"], theme="scope")
    assert h.lstrip().startswith("<!DOCTYPE html>")
    assert "<!-- theme: scope -->" in h            # 主题锚点(editorial 没有)
    assert "https://github.com/a/b" in h
    assert "综合榜" in h and "标杆榜" in h and "爆发榜" in h
    assert "+100" in h
    assert "prefers-reduced-motion" in h


def test_render_scope_escapes_untrusted():
    r = _rankings(False)
    r["combined"][0]["description"] = "x <script> & y"
    h = render_html(r, "2026-05-30", ["A"], theme="scope")
    assert "&lt;script&gt;" in h and "<script>" not in h.split("</head>")[1]


def _theme_smoke(theme):
    h = render_html(_rankings(False), "2026-05-30", ["板块"], theme=theme)
    assert h.lstrip().startswith("<!DOCTYPE html>")
    assert f"<!-- theme: {theme} -->" in h
    assert "https://github.com/a/b" in h
    assert "综合榜" in h and "标杆榜" in h and "爆发榜" in h
    assert "+100" in h
    assert "prefers-reduced-motion" in h
    r = _rankings(False)
    r["combined"][0]["description"] = "x <script> & y"
    h2 = render_html(r, "2026-05-30", ["A"], theme=theme)
    assert "&lt;script&gt;" in h2 and "<script>" not in h2.split("</head>")[1]


def test_render_console_theme_smoke():
    _theme_smoke("console")


def test_render_terminal_theme_smoke():
    _theme_smoke("terminal")


def test_render_homelab_theme_smoke():
    _theme_smoke("homelab")
