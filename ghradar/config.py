import os
import yaml

DEFAULTS = {
    "pool_min_stars": 50,
    "fetch_cap_per_keyword": 300,
    "top_k": 15,
    "burst_min_delta": 20,
    "weights": {"stock": 0.4, "velocity": 0.6},
    "report_folder": "GitHub雷达",
}

def load_config(path):
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    cfg = dict(DEFAULTS)
    cfg.update(raw)
    weights = dict(DEFAULTS["weights"])
    weights.update(raw.get("weights") or {})
    cfg["weights"] = weights
    if not cfg.get("domains"):
        raise ValueError("config 缺少 domains")
    if not cfg.get("vault_path"):
        raise ValueError("config 缺少 vault_path")
    cfg["github_token"] = os.environ.get("GITHUB_TOKEN")
    return cfg

def all_keywords(cfg):
    seen, out = set(), []
    for kw_list in cfg["domains"].values():
        for k in kw_list:
            if k not in seen:
                seen.add(k)
                out.append(k)
    return out
