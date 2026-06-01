# ghradar/overview.py
"""跨全部板块的总览:_总览.md(表格) + _仪表盘.html(指挥中心)。
只有当天板块真去搜,这里读 boards_state 缓存来展示全部 5 个板块的最新态。"""
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
# 居中对称版式:中央雷达报头 → 轮值环 → 今日 hero → 其余 4 板块对称网格。
# chrome 调色板可选(_DASH_PALETTES),板块卡片仍各用自己主题强调色。
# 不含 <script>,外部文本全转义,prefers-reduced-motion 回退。
# ============================================================

_DASH_FONTS = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link href="https://fonts.googleapis.com/css2?'
    'family=Oxanium:wght@400;500;600;700;800&family=IBM+Plex+Mono:wght@400;500;600'
    '&display=swap" rel="stylesheet">'
)

# chrome 调色板(中性,衬托 5 个板块色)。每套定义 bg/panel/line/ink/signal 等。
_DASH_PALETTES = {
    "slate": {
        "label": "石板青 · Slate Teal",
        "vars": ("--bg:#070d12;--panel:#0c151e;--panel-2:#0f1a25;--line:#1b2a37;"
                 "--ink:#dbe7f0;--ink-soft:#90a6b8;--muted:#566b7d;--signal:#3fd0c0;"),
    },
    "midnight": {
        "label": "午夜靛 · Midnight Gold",
        "vars": ("--bg:#0a0e1a;--panel:#11162a;--panel-2:#161d34;--line:#262f49;"
                 "--ink:#e7e4f1;--ink-soft:#a6a3bd;--muted:#6b6a86;--signal:#e3aa52;"),
    },
    "phosphor": {
        "label": "碳黑磷光 · CRT Phosphor",
        "vars": ("--bg:#050806;--panel:#0b110c;--panel-2:#0e150f;--line:#1c2a1d;"
                 "--ink:#cfe8d2;--ink-soft:#86a98a;--muted:#56705a;--signal:#4ef0a0;"),
    },
}

_DASH_FONT_VARS = ('--display:"Oxanium","PingFang SC","Microsoft YaHei",sans-serif;'
                   '--mono:"IBM Plex Mono",ui-monospace,SFMono-Regular,monospace;')

_DASH_BASE_CSS = r"""
*{margin:0;padding:0;box-sizing:border-box}
html{scroll-behavior:smooth}
body{background:var(--bg);color:var(--ink);font-family:var(--display);font-size:16px;line-height:1.6;
  -webkit-font-smoothing:antialiased;min-height:100vh;
  background-image:
    radial-gradient(circle at 50% -4%,color-mix(in srgb,var(--signal) 9%,transparent),transparent 44%),
    repeating-linear-gradient(0deg,rgba(140,170,190,.018) 0 1px,transparent 1px 42px),
    repeating-linear-gradient(90deg,rgba(140,170,190,.018) 0 1px,transparent 1px 42px)}
.mono{font-family:var(--mono)}
.wrap{max-width:1040px;margin:0 auto;padding:42px 28px 64px;text-align:center}

/* ---- 中央雷达报头 ---- */
.hd{position:relative;padding:6px 0 2px}
.scope{position:absolute;left:50%;top:-14px;transform:translateX(-50%);width:360px;height:360px;pointer-events:none;
  -webkit-mask:radial-gradient(circle at center,#000 26%,transparent 70%);
  mask:radial-gradient(circle at center,#000 26%,transparent 70%);opacity:.55}
.scope>div{position:absolute;inset:0;border-radius:50%}
.scope .rings{background:repeating-radial-gradient(circle at center,color-mix(in srgb,var(--signal) 24%,transparent) 0 1px,transparent 1px 36px)}
.scope .cross{background:
  linear-gradient(0deg,transparent calc(50% - .5px),color-mix(in srgb,var(--signal) 16%,transparent) 50%,transparent calc(50% + .5px)),
  linear-gradient(90deg,transparent calc(50% - .5px),color-mix(in srgb,var(--signal) 16%,transparent) 50%,transparent calc(50% + .5px))}
.scope .sweep{background:conic-gradient(from 0deg,transparent 0 314deg,color-mix(in srgb,var(--signal) 30%,transparent) 352deg,var(--signal) 360deg);
  animation:sweep 6s linear infinite}
@keyframes sweep{to{transform:rotate(360deg)}}
.rule{height:1px;border:none;position:relative;z-index:1;
  background:linear-gradient(90deg,transparent,var(--line) 18%,var(--line) 82%,transparent)}
.kick{font-family:var(--mono);font-size:11px;letter-spacing:.42em;text-transform:uppercase;color:var(--muted);padding:15px 0 0;position:relative;z-index:1}
h1.word{font-weight:800;font-size:clamp(38px,7vw,68px);letter-spacing:.05em;line-height:1;margin:9px 0 7px;position:relative;z-index:1}
h1.word .mid{color:var(--signal)}
.tag{font-weight:600;font-size:14.5px;letter-spacing:.18em;color:var(--ink-soft);margin-bottom:16px;position:relative;z-index:1}
.telem{display:flex;flex-wrap:wrap;justify-content:center;align-items:center;gap:9px 16px;font-family:var(--mono);font-size:12px;color:var(--ink-soft);padding:14px 0 2px;position:relative;z-index:1}
.telem span{display:inline-flex;align-items:center;gap:7px}
.telem b{color:var(--ink);font-weight:500}
.telem .sep{color:var(--line)}
.dot{width:8px;height:8px;border-radius:50%;background:var(--signal);box-shadow:0 0 9px var(--signal);animation:pulse 2.4s ease-in-out infinite}
@keyframes pulse{50%{opacity:.3}}

/* ---- 轮值环(居中) ---- */
.cycle{margin:28px auto 0;max-width:920px;border:1px solid var(--line);border-radius:16px;background:var(--panel);padding:22px 26px}
.cyc-lab{font-family:var(--mono);font-size:10.5px;letter-spacing:.3em;text-transform:uppercase;color:var(--muted);margin-bottom:18px}
.track{display:grid;grid-template-columns:repeat(5,1fr);position:relative}
.track::before{content:"";position:absolute;left:10%;right:10%;top:12px;height:2px;background:repeating-linear-gradient(90deg,var(--line) 0 8px,transparent 8px 15px)}
.node{display:flex;flex-direction:column;align-items:center;gap:10px;position:relative;z-index:1;padding:0 4px}
.node .pip{width:26px;height:26px;border-radius:50%;border:2px solid var(--line);background:var(--bg);display:grid;place-items:center;font-family:var(--mono);font-size:11px;font-weight:600;color:var(--muted)}
.node.on .pip{border-color:var(--accent);background:var(--accent);color:#04070b;box-shadow:0 0 0 5px color-mix(in srgb,var(--accent) 20%,transparent),0 0 20px color-mix(in srgb,var(--accent) 55%,transparent)}
.node.next .pip{border-color:var(--accent);color:var(--accent)}
.node .nm{font-size:12.5px;font-weight:600;color:var(--ink-soft);line-height:1.3;max-width:13ch}
.node.on .nm{color:var(--ink)}
.node .when{font-family:var(--mono);font-size:9.5px;letter-spacing:.14em;text-transform:uppercase;color:var(--muted)}
.node.on .when,.node.next .when{color:var(--accent)}

/* ---- 今日 hero(居中) ---- */
.hero{max-width:640px;margin:30px auto 0;border:1px solid color-mix(in srgb,var(--accent) 55%,var(--line));border-radius:18px;
  background:linear-gradient(180deg,color-mix(in srgb,var(--accent) 9%,var(--panel)),var(--panel));
  padding:26px 30px 24px;position:relative;overflow:hidden;
  box-shadow:0 0 0 1px color-mix(in srgb,var(--accent) 28%,transparent),0 22px 60px -30px color-mix(in srgb,var(--accent) 72%,transparent)}
.hero .h-badge{display:inline-flex;align-items:center;gap:8px;font-family:var(--mono);font-size:11px;letter-spacing:.2em;text-transform:uppercase;color:var(--accent)}
.hero .h-badge .b-dot{width:7px;height:7px;border-radius:50%;background:var(--accent);box-shadow:0 0 9px var(--accent)}
.hero .h-name{font-weight:800;font-size:clamp(22px,3.6vw,31px);color:var(--ink);margin:11px 0 3px;letter-spacing:.01em}
.hero .h-skin{font-family:var(--mono);font-size:10px;letter-spacing:.16em;text-transform:uppercase;color:var(--accent);margin-bottom:18px}
.hero .h-stats{display:grid;grid-template-columns:1fr 1fr;gap:16px;border-top:1px solid color-mix(in srgb,var(--accent) 22%,var(--line));padding-top:18px;text-align:left}
.hero .stat .k{font-family:var(--mono);font-size:10px;letter-spacing:.12em;text-transform:uppercase;color:var(--muted)}
.hero .stat .nm{font-size:16px;color:var(--ink);margin-top:6px;word-break:break-word}
.hero .stat .nm a{color:var(--ink);text-decoration:none}
.hero .stat .nm a:hover{color:var(--accent);text-decoration:underline;text-underline-offset:2px}
.hero .stat .vel{font-family:var(--mono);font-size:14px;color:var(--accent);margin-top:4px}
.hero .h-foot{font-family:var(--mono);font-size:10.5px;letter-spacing:.06em;color:var(--muted);margin-top:18px}
.board-link{color:inherit;text-decoration:none;display:inline-flex;align-items:center;gap:7px}
.board-link:hover{color:var(--accent)}
.board-link .arr{font-size:.74em;opacity:.5;transition:opacity .15s}
.board-link:hover .arr{opacity:1}
.h-cta{display:inline-block;margin-top:18px;font-family:var(--mono);font-size:11px;letter-spacing:.1em;
  color:var(--accent);text-decoration:none;border:1px solid color-mix(in srgb,var(--accent) 42%,var(--line));
  border-radius:999px;padding:7px 16px;transition:background .15s}
.h-cta:hover{background:color-mix(in srgb,var(--accent) 14%,transparent)}

/* ---- 其余 4 板块(对称网格) ---- */
.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:18px auto 0;text-align:left}
.card{position:relative;border:1px solid var(--line);border-top:3px solid var(--accent);border-radius:13px;background:var(--panel);
  padding:15px 15px 14px;overflow:hidden;opacity:0;transform:translateY(10px);animation:rise .5s ease forwards;transition:transform .2s ease,border-color .2s ease}
@keyframes rise{to{opacity:1;transform:none}}
.card::after{content:"";position:absolute;inset:0;pointer-events:none;background:radial-gradient(circle at 100% 0,color-mix(in srgb,var(--accent) 9%,transparent),transparent 60%)}
.card:hover{transform:translateY(-3px);border-color:color-mix(in srgb,var(--accent) 50%,var(--line))}
.card .c-name{font-weight:700;font-size:14.5px;color:var(--ink);line-height:1.25;position:relative;z-index:1}
.card .skin{font-family:var(--mono);font-size:9px;letter-spacing:.12em;text-transform:uppercase;color:var(--accent);margin-top:4px}
.card .badge{display:inline-flex;align-items:center;gap:6px;font-family:var(--mono);font-size:9.5px;letter-spacing:.12em;text-transform:uppercase;margin-top:11px;color:var(--accent)}
.card .badge.dim{color:var(--muted)}
.card .badge .b-dot{width:5px;height:5px;border-radius:50%;background:currentColor}
.card .mlab{font-family:var(--mono);font-size:9px;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);margin-top:12px}
.card .mnm{font-size:13px;color:var(--ink);margin-top:2px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.card .mnm a{color:var(--ink);text-decoration:none}.card .mnm a:hover{color:var(--accent)}
.card .c-foot{font-family:var(--mono);font-size:9.5px;color:var(--muted);margin-top:7px}
.card .empty{font-style:italic;color:var(--muted);font-size:12.5px;margin-top:9px}

.colophon{margin-top:34px;font-family:var(--mono);font-size:11px;letter-spacing:.12em;text-transform:uppercase;color:var(--muted)}

@media (prefers-reduced-motion: reduce){
  .scope .sweep{animation:none}.dot{animation:none}
  .card{opacity:1!important;transform:none!important;animation:none!important;transition:none}
}
@media(max-width:860px){.grid{grid-template-columns:repeat(2,1fr)}}
@media(max-width:620px){.cycle{overflow-x:auto}.track{min-width:480px}.grid{grid-template-columns:1fr}}
"""

_SKIN_CN = {"editorial": "Claude", "scope": "Gemini", "console": "OpenAI",
            "terminal": "Linear", "homelab": "Supabase"}
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


def _link(e):
    if not e:
        return "—"
    return (f'<a href="{_esc(e["html_url"])}" target="_blank" rel="noopener">'
            f'{_esc(e["full_name"])}</a>')


def _hero_card(domain, st, accent, skin, today_str):
    if not st:
        inner = '<div class="h-foot">尚未采集 · 待首次轮值</div>'
    else:
        c, b = _top(st, "combined"), _top(st, "burst")
        inner = (
            '<div class="h-stats">'
            f'<div class="stat"><div class="k">综合榜首</div><div class="nm">{_link(c)}</div>'
            f'<div class="vel">{_esc(_vel_text(c))}</div></div>'
            f'<div class="stat"><div class="k">爆发榜首</div><div class="nm">{_link(b)}</div></div>'
            '</div>'
            f'<div class="h-foot">上次 {_esc(_rel_days(st.get("date_str"), today_str))}'
            f' · 候选池 {_esc(st.get("pool_size", "—"))}</div>'
        )
    if st:
        name_html = (f'<a class="board-link" href="{_board_href(domain)}">'
                     f'{_esc(domain)} <span class="arr">↗</span></a>')
        cta = f'<a class="h-cta" href="{_board_href(domain)}">打开本板完整三榜 →</a>'
    else:
        name_html, cta = _esc(domain), ""
    return (
        f'<section class="hero" style="--accent:{accent}">'
        '<div class="h-badge"><span class="b-dot"></span>今日刊印 · LIVE</div>'
        f'<div class="h-name">{name_html}</div>'
        f'<div class="h-skin">视觉皮肤 · {_esc(skin)}</div>'
        f'{inner}{cta}</section>'
    )


def _mini_card(domain, st, accent, skin, is_next, delta, today_str, idx):
    if is_next:
        badge = '<div class="badge"><span class="b-dot"></span>下一班 · 明日</div>'
    else:
        tail = f" · {delta} 天后" if (delta and delta > 1) else ""
        badge = f'<div class="badge dim"><span class="b-dot"></span>待轮值{tail}</div>'
    if not st:
        body = badge + '<div class="empty">尚未采集</div>'
    else:
        c = _top(st, "combined")
        body = (
            badge
            + '<div class="mlab">综合榜首</div>'
            f'<div class="mnm">{_link(c)}</div>'
            f'<div class="c-foot">{_esc(_vel_text(c))} · 池 {_esc(st.get("pool_size", "—"))}</div>'
        )
    if st:
        name_html = (f'<a class="board-link" href="{_board_href(domain)}">'
                     f'{_esc(domain)} <span class="arr">↗</span></a>')
    else:
        name_html = _esc(domain)
    return (
        f'<div class="card" style="--accent:{accent};animation-delay:{idx * 0.05:.2f}s">'
        f'<div class="c-name">{name_html}</div>'
        f'<div class="skin">{_esc(skin)}</div>{body}</div>'
    )


def render_dashboard_html(states, domains, today, nxt, today_str, themes=None, palette="slate"):
    """雷达指挥中心(居中对称):中央报头 + 轮值环 + 今日 hero + 其余 4 板块网格。
    themes={板块:主题键} 决定卡片强调色;palette 选 chrome 调色板(见 _DASH_PALETTES)。"""
    themes = themes or {}
    pal = _DASH_PALETTES.get(palette) or _DASH_PALETTES["slate"]
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

    style = "<style>:root{" + pal["vars"] + _DASH_FONT_VARS + "}" + _DASH_BASE_CSS + "</style>"
    return (
        '<!DOCTYPE html>\n<html lang="zh-CN">\n<head>\n<meta charset="UTF-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        f"<title>GitHub 雷达 · 指挥中心 · {_esc(today_str)}</title>\n"
        + _DASH_FONTS + "\n" + style + "\n</head>\n<body>\n"
        '<div class="wrap">\n'
        '<header class="hd">'
        '<div class="scope"><div class="rings"></div><div class="cross"></div><div class="sweep"></div></div>'
        '<hr class="rule">'
        '<div class="kick">GH · RADAR OPS · 总览仪表盘</div>'
        '<h1 class="word">GH<span class="mid">·</span>RADAR</h1>'
        '<div class="tag">指挥中心 · MISSION CONTROL</div>'
        '<hr class="rule">'
        '<div class="telem">'
        f'<span><i class="dot"></i>今日板块 <b>{_esc(today)}</b></span><span class="sep">/</span>'
        f'<span>▷ 接下来 <b>{_esc(nxt)}</b></span><span class="sep">/</span>'
        f'<span>5 天轮换 · {n} 个板块</span><span class="sep">/</span>'
        f'<span>快照 <b>{_esc(today_str)}</b></span>'
        '</div></header>\n'
        '<section class="cycle"><div class="cyc-lab">轮值环 · 5-DAY ROTATION CYCLE</div>'
        f'<div class="track">{"".join(nodes)}</div></section>\n'
        f'{hero}\n'
        f'<section class="grid">{"".join(minis)}</section>\n'
        f'<div class="colophon">GH·RADAR — Search API + 本地快照 · 每日 08:30 自动轮值刊印 · 数据快照 {_esc(today_str)}</div>\n'
        '</div>\n</body>\n</html>\n'
    )
