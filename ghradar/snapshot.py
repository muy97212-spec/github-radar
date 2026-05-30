import json
import os
from datetime import datetime, timezone

def load_snapshot(path):
    if not os.path.exists(path):
        return {"generated_at": None, "repos": {}}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_snapshot(path, repos, generated_at=None):
    generated_at = generated_at or datetime.now(timezone.utc).isoformat()
    data = {
        "generated_at": generated_at,
        "repos": {r["full_name"]: r["stars"] for r in repos},
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return data
