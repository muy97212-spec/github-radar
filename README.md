# GitHub 雷达(GitHub Radar)

扫描你固定关注领域的 GitHub 项目,产出 **综合 / 标杆(存量前 5%)/ 爆发(增速)** 三榜
Markdown 报告,写入你的 Obsidian vault。

为什么不用现成 trending 工具:官方 GitHub Trending 不在 API 里、只能按编程语言筛,
做不到"按领域关键词找黑马"。本工具改用 **Search API + 本地快照**,在你关心的领域内
既抓"已经很大"的标杆,也抓"小而快"的黑马。设计细节见
[docs/superpowers/specs](docs/superpowers/specs/2026-05-30-github-radar-design.md)。

## 用法

```bash
# 1) 依赖(建议用 venv 隔离)
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt

# 2) 复制配置并改成你的 Obsidian vault 路径
cp config.example.yaml config.yaml
#   编辑 config.yaml 里的 vault_path(不改也能跑,会落到项目内 reports/)

# 3) 跑(GITHUB_TOKEN 提升搜索限流额度,未认证约 10 次/分钟)
export GITHUB_TOKEN="$(gh auth token)"
.venv/bin/python radar.py          # 轮换模式:只跑当天那一个板块
.venv/bin/python radar.py --all    # 预热:一次把全部板块跑出来(首次想立刻看到全部板块时用)
```

报告输出到 `config.yaml` 里 `vault_path` / `report_folder` 指定的目录(指向你的 Obsidian vault,
得到 `GitHub雷达/<日期>.md`)。Obsidian 会自动收录,在那个文件夹开个窗口即可按时间线翻阅。

**首次运行**没有历史快照,增速为"年龄均速"估算(报告顶部会标注「首跑 · 增速为估算」);
之后每跑一次都会存一份 `snapshot.json`,下次即按两次之间的**真实涨幅**计算增速。

## 网页版报告 + 总览仪表盘

每个板块除 Markdown 外,还在**同一子文件夹**生成 HTML:`<日期>.html`(归档)与
`_latest.html`(固定名、永远最新一期,适合存浏览器书签)。9 个板块共用同一套「晨报」
大报头排版,统一**暖象牙白 + Fraunces 衬线**的高级风,只换**强调色 / 底纹微染**:

| 主题键 | 强调色 | 对应板块(默认) |
|--------|--------|----------------|
| `editorial` | 砖红 | 内容创作与分发 |
| `console` | 靛蓝 | AI/大模型应用与框架 |
| `scope` | 森绿 | 自动化与工作流 |
| `terminal` | 赭石 | 开发者工具 / CLI |
| `homelab` | 黄铜 | 自托管 / 效率应用 |
| `atelier` | 梅紫 | 前端 / UI 设计与灵感 |
| `stream` | 青 | 数据 / 向量检索 |
| `cipher` | 玄青 | 安全 / 隐私 |
| `atlas` | 黛紫 | 学习 / Awesome 资源 |

vault 根目录另有一张 **`_仪表盘.html`(总览封面)**:与板块同一套暖纸编辑部排版,
居中、易读——大报头 + 今日/下一班导语 + 轮值进度条 + 今日 hero + 其余板块对称卡片
(各用本板强调色),**点卡片名即跳进对应板块的 `_latest.html`**。
把这张仪表盘存成书签,就是你每天的入口。

HTML 由 `ghradar/report.py` / `ghradar/overview.py` 在本地生成:行内容服务端烘焙、
不含第三方脚本、外部文本全部转义、`prefers-reduced-motion` 有降级。标题字体走 Google
Fonts,离线自动降级为系统字体。Markdown 仍是 Obsidian 内的主入口(可搜索、按时间线归档)。

## 板块轮换(N 天周期 = 板块数)

`rotation: true`(默认)时,每天按日期取模只跑**一个**板块(`config.yaml` 的
`domains` 顺序即循环序号),跑完一圈回到第 1 个。默认 9 个板块即 9 天一圈。输出结构:

```
GitHub雷达/
├── _总览.md          # 全部板块一览表(Obsidian 内直接看;每行 [[wikilink]] 连到该板块)
├── _仪表盘.html      # 总览仪表盘(浏览器入口,卡片点进各板块)
└── <板块名>/         # 每板块一个子文件夹
    ├── _latest.html  # 该板块最新一期网页(对应主题皮肤)
    ├── _latest.md    # 固定名 Markdown(供 Obsidian wikilink / Graph 连接)
    ├── <日期>.html
    └── <日期>.md
```

**两种看法**:① 浏览器把 `_仪表盘.html` 存书签 → 点卡片进 `<板块>/_latest.html` → 点仓库名去
GitHub(一路可点);② Obsidian 里 `_总览.md` 用 `[[<板块>/_latest]]` 连到各板块笔记,Graph
关系图即可互相跳转。轮换下板块内容一天补一块、跑满一圈即集齐;想立刻看全部就用 `radar.py --all`。

增速在轮换下仍准确:快照按「每仓库各自上次见到日期」计算(某板块 N 天轮一次→得
N 天平均日增速)。各板块的视觉皮肤见上面「网页版报告」一节(由 `themes:` 配置)。
设 `rotation: false` 可回退为每天跑全部板块、写到主文件夹根。

## 三个榜怎么来的

- 🥇 **综合榜** = 归一化加权 `weights.stock × 存量分 + weights.velocity × 增速分`(默认 0.4 / 0.6,偏向发现黑马)
- 🏆 **标杆榜** = 候选池里 star 总数排前 5% 的项目(大而稳)
- 🚀 **爆发榜** = 按增速排序、不看绝对星数,**日增速**达 `burst_min_velocity`(星/天)才入榜(小而快的黑马)

存量与增速是**两个独立排名**:前 5% 只决定标杆榜谁能上,完全不淘汰爆发榜里的黑马。

## 配置(`config.yaml`,从 `config.example.yaml` 复制而来)

| 字段 | 含义 |
|------|------|
| `domains` | 领域 → 关键词列表(候选池来源) |
| `pool_min_stars` | 候选池低门槛(默认 50,放低以让黑马进池) |
| `fetch_cap_per_keyword` | 每个关键词最多取多少(默认 300) |
| `top_k` | 每个榜显示几条(默认 15) |
| `burst_min_velocity` | 爆发榜入榜的最小**日增速**(星/天,默认 20) |
| `weights` | 综合榜的 `stock` / `velocity` 权重 |
| `rotation` | `true`(默认)每天轮一个板块;`false` 每天跑全部 |
| `themes` | 板块 → 视觉皮肤键(editorial / console / scope / terminal / homelab / atelier / stream / cipher / atlas) |
| `vault_path` / `report_folder` | 报告输出目录(vault 不存在时降级到项目内 `reports/`) |

GitHub token 从环境变量 `GITHUB_TOKEN` 读,不写进配置文件。

## 定时(每天自动跑)

工具本身跨平台(`python3 radar.py` 哪都能跑),但"每天 8:30 自动触发"是操作系统的活,分系统配置。
统一入口是 `scripts/run-radar.sh`(它会自动处理 token:优先用 `GITHUB_TOKEN`,没有再尝试 `gh`)。

**macOS(launchd,推荐)** —— 比 cron 可靠:到点时若在睡眠,唤醒后会补跑。

先编辑 `scripts/com.github-radar.plist`,把里面的 `/path/to/github-radar` 换成你的项目绝对路径,然后:

```bash
cp scripts/com.github-radar.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.github-radar.plist
launchctl enable gui/$(id -u)/com.github-radar
# 卸载:launchctl bootout gui/$(id -u)/com.github-radar
# 立即测试一次:launchctl kickstart -k gui/$(id -u)/com.github-radar
```
日志看 `radar-launchd.log`。

**Linux(cron):**
```cron
30 8 * * * /path/to/github-radar/scripts/run-radar.sh >> /path/to/github-radar/radar-cron.log 2>&1
```

**Windows(任务计划程序):** 新建任务,每天 08:30,操作设为运行
`python C:\path\to\github-radar\radar.py`,并在环境变量里设好 `GITHUB_TOKEN`(或先 `gh auth login`)。

## 测试

```bash
python3 -m pytest -q
```
