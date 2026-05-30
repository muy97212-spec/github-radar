# GitHub 雷达(GitHub Radar)设计文档

- 日期:2026-05-30
- 状态:设计已确认,待写实现计划
- 项目位置:`/Users/jenson/github-radar/`(独立 git 仓库,与 social-auto-upload 分开)

## 1. 目标

一个本地运行的 Python CLI 工具,定期扫描用户**固定关注领域**里的 GitHub 项目,
找出两类值得关注的项目并生成 Markdown 报告推进 Obsidian:

1. **存量高** —— 在候选池里 star 总数排前 5% 的"领域标杆"。
2. **增速快** —— 短时间内 star 涨得快的"黑马",不看绝对星数。

关注领域(固定两类):
- 自动化与工作流
- 内容创作与分发

## 2. 现有方案调研与设计依据

动手前调研了 GitHub 上的同类工具,结论是**没有现成工具能直接顶替本需求**,
只有可复用的"零件"。调研同时反向验证了技术选型。

| 类别 | 代表 | 为什么不够用 |
|------|------|-------------|
| Trending 数据源 | huchenme/github-trending-api(822⭐) | 抓官方 trending 页,**只能按编程语言 + 日/周/月筛,无法按领域关键词过滤**;自带 `currentPeriodStars` 增幅可借鉴 |
| Trending 摘要工具 | VivienneSuu/github-trending-digest(9⭐) | 领域写死 9 个分类(无"内容分发/自动化发布");动能靠全局周榜(非领域内真增速);输出仅终端/Telegram/邮件,**无 Obsidian** |
| Star 增长可视化 | star-history.com | 给**已知**仓库画曲线做对比,属"验证"而非"发现",帮不到找黑马 |
| 监控 SaaS | PageCrawl.io | 托管付费,盯官方 trending 页(语言/话题),不进 Obsidian,数据不在本地 |

**两个关键结论(必须吸取):**

1. **官方 GitHub Trending 不在 API 里,只能按语言筛** —— 因此所有 trending 工具都做不到
   "按领域关键词找黑马"。本工具必须改用 **REST Search API + 自己存本地快照算增速**,
   绕开这条死路。这是本设计的核心依据。
2. 能复用的只有零件,拼装工作量小,**自己做不算重复造轮子**。不去 fork 任何现成项目。

(后续可选:跑顺后把它包成一个 Claude Code skill,一句话唤起。**本期不做**。)

## 3. 核心设计原则:两个信号是平行镜子,不是串联过滤器

最易踩的坑:先用"前 5%"硬过滤,再在结果里算增速 —— 这样**正在爆发但还小的黑马
永远进不来**。修正:存量与增速是对同一个宽候选池的**两个独立排名**,互不淘汰。

- "前 5%" **只决定标杆榜谁能上**,完全不影响爆发榜。
- 一个 80→400 星的黑马,只要进了候选池(star ≥ 低门槛),就会在爆发榜冒出来,
  哪怕它离前 5% 还差得远。

## 4. 架构与数据流

```
配置(domains + keywords)
        ↓
GitHub REST Search API ──→ 宽候选池
   (每个关键词:star ≥ pool_min_stars,取 top fetch_cap_per_keyword,合并去重)
   ← 关键:门槛放低,中小项目也进池,黑马才抓得到
        ↓
读上次快照(snapshot.json),对池里每个仓库算两个独立分数:
        ├─ 存量分:基于绝对 star 数
        └─ 增速分:本次 star − 上次 star;无历史 → 年轻高星代理(stars ÷ 仓库年龄天数)
        ↓
产出三个榜(互不淘汰):
   🥇 综合榜  = 归一化加权(stock×0.4 + velocity×0.6),取 Top K   ← 今日最值得看
   🏆 标杆榜  = 按存量排序,取候选池前 5%,再取 Top K              ← 大而稳
   🚀 爆发榜  = 按增速排序(涨幅 ≥ burst_min_delta 才入榜),Top K  ← 小而快的黑马
        ↓
写本次快照(覆盖,供下次对比)+ 渲染 Markdown(三个分区) → 写入 Obsidian vault
```

一个项目可能同时上多个榜(又大又在涨),报告中保留,允许重复。

## 5. 模块拆分(单一职责,可独立测试)

| 模块 | 职责 | 依赖 |
|------|------|------|
| `config.py` | 读取/校验 `config.yaml`;补默认值;从环境变量读 token | pyyaml |
| `github_client.py` | 封装 Search API:分页、限流退避、关键词查询 | requests |
| `snapshot.py` | 读/写本地 star 快照(JSON);记录每仓库 star 与时间戳 | 标准库 |
| `scoring.py` | **纯函数**:输入仓库列表+上次快照+配置,输出三个排好序的榜 | 无 IO |
| `report.py` | 把三个榜渲染成带 frontmatter 的 Markdown | 标准库 |
| `radar.py` | CLI 入口:串联以上;处理 vault 写入与降级 | 上述模块 |

`scoring.py` 不做任何 IO,是最该重点单测的地方。

## 6. 打分逻辑(综合榜如何加权)

- **存量分**:`log(stars)` 后在候选池内做 min-max 归一到 0–1(用 log 避免超大项目一家独大)。
- **增速分**:`delta = 本次 star − 上次 star`,在候选池内 min-max 归一到 0–1。
  - 无历史(首跑或该仓库首次出现):用代理 `stars ÷ max(仓库年龄天数, 1)`,同样归一。
- **综合分** = `weights.stock × 存量分 + weights.velocity × 增速分`,默认 `0.4 / 0.6`(偏向发现黑马)。

边界:候选池只有 1 个仓库、或所有值相等时,min-max 归一退化为 1.0(避免除零)。

## 7. 配置文件 `config.yaml`

```yaml
domains:
  自动化与工作流: [workflow automation, RPA, browser automation, playwright, n8n, scraping]
  内容创作与分发: [content automation, social media automation, video generation,
                  auto upload, multi-platform publish, AIGC content]
pool_min_stars: 50          # 候选池低门槛,保证黑马能进池
fetch_cap_per_keyword: 300  # 每个关键词最多取多少(3 页 × 100)
top_k: 15                   # 每个榜显示几条
burst_min_delta: 20         # 爆发榜:本次涨幅至少 +20 星才入榜
weights: { stock: 0.4, velocity: 0.6 }
vault_path: "/Users/jenson/Documents/Obsidian Vault"
report_folder: "GitHub雷达"
```

- GitHub token 从环境变量 `GITHUB_TOKEN` 读,**不写进文件**。
- 关键词在 GitHub 仓库搜索里匹配 名称/描述/README/topics,够用。

## 8. 输出(Obsidian)

每次运行生成一份带 frontmatter 的笔记,路径
`<vault_path>/<report_folder>/<YYYY-MM-DD>.md`,Obsidian 自动收录;
用户在该文件夹开窗口即可时间线式翻阅。

frontmatter 示例与每条目格式:

```markdown
---
tags: [github雷达]
date: 2026-05-30
generated_by: github-radar
---

# GitHub 雷达 · 2026-05-30

> 候选池 N 个仓库 · 领域:自动化与工作流 / 内容创作与分发

## 🥇 综合榜
1. **[owner/repo](https://github.com/owner/repo)** · ⭐ 12,340 · 📈 +210 (30/天) · `Python`
   一句话简介。`topic-a` `topic-b`
...

## 🏆 标杆榜(存量前 5%)
...

## 🚀 爆发榜(增速)
...
```

每条字段:仓库名(链接)· ⭐ 总星 · 📈 Δ涨幅(及每天均值)· 主语言 · 一句话简介 · topics。

## 9. 错误处理

- **无 token**:警告并降速运行(未认证限流更严),不直接崩。
- **API 限流(403)**:读 `X-RateLimit-Reset` 退避重试;个别关键词失败也照常用已得数据出报告。
- **首次运行无快照**:爆发榜改按代理分(stars ÷ 年龄天数)排序并直接取 Top K
  ——此时 `burst_min_delta`(基于真实涨幅)不适用、不生效;报告顶部标注"首跑 · 增速为估算"。
- **vault 路径不存在**:落到项目内 `./reports/` 并警告,不丢数据。

## 10. 测试策略(TDD)

- `scoring.py`(纯函数):造仓库列表 + 假快照做单测,覆盖 存量/增速/综合 三榜、
  无历史代理、min-max 边界(单仓库、全相等)。
- `github_client.py`:mock HTTP,验证分页、限流退避、查询拼装。
- `snapshot.py`:临时文件读写往返。
- `report.py`:对 Markdown 输出做快照测试(含 frontmatter)。
- `config.py`:默认值填充、缺字段校验。

## 11. 技术栈与项目布局

- Python 3.12(与 social-auto-upload 环境一致)。
- 依赖最小化:`requests` + `pyyaml`;测试用 `pytest`。
- 运行:手动 `python radar.py`;以后定时挂 cron 或已有的 scheduled task。

```
github-radar/
  radar.py
  radar/
    __init__.py
    config.py
    github_client.py
    snapshot.py
    scoring.py
    report.py
  config.yaml
  snapshot.json        # 运行时生成(gitignore)
  reports/             # vault 不可用时的降级输出(gitignore)
  tests/
  requirements.txt
  docs/superpowers/specs/2026-05-30-github-radar-design.md
```

## 12. 明确不做(Out of Scope)

- 不 fork / 不依赖任何现成 trending 项目。
- 不做邮件/Telegram/RSS 推送(只写 Obsidian Markdown)。
- 不爬官方 trending 页(走 Search API + 本地快照)。
- 不做 Web UI / 可视化曲线。
- 不在本期包成 Claude Code skill(跑顺后可另起一期)。
