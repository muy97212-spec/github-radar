#!/bin/sh
# 运行 GitHub 雷达。可被 launchd(mac)/cron(linux)/任务计划程序(windows, 经 WSL/git-bash)调用。
# token 规则:优先用已设置的 GITHUB_TOKEN;没有则尝试 gh(若已安装并登录);仍没有则未认证运行(限流更严)。
DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$DIR" || exit 1
if [ -z "$GITHUB_TOKEN" ] && command -v gh >/dev/null 2>&1; then
  GITHUB_TOKEN="$(gh auth token 2>/dev/null)"
  export GITHUB_TOKEN
fi
# 固定用项目 venv 里的 python(依赖装在这);没有 venv 才回退到系统 python3。
if [ -x "$DIR/.venv/bin/python" ]; then
  PY="$DIR/.venv/bin/python"
else
  PY=python3
fi
echo "----- $(date '+%Y-%m-%d %H:%M:%S') run-radar ($PY) -----"
exec "$PY" radar.py
