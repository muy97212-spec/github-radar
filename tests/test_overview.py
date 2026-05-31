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
