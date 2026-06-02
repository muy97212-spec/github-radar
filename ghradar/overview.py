# ghradar/overview.py
"""跨全部板块的总览:_总览.md(表格) + _仪表盘.html(暖纸总览封面)。
只有当天板块真去搜,这里读 boards_state 缓存来展示全部板块(数量随 config)的最新态。"""
import html as _html
from datetime import datetime

from urllib.parse import quote as _urlquote

from ghradar.report import theme_accent
from ghradar.domains import slugify


def _board_href(domain):
    """仪表盘在 vault 根,板块报告在 <slug>/_latest.html,返回相对链接(已转义路径)。"""
    return _urlquote(slugify(domain)) + "/_latest.html"


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
        "> 🖥️ 网页总览：[打开 _仪表盘.html](_仪表盘.html)（浏览器里点卡片即进各板块完整三榜）", "",
        "| 板块 | 上次更新 | 候选池 | 综合榜首 | 榜首增速 | 爆发榜首 |",
        "|------|---------|-------|---------|---------|---------|",
    ]
    for d in domains:
        st = states.get(d)
        mark = " ⬅️ 今天" if d == today else ""
        if not st:
            lines.append(f"| {d}{mark} | 尚未采集 | — | — | — | — |")
            continue
        link = f"[[{slugify(d)}/_latest\\|{d}]]"   # → 该板块稳定笔记,Obsidian Graph 连通
        c = _top(st, "combined")
        b = _top(st, "burst")
        lines.append(
            f"| {link}{mark} | {_rel_days(st.get('date_str'), today_str)} "
            f"| {st.get('pool_size', '—')} | {c['full_name'] if c else '—'} "
            f"| {_vel_text(c)} | {b['full_name'] if b else '—'} |"
        )
    return "\n".join(lines) + "\n"


# ============================================================
# 总览仪表盘 _仪表盘.html —— 暖纸「总览封面」
# 与板块报告同一家族(暖象牙白 + Fraunces 衬线大报头),居中、易读、不走科技风。
# 报头 → 今日/下一班导语 → N 日轮值条 → 今日 hero → 其余板块对称网格 → 版尾。
# 每个板块用自己的主题强调色(theme_accent),不含 <script>,外部文本全转义,
# prefers-reduced-motion 有降级。
# ============================================================

_DASH_FONTS = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link href="https://fonts.googleapis.com/css2?'
    'family=Fraunces:opsz,wght@9..144,400;9..144,600;9..144,900'
    '&family=Spectral:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600'
    '&display=swap" rel="stylesheet">'
)

_DASH_ROOT_VARS = (
    "--paper:#f4eee2;--ink:#211c15;--ink-soft:#4a4136;--muted:#857862;"
    "--rule:#d8ccb6;--rule-dark:#b6a888;"
    '--display:"Fraunces","Songti SC","STSong",serif;'
    '--body:"Spectral","Songti SC","PingFang SC",serif;'
    '--mono:"IBM Plex Mono",ui-monospace,monospace;'
)

_DASH_BASE_CSS = r"""
*{margin:0;padding:0;box-sizing:border-box}
html{scroll-behavior:smooth}
body{background:var(--paper);color:var(--ink);font-family:var(--body);font-size:16px;line-height:1.6;
  -webkit-font-smoothing:antialiased;
  background-image:radial-gradient(rgba(120,90,40,.035) 1px,transparent 1px);background-size:3px 3px}
.mono{font-family:var(--mono);font-feature-settings:"tnum" 1}
.wrap{max-width:900px;margin:0 auto;padding:0 34px 70px;text-align:center}

/* ---- 报头(编辑部) ---- */
.masthead{padding-top:42px}
.rule-thick{height:4px;background:var(--ink);border:none}
.rule-thin{height:1px;background:var(--rule-dark);border:none}
.dateline{display:flex;justify-content:space-between;align-items:center;font-family:var(--mono);font-size:11px;
  letter-spacing:.16em;text-transform:uppercase;color:var(--ink-soft);padding:7px 2px;gap:10px}
.wordmark{padding:16px 0}
.wordmark h1{font-family:var(--display);font-weight:900;font-size:clamp(44px,8.4vw,86px);line-height:.92;letter-spacing:-.02em;font-optical-sizing:auto}
.wordmark .sub{font-family:var(--display);font-style:italic;font-weight:400;font-size:clamp(15px,2.4vw,20px);color:var(--ink-soft);margin-top:9px}
.intro{font-family:var(--body);font-size:17px;color:var(--ink-soft);padding:22px 0 2px}
.intro b{font-family:var(--display);font-weight:600;color:var(--ink)}

/* ---- 轮值进度条 ---- */
.cycle{margin:26px auto 0;max-width:960px;border-top:2px solid var(--ink);border-bottom:1px solid var(--rule);padding:16px 6px 18px}
.cyc-lab{font-family:var(--mono);font-size:10.5px;letter-spacing:.26em;text-transform:uppercase;color:var(--muted);margin-bottom:16px}
.track{display:grid;grid-template-columns:repeat(var(--cols,5),1fr);position:relative}
.track::before{content:"";position:absolute;left:10%;right:10%;top:13px;height:1px;background:var(--rule-dark)}
.node{display:flex;flex-direction:column;align-items:center;gap:7px;position:relative;z-index:1;padding:0 4px}
.node .pip{width:28px;height:28px;border-radius:50%;border:1.5px solid var(--rule-dark);background:var(--paper);
  display:grid;place-items:center;font-family:var(--mono);font-size:12px;font-weight:600;color:var(--muted)}
.node.on .pip{border-color:var(--accent);background:var(--accent);color:var(--paper)}
.node.next .pip{border-color:var(--accent);color:var(--accent)}
.node .nm{font-family:var(--display);font-size:13px;font-weight:600;color:var(--ink-soft);line-height:1.3;max-width:13ch}
.node.on .nm{color:var(--ink)}
.node .when{font-family:var(--mono);font-size:9.5px;letter-spacing:.12em;text-transform:uppercase;color:var(--muted)}
.node.on .when,.node.next .when{color:var(--accent)}

/* ---- 今日 hero ---- */
.hero{margin:26px auto 0;text-align:left;border:1px solid var(--rule-dark);border-top:4px solid var(--accent);
  background:linear-gradient(180deg,color-mix(in srgb,var(--accent) 7%,var(--paper)),var(--paper));padding:22px 26px 20px}
.h-badge{font-family:var(--mono);font-size:11px;letter-spacing:.2em;text-transform:uppercase;color:var(--accent);display:flex;align-items:center;gap:8px}
.h-badge .b-dot{width:7px;height:7px;border-radius:50%;background:var(--accent)}
.h-name{font-family:var(--display);font-weight:900;font-size:clamp(24px,4vw,36px);line-height:1.06;margin:10px 0 16px}
.h-name a{color:var(--ink);text-decoration:none}
.h-name a:hover{color:var(--accent)}
.h-stats{display:grid;grid-template-columns:1fr 1fr;gap:18px;border-top:1px solid color-mix(in srgb,var(--accent) 22%,var(--rule));padding-top:15px}
.h-stats.one{grid-template-columns:1fr}
.stat .k{font-family:var(--mono);font-size:10px;letter-spacing:.12em;text-transform:uppercase;color:var(--muted)}
.stat .nm{font-family:var(--display);font-weight:600;font-size:16.5px;color:var(--ink);margin-top:6px;word-break:break-word}
.stat .nm a{color:var(--ink);text-decoration:none}.stat .nm a:hover{color:var(--accent);text-decoration:underline;text-underline-offset:2px}
.stat .vel{font-family:var(--mono);font-size:14px;color:var(--accent);margin-top:4px}
.h-foot-row{display:flex;justify-content:space-between;align-items:baseline;gap:14px;flex-wrap:wrap;margin-top:15px}
.h-foot{font-family:var(--mono);font-size:11px;letter-spacing:.04em;color:var(--muted)}
.h-cta{font-family:var(--mono);font-size:11px;letter-spacing:.08em;color:var(--accent);white-space:nowrap;
  text-decoration:none;border:1px solid color-mix(in srgb,var(--accent) 45%,var(--rule));padding:6px 14px}
.h-cta:hover{background:color-mix(in srgb,var(--accent) 12%,transparent)}
.board-link{color:inherit;text-decoration:none}
.board-link .arr{font-size:.74em;opacity:.5}
.board-link:hover{color:var(--accent)}.board-link:hover .arr{opacity:1}

/* ---- 其余板块(对称网格) ---- */
.grid{display:grid;grid-template-columns:repeat(var(--gcols,3),1fr);gap:14px;margin:14px auto 0;text-align:left}
.card{min-width:0;border:1px solid var(--rule);border-top:3px solid var(--accent);background:var(--paper);padding:14px 15px 13px;
  opacity:0;transform:translateY(8px);animation:rise .5s ease forwards}
@keyframes rise{to{opacity:1;transform:none}}
.card:hover{border-color:var(--rule-dark)}
.card.next{border-top-width:4px}
.c-head{display:flex;justify-content:space-between;align-items:baseline;gap:8px;margin-bottom:2px}
.c-name{font-family:var(--display);font-weight:700;font-size:15px;color:var(--ink);line-height:1.25}
.c-name a{color:var(--ink);text-decoration:none}.c-name a:hover{color:var(--accent)}
.tag{font-family:var(--mono);font-size:8.5px;letter-spacing:.1em;text-transform:uppercase;color:var(--accent);flex:none;
  border:1px solid color-mix(in srgb,var(--accent) 40%,var(--rule));padding:2px 6px;white-space:nowrap}
.c-foot{font-family:var(--mono);font-size:9.5px;color:var(--muted);margin-top:10px}
.rec{display:flex;gap:9px;align-items:baseline;margin-top:8px}
.rec .rn{flex:0 1 auto;min-width:0;font-family:var(--display);font-weight:600;font-size:13px;color:var(--ink);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.rec .rn a{color:var(--ink);text-decoration:none}.rec .rn a:hover{color:var(--accent)}
.rec .rv{flex:none;font-family:var(--mono);font-size:10px;color:var(--accent);white-space:nowrap}
.empty{font-style:italic;color:var(--muted);font-size:12.5px;margin-top:9px}

.colophon{margin-top:42px;border-top:4px solid var(--ink);padding-top:18px;font-family:var(--mono);font-size:11px;
  letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}

@media (prefers-reduced-motion: reduce){.card{opacity:1!important;transform:none!important;animation:none!important}}
@media(max-width:760px){.grid{grid-template-columns:repeat(2,1fr)}}
@media(max-width:520px){.cycle{overflow-x:auto}.track{min-width:calc(var(--cols,5)*94px)}.grid{grid-template-columns:1fr}.h-stats{grid-template-columns:1fr}}
"""

# 板块 → 色板中文名(配色身份,见 report._THEMES)
_SKIN_CN = {"editorial": "砖红", "console": "靛蓝", "scope": "森绿",
            "terminal": "赭石", "homelab": "黄铜",
            "atelier": "梅紫", "atlas": "黛紫"}
_CYCLE_THEMES = ["editorial", "scope", "console", "terminal", "homelab",
                 "atelier", "atlas"]


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
    when = "下一班" if (is_next and not is_today) else _cycle_when(delta)
    return (
        f'<div class="{cls}" style="--accent:{accent}">'
        f'<div class="pip">{idx + 1}</div>'
        f'<div class="nm">{_esc(domain)}</div>'
        f'<div class="when">{_esc(when)}</div></div>'
    )


def _link(e):
    if not e:
        return "—"
    return (f'<a href="{_esc(e["html_url"])}" target="_blank" rel="noopener">'
            f'{_esc(e["full_name"])}</a>')


def _hero_card(domain, st, accent, skin, today_str):
    if not st:
        name_html = _esc(domain)
        inner = '<div class="h-foot-row"><span class="h-foot">尚未采集 · 待首次轮值</span></div>'
    else:
        c, b = _top(st, "combined"), _top(st, "burst")
        # 综合榜首 == 爆发榜首 时合成一条「双料榜首」,不再并列两遍
        if c and b and c.get("full_name") == b.get("full_name"):
            stats = ('<div class="h-stats one"><div class="stat">'
                     '<div class="k">综合 + 爆发 · 双料榜首</div>'
                     f'<div class="nm">{_link(c)}</div>'
                     f'<div class="vel">{_esc(_vel_text(c))}</div></div></div>')
        else:
            stats = (
                '<div class="h-stats">'
                f'<div class="stat"><div class="k">综合榜首</div><div class="nm">{_link(c)}</div>'
                f'<div class="vel">{_esc(_vel_text(c))}</div></div>'
                f'<div class="stat"><div class="k">爆发榜首</div><div class="nm">{_link(b)}</div>'
                f'<div class="vel">{_esc(_vel_text(b))}</div></div>'
                '</div>')
        inner = (stats + '<div class="h-foot-row">'
                 f'<span class="h-foot">候选池 {_esc(st.get("pool_size", "—"))}'
                 f' · 更新于 {_esc(_rel_days(st.get("date_str"), today_str))}</span>'
                 f'<a class="h-cta" href="{_board_href(domain)}">完整三榜 →</a></div>')
        name_html = (f'<a class="board-link" href="{_board_href(domain)}">'
                     f'{_esc(domain)} <span class="arr">↗</span></a>')
    return (
        f'<section class="hero" style="--accent:{accent}">'
        '<div class="h-badge"><span class="b-dot"></span>今日刊印 · LIVE</div>'
        f'<div class="h-name">{name_html}</div>{inner}</section>'
    )


def _mini_card(domain, st, accent, skin, is_next, delta, today_str, idx):
    # 轮值时机已在上方进度条标注,卡片不再重复「待轮值 X 天后」;只给「下一班」留个小标
    tag = '<span class="tag">明日轮值</span>' if is_next else ""
    if not st:
        body = '<div class="empty">尚未采集</div>'
    else:
        recs = "".join(
            f'<div class="rec"><span class="rn">{_link(e)}</span>'
            f'<span class="rv">{_esc(_vel_text(e))}</span></div>'
            for e in (st.get("combined") or [])[:2])
        body = ((recs or '<div class="empty">本期无</div>')
                + f'<div class="c-foot">候选池 {_esc(st.get("pool_size", "—"))} →</div>')
    if st:
        name_html = (f'<a class="board-link" href="{_board_href(domain)}">'
                     f'{_esc(domain)} <span class="arr">↗</span></a>')
    else:
        name_html = _esc(domain)
    cls = "card next" if is_next else "card"
    return (
        f'<div class="{cls}" style="--accent:{accent};animation-delay:{idx * 0.05:.2f}s">'
        f'<div class="c-head"><div class="c-name">{name_html}</div>{tag}</div>{body}</div>'
    )


def render_dashboard_html(states, domains, today, nxt, today_str, themes=None):
    """暖纸总览封面(居中):编辑部报头 + 五日轮值条 + 今日 hero + 其余 4 板块网格。
    themes={板块:主题键} 决定每块强调色(theme_accent);与板块报告同一暖纸家族。"""
    themes = themes or {}
    n = len(domains)
    t_idx = domains.index(today) if today in domains else 0

    nodes, minis, hero = [], [], ""
    for i, d in enumerate(domains):
        delta = (i - t_idx) % n
        is_today = (d == today)
        is_next = (d == nxt) and not is_today
        tk = themes.get(d) or _CYCLE_THEMES[i % len(_CYCLE_THEMES)]
        accent = theme_accent(tk)
        skin = _SKIN_CN.get(tk, tk)
        nodes.append(_dash_node(d, accent, is_today, is_next, delta, i))
        if is_today:
            hero = _hero_card(d, states.get(d), accent, skin, today_str)
        else:
            minis.append(_mini_card(d, states.get(d), accent, skin, is_next, delta, today_str, i))

    # 网格列数随卡片数取均衡(6→3×2, 4→2×2, 8→4×2),整组填满 wrap、居中且与 hero 等宽
    m = len(minis)
    gcols = m if m <= 3 else (3 if m % 3 == 0 else (2 if m % 2 == 0 else 3))

    style = "<style>:root{" + _DASH_ROOT_VARS + "}" + _DASH_BASE_CSS + "</style>"
    return (
        '<!DOCTYPE html>\n<html lang="zh-CN">\n<head>\n<meta charset="UTF-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        f"<title>GitHub 雷达 · 总览 · {_esc(today_str)}</title>\n"
        + _DASH_FONTS + "\n" + style + "\n</head>\n<body>\n"
        '<div class="wrap">\n'
        '<header class="masthead"><hr class="rule-thin">'
        '<div class="dateline"><span>总览 · Overview</span>'
        f'<span>{n} 天轮换 · {n} 板块</span><span>快照 {_esc(today_str)}</span></div>'
        '<hr class="rule-thick">'
        '<div class="wordmark"><h1>GitHub 雷达</h1>'
        f'<div class="sub">全 {n} 板块总览 · 每日轮值刊印</div></div>'
        '<hr class="rule-thick"></header>\n'
        f'<div class="intro">今日轮值 <b>{_esc(today)}</b> · 下一班 <b>{_esc(nxt)}</b></div>\n'
        f'<section class="cycle"><div class="cyc-lab">{n} 日轮值 · Rotation</div>'
        f'<div class="track" style="--cols:{n}">{"".join(nodes)}</div></section>\n'
        f'{hero}\n'
        f'<section class="grid" style="--gcols:{gcols}">{"".join(minis)}</section>\n'
        '<div class="colophon">GitHub 雷达 · Search API + 本地快照 · '
        f'每日 08:30 自动轮值刊印 · 快照 {_esc(today_str)}</div>\n'
        '</div>\n</body>\n</html>\n'
    )
