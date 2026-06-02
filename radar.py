import os
import sys
from datetime import datetime, timezone

from ghradar.config import load_config, all_keywords
from ghradar.github_client import GitHubClient
from ghradar.snapshot import load_snapshot, save_snapshot
from ghradar.scoring import build_rankings
from ghradar.report import render_markdown, render_html
from ghradar.domains import slugify, select_domain, next_domain
from ghradar.state import save_board_state, load_all_board_states
from ghradar.overview import render_overview_md, render_dashboard_html

HERE = os.path.dirname(os.path.abspath(__file__))


def collect_repos(client, keywords, min_stars, cap):
    seen = {}
    for kw in keywords:
        try:
            for r in client.search_repos(kw, min_stars, cap):
                cur = seen.get(r["full_name"])
                if cur is None or r["stars"] > cur["stars"]:
                    seen[r["full_name"]] = r
        except Exception as ex:
            print(f"⚠️ 关键词 '{kw}' 查询失败,跳过:{ex}", file=sys.stderr)
    return list(seen.values())


def base_folder(cfg):
    folder = os.path.join(cfg["vault_path"], cfg["report_folder"])
    if not os.path.isdir(cfg["vault_path"]):
        folder = os.path.join(HERE, "reports")
        print(f"⚠️ vault 路径不存在,改写本地 {folder}", file=sys.stderr)
    os.makedirs(folder, exist_ok=True)
    return folder


def _write(path, text):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def run_one_board(client, cfg, domain, prev, now, date_str, base, state_dir):
    """跑单个板块:采集 → 打分 → 写 <slug>/ 子文件夹(<日期>.md/.html + _latest.md/.html)
    → 存板块状态。返回 (repos, rankings)。_latest.md 是稳定名,供 Obsidian wikilink。"""
    keywords = cfg["domains"][domain]
    repos = collect_repos(client, keywords, cfg["pool_min_stars"], cfg["fetch_cap_per_keyword"])
    rankings = build_rankings(repos, prev, cfg, now=now)
    theme = (cfg.get("themes") or {}).get(domain, "editorial")
    folder = os.path.join(base, slugify(domain))
    os.makedirs(folder, exist_ok=True)
    md = render_markdown(rankings, date_str, [domain])
    _write(os.path.join(folder, f"{date_str}.md"), md)
    _write(os.path.join(folder, "_latest.md"), md)
    html = render_html(rankings, date_str, [domain], theme=theme)
    _write(os.path.join(folder, f"{date_str}.html"), html)
    _write(os.path.join(folder, "_latest.html"), html)
    save_board_state(state_dir, domain, rankings, date_str, now=now)
    return repos, rankings


def _write_overview(cfg, base, states, domains, today, nxt, date_str):
    _write(os.path.join(base, "_总览.md"),
           render_overview_md(states, domains, today, date_str))
    _write(os.path.join(base, "_仪表盘.html"),
           render_dashboard_html(states, domains, today, nxt, date_str, themes=cfg.get("themes")))


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    run_all = "--all" in argv
    cfg = load_config(os.path.join(HERE, "config.yaml"))
    if not cfg["github_token"]:
        print("⚠️ 未设置 GITHUB_TOKEN,未认证搜索限流约 10 次/分钟", file=sys.stderr)
    client = GitHubClient(token=cfg["github_token"])
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d")
    domains = list(cfg["domains"].keys())
    snap_path = os.path.join(HERE, "snapshot.json")
    prev = load_snapshot(snap_path)
    base = base_folder(cfg)
    state_dir = os.path.join(HERE, "boards_state")
    today = select_domain(domains, now)
    nxt = next_domain(domains, now)

    if run_all:
        merged = {}
        for d in domains:
            repos, rankings = run_one_board(client, cfg, d, prev, now, date_str, base, state_dir)
            for r in repos:
                merged[r["full_name"]] = r
            print(f"  · 「{d}」候选池 {rankings['pool_size']}")
        save_snapshot(snap_path, list(merged.values()), now=now, base=prev)
        states = load_all_board_states(state_dir, domains)
        _write_overview(cfg, base, states, domains, today, nxt, date_str)
        print(f"✅ 全部 {len(domains)} 板块已跑(新结构)→ {base} · 总览/仪表盘已更新")
    elif cfg.get("rotation", True):
        repos, rankings = run_one_board(client, cfg, today, prev, now, date_str, base, state_dir)
        save_snapshot(snap_path, repos, now=now, base=prev)
        states = load_all_board_states(state_dir, domains)
        _write_overview(cfg, base, states, domains, today, nxt, date_str)
        print(f"✅ 「{today}」板块报告 → {os.path.join(base, slugify(today))}"
              f" · 总览已更新(候选池 {rankings['pool_size']})")
    else:
        repos = collect_repos(client, all_keywords(cfg),
                              cfg["pool_min_stars"], cfg["fetch_cap_per_keyword"])
        rankings = build_rankings(repos, prev, cfg, now=now)
        _write(os.path.join(base, f"{date_str}.md"), render_markdown(rankings, date_str, domains))
        html = render_html(rankings, date_str, domains)
        _write(os.path.join(base, f"{date_str}.html"), html)
        _write(os.path.join(base, "_latest.html"), html)
        save_snapshot(snap_path, repos, now=now, base=prev)
        print(f"✅ 报告(全板块)→ {base}(候选池 {rankings['pool_size']})")


if __name__ == "__main__":
    main()
