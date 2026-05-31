# ghradar/overview.py
"""跨全部板块的总览:_总览.md(表格) + _仪表盘.html(面板)。
只有当天板块真去搜,这里读 boards_state 缓存来展示全部 5 个板块的最新态。"""
import html as _html
from datetime import datetime


def _esc(s):
    return _html.escape(str(s) if s is not None else "")


def _rel_days(date_str, today_str):
    try:
        d0 = datetime.strptime(date_str, "%Y-%m-%d").date()
        d1 = datetime.strptime(today_str, "%Y-%m-%d").date()
        n = (d1 - d0).days
        return "今天" if n <= 0 else f"{n} 天前"
    except (ValueError, TypeError):
        return date_str or "—"


def _vel_text(e):
    if e is None:
        return "—"
    if e.get("is_estimated"):
        return f"约 +{e['velocity_per_day']:.0f}/天"
    if e.get("delta") == 0:
        return "持平"
    return f"+{e.get('delta')}/天"


def _top(state, board):
    items = (state or {}).get(board) or []
    return items[0] if items else None


def render_overview_md(states, domains, today, today_str):
    lines = [
        "---", "tags: [github雷达, 总览]", f"date: {today_str}", "---", "",
        "# GitHub 雷达 · 总览", "",
        f"> 今日板块：**{today}** · 5 天轮换 · 快照 {today_str}", "",
        "| 板块 | 上次更新 | 候选池 | 综合榜首 | 榜首增速 | 爆发榜首 |",
        "|------|---------|-------|---------|---------|---------|",
    ]
    for d in domains:
        st = states.get(d)
        mark = " ⬅️ 今天" if d == today else ""
        if not st:
            lines.append(f"| {d}{mark} | 尚未采集 | — | — | — | — |")
            continue
        c = _top(st, "combined")
        b = _top(st, "burst")
        lines.append(
            f"| {d}{mark} | {_rel_days(st.get('date_str'), today_str)} "
            f"| {st.get('pool_size', '—')} | {c['full_name'] if c else '—'} "
            f"| {_vel_text(c)} | {b['full_name'] if b else '—'} |"
        )
    return "\n".join(lines) + "\n"


# ---- 仪表盘(占位:可用 + 通过 smoke 测试;后续任务用 frontend-design 美化) ----
_DASH_CSS = """
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:ui-sans-serif,system-ui,"PingFang SC",sans-serif;background:#0f1115;color:#e6e6e6;padding:32px}
h1{font-size:22px;margin-bottom:4px}.sub{color:#9aa0a6;font-size:13px;margin-bottom:24px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:16px}
.card{background:#171a21;border:1px solid #262b34;border-radius:12px;padding:18px}
.card.today{border-color:#7cf03d;box-shadow:0 0 0 1px #7cf03d}
.card h2{font-size:15px;margin-bottom:8px}.card .meta{color:#9aa0a6;font-size:12px}
.card .top{margin-top:10px;font-size:13px}.tag{font-size:11px;color:#0f1115;background:#7cf03d;border-radius:4px;padding:1px 6px}
@media (prefers-reduced-motion: reduce){*{animation:none!important;transition:none!important}}
"""


def render_dashboard_html(states, domains, today, nxt, today_str):
    cards = []
    for d in domains:
        st = states.get(d)
        cls = "card today" if d == today else "card"
        tag = '<span class="tag">今天</span>' if d == today else (
            "（接下来）" if d == nxt else "")
        if not st:
            body = '<div class="meta">尚未采集</div>'
        else:
            c = _top(st, "combined")
            body = (f'<div class="meta">{_esc(_rel_days(st.get("date_str"), today_str))}'
                    f' · 池 {st.get("pool_size", "—")}</div>'
                    f'<div class="top">综合榜首：{_esc(c["full_name"]) if c else "—"}'
                    f' · {_esc(_vel_text(c))}</div>')
        cards.append(f'<div class="{cls}"><h2>{_esc(d)} {tag}</h2>{body}</div>')
    return (
        '<!DOCTYPE html>\n<html lang="zh-CN">\n<head>\n<meta charset="UTF-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        f"<title>GitHub 雷达 · 总览仪表盘 · {_esc(today_str)}</title>\n"
        f"<style>{_DASH_CSS}</style>\n</head>\n<body>\n"
        f"<h1>GitHub 雷达 · 总览仪表盘</h1>"
        f'<div class="sub">今日板块 {_esc(today)} · 接下来 {_esc(nxt)} · 快照 {_esc(today_str)}</div>'
        f'<div class="grid">{"".join(cards)}</div>\n</body>\n</html>\n'
    )
