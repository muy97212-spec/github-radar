# GitHub 雷达(GitHub Radar)

扫描你固定关注领域的 GitHub 项目,产出 **综合 / 标杆(存量前 5%)/ 爆发(增速)** 三榜
Markdown 报告,写入你的 Obsidian vault。

为什么不用现成 trending 工具:官方 GitHub Trending 不在 API 里、只能按编程语言筛,
做不到"按领域关键词找黑马"。本工具改用 **Search API + 本地快照**,在你关心的领域内
既抓"已经很大"的标杆,也抓"小而快"的黑马。设计细节见
[docs/superpowers/specs](docs/superpowers/specs/2026-05-30-github-radar-design.md)。

## 用法

```bash
pip install -r requirements.txt
export GITHUB_TOKEN="$(gh auth token)"   # 提升搜索限流额度(未认证约 10 次/分钟)
python3 radar.py
```

报告输出到 `config.yaml` 里 `vault_path` / `report_folder` 指定的目录(默认你的 Obsidian vault
`GitHub雷达/<日期>.md`)。Obsidian 会自动收录,在那个文件夹开个窗口即可按时间线翻阅。

**首次运行**没有历史快照,增速为"年龄均速"估算(报告顶部会标注「首跑 · 增速为估算」);
之后每跑一次都会存一份 `snapshot.json`,下次即按两次之间的**真实涨幅**计算增速。

## 三个榜怎么来的

- 🥇 **综合榜** = 归一化加权 `weights.stock × 存量分 + weights.velocity × 增速分`(默认 0.4 / 0.6,偏向发现黑马)
- 🏆 **标杆榜** = 候选池里 star 总数排前 5% 的项目(大而稳)
- 🚀 **爆发榜** = 按增速排序、不看绝对星数,涨幅达 `burst_min_delta` 才入榜(小而快的黑马)

存量与增速是**两个独立排名**:前 5% 只决定标杆榜谁能上,完全不淘汰爆发榜里的黑马。

## 配置(`config.yaml`)

| 字段 | 含义 |
|------|------|
| `domains` | 领域 → 关键词列表(候选池来源) |
| `pool_min_stars` | 候选池低门槛(默认 50,放低以让黑马进池) |
| `fetch_cap_per_keyword` | 每个关键词最多取多少(默认 300) |
| `top_k` | 每个榜显示几条(默认 15) |
| `burst_min_delta` | 爆发榜入榜的最小真实涨幅(默认 20) |
| `weights` | 综合榜的 `stock` / `velocity` 权重 |
| `vault_path` / `report_folder` | 报告输出目录(vault 不存在时降级到项目内 `reports/`) |

GitHub token 从环境变量 `GITHUB_TOKEN` 读,不写进配置文件。

## 定时(可选)

挂 cron,例如每天 9 点跑一次:

```cron
0 9 * * * cd /Users/jenson/github-radar && GITHUB_TOKEN=$(gh auth token) /usr/bin/python3 radar.py
```

## 测试

```bash
python3 -m pytest -q
```
