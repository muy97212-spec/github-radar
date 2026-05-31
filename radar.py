import os
import sys
from datetime import datetime, timezone

from ghradar.config import load_config, all_keywords
from ghradar.github_client import GitHubClient
from ghradar.snapshot import load_snapshot, save_snapshot
from ghradar.scoring import build_rankings
from ghradar.report import render_markdown, render_html

HERE = os.path.dirname(os.path.abspath(__file__))

def collect_repos(client, keywords, min_stars, cap):
    seen = {}
    for kw in keywords:
        try:
            for r in client.search_repos(kw, min_stars, cap):
                # 关键词重叠时同一仓库会出现多次;保留 star 更高的那份,
                # 使去重结果不依赖关键词的遍历顺序。
                cur = seen.get(r["full_name"])
                if cur is None or r["stars"] > cur["stars"]:
                    seen[r["full_name"]] = r
        except Exception as ex:
            print(f"⚠️ 关键词 '{kw}' 查询失败,跳过:{ex}", file=sys.stderr)
    return list(seen.values())

def output_path(cfg, date_str):
    folder = os.path.join(cfg["vault_path"], cfg["report_folder"])
    if not os.path.isdir(cfg["vault_path"]):
        folder = os.path.join(HERE, "reports")
        print(f"⚠️ vault 路径不存在,改写本地 {folder}", file=sys.stderr)
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, f"{date_str}.md")

def main():
    cfg = load_config(os.path.join(HERE, "config.yaml"))
    if not cfg["github_token"]:
        print("⚠️ 未设置 GITHUB_TOKEN,未认证搜索限流约 10 次/分钟(设置后约 30 次/分钟)", file=sys.stderr)
    client = GitHubClient(token=cfg["github_token"])
    repos = collect_repos(client, all_keywords(cfg),
                          cfg["pool_min_stars"], cfg["fetch_cap_per_keyword"])
    # 快照固定存在 radar.py 同目录(项目内),与报告输出目录(vault)无关。
    snap_path = os.path.join(HERE, "snapshot.json")
    prev = load_snapshot(snap_path)
    now = datetime.now(timezone.utc)
    rankings = build_rankings(repos, prev, cfg, now=now)
    date_str = now.strftime("%Y-%m-%d")
    domains = list(cfg["domains"].keys())
    md = render_markdown(rankings, date_str, domains)
    html = render_html(rankings, date_str, domains)
    out = output_path(cfg, date_str)
    folder = os.path.dirname(out)
    with open(out, "w", encoding="utf-8") as f:
        f.write(md)
    # 网页版:带日期一份(归档)+ _latest.html 固定一份(供浏览器书签,永远是今天)
    html_path = os.path.join(folder, f"{date_str}.html")
    latest_path = os.path.join(folder, "_latest.html")
    for p in (html_path, latest_path):
        with open(p, "w", encoding="utf-8") as f:
            f.write(html)
    save_snapshot(snap_path, repos, generated_at=now.isoformat())
    print(f"✅ 报告已写入 {out} + 网页版 {date_str}.html / _latest.html(候选池 {rankings['pool_size']} 个)")

if __name__ == "__main__":
    main()
