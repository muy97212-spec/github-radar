# ghradar/snapshot.py
import json
import os
from datetime import datetime, timezone


def _iso(now):
    return now.isoformat() if hasattr(now, "isoformat") else str(now)


def _normalize(data):
    """统一为 {last_run, repos:{name:{stars,seen}}}；兼容旧的裸 star 格式。"""
    if not data:
        return {"last_run": None, "repos": {}}
    last_run = data.get("last_run") or data.get("generated_at")
    norm = {}
    for name, v in (data.get("repos") or {}).items():
        if isinstance(v, dict):
            norm[name] = {"stars": v.get("stars", 0), "seen": v.get("seen") or last_run}
        else:                                  # 旧格式:裸 star → 用全局时间当 seen
            norm[name] = {"stars": v, "seen": last_run}
    return {"last_run": last_run, "repos": norm}


def load_snapshot(path):
    if not os.path.exists(path):
        return {"last_run": None, "repos": {}}
    with open(path, "r", encoding="utf-8") as f:
        return _normalize(json.load(f))


def save_snapshot(path, repos, now=None, base=None):
    """合并写入:以 base(上次快照)为底,更新/插入今天这批仓库,其余原样保留。"""
    now = now or datetime.now(timezone.utc)
    now_iso = _iso(now)
    merged = dict((base or {}).get("repos") or {})
    for r in repos:
        merged[r["full_name"]] = {"stars": r["stars"], "seen": now_iso}
    data = {"last_run": now_iso, "repos": merged}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return data
