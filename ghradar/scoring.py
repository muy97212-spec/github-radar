import math
from datetime import datetime, timezone

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
    prev_time = _parse_iso((prev_snapshot or {}).get("generated_at"))
    elapsed_days = max((now - prev_time).total_seconds() / 86400.0, 1.0) if prev_time else 1.0

    enriched = []
    for r in repos:
        name, stars = r["full_name"], r["stars"]
        has_prev = (not first_run) and (name in prev_repos)
        if has_prev:
            delta = max(stars - prev_repos[name], 0)
            velocity_value = delta / elapsed_days
            is_estimated = False
        else:
            delta = None
            velocity_value = stars / _age_days(r.get("created_at"), now)
            is_estimated = True
        e = dict(r)
        e.update(delta=delta, velocity_value=velocity_value,
                 velocity_per_day=velocity_value, is_estimated=is_estimated)
        enriched.append(e)

    stock_scores = _minmax([math.log(e["stars"] + 1) for e in enriched])
    velocity_scores = _minmax([e["velocity_value"] for e in enriched])
    w = config["weights"]
    for e, ss, vs in zip(enriched, stock_scores, velocity_scores):
        e["stock_score"] = ss
        e["velocity_score"] = vs
        e["combined_score"] = w["stock"] * ss + w["velocity"] * vs

    top_k = config["top_k"]
    combined = sorted(enriched, key=lambda e: e["combined_score"], reverse=True)[:top_k]

    by_stars = sorted(enriched, key=lambda e: e["stars"], reverse=True)
    cutoff = max(1, math.ceil(len(by_stars) * 0.05))
    landmark = by_stars[:cutoff][:top_k]

    burst_min = config["burst_min_delta"]
    burst_candidates = [
        e for e in enriched
        if e["is_estimated"] or (e["delta"] is not None and e["delta"] >= burst_min)
    ]
    burst = sorted(burst_candidates, key=lambda e: e["velocity_value"], reverse=True)[:top_k]

    return {"first_run": first_run, "pool_size": len(enriched),
            "combined": combined, "landmark": landmark, "burst": burst}
