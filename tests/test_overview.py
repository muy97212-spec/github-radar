# tests/test_overview.py
from ghradar.overview import render_overview_md, render_dashboard_html

def _state(domain, date_str, top_name, delta):
    e = {"full_name": top_name, "html_url": f"https://github.com/{top_name}",
         "stars": 1234, "velocity_per_day": float(delta), "delta": delta, "is_estimated": False}
    return {"domain": domain, "slug": domain, "updated_at": "x", "date_str": date_str,
            "pool_size": 99, "combined": [e], "burst": [e]}

DOMAINS = ["自动化与工作流", "内容创作与分发", "AI/大模型应用与框架",
           "开发者工具 / CLI", "自托管 / 效率应用"]

def test_overview_md_has_row_per_board_and_marks_uncollected():
    states = {d: None for d in DOMAINS}
    states["自动化与工作流"] = _state("自动化与工作流", "2026-05-31", "D4Vinci/Scrapling", 293)
    md = render_overview_md(states, DOMAINS, today="自动化与工作流", today_str="2026-05-31")
    assert md.count("|") >= 6 * (len(DOMAINS) + 2)   # 表头 + 分隔 + 5 行
    assert "尚未采集" in md                            # 未采集板块
    assert "D4Vinci/Scrapling" in md                  # 已采集榜首
    assert "今天" in md                                # 今日板块标记/相对天数

def test_overview_md_relative_days():
    states = {d: None for d in DOMAINS}
    states["内容创作与分发"] = _state("内容创作与分发", "2026-05-26", "a/b", 10)
    md = render_overview_md(states, DOMAINS, today="自动化与工作流", today_str="2026-05-31")
    assert "5 天前" in md

def test_dashboard_html_is_full_doc_and_escapes():
    states = {d: None for d in DOMAINS}
    states["AI/大模型应用与框架"] = _state("AI/大模型应用与框架", "2026-05-31", "x<script>/y", 5)
    h = render_dashboard_html(states, DOMAINS, today="AI/大模型应用与框架",
                              nxt="开发者工具 / CLI", today_str="2026-05-31")
    assert h.lstrip().startswith("<!DOCTYPE html>")
    assert "<script>/y" not in h and "&lt;script&gt;" in h   # 转义
    assert "AI/大模型应用与框架" in h
    assert "prefers-reduced-motion" in h                     # 无障碍回退存在
    assert "<script>" not in h.split("</head>")[1]           # body 内无裸 script


def test_dashboard_marks_today_and_next():
    states = {d: None for d in DOMAINS}
    h = render_dashboard_html(states, DOMAINS, today=DOMAINS[0],
                              nxt=DOMAINS[1], today_str="2026-05-31")
    assert "LIVE" in h or "今日" in h          # 今日板块标记
    assert "下一班" in h                        # 接下来板块标记
    assert DOMAINS[0] in h and DOMAINS[1] in h
    assert "轮值环" in h                        # 5 天轮值环存在


def test_dashboard_links_collected_board_to_its_report():
    from urllib.parse import quote
    from ghradar.domains import slugify
    states = {d: None for d in DOMAINS}
    states[DOMAINS[0]] = _state(DOMAINS[0], "2026-05-31", "a/b", 10)  # 已采集(mini 卡)
    h = render_dashboard_html(states, DOMAINS, today=DOMAINS[1],
                              nxt=DOMAINS[2], today_str="2026-05-31")
    assert quote(slugify(DOMAINS[0])) + "/_latest.html" in h          # 已采集 → 有跳转
    assert quote(slugify(DOMAINS[3])) + "/_latest.html" not in h      # 未采集 → 不造失效链接


def test_dashboard_uses_configured_theme_accent():
    from ghradar.report import theme_accent
    states = {d: None for d in DOMAINS}
    # 配置了 console 主题的板块,其强调色应出现在卡片/节点上色里(不写死具体色值)
    themes = {DOMAINS[0]: "console"}
    h = render_dashboard_html(states, DOMAINS, today=DOMAINS[0], nxt=DOMAINS[1],
                              today_str="2026-05-31", themes=themes)
    assert theme_accent("console") in h
