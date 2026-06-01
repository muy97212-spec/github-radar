#!/usr/bin/env python3
"""本地预览生成器 —— 用内置样例数据离线重建 web/ 下的样张,便于挑配色/改排版。

不打 GitHub API、不依赖实时快照,纯渲染当前代码的输出:
  - web/_preview_<theme>.html   5 套板块皮肤(editorial/console/scope/terminal/homelab)
  - web/_preview_dashboard.html 暖纸总览仪表盘

用法:  .venv/bin/python scripts/make_previews.py
web/ 是 gitignored 的草稿区,删了随时跑这个脚本重建即可。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ghradar.report import render_html, _THEMES  # noqa: E402
from ghradar.overview import render_dashboard_html  # noqa: E402

WEB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web")
DATE = "2026-05-31"

# 每套皮肤对应的板块标签(仅用于报头文案展示)
THEME_LABEL = {
    "editorial": "内容创作与分发",
    "console": "AI/大模型应用与框架",
    "scope": "自动化与工作流",
    "terminal": "开发者工具 / CLI",
    "homelab": "自托管 / 效率应用",
}

DOMAINS = ["自动化与工作流", "内容创作与分发", "AI/大模型应用与框架",
           "开发者工具 / CLI", "自托管 / 效率应用"]
THEMES = {"自动化与工作流": "scope", "内容创作与分发": "editorial",
          "AI/大模型应用与框架": "console", "开发者工具 / CLI": "terminal",
          "自托管 / 效率应用": "homelab"}


def _entry(name, stars, delta, est=False):
    return {"full_name": name, "html_url": f"https://github.com/{name}",
            "stars": stars, "velocity_per_day": float(delta), "delta": delta,
            "is_estimated": est}


def _sample_rankings():
    combined = [_entry("sgl-project/sglang", 28710, 71),
                _entry("ggml-org/llama.cpp", 113973, 33),
                _entry("unslothai/unsloth", 41200, 58),
                _entry("crewAIInc/crewAI", 39800, 27),
                _entry("Mintplex-Labs/anything-llm", 51200, 19)]
    landmark = [_entry("ggml-org/llama.cpp", 113973, 33),
                _entry("langchain-ai/langchain", 102300, 22),
                _entry("Mintplex-Labs/anything-llm", 51200, 19)]
    burst = [_entry("sgl-project/sglang", 28710, 71),
             _entry("unslothai/unsloth", 41200, 58),
             _entry("modelscope/ms-swift", 9700, 44)]
    return {"pool_size": 751, "first_run": False,
            "combined": combined, "landmark": landmark, "burst": burst}


def _sample_states():
    r = _sample_rankings()
    base = {"updated_at": "2026-05-31T15:38:14+00:00", "date_str": DATE,
            "pool_size": r["pool_size"], "combined": r["combined"], "burst": r["burst"]}
    states = {d: None for d in DOMAINS}
    # 今日板块 + 另两个"已采集",其余留空(演示未采集态/不造失效链接)
    for d in ("AI/大模型应用与框架", "自动化与工作流", "自托管 / 效率应用"):
        states[d] = {"domain": d, "slug": d, **base}
    return states


def main():
    os.makedirs(WEB, exist_ok=True)
    written = []
    rk = _sample_rankings()
    for theme in _THEMES:
        html = render_html(rk, DATE, [THEME_LABEL.get(theme, theme)], theme=theme)
        path = os.path.join(WEB, f"_preview_{theme}.html")
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        written.append(path)

    states = _sample_states()
    html = render_dashboard_html(states, DOMAINS, today="AI/大模型应用与框架",
                                 nxt="开发者工具 / CLI", today_str=DATE, themes=THEMES)
    path = os.path.join(WEB, "_preview_dashboard.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    written.append(path)

    for p in written:
        print("✅", os.path.relpath(p))
    print(f"\n共 {len(written)} 张 → 用浏览器 file:// 打开挑选即可。")


if __name__ == "__main__":
    main()
