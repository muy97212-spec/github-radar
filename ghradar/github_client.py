import time
import requests

API = "https://api.github.com/search/repositories"

class GitHubClient:
    def __init__(self, token=None, session=None, sleep=time.sleep):
        self.token = token
        self.session = session or requests.Session()
        self.sleep = sleep

    def _headers(self):
        h = {"Accept": "application/vnd.github+json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def _get(self, params):
        for _ in range(5):
            resp = self.session.get(API, headers=self._headers(), params=params, timeout=30)
            if resp.status_code in (403, 429):
                retry_after = resp.headers.get("Retry-After")
                if retry_after:
                    self.sleep(int(retry_after))
                    continue
                if resp.headers.get("X-RateLimit-Remaining") == "0":
                    reset = int(resp.headers.get("X-RateLimit-Reset", "0"))
                    self.sleep(max(reset - int(time.time()), 1))
                    continue
            resp.raise_for_status()
            return resp.json()
        resp.raise_for_status()
        return resp.json()

    def search_repos(self, keyword, min_stars, cap):
        per_page = 100
        pages = max(1, -(-cap // per_page))  # ceil(cap/per_page)
        items = []
        for page in range(1, pages + 1):
            data = self._get({
                "q": f"{keyword} stars:>={min_stars}",
                "sort": "stars", "order": "desc",
                "per_page": per_page, "page": page,
            })
            page_items = data.get("items", [])
            if not page_items:
                break
            items.extend(page_items)
            if len(page_items) < per_page:
                break
        return [self._normalize(it) for it in items[:cap]]

    @staticmethod
    def _normalize(it):
        return {
            "full_name": it["full_name"],
            "html_url": it["html_url"],
            "stars": it.get("stargazers_count", 0),
            "language": it.get("language"),
            "description": it.get("description") or "",
            "topics": it.get("topics") or [],
            "created_at": it.get("created_at"),
        }
