# v{MAJOR.MINOR.PATCH}

**Tag:** `v{MAJOR.MINOR.PATCH}`
**Date:** YYYY-MM-DD
**Previous:** `v{上一版本}`

---

## Overview

一段话说明本版本的主题与定位（例：架构重构 / 功能补齐 / 稳定性收口）。

## Breaking Changes

（无破坏性变更则写"无"。有则逐条列出：旧行为 → 新行为 + 迁移指南链接。）

## New Features

- 功能 1（模块路径）
- 功能 2（模块路径）

## Improvements

- 改进 1

## Bug Fixes

- 修复 1（关联 issue / 影响面）

## Migration Guide（仅 Breaking Changes 时必填）

说明用户从上一版本升级需要做什么。

---

> 发布流程：1) 把 CHANGELOG.md 的 `## [Unreleased]` 改为 `## [x.y.z] - YYYY-MM-DD`；
> 2) 复制本模板为 `docs/releases/v{x.y.z}.md` 并填写；
> 3) 更新 `crawlo/__version__.py`；4) 运行 `crawlo release --dry-run` 确认全绿后打 tag。
