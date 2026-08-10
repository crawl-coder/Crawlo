#!/usr/bin/env bash
# 发布就绪检查（P0-A4）——供 CI 与开发者本地使用
#
# 用法：
#   scripts/release_check.sh          # 只做 dry-run 检查（默认）
#   scripts/release_check.sh --tests  # 检查 + 跑全量测试
set -euo pipefail

cd "$(dirname "$0")/.."

if [[ "${1:-}" == "--tests" ]]; then
  python -m crawlo.commands.release
else
  python -m crawlo.commands.release --dry-run
fi
