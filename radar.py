import os
import sys
from datetime import datetime, timezone

from ghradar.config import load_config, all_keywords
from ghradar.github_client import GitHubClient
from ghradar.snapshot import load_snapshot, save_snapshot
from ghradar.scoring import build_rankings
from ghradar.report import render_markdown

HERE = os.path.dirname(os.path.abspath(__file__))

def collect_repos(client, keywords, min_stars, cap):
    seen = {}
    for kw in keywords:
        try:
            for r in client.search_repos(kw, min_stars, cap):
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
        print("⚠️ 未设置 GITHUB_TOKEN,降速运行(限流更严)", file=sys.stderr)
    client = GitHubClient(token=cfg["github_token"])
    repos = collect_repos(client, all_keywords(cfg),
                          cfg["pool_min_stars"], cfg["fetch_cap_per_keyword"])
    snap_path = os.path.join(HERE, "snapshot.json")
    prev = load_snapshot(snap_path)
    now = datetime.now(timezone.utc)
    rankings = build_rankings(repos, prev, cfg, now=now)
    date_str = now.strftime("%Y-%m-%d")
    md = render_markdown(rankings, date_str, list(cfg["domains"].keys()))
    out = output_path(cfg, date_str)
    with open(out, "w", encoding="utf-8") as f:
        f.write(md)
    save_snapshot(snap_path, repos, generated_at=now.isoformat())
    print(f"✅ 报告已写入 {out}(候选池 {rankings['pool_size']} 个)")

if __name__ == "__main__":
    main()
