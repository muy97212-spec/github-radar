# ghradar/state.py
"""每板块跑完缓存一份精简榜单 JSON,供总览(表格/仪表盘)读取全部板块。
存项目目录 boards_state/<slug>.json,不进 vault。"""
import json
import os
from datetime import datetime, timezone

from ghradar.domains import slugify

_KEEP = ("full_name", "html_url", "stars", "velocity_per_day", "delta", "is_estimated")


def _trim(e):
    return {k: e.get(k) for k in _KEEP}


def save_board_state(dir_path, domain, rankings, date_str, now=None):
    now = now or datetime.now(timezone.utc)
    os.makedirs(dir_path, exist_ok=True)
    state = {
        "domain": domain,
        "slug": slugify(domain),
        "updated_at": now.isoformat() if hasattr(now, "isoformat") else str(now),
        "date_str": date_str,
        "pool_size": rankings["pool_size"],
        "combined": [_trim(e) for e in rankings["combined"][:5]],
        "burst": [_trim(e) for e in rankings["burst"][:3]],
    }
    path = os.path.join(dir_path, slugify(domain) + ".json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    return state


def load_all_board_states(dir_path, domains):
    out = {}
    for d in domains:
        path = os.path.join(dir_path, slugify(d) + ".json")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                out[d] = json.load(f)
        else:
            out[d] = None
    return out
