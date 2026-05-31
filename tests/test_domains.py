# tests/test_domains.py
from datetime import datetime, timedelta, timezone
from ghradar.domains import slugify, select_domain, next_domain

def test_slugify_replaces_slash_and_spaces():
    assert slugify("AI/大模型应用与框架") == "AI·大模型应用与框架"
    assert slugify("开发者工具 / CLI") == "开发者工具·CLI"
    assert slugify("自动化与工作流") == "自动化与工作流"

def test_select_domain_cycles_and_covers_all():
    domains = ["A", "B", "C", "D", "E"]
    base = datetime(2026, 5, 31, tzinfo=timezone.utc)
    picks = [select_domain(domains, base + timedelta(days=i)) for i in range(6)]
    assert picks[5] == picks[0]            # 第 6 天回到第 1 个
    assert set(picks[:5]) == set(domains)  # 5 天覆盖全部

def test_select_domain_matches_ordinal_formula():
    domains = ["A", "B", "C", "D", "E"]
    d = datetime(2026, 5, 31, tzinfo=timezone.utc)
    assert select_domain(domains, d) == domains[d.toordinal() % 5]

def test_next_domain_is_following_day():
    domains = ["A", "B", "C", "D", "E"]
    base = datetime(2026, 5, 31, tzinfo=timezone.utc)
    assert next_domain(domains, base) == select_domain(domains, base + timedelta(days=1))
