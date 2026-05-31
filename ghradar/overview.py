# ghradar/overview.py
"""跨全部板块的总览:_总览.md(表格) + _仪表盘.html(面板)。
只有当天板块真去搜,这里读 boards_state 缓存来展示全部 5 个板块的最新态。"""
import html as _html
from datetime import datetime

from ghradar.report import theme_accent


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


# ============================================================
# 总览仪表盘 _仪表盘.html —— 雷达指挥中心 / Mission Control
# 暗色作战面板:旋转 PPI 扫描 + 5 天「轮值环」+ 各板块卡片(用其主题强调色着色)。
# chrome 用中性青绿,让 5 个板块色在卡片/环上跳出来。不含 <script>,外部文本全转义。
# ============================================================

_DASH_FONTS = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link href="https://fonts.googleapis.com/css2?'
    'family=Oxanium:wght@400;500;600;700;800&family=IBM+Plex+Mono:wght@400;500;600'
    '&display=swap" rel="stylesheet">'
)

_DASH_CSS = r"""
*{margin:0;padding:0;box-sizing:border-box}
:root{
  --bg:#070b11;--panel:#0d141d;--panel-2:#101a25;
  --line:#1b2734;--ink:#d8e4ee;--ink-soft:#90a3b5;--muted:#566a7c;
  --signal:#3fd0c0;
  --display:"Oxanium","PingFang SC","Microsoft YaHei",sans-serif;
  --mono:"IBM Plex Mono",ui-monospace,SFMono-Regular,monospace;
}
html{scroll-behavior:smooth}
body{background:var(--bg);color:var(--ink);font-family:var(--display);font-size:16px;line-height:1.6;
  -webkit-font-smoothing:antialiased;min-height:100vh;
  background-image:
    radial-gradient(circle at 88% -10%,rgba(63,208,192,.07),transparent 42%),
    radial-gradient(circle at 4% 112%,rgba(34,211,238,.05),transparent 46%),
    repeating-linear-gradient(0deg,rgba(120,160,190,.02) 0 1px,transparent 1px 40px),
    repeating-linear-gradient(90deg,rgba(120,160,190,.02) 0 1px,transparent 1px 40px)}
.mono{font-family:var(--mono)}
.wrap{max-width:1080px;margin:0 auto;padding:34px 30px 64px}

/* ---- 指挥头 ---- */
.hd{position:relative;border:1px solid var(--line);border-radius:18px;overflow:hidden;
  background:linear-gradient(155deg,var(--panel-2),var(--panel));padding:28px 30px}
.hd .ppi,.hd .sweep{position:absolute;top:-78px;right:-78px;width:280px;height:280px;border-radius:50%;
  -webkit-mask:radial-gradient(circle at center,#000 58%,transparent 71%);
  mask:radial-gradient(circle at center,#000 58%,transparent 71%)}
.hd .ppi{opacity:.55;background:
  repeating-radial-gradient(circle at center,rgba(120,200,220,.12) 0 1px,transparent 1px 32px),
  conic-gradient(from 0deg,transparent 0 89deg,rgba(120,200,220,.10) 90deg 91deg,transparent 91deg 179deg,
    rgba(120,200,220,.10) 180deg 181deg,transparent 181deg 269deg,rgba(120,200,220,.10) 270deg 271deg,transparent 271deg)}
.hd .sweep{background:conic-gradient(from 0deg,transparent 0 296deg,
  color-mix(in srgb,var(--signal) 22%,transparent) 344deg,var(--signal) 360deg);
  animation:sweep 6.5s linear infinite;mix-blend-mode:screen}
@keyframes sweep{to{transform:rotate(360deg)}}
.hd .kick{font-family:var(--mono);font-size:11px;letter-spacing:.34em;text-transform:uppercase;color:var(--muted)}
.hd h1{font-weight:800;font-size:clamp(32px,5.6vw,56px);letter-spacing:.03em;line-height:1;margin:9px 0 5px}
.hd h1 .mid{color:var(--signal)}
.hd .tag{font-weight:600;font-size:15px;color:var(--ink-soft);letter-spacing:.07em}
.telem{display:flex;flex-wrap:wrap;gap:9px 22px;margin-top:20px;font-family:var(--mono);font-size:12px;color:var(--ink-soft)}
.telem span{display:inline-flex;align-items:center;gap:8px}
.telem b{color:var(--ink);font-weight:500}
.dot{width:8px;height:8px;border-radius:50%;background:var(--signal);box-shadow:0 0 9px var(--signal);
  animation:pulse 2.4s ease-in-out infinite}
@keyframes pulse{50%{opacity:.3}}

/* ---- 轮值环 ---- */
.cycle{margin:22px 0 6px;border:1px solid var(--line);border-radius:16px;background:var(--panel);padding:22px 24px}
.cycle .lab{font-family:var(--mono);font-size:10.5px;letter-spacing:.28em;text-transform:uppercase;color:var(--muted);margin-bottom:18px}
.track{display:grid;grid-template-columns:repeat(5,1fr);position:relative}
.track::before{content:"";position:absolute;left:10%;right:10%;top:12px;height:2px;
  background:repeating-linear-gradient(90deg,var(--line) 0 8px,transparent 8px 15px)}
.node{display:flex;flex-direction:column;align-items:center;text-align:center;gap:10px;position:relative;z-index:1;padding:0 4px}
.node .pip{width:26px;height:26px;border-radius:50%;border:2px solid var(--line);background:var(--bg);
  display:grid;place-items:center;font-family:var(--mono);font-size:11px;font-weight:600;color:var(--muted)}
.node.on .pip{border-color:var(--accent);background:var(--accent);color:#04070b;
  box-shadow:0 0 0 5px color-mix(in srgb,var(--accent) 20%,transparent),0 0 20px color-mix(in srgb,var(--accent) 55%,transparent)}
.node.next .pip{border-color:var(--accent);color:var(--accent)}
.node .nm{font-size:12.5px;font-weight:600;color:var(--ink-soft);line-height:1.3;max-width:13ch}
.node.on .nm{color:var(--ink)}
.node .when{font-family:var(--mono);font-size:9.5px;letter-spacing:.14em;text-transform:uppercase;color:var(--muted)}
.node.on .when{color:var(--accent)}
.node.next .when{color:var(--accent)}

/* ---- 板块卡片 ---- */
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:16px;margin-top:18px}
.card{position:relative;border:1px solid var(--line);border-top:3px solid var(--accent);border-radius:14px;
  background:var(--panel);padding:17px 18px 15px;overflow:hidden;
  transition:transform .2s ease,border-color .2s ease;
  opacity:0;transform:translateY(10px);animation:rise .5s ease forwards}
@keyframes rise{to{opacity:1;transform:none}}
.card::after{content:"";position:absolute;inset:0;pointer-events:none;
  background:radial-gradient(circle at 100% 0,color-mix(in srgb,var(--accent) 11%,transparent),transparent 56%)}
.card:hover{transform:translateY(-3px);border-color:color-mix(in srgb,var(--accent) 50%,var(--line))}
.card.today{border-color:color-mix(in srgb,var(--accent) 55%,var(--line));
  box-shadow:0 0 0 1px color-mix(in srgb,var(--accent) 38%,transparent),
    0 16px 42px -20px color-mix(in srgb,var(--accent) 65%,transparent)}
.c-top{display:flex;align-items:flex-start;justify-content:space-between;gap:10px;position:relative;z-index:1}
.c-name{font-weight:700;font-size:18.5px;letter-spacing:.01em;color:var(--ink);line-height:1.22}
.skin{font-family:var(--mono);font-size:9.5px;letter-spacing:.14em;text-transform:uppercase;white-space:nowrap;
  color:var(--accent);border:1px solid color-mix(in srgb,var(--accent) 42%,var(--line));border-radius:999px;padding:3px 9px}
.badge{display:inline-flex;align-items:center;gap:7px;font-family:var(--mono);font-size:10.5px;letter-spacing:.14em;
  text-transform:uppercase;margin-top:12px;color:var(--accent)}
.badge .b-dot{width:6px;height:6px;border-radius:50%;background:var(--accent);box-shadow:0 0 8px var(--accent)}
.badge.dim{color:var(--muted)}.badge.dim .b-dot{background:var(--muted);box-shadow:none}
.c-rule{height:1px;background:var(--line);margin:13px 0 4px}
.row{display:flex;align-items:baseline;justify-content:space-between;gap:12px;padding:5px 0}
.row .k{font-family:var(--mono);font-size:10px;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);white-space:nowrap}
.row .v{font-size:14px;color:var(--ink);text-align:right;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.row .v a{color:var(--ink);text-decoration:none}
.row .v a:hover{color:var(--accent);text-decoration:underline;text-underline-offset:2px}
.row .vel{font-family:var(--mono);color:var(--accent);font-size:13px}
.c-foot{display:flex;gap:16px;font-family:var(--mono);font-size:10px;letter-spacing:.06em;color:var(--muted);margin-top:11px}
.empty{color:var(--muted);font-style:italic;font-size:13.5px;padding:10px 0 4px}

.colophon{margin-top:30px;text-align:center;font-family:var(--mono);font-size:11px;letter-spacing:.12em;
  text-transform:uppercase;color:var(--muted)}

@media (prefers-reduced-motion: reduce){
  .hd .sweep{animation:none;background:conic-gradient(from 300deg,transparent 0 300deg,color-mix(in srgb,var(--signal) 30%,transparent) 360deg)}
  .dot{animation:none}
  .card{opacity:1!important;transform:none!important;animation:none!important;transition:none}
}
@media(max-width:620px){
  .cycle{overflow-x:auto}.track{min-width:480px}
  .node .nm{font-size:11px}
}
"""

# 主题 → 卡片右上角中文小标(skin pill)
_SKIN_CN = {"editorial": "晨报", "scope": "示波", "console": "推理台",
            "terminal": "终端", "homelab": "面板"}
# 未配置主题时,按位置轮配 5 套皮肤,保证每板块卡片都有独立色
_CYCLE_THEMES = ["editorial", "scope", "console", "terminal", "homelab"]


def _cycle_when(delta):
    if delta is None:
        return ""
    if delta == 0:
        return "今天"
    if delta == 1:
        return "明天"
    return f"{delta} 天后"


def _dash_node(domain, accent, is_today, is_next, delta, idx):
    cls = "node on" if is_today else ("node next" if is_next else "node")
    when = "明天 · 下一班" if (is_next and not is_today) else _cycle_when(delta)
    return (
        f'<div class="{cls}" style="--accent:{accent}">'
        f'<div class="pip">{idx + 1}</div>'
        f'<div class="nm">{_esc(domain)}</div>'
        f'<div class="when">{_esc(when)}</div></div>'
    )


def _dash_card(domain, st, accent, skin, is_today, is_next, delta, today_str, idx):
    cls = "card today" if is_today else "card"
    if is_today:
        badge = '<div class="badge"><span class="b-dot"></span>今日刊印 · LIVE</div>'
    elif is_next:
        badge = '<div class="badge"><span class="b-dot"></span>下一班 · 明日轮值</div>'
    else:
        tail = f" · {delta} 天后" if (delta and delta > 1) else ""
        badge = f'<div class="badge dim"><span class="b-dot"></span>待轮值{tail}</div>'

    if not st:
        body = badge + '<div class="empty">尚未采集 · 待首次轮值</div>'
    else:
        def _nm(e):
            if not e:
                return '<span class="v">—</span>'
            return (f'<span class="v"><a href="{_esc(e["html_url"])}" target="_blank" '
                    f'rel="noopener">{_esc(e["full_name"])}</a></span>')
        c, b = _top(st, "combined"), _top(st, "burst")
        body = badge + (
            '<div class="c-rule"></div>'
            f'<div class="row"><span class="k">综合榜首</span>{_nm(c)}</div>'
            f'<div class="row"><span class="k">增速</span>'
            f'<span class="v vel">{_esc(_vel_text(c))}</span></div>'
            f'<div class="row"><span class="k">爆发榜首</span>{_nm(b)}</div>'
            f'<div class="c-foot"><span>上次 {_esc(_rel_days(st.get("date_str"), today_str))}</span>'
            f'<span>候选池 {_esc(st.get("pool_size", "—"))}</span></div>'
        )
    return (
        f'<div class="{cls}" style="--accent:{accent};animation-delay:{idx * 0.06:.2f}s">'
        f'<div class="c-top"><div class="c-name">{_esc(domain)}</div>'
        f'<div class="skin">{_esc(skin)}</div></div>{body}</div>'
    )


def render_dashboard_html(states, domains, today, nxt, today_str, themes=None):
    """雷达指挥中心:轮值环 + 各板块卡片(用其主题强调色着色)。themes={板块:主题键}。"""
    themes = themes or {}
    n = len(domains)
    try:
        t_idx = domains.index(today)
    except ValueError:
        t_idx = 0

    nodes, cards = [], []
    for i, d in enumerate(domains):
        delta = (i - t_idx) % n
        is_today = (d == today)
        is_next = (d == nxt) and not is_today
        tk = themes.get(d) or _CYCLE_THEMES[i % len(_CYCLE_THEMES)]
        accent = theme_accent(tk)
        skin = _SKIN_CN.get(tk, tk)
        nodes.append(_dash_node(d, accent, is_today, is_next, delta, i))
        cards.append(_dash_card(d, states.get(d), accent, skin, is_today, is_next, delta, today_str, i))

    return (
        '<!DOCTYPE html>\n<html lang="zh-CN">\n<head>\n<meta charset="UTF-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        f"<title>GitHub 雷达 · 指挥中心 · {_esc(today_str)}</title>\n"
        + _DASH_FONTS + "\n<style>" + _DASH_CSS + "</style>\n</head>\n<body>\n"
        '<div class="wrap">\n'
        '<header class="hd"><div class="ppi"></div><div class="sweep"></div>'
        '<div class="kick">GH·RADAR OPS · 总览仪表盘</div>'
        '<h1>GH<span class="mid">·</span>RADAR</h1>'
        '<div class="tag">指挥中心 · MISSION CONTROL</div>'
        '<div class="telem">'
        f'<span><i class="dot"></i>今日板块 <b>{_esc(today)}</b></span>'
        f'<span>▷ 接下来 <b>{_esc(nxt)}</b></span>'
        f'<span>5 天轮换 · {n} 个板块</span>'
        f'<span>快照 <b>{_esc(today_str)}</b></span>'
        '</div></header>\n'
        '<section class="cycle"><div class="lab">轮值环 · 5-DAY ROTATION CYCLE</div>'
        f'<div class="track">{"".join(nodes)}</div></section>\n'
        f'<section class="grid">{"".join(cards)}</section>\n'
        f'<div class="colophon">GH·RADAR — Search API + 本地快照 · 每日 08:30 自动轮值刊印 · 数据快照 {_esc(today_str)}</div>\n'
        '</div>\n</body>\n</html>\n'
    )
