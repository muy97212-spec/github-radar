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
