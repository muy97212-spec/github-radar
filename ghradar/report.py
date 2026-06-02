import html as _html
from datetime import datetime


def _fmt_entry(i, e):
    stars = f"{e['stars']:,}"
    if e.get("delta") is None:
        growth = f"📈 ~{e['velocity_per_day']:.0f}/天(估算)"
    else:
        growth = f"📈 +{e['delta']} ({e['velocity_per_day']:.0f}/天)"
    lang = f"`{e['language']}`" if e.get("language") else ""
    topics = " ".join(f"`{t}`" for t in (e.get("topics") or [])[:5])
    desc = (e.get("description") or "").strip()
    line1 = f"{i}. **[{e['full_name']}]({e['html_url']})** · ⭐ {stars} · {growth} · {lang}"
    line1 = line1.rstrip(" ·")
    parts = [line1]
    if desc:
        parts.append(f"   {desc}")
    if topics:
        parts.append(f"   {topics}")
    return "\n".join(parts)

def _section(title, entries):
    if not entries:
        return f"## {title}\n\n_(本期无)_\n"
    body = "\n".join(_fmt_entry(i, e) for i, e in enumerate(entries, 1))
    return f"## {title}\n\n{body}\n"

def render_markdown(rankings, date_str, domains):
    domain_str = " / ".join(domains)
    note = " · ⚠️ 首跑 · 增速为估算" if rankings["first_run"] else ""
    lines = [
        "---",
        "tags: [github雷达]",
        f"date: {date_str}",
        "generated_by: github-radar",
        "---",
        "",
        f"# GitHub 雷达 · {date_str}",
        "",
        f"> 候选池 {rankings['pool_size']} 个仓库 · 领域:{domain_str}{note}",
        "",
        _section("🥇 综合榜", rankings["combined"]),
        _section("🏆 标杆榜(存量前 5%)", rankings["landmark"]),
        _section("🚀 爆发榜(增速)", rankings["burst"]),
    ]
    return "\n".join(lines)


# ============================================================
# 网页版报告 —— 单一「编辑部大报」排版(masthead → 导语 → 异动条 →
# 三榜 → 版尾),由真实 rankings 服务端烘焙;不含 <script>,外部文本全转义。
# 每个板块用同一套排版,只换「字体 + 配色 + 底纹」(见 _THEMES)。
# ============================================================

# 排版基底:所有视觉值走 CSS 变量,主题只改 :root。各主题须定义:
# --paper --ink --ink-soft --muted --rule --rule-dark --red --red-deep
# --display --body --mono --texture --texture-size
_BASE_CSS = r"""
*{margin:0;padding:0;box-sizing:border-box}
html{scroll-behavior:smooth}
body{background:var(--paper);color:var(--ink);font-family:var(--body);font-size:16px;line-height:1.6;
  -webkit-font-smoothing:antialiased;background-image:var(--texture,none);background-size:var(--texture-size,auto)}
.mono{font-family:var(--mono);font-feature-settings:"tnum" 1}
.wrap{max-width:880px;margin:0 auto;padding:0 34px 70px}
.masthead{padding-top:42px}
.rule-thick{height:4px;background:var(--ink);border:none}
.rule-thin{height:1px;background:var(--rule-dark);border:none}
.dateline{display:flex;justify-content:space-between;align-items:center;font-family:var(--mono);font-size:11px;
  letter-spacing:.16em;text-transform:uppercase;color:var(--ink-soft);padding:7px 2px}
.wordmark{text-align:center;padding:14px 0 16px}
.wordmark h1{font-family:var(--display);font-weight:900;font-size:clamp(46px,9vw,96px);line-height:.92;letter-spacing:-.02em;font-optical-sizing:auto}
.wordmark .sub{font-family:var(--display);font-style:italic;font-weight:400;font-size:clamp(15px,2.4vw,20px);color:var(--ink-soft);margin-top:8px;letter-spacing:.02em}
.top{padding:36px 0 8px}
.lede{font-size:18.5px;line-height:1.72;color:var(--ink-soft);max-width:62ch;margin:0 auto;text-align:justify}
.lede p:first-letter{font-family:var(--display);font-weight:900;float:left;font-size:74px;line-height:.72;padding:7px 12px 0 0;color:var(--red)}
.lede b{color:var(--ink);font-weight:600}
.movers{margin-top:38px;border-top:3px solid var(--ink);border-bottom:3px solid var(--ink)}
.movers .cap{font-family:var(--mono);font-size:10.5px;letter-spacing:.24em;text-transform:uppercase;color:var(--muted);text-align:center;padding:10px 0;border-bottom:1px solid var(--rule)}
.movers .grid{display:grid;grid-template-columns:1fr 1fr}
.mover{padding:18px 26px;border-left:1px solid var(--rule)}
.mover:first-child{border-left:none}
.mover .lab{font-family:var(--display);font-style:italic;font-size:14px;color:var(--red-deep)}
.mover .nm{font-family:var(--display);font-weight:600;font-size:17px;line-height:1.25;word-break:break-word;margin:2px 0 4px}
.mover .nm a{color:inherit;text-decoration:none}
.mover .nm a:hover{color:var(--red-deep);text-decoration:underline;text-underline-offset:3px;text-decoration-thickness:1px}
.mover .num{font-family:var(--mono);font-size:30px;font-weight:500;color:var(--red);letter-spacing:-.02em;line-height:1}
.mover .num small{font-size:13px;color:var(--muted)}
.mover .meta{font-family:var(--mono);font-size:11px;color:var(--muted);margin-top:4px}
.section{margin-top:46px}
.sec-h{display:flex;align-items:baseline;gap:14px;border-bottom:2px solid var(--ink);padding-bottom:7px}
.sec-h h2{font-family:var(--display);font-weight:600;font-size:23px;letter-spacing:.01em}
.sec-h .en{font-family:var(--mono);font-size:11px;letter-spacing:.22em;text-transform:uppercase;color:var(--muted)}
.sec-h .by{margin-left:auto;font-family:var(--body);font-style:italic;font-size:13.5px;color:var(--muted)}
.empty{color:var(--muted);font-style:italic;padding:16px 2px}
.entry{display:grid;grid-template-columns:34px 1fr auto;gap:18px;align-items:baseline;padding:15px 2px;
  border-bottom:1px solid var(--rule);opacity:0;transform:translateY(8px);animation:rise .5s ease forwards}
@keyframes rise{to{opacity:1;transform:none}}
.entry:hover{background:linear-gradient(90deg,color-mix(in srgb,var(--red) 8%,transparent),transparent 70%)}
.rk{font-family:var(--display);font-style:italic;font-size:22px;color:var(--rule-dark);text-align:right;font-weight:600}
.entry:nth-child(-n+4) .rk{color:var(--red)}
.e-main{min-width:0}
.e-top{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap}
.e-name{font-family:var(--display);font-weight:600;font-size:18.5px;color:var(--ink);text-decoration:none;letter-spacing:.005em}
.e-name:hover{color:var(--red-deep);text-decoration:underline;text-underline-offset:3px;text-decoration-thickness:1px}
.e-lang{font-family:var(--mono);font-size:10.5px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);border:1px solid var(--rule-dark);border-radius:2px;padding:1px 6px}
.e-desc{font-size:14.5px;line-height:1.5;color:var(--ink-soft);margin-top:5px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.e-tags{margin-top:6px;font-family:var(--mono);font-size:11px;color:var(--muted);letter-spacing:.02em}
.e-tags span::after{content:" · "}
.e-tags span:last-child::after{content:""}
.e-stat{text-align:right;white-space:nowrap}
.e-stars{font-family:var(--mono);font-size:13px;color:var(--ink-soft)}
.e-stars b{color:var(--ink);font-weight:500}
.e-vel{font-family:var(--mono);font-size:16px;color:var(--red);font-weight:500;margin-top:2px;letter-spacing:-.01em}
.e-vel.flat{color:var(--muted)} .e-vel.est{color:var(--muted);font-style:italic}
.e-bar{height:2px;background:var(--rule);margin-top:7px;width:118px;margin-left:auto;overflow:hidden;position:relative}
.e-bar>i{position:absolute;inset:0 auto 0 0;background:var(--red);transform-origin:left;transform:scaleX(0);animation:fill 1s ease forwards}
.e-bar.est>i{background:repeating-linear-gradient(90deg,var(--rule-dark) 0 3px,transparent 3px 6px)}
@keyframes fill{to{transform:scaleX(var(--w,0))}}
.colophon{margin-top:54px;border-top:4px solid var(--ink);padding-top:20px}
.colophon .grid{display:grid;grid-template-columns:repeat(3,1fr);gap:26px}
.colophon h3{font-family:var(--display);font-weight:600;font-size:15px;margin-bottom:5px}
.colophon p{font-size:13.5px;line-height:1.55;color:var(--ink-soft)}
.colophon .red{color:var(--red-deep);font-weight:600}
.colophon .foot{font-family:var(--mono);font-size:11px;letter-spacing:.08em;color:var(--muted);margin-top:24px;text-align:center;text-transform:uppercase}
@media (prefers-reduced-motion: reduce){
  .entry{opacity:1!important;transform:none!important;animation:none!important}
  .e-bar>i{transform:scaleX(var(--w))!important;animation:none!important}
}
@media(max-width:720px){
  .movers .grid{grid-template-columns:1fr}
  .mover{border-left:none} .mover+.mover{border-top:1px solid var(--rule)}
  .colophon .grid{grid-template-columns:1fr}
  .entry{grid-template-columns:26px 1fr;gap:12px}
  .e-stat{grid-column:2;text-align:left;display:flex;gap:16px;align-items:baseline}
  .e-bar{display:none}
}
"""


def _fonts(families):
    return ('<link rel="preconnect" href="https://fonts.googleapis.com">'
            '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
            f'<link href="https://fonts.googleapis.com/css2?{families}&display=swap" rel="stylesheet">')


# 七套主题:统一「暖象牙白 + 衬线」高级风,共用同一排版与字体,
# 只换强调色 + 底纹微染。kicker = 报头左上角的小标。
_IVORY_FONTS = _fonts("family=Fraunces:opsz,wght@9..144,400;9..144,600;9..144,900"
                      "&family=Spectral:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500")
_IVORY_TYPE = ('--display:"Fraunces","Songti SC","STSong",serif;'
               '--body:"Spectral","Songti SC","PingFang SC",serif;'
               '--mono:"IBM Plex Mono",ui-monospace,monospace;')


def _ivory_theme(kicker, accent, deep, tex):
    """暖纸底高级风主题:纸/墨/线统一,仅 accent(--red) 与底纹随板块变。"""
    return {
        "kicker": kicker,
        "accent": accent,
        "fonts": _IVORY_FONTS,
        "root": (":root{"
                 "--paper:#f4eee2;--ink:#211c15;--ink-soft:#4a4136;--muted:#857862;"
                 "--rule:#d8ccb6;--rule-dark:#b6a888;"
                 f"--red:{accent};--red-deep:{deep};" + _IVORY_TYPE +
                 f"--texture:radial-gradient({tex} 1px,transparent 1px);--texture-size:3px 3px}}"),
    }


_THEMES = {
    # 板块 → (报头小标, 强调色, 深强调色, 底纹微染 rgba)
    "editorial": _ivory_theme("晨报 · Daily Dispatch",            # 砖红
                              "#c0341d", "#8f2414", "rgba(120,90,40,.035)"),
    "console":   _ivory_theme("智能前线 · FRONTIER BRIEF",        # 靛蓝
                              "#2c5882", "#1e3f60", "rgba(44,88,130,.05)"),
    "scope":     _ivory_theme("自动化简报 · FLUX DISPATCH",       # 森绿
                              "#2f6a47", "#204c33", "rgba(47,106,71,.05)"),
    "terminal":  _ivory_theme("开发者前线 · FORGE BRIEF",         # 赭石
                              "#a55228", "#7d3c1a", "rgba(165,82,40,.05)"),
    "homelab":   _ivory_theme("自托管简报 · STACK BRIEF",         # 黄铜
                              "#8a7327", "#655119", "rgba(138,115,39,.05)"),
    "atelier":   _ivory_theme("设计前线 · ATELIER BRIEF",         # 梅紫(前端/UI 设计)
                              "#9c3f6d", "#762d51", "rgba(156,63,109,.05)"),
    "atlas":     _ivory_theme("求知简报 · ATLAS BRIEF",           # 黛紫(学习/Awesome)
                              "#6a4a9c", "#4f3678", "rgba(106,74,156,.05)"),
}

def theme_accent(theme):
    """板块强调色,供总览仪表盘给卡片着色;未知主题回退 editorial。"""
    return (_THEMES.get(theme) or _THEMES["editorial"]).get("accent", "#c0341d")


_HTML_BOARDS_META = [
    ("综合榜", "Combined", "存量 × 增速 · 黑马优先", "combined"),
    ("标杆榜", "Landmark · Top 5%", "存量前 5% · 大而稳", "landmark"),
    ("爆发榜", "Burst · Velocity", "纯增速 · 小而快", "burst"),
]


def _esc(s):
    return _html.escape(str(s) if s is not None else "")


def _vel_html(e, small_color="var(--muted)"):
    """返回 (文本, css 类)。估算/持平/真实涨幅 三态。"""
    suffix = f'<small style="font-size:11px;color:{small_color}"> /日</small>'
    if e.get("is_estimated"):
        return f'约 +{e["velocity_per_day"]:.0f}{suffix}', "est"
    if e.get("delta") == 0:
        return "持平", "flat"
    return f'▲ +{e["delta"]}{suffix}', ""


def _html_entry(i, e, max_v):
    v = e["velocity_per_day"]
    w = max(v / max_v, 0.015) if max_v > 0 else 0.015
    lang = _esc(e.get("language") or "")
    lang_html = f'<span class="e-lang">{lang}</span>' if lang else ""
    tags = "".join(f"<span>{_esc(t)}</span>" for t in (e.get("topics") or [])[:3])
    vel_txt, vel_cls = _vel_html(e)
    bar_cls = "est" if e.get("is_estimated") else ""
    return (
        f'<div class="entry" style="animation-delay:{(i - 1) * 0.04:.2f}s">'
        f'<div class="rk">{i}</div>'
        f'<div class="e-main"><div class="e-top">'
        f'<a class="e-name" href="{_esc(e["html_url"])}" target="_blank" rel="noopener">{_esc(e["full_name"])}</a>'
        f'{lang_html}</div>'
        f'<div class="e-desc">{_esc((e.get("description") or "").strip())}</div>'
        f'<div class="e-tags">{tags}</div></div>'
        f'<div class="e-stat"><div class="e-stars">★ <b>{e["stars"]:,}</b></div>'
        f'<div class="e-vel {vel_cls}">{vel_txt}</div>'
        f'<div class="e-bar {bar_cls}"><i style="--w:{w:.3f}"></i></div></div>'
        f"</div>"
    )


def _html_section(name, en, by, entries):
    if not entries:
        rows = '<div class="empty">(本期无)</div>'
    else:
        max_v = max((e["velocity_per_day"] for e in entries), default=1.0) or 1.0
        rows = "".join(_html_entry(i, e, max_v) for i, e in enumerate(entries, 1))
    return (
        f'<section class="section"><div class="sec-h">'
        f"<h2>{_esc(name)}</h2><span class=\"en\">{_esc(en)}</span>"
        f'<span class="by">{_esc(by)} · {len(entries)} 项</span></div>{rows}</section>'
    )


def _html_movers(rankings):
    pool = rankings["burst"] or rankings["combined"] or rankings["landmark"] or []
    if not pool:
        return '<div class="movers"><div class="cap">今日异动 · Top Movers</div>' \
               '<div class="grid"><div class="mover"><div class="meta">(暂无显著异动)</div></div></div></div>'
    headline = max(pool, key=lambda e: e["velocity_per_day"])
    picks = [("头条 · 最快信号", headline)]
    smalls = sorted(pool, key=lambda e: e["stars"])[: max(1, len(pool) // 2)]
    dh = max(smalls, key=lambda e: e["velocity_per_day"])
    if dh["full_name"] != headline["full_name"]:
        picks.append(("黑马 · 小基数高增速", dh))
    items = []
    for label, e in picks:
        if e.get("is_estimated"):
            num = f'约 +{e["velocity_per_day"]:.0f}<small> 星/日</small>'
        elif e.get("delta") == 0:
            num = "持平"
        else:
            num = f'+{e["delta"]}<small> 星/日</small>'
        meta = f'★ {e["stars"]:,}' + (f' · {_esc(e["language"])}' if e.get("language") else "")
        items.append(
            f'<div class="mover"><div class="lab">{_esc(label)}</div>'
            f'<div class="nm"><a href="{_esc(e["html_url"])}" target="_blank" rel="noopener">'
            f'{_esc(e["full_name"])}</a></div>'
            f'<div class="num">{num}</div><div class="meta">{meta}</div></div>'
        )
    return ('<div class="movers"><div class="cap">今日异动 · Top Movers</div>'
            '<div class="grid">' + "".join(items) + "</div></div>")


def _date_cn(date_str):
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return f"{dt.year} 年 {dt.month} 月 {dt.day} 日 · 星期{'一二三四五六日'[dt.weekday()]}"
    except ValueError:
        return _esc(date_str)


def render_html(rankings, date_str, domains, theme="editorial"):
    """统一排版,按 theme 换字体/配色/底纹。未知主题回退 editorial。"""
    t = _THEMES.get(theme) or _THEMES["editorial"]
    theme_key = theme if theme in _THEMES else "editorial"
    domain_str = _esc(" / ".join(domains))
    pool = rankings["pool_size"]
    first_run = rankings["first_run"]
    note = " · 首跑 · 增速为估算" if first_run else ""

    lede = (f"今晨的扫描覆盖 <b>{pool:,}</b> 个仓库,从中分离出两类信号:"
            "<b>又大又稳的标杆</b>,与<b>小而快的黑马</b>。存量与增速各自独立成榜,互不淘汰。")
    if first_run:
        lede += "首跑暂无历史快照,增速以“年龄均速”估算并标注「首跑·估算」,自明日起即为真实涨幅。"
    else:
        movers = rankings["burst"] or rankings["combined"]
        if movers:
            top = max(movers, key=lambda e: e["velocity_per_day"])
            if not top.get("is_estimated") and top.get("delta"):
                lede += f"当日最强信号来自 <b>{_esc(top['full_name'])}</b>,单日 <b>+{top['delta']}</b> 星。"

    boards = "".join(
        _html_section(name, en, by, rankings[key]) for name, en, by, key in _HTML_BOARDS_META
    )

    return (
        '<!DOCTYPE html>\n<html lang="zh-CN">\n<head>\n<meta charset="UTF-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        f"<title>GitHub 雷达 · {domain_str} · {_esc(date_str)}</title>\n"
        + t["fonts"] + "\n<style>" + t["root"] + _BASE_CSS + "</style>\n</head>\n<body>\n"
        f"<!-- theme: {theme_key} -->\n"
        '<div class="wrap">\n'
        '<div class="masthead"><hr class="rule-thin">'
        f'<div class="dateline"><span>{_esc(t["kicker"])}</span>'
        f"<span>候选池 {pool:,}</span><span>{_date_cn(date_str)}</span></div>"
        '<hr class="rule-thick">'
        f'<div class="wordmark"><h1>GitHub 雷达</h1><div class="sub">高星 × 高增速 · {domain_str}{note}</div></div>'
        '<hr class="rule-thick"></div>\n'
        f'<div class="top"><div class="lede"><p>{lede}</p></div>{_html_movers(rankings)}</div>\n'
        f'<main>{boards}</main>\n'
        '<div class="colophon"><div class="grid">'
        '<div><h3>综合榜</h3><p>归一化加权 <span class="red">0.4 存量 + 0.6 增速</span>,偏向发现黑马。</p></div>'
        '<div><h3>标杆榜</h3><p>候选池里星数排<span class="red">前 5%</span>者入选 —— 大而稳。</p></div>'
        '<div><h3>爆发榜</h3><p>只论<span class="red">增速</span>、不看绝对星数 —— 小而快的黑马在此发光。</p></div>'
        '</div>'
        f'<div class="foot">GH·RADAR — Search API + 本地快照 · 每日 08:30 自动刊印 · 数据快照 {_esc(date_str)}</div>'
        '</div>\n</div>\n</body>\n</html>\n'
    )
