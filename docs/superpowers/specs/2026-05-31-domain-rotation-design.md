# 设计：板块轮换（5 天一循环）

- 日期：2026-05-31
- 项目：GitHub 雷达（github-radar）
- 状态：已与用户确认，待写实现计划

## 背景与动机

当前雷达每天用**同一批关键词**扫两个领域（自动化与工作流 / 内容创作与分发），
每天产出一份覆盖相同范围的报告。用户希望：

- 覆盖**更多领域类别**（且偏向星标较高的赛道）；
- 不要每天都扫全部、内容雷同——改为**每天聚焦一个板块**，跨天覆盖更多面；
- 以**周期**的方式判定当天跑哪个板块。

用户拍板的形态：**5 个板块，一天跑一个，第 6 天回到第 1 个**——一个简单的 5 天循环，
不要复杂调度。加板块的方式要简单：复制现有板块、改关键词即可。

## 关键约束：轮换不能破坏「真实增速」

雷达最有价值的功能是「真实日增速」（报告里的 `+293/天`）。它依赖
`snapshot.json` 保存上一轮每个仓库的 star，今天减上次得到增量。

直接做轮换会破坏它，原因有二：

1. **快照被整体覆盖**：现状每跑一次就用当天这批仓库替换整个快照。轮换后，某板块过
   5 天再轮回来时，它的仓库早被这几天别的板块挤掉，永远算不出真实增速。
2. **时间戳是全局一个**：现状只记一个「上次生成时间」=昨天，但该板块真正上次出现是
   ~5 天前，用昨天当基准会把增速放大约 5 倍。

**解法**：把快照从「只记昨天」改成**每个仓库记 `{star 数, 上次见到的日期}`**，
且每天只更新今天这个板块的仓库、其余原样保留。增速改用**每仓库各自的间隔**：
`(今天 star − 上次 star) ÷ 实际间隔天数`。某板块 5 天才轮到一次 →
间隔≈5 天 → 得到「5 天平均日增速」，仍是真实数据，不再天天「估算」。
此设计对任意节奏（每天/每周/不规则）都成立。

## 五个板块（轮换池）

`config.yaml` 的 `domains` 扩为 5 项，**顺序即循环序号 0..4**：

| 序号 | 板块 | 关键词方向 |
|------|------|-----------|
| 0 | 自动化与工作流 | 现有 |
| 1 | 内容创作与分发 | 现有（含设计/多媒体生成，本就重叠） |
| 2 | AI/大模型应用与框架 | LLM 应用、Agent 框架、RAG、推理引擎 |
| 3 | 开发者工具 / CLI | 终端工具、效率 CLI、编辑器插件、本地开发利器 |
| 4 | 自托管 / 效率应用 | self-hosted、知识管理、笔记、看板 |

> 加板块 = 在 `domains` 下复制一段、改领域名与关键词。`config.example.yaml`
> 放好这 5 个模板，README 写明「复制粘贴改关键词即可」。

## 当天跑哪个板块：日期取模（无状态）

```
板块序号 = 当天日期序数(date.toordinal()) % len(domains)
今日板块 = domains[板块序号]
```

- **无状态、可预测**：看日期就知道今天是哪个板块。
- **漏跑不错乱**：某天电脑关机没跑，第二天按它自己的日期照常对号入座
  （不会像「计数器 +1」那样补跑昨天的板块、导致顺序漂移）。
- 用 `radar.py` 现有的 `now = datetime.now(timezone.utc)` 取日期，与
  `date_str` 同源，保持一致。

> 备选方案「绑定星期几（周一=板块1…）」与「计数器累加」均已考虑，用户表示都可接受；
> 选「日期取模」因其无状态、漏跑不漂移、最直观。

## 组件改动

### 1. `config.yaml` / `config.example.yaml`
- `domains` 扩为 5 项（见上表）。
- 新增开关 `rotation: true`（默认开）。`true` = 每天按日期取模只跑一个板块；
  `false` = 旧行为（每天跑全部板块），用于回退/测试。
- `burst_min_delta` → 重命名 `burst_min_velocity`（默认 20，语义=日增速门槛，
  见 scoring 改动）。

### 2. `ghradar/snapshot.py`
- 新快照格式：
  ```json
  {
    "last_run": "2026-05-31T15:30:00+00:00",
    "repos": {
      "owner/name": {"stars": 1234, "seen": "2026-05-31T15:30:00+00:00"}
    }
  }
  ```
- `load_snapshot(path)`：**向后兼容**。读到旧格式
  `{generated_at, repos:{name: stars}}` 时，自动把每个仓库迁移成
  `{stars, seen: generated_at}`，统一返回新格式。
- `save_snapshot(path, repos, now, base)`：**合并而非覆盖**。以 `base`（上次快照）
  为底，更新/插入今天这批仓库为 `{stars, seen: now}`，其余仓库原样保留；
  写回 `last_run = now`。

### 3. `ghradar/scoring.py` — `build_rankings`
- `prev_repos[name]` 现在是 `{stars, seen}`（而非裸 star）。
- 每个仓库各自算间隔：命中上次记录则
  `delta = max(stars - prev.stars, 0)`，
  `elapsed = max((now - parse(prev.seen)).days_float, 1.0)`，
  `velocity = delta / elapsed`，`is_estimated=False`；
  未命中则按现状 `velocity = stars / age`，`is_estimated=True`。
- 删除原来的全局 `prev_time / elapsed_days`。
- `first_run` 仍以 `len(prev_repos)==0` 判定。
- **爆发榜阈值改为按日增速**：现状 `burst` 用「原始 delta ≥ `burst_min_delta`」
  做门槛，这在 5 天间隔下会被放大约 5 倍（门槛变松）。改为按
  `velocity_per_day ≥ burst_min_velocity`（新配置项，默认 20/天，语义=
  原 `burst_min_delta` 的「每天」版），使门槛对任意间隔都一致。
  排序仍按 `velocity_per_day` 降序。`config.yaml` 把 `burst_min_delta`
  重命名为 `burst_min_velocity`（含义即「日增速门槛」）。

### 4. `ghradar/domains.py`（新增小模块）
- `select_domain(domains: list[str], when: datetime) -> str`：日期取模选板块。
- 单一职责、便于独立测试。

### 5. `radar.py`
- 读 `domains = list(cfg["domains"].keys())`。
- `rotation` 为真：`today = select_domain(domains, now)`，只用
  `cfg["domains"][today]` 的关键词搜，`domains_for_report = [today]`。
  为假：沿用全部板块。
- `build_rankings` 传入 `load_snapshot` 后的（已归一）prev。
- 结束时 `save_snapshot(path, repos, now, base=prev)` 做合并。
- 报告标题体现「今日板块」。

### 6. `ghradar/report.py`
- `render_markdown / render_html` 已接受 `domains` 列表参数；轮换时传
  `[today]`。标题/副标题加「今日板块：<名>」字样（中英 HTML 都加）。

## 数据流（轮换日）

```
launchd 08:30
  → load_config (5 板块, rotation=true)
  → now=UTC; today = domains[now.toordinal() % 5]
  → 只用 today 的关键词调 GitHub Search API → repos
  → prev = load_snapshot()            # 归一为 {name:{stars,seen}}
  → rankings = build_rankings(repos, prev, cfg, now)   # 每仓库各自间隔算增速
  → 写 <date>.md / <date>.html / _latest.html （标题含今日板块）
  → save_snapshot(merge)：更新 today 的仓库，其余板块数据保留
```

## 错误处理与边界

- **旧快照迁移**：首次以新代码运行时，`load_snapshot` 把现有
  `snapshot.json`（旧格式、含 5/30 那批）迁移为新格式，`seen` 取旧
  `generated_at`。不丢历史、不报错。
- **跨板块重复仓库**（如 n8n 同属自动化与 AI）：谁先轮到谁更新其
  `seen/stars`；下次另一板块再遇到就按较短间隔算，无副作用。
- **某板块首次出现的仓库**：`is_estimated=True`，报告标「估算」，与现状一致。
- **关键词查询失败**：沿用现有「跳过并告警」逻辑。
- **vault 路径缺失**：沿用现有回退到本地 `reports/`。

## 测试策略（TDD）

- `test_domains.py`：取模选板块确定性；序号 0..4 循环；第 N+1 天回到第 0 个。
- `test_snapshot.py`：新格式往返；旧格式迁移；合并保留其他板块仓库且只更新今天的。
- `test_scoring.py`：每仓库各自间隔的真实增速（如 seen 在 5 天前 → delta/5）；
  未命中仓库走估算；更新现有用例的 prev 夹具到新格式。
- `test_radar.py`：rotation 开启时只搜当天板块的关键词；save_snapshot 合并后
  其他板块仓库仍在；报告标题含今日板块。
- 全量 `pytest` 绿（现 35 项 + 新增）。

## 范围之外（YAGNI）

- 不做每板块单独的 `_latest_<板块>.html`（如需将来再加）。
- 不做绑定星期几/可配置循环长度（循环长度即板块数）。
- 不做板块权重差异化（沿用同一套 weights）。
