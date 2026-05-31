# 设计：板块轮换 + 分主题展示 + 总览

- 日期：2026-05-31
- 项目：GitHub 雷达（github-radar）
- 状态：已与用户确认全部要点，待写实现计划

## 背景与动机

当前雷达每天用**同一批关键词**扫两个领域，产出覆盖范围相同的报告。用户希望：

- 覆盖**更多领域类别**（偏向星标较高的赛道）；
- 不要每天扫全部、内容雷同——改为**每天聚焦一个板块**，跨天覆盖更多面；
- 以**周期**判定当天跑哪个板块；
- 在 Obsidian 里有 **5 个常驻「窗口」**（每板块一个），点开即该板块最新榜单；
- 5 个板块**各有符合自身主题的视觉风格**，便于区分；
- 另有**总览表格**与**总览仪表盘**，一眼看全 5 个板块的最新状态。

用户拍板形态：**5 个板块，一天跑一个，第 6 天回到第 1 个**（简单 5 天循环，不要复杂调度）。
加板块的方式要简单：复制现有板块、改关键词即可。

## 关键约束：轮换不能破坏「真实增速」

雷达最有价值的功能是「真实日增速」（报告里的 `+293/天`），依赖 `snapshot.json`
保存上一轮每仓库 star、今天减上次得增量。直接轮换会破坏它：

1. **快照被整体覆盖**：现状每跑一次就用当天这批仓库替换整个快照。轮换后某板块过 5 天
   再轮回来时，它的仓库早被挤掉，永远算不出真实增速。
2. **时间戳全局只有一个**：现状只记一个「上次生成时间」=昨天，但该板块真正上次出现是
   ~5 天前，用昨天当基准会把增速放大约 5 倍。

**解法**：快照改成**每个仓库记 `{star 数, 上次见到日期}`**，每天只更新今天板块的仓库、
其余原样保留。增速改用**每仓库各自间隔**：`(今天 star − 上次 star) ÷ 实际间隔天数`。
某板块 5 天轮一次 → 间隔≈5 天 → 得「5 天平均日增速」，仍是真实数据，不再天天「估算」。
此设计对任意节奏（每天/每周/不规则）都成立。

## 五个板块（轮换池）

`config.yaml` 的 `domains` 扩为 5 项，**顺序即循环序号 0..4**：

| 序号 | 板块（display name） | 文件夹 slug | 关键词方向 |
|------|----------------------|-------------|-----------|
| 0 | 自动化与工作流 | 自动化与工作流 | 现有 |
| 1 | 内容创作与分发 | 内容创作与分发 | 现有（含设计/多媒体生成） |
| 2 | AI/大模型应用与框架 | AI·大模型应用与框架 | LLM 应用、Agent 框架、RAG、推理引擎 |
| 3 | 开发者工具 / CLI | 开发者工具·CLI | 终端工具、效率 CLI、编辑器插件、本地开发利器 |
| 4 | 自托管 / 效率应用 | 自托管·效率应用 | self-hosted、知识管理、笔记、看板 |

- **文件夹 slug 安全化**：`slugify(name) = name.replace("/", "·").replace(" ", "")`
  （文件夹名不允许含 `/`）。
- 加板块 = 在 `domains` 下复制一段、改名与关键词；`config.example.yaml` 放好 5 个模板，
  README 写明「复制粘贴改关键词即可」。

## 当天跑哪个板块：日期取模（无状态）

```
idx        = now(UTC).toordinal() % len(domains)
今日板块   = domains[idx]
明日板块   = domains[(now.toordinal()+1) % len(domains)]   # 仪表盘用来提示"接下来轮到谁"
```

- **无状态、可预测**：看日期就知道今天是哪个板块。
- **漏跑不错乱**：某天关机没跑，第二天按它自己的日期照常对号入座（不像「计数器+1」会补跑/漂移）。
- 用 `radar.py` 现有 `now = datetime.now(timezone.utc)` 取日期，与 `date_str` 同源。
- 备选「绑定星期几」「计数器累加」均已考虑、用户都可接受；选「日期取模」因其无状态、最直观。

## Obsidian 输出结构

```
GitHub雷达/                      ← 主文件夹(report_folder)
├── _总览.md                     ← ① 总览表格(Obsidian 内直接渲染)
├── _仪表盘.html                 ← ② 总览仪表盘(浏览器, bespoke 设计)
├── 自动化与工作流/
│   ├── _latest.html             ← 点开 = 该板块最新一期(对应主题皮肤)
│   ├── 2026-05-31.html          ← 历史归档(带日期)
│   └── 2026-05-31.md            ← 历史归档(Obsidian 内可读/可搜)
├── 内容创作与分发/
├── AI·大模型应用与框架/
├── 开发者工具·CLI/
└── 自托管·效率应用/
```

- 每板块一个子文件夹；`_latest.html` 是该板块「常驻窗口」，轮到当天刷新覆盖，归档另存。
- 带日期的 `.md/.html` 为存档，互不覆盖。

## 分主题视觉（5 套皮肤 + 1 个仪表盘）

5 个板块各用一套符合主题的皮肤；**共用同一套 HTML 结构**（标题 + 综合/标杆/爆发三榜 +
HTML 转义 + `prefers-reduced-motion` 回退），**只换一层 CSS**：

| 板块 | 主题 key | 视觉方向 | 关键元素 |
|------|----------|---------|---------|
| 自动化与工作流 | `scope` | 示波器/蓝图(深色) ← 复用已做 `web/report.html` | Chakra Petch + IBM Plex Mono、磷光绿、扫描线、机械感 |
| 内容创作与分发 | `editorial` | 编辑部晨报(浅色) ← 复用现 `render_html` | Fraunces + 宋体、纸张底、朱红 |
| AI/大模型应用与框架 | `console` | 推理控制台(近黑) 新 | 近黑底、电青/柠檬高光、细网格、model-card 质感(避开 AI 紫) |
| 开发者工具 / CLI | `terminal` | 终端 TUI 新 | 全等宽、`#0c0c0c` 底、绿/琥珀提示符、ASCII 分隔线 |
| 自托管 / 效率应用 | `homelab` | 家庭实验室面板(浅色) 新 | Space Grotesk、留白、柔和卡片阴影、青绿点缀 |
| **总览仪表盘** | (bespoke) | 指挥中心 新 | 5 张卡片各带本板块主色色卡，标「今天是谁/接下来轮到谁」，一眼看全 |

- 主题分配放进 config（可改）：`themes: {<板块名>: <主题key>}`，缺省回退 `editorial`。
- `render_html(rankings, date_str, domain, theme="editorial")`：theme 选 CSS。
- 仪表盘是单独定制的另一套，不走 `render_html`。
- 所有皮肤都保留：服务端烘焙行(无 `<script>`)、外部文本 HTML 转义、reduced-motion 回退。

## 组件改动

### 1. `config.yaml` / `config.example.yaml`
- `domains` 扩为 5 项（见上表）。
- 新增 `rotation: true`（默认开）。`true`=每天按日期取模只跑一个板块；`false`=旧行为(跑全部)，便于回退/测试。
- 新增 `themes: {板块名: 主题key}`（缺省 `editorial`）。
- `burst_min_delta` → 重命名 `burst_min_velocity`（默认 20，语义=日增速门槛，见 scoring）。

### 2. `ghradar/domains.py`（新）
- `slugify(name) -> str`：`/`→`·`、去空格。
- `select_domain(domains, when) -> str`：日期取模选当天板块。
- `next_domain(domains, when) -> str`：取模 +1，供仪表盘提示。

### 3. `ghradar/snapshot.py`
- 新格式：
  ```json
  {"last_run": "2026-05-31T..Z",
   "repos": {"owner/name": {"stars": 1234, "seen": "2026-05-31T..Z"}}}
  ```
- `load_snapshot(path)`：**向后兼容**，读到旧格式 `{generated_at, repos:{name:stars}}` 时
  把每仓库迁移成 `{stars, seen: generated_at}`，统一返回新格式。
- `save_snapshot(path, repos, now, base)`：**合并而非覆盖**——以 `base` 为底，更新/插入
  今天这批仓库为 `{stars, seen: now}`，其余原样保留；写回 `last_run = now`。

### 4. `ghradar/scoring.py` — `build_rankings`
- `prev_repos[name]` 现为 `{stars, seen}`。
- 每仓库各自算间隔：命中则 `delta=max(stars-prev.stars,0)`、
  `elapsed=max((now-parse(prev.seen)).days_float,1.0)`、`velocity=delta/elapsed`、
  `is_estimated=False`；未命中按现状 `velocity=stars/age`、`is_estimated=True`。
- 删除全局 `prev_time/elapsed_days`；`first_run` 仍以 `len(prev_repos)==0` 判定。
- **爆发榜阈值改按日增速**：原「原始 delta ≥ `burst_min_delta`」在 5 天间隔下被放大约 5 倍。
  改为 `velocity_per_day ≥ burst_min_velocity`（默认 20/天），对任意间隔一致；排序仍按
  `velocity_per_day` 降序。

### 5. `ghradar/state.py`（新，板块状态缓存）
- 只有当天那个板块真去搜，但总览要展示全部 5 个 → 每板块跑完缓存一份结构化 JSON。
- 存项目目录 `boards_state/<slug>.json`（与 `snapshot.json` 并列，**不进 vault**）。
- 内容(精简)：`{domain, slug, updated_at, date_str, pool_size,
  combined:[top5], burst:[top3]}`；每条仅留 `full_name, html_url, stars,
  velocity_per_day, delta, is_estimated`。
- `save_board_state(dir, domain, rankings, date_str, now)`；
  `load_all_board_states(dir, domains) -> {domain: state|None}`（未采集→None）。

### 6. `ghradar/report.py`
- `render_markdown / render_html` 接受单板块 `domain`。
- 加 `THEMES`（主题key→CSS）；`render_html(..., theme)` 选皮肤；结构/转义/无障碍共用。
- 5 套皮肤：`editorial`(现成)、`scope`(移植 `web/report.html`)、`console`、`terminal`、`homelab`。

### 7. `ghradar/overview.py`（新）
- `render_overview_md(states, domains, today, nxt) -> str`：5 行表格
  「板块 | 上次更新 | 候选池 | 综合榜首 | 榜首增速 | 爆发榜首」；未采集显示「尚未采集」。
  「上次更新」用相对天数（今天/N 天前）。
- `render_dashboard_html(states, domains, today, nxt) -> str`：bespoke 指挥中心面板
  （5 张主色卡片、今天/接下来标记、HTML 转义、reduced-motion 回退、无 `<script>`）。

### 8. `radar.py`
- 读 `domains`、`themes`、`rotation`。
- rotation 真：`today=select_domain(domains,now)`，仅用 `cfg["domains"][today]` 关键词搜，
  写入子文件夹 `<slug>/`（`<date>.md`、`<date>.html`、`_latest.html`，主题=themes[today]）；
  `save_board_state(...)`。
- 之后**每天都**：`load_all_board_states` → 写 `_总览.md` 与 `_仪表盘.html` 到主文件夹根。
- `save_snapshot(merge)`；旧快照首次自动迁移。
- rotation 假：沿用全部板块（保留回退路径）。

### 9. `.gitignore`
- 加 `boards_state/`（与 `snapshot.json` 同样属本地运行态，不入库）。

## 数据流（轮换日）

```
launchd 08:30
  → load_config(5 板块, rotation=true, themes)
  → now=UTC; today=domains[now.toordinal()%5]; nxt=domains[(+1)%5]
  → 仅用 today 关键词调 Search API → repos
  → prev = load_snapshot()                      # 归一为 {name:{stars,seen}}
  → rankings = build_rankings(repos, prev, cfg, now)   # 每仓库各自间隔算增速
  → 写 <slug>/<date>.md / <date>.html / _latest.html   # 用 today 的主题皮肤
  → save_board_state(boards_state/<slug>.json, rankings)
  → states = load_all_board_states(...)
  → 写 _总览.md + _仪表盘.html 到主文件夹根            # 反映全部 5 板块最新态
  → save_snapshot(merge)                              # 更新 today 仓库, 其余保留
```

## 错误处理与边界

- **旧快照迁移**：首次新代码运行时把现有 `snapshot.json`(含 5/30 那批)迁移为新格式，
  `seen` 取旧 `generated_at`，不丢历史、不报错。
- **旧的根目录文件**(`2026-05-30.md/html`、根 `_latest.html`)为历史遗留，保留不动；新输出进子文件夹。
- **跨板块重复仓库**(如 n8n 同属自动化与 AI)：谁先轮到谁更新其 `seen/stars`，下次另一板块
  按较短间隔算，无副作用。
- **某板块首次出现的仓库**：`is_estimated=True`，报告标「估算」，与现状一致。
- **未采集板块**：总览/仪表盘显示「尚未采集」，不崩。
- **关键词查询失败 / vault 缺失**：沿用现有「跳过告警」「回退本地 reports/」逻辑。

## 测试策略（TDD）

- `test_domains.py`：`slugify`(/→·、去空格)；`select_domain` 确定性 + 0..4 循环 + 第 N+1 天回到 0；`next_domain`。
- `test_snapshot.py`：新格式往返；旧格式迁移；合并保留其他板块仓库且只更新今天的。
- `test_scoring.py`：每仓库各自间隔的真实增速(seen 在 5 天前→delta/5)；未命中走估算；
  爆发榜按 `velocity_per_day` 过滤；更新现有用例 prev 夹具到新格式。
- `test_state.py`：保存/读取往返、字段精简、未采集→None。
- `test_overview.py`：表格 5 行含「尚未采集」；相对天数；仪表盘是完整文档、转义、含今天/接下来标记。
- `test_report.py`：每套主题 `render_html` 都是完整文档、含对应字体/主题标记、结构一致(同样的仓库都在)、外部文本转义；reduced-motion 回退存在。
- `test_radar.py`：rotation 开时只搜当天板块；输出落在 `<slug>/` 子文件夹；根目录有 `_总览.md`+`_仪表盘.html`；板块状态已更新；snapshot 合并后其他板块仓库仍在。
- 全量 `pytest` 绿（现 35 项 + 新增）。

## 实现分期（writing-plans 细化）

1. **后端骨架**：domains.py + snapshot 改造 + scoring 改造 + state.py + radar 串联 +
   overview.md（表格）。全程 TDD，测试全绿——此时功能已可跑、报告进子文件夹、总览表格可用。
2. **视觉皮肤**：report.py 主题化 + 4 套新皮肤(scope 移植 + console/terminal/homelab) + editorial 接入；用 frontend-design 技能逐套打磨、Claude Preview 截图验收。
3. **仪表盘**：overview.py 的 `_仪表盘.html` bespoke 设计 + 验收。

## 范围之外（YAGNI）

- 不做绑定星期几 / 可配置循环长度（循环长度即板块数）。
- 不做板块差异化权重（沿用同一套 weights）。
- 不做历史趋势图 / 跨期对比页（将来再说）。
