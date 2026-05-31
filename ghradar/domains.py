# ghradar/domains.py
"""板块名 → 文件夹安全 slug；按日期无状态地选当天/明日板块。"""


def slugify(name):
    """文件夹名不允许含 '/'，统一换成 '·' 并去空格。"""
    return name.replace("/", "·").replace(" ", "")


def select_domain(domains, when):
    """当天板块 = domains[日期序数 % 板块数]。无状态、可预测、漏跑不漂移。"""
    return domains[when.toordinal() % len(domains)]


def next_domain(domains, when):
    """明日板块，供仪表盘提示『接下来轮到谁』。"""
    return domains[(when.toordinal() + 1) % len(domains)]
