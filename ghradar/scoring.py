import math
from datetime import datetime, timezone

# 标杆榜取候选池存量(star)最高的这个比例。spec 定为前 5%。
LANDMARK_FRACTION = 0.05

def _parse_iso(s):
    if not s:
        return None
    return datetime.fromisoformat(s.replace("Z", "+00:00"))

def _minmax(values):
    if not values:
        return []
    lo, hi = min(values), max(values)
    if hi == lo:
        return [1.0 for _ in values]
    return [(v - lo) / (hi - lo) for v in values]

def _age_days(created_at, now):
    created = _parse_iso(created_at)
    if not created:
        return 1.0
    return max((now - created).total_seconds() / 86400.0, 1.0)

def build_rankings(repos, prev_snapshot, config, now=None):
    now = now or datetime.now(timezone.utc)
    prev_repos = (prev_snapshot or {}).get("repos") or {}
    first_run = len(prev_repos) == 0

    enriched = []
    for r in repos:
        name, stars = r["full_name"], r["stars"]
        prev = None if first_run else prev_repos.get(name)
        if prev is not None:
            prev_stars = prev["stars"] if isinstance(prev, dict) else prev
            seen = _parse_iso(prev.get("seen")) if isinstance(prev, dict) else None
            # 每仓库各自的间隔:轮换下某板块可能 5 天才见一次。
            elapsed = max((now - seen).total_seconds() / 86400.0, 1.0) if seen else 1.0
            delta = max(stars - prev_stars, 0)
            velocity_per_day = delta / elapsed
            is_estimated = False
        else:
            delta = None
            velocity_per_day = stars / _age_days(r.get("created_at"), now)
            is_estimated = True
        e = dict(r)
        e.update(delta=delta, velocity_per_day=velocity_per_day, is_estimated=is_estimated)
        enriched.append(e)

    stock_scores = _minmax([math.log(e["stars"] + 1) for e in enriched])
    velocity_scores = _minmax([e["velocity_per_day"] for e in enriched])
    w = config["weights"]
    for e, ss, vs in zip(enriched, stock_scores, velocity_scores):
        e["stock_score"] = ss
        e["velocity_score"] = vs
        e["combined_score"] = w["stock"] * ss + w["velocity"] * vs

    top_k = config["top_k"]
    combined = sorted(enriched, key=lambda e: e["combined_score"], reverse=True)[:top_k]

    by_stars = sorted(enriched, key=lambda e: e["stars"], reverse=True)
    cutoff = max(1, math.ceil(len(by_stars) * LANDMARK_FRACTION))
    landmark = by_stars[:cutoff][:top_k]

    # 爆发榜门槛按"日增速"而非原始增量:轮换下间隔不固定,日增速才同量纲。
    burst_min_v = config.get("burst_min_velocity", config.get("burst_min_delta", 20))
    burst_candidates = [
        e for e in enriched
        if e["is_estimated"] or e["velocity_per_day"] >= burst_min_v
    ]
    burst = sorted(burst_candidates, key=lambda e: e["velocity_per_day"], reverse=True)[:top_k]

    return {"first_run": first_run, "pool_size": len(enriched),
            "combined": combined, "landmark": landmark, "burst": burst}
