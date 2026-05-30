# tests/test_github_client.py
from ghradar.github_client import GitHubClient

class FakeResp:
    def __init__(self, status=200, headers=None, payload=None):
        self.status_code = status
        self.headers = headers or {}
        self._payload = payload or {}
    def json(self):
        return self._payload
    def raise_for_status(self):
        if self.status_code >= 400:
            raise AssertionError(f"HTTP {self.status_code}")

class FakeSession:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []
    def get(self, url, headers=None, params=None, timeout=None):
        self.calls.append(params)
        return self._responses.pop(0)

def _item(name, stars):
    return {"full_name": name, "html_url": f"https://github.com/{name}",
            "stargazers_count": stars, "language": "Python",
            "description": "d", "topics": ["t"], "created_at": "2024-01-01T00:00:00Z"}

def test_normalize_maps_fields():
    sess = FakeSession([FakeResp(payload={"items": [_item("a/b", 42)]})])
    client = GitHubClient(token="x", session=sess)
    repos = client.search_repos("kw", min_stars=50, cap=100)
    assert repos[0] == {
        "full_name": "a/b", "html_url": "https://github.com/a/b", "stars": 42,
        "language": "Python", "description": "d", "topics": ["t"],
        "created_at": "2024-01-01T00:00:00Z"}

def test_pagination_stops_on_short_page():
    sess = FakeSession([FakeResp(payload={"items": [_item("a/b", 10)]})])  # <100 → 停
    client = GitHubClient(token="x", session=sess)
    repos = client.search_repos("kw", min_stars=50, cap=300)
    assert len(repos) == 1
    assert len(sess.calls) == 1  # 没翻第二页

def test_rate_limit_retry_then_success():
    slept = []
    limited = FakeResp(status=403, headers={"X-RateLimit-Remaining": "0",
                                            "X-RateLimit-Reset": "0"})
    ok = FakeResp(payload={"items": [_item("a/b", 10)]})
    sess = FakeSession([limited, ok])
    client = GitHubClient(token="x", session=sess, sleep=lambda s: slept.append(s))
    repos = client.search_repos("kw", min_stars=50, cap=100)
    assert len(repos) == 1
    assert slept  # 限流后睡过
