# 🔄 下载延迟中间件指南

## 📋 概述

`DownloadDelayMiddleware` 是 Crawlo 的限流中间件，用于控制请求频率。它支持**简单配置**和**高级配置**，提供灵活的延迟控制功能。

**注意**：早期版本中的 `ThrottleMiddleware` 已被简化为 `DownloadDelayMiddleware`，专注于延迟控制。并发控制已移至下载器层实现。

---

## ✅ 参数兼容性

### 核心参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `DOWNLOAD_DELAY` | float | `0.5` | **统一的延迟配置**（秒） |
| `RANDOMNESS` | bool | `True` | 是否启用随机延迟 |
| `RANDOM_RANGE` | list | `[0.5, 1.5]` | 随机延迟范围倍数 |

### 可选参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `DOWNLOAD_DELAY_ENABLED` | bool | `True` | 是否启用延迟中间件 |
| `DOWNLOAD_DELAY_RANDOM` | bool | `True` | 同 `RANDOMNESS` |

> ⚠️ **注意**：早期版本的 `THROTTLE_*` 参数已移除，统一使用 `DOWNLOAD_DELAY` 相关参数

---

## 🎯 配置优先级

```
DOWNLOAD_DELAY (唯一配置)
    ↓
默认值 0.5s (如果没有配置)
```

**重要**：统一使用 `DOWNLOAD_DELAY`，不再有其他延迟配置参数。

---

## 📖 使用场景

### 场景 1：简单延迟（小型项目）✅ 推荐

**适用场景**：
- 单一目标网站
- 简单爬虫项目
- 快速原型开发

**配置示例**：

```python
# settings.py

# 固定延迟：每个请求间隔 2 秒
DOWNLOAD_DELAY = 2.0
RANDOMNESS = False

# 或随机延迟：1-3 秒之间随机
DOWNLOAD_DELAY = 2.0
RANDOMNESS = True
RANDOM_RANGE = [0.5, 1.5]
```

**效果**：
- ✅ 自动使用 DownloadDelayMiddleware
- ✅ 零配置迁移成本
- ✅ 保持原有行为

---

### 场景 2：多域名不同延迟（中型项目）✅ 推荐

**适用场景**：
- 爬取多个网站
- 不同网站需要不同延迟
- 需要精细控制

**配置示例**：

```python
# settings.py

# 全局默认延迟
DOWNLOAD_DELAY = 1.0

# 域名特定配置
DOWNLOAD_DELAY_OVERRIDES = {
    'example.com': {
        'delay': 2.0,  # 慢速网站，2秒延迟
    },
    'api.example.com': {
        'delay': 0.1,  # API 接口，快速
    },
    'slow-site.org': {
        'delay': 3.0,  # 非常慢的网站
    },
}
```

**效果**：
- ✅ 不同域名不同延迟
- ✅ 简单配置

---

### 场景 3：随机延迟增强（推荐）

**适用场景**：
- 需要随机延迟避免被检测
- 简单的反爬虫策略

**配置示例**：

```python
# settings.py

DOWNLOAD_DELAY = 1.0
RANDOMNESS = True  # 启用随机延迟
RANDOM_RANGE = [0.5, 1.5]  # 延迟范围：0.5s - 1.5s
```

**随机延迟原理**：
- 基础延迟为 DOWNLOAD_DELAY
- 实际延迟 = DOWNLOAD_DELAY × random(RANDOM_RANGE)
- 使请求间隔更自然

---

### 场景 4：禁用延迟（可选）

如果你不需要延迟控制，可以禁用它：

```python
# settings.py

# 禁用延迟中间件
DOWNLOAD_DELAY_ENABLED = False
# 或
DOWNLOAD_DELAY = 0
```

**效果**：
- ✅ 请求无延迟
- ✅ 适合对速度要求极高的场景
- ⚠️ 注意：可能触发目标网站的限流机制

---

## 🔄 迁移示例

### 示例 1：从旧配置迁移

**旧配置**（DownloadDelayMiddleware）：

```python
custom_settings = {
    'DOWNLOAD_DELAY': 0.5,
    'RANDOMNESS': True,
    'RANDOM_RANGE': [0.5, 1.5],
    'CONCURRENCY': 6,
}
```

**新配置**（保持完全不变）：

```python
custom_settings = {
    'DOWNLOAD_DELAY': 0.5,    # ✅ 仍然有效！
    'RANDOMNESS': True,        # ✅ 转换为 auto_throttle
    'RANDOM_RANGE': [0.5, 1.5],  # ⚠️ 仅用于日志
    'CONCURRENCY': 6,
}
```

**变化**：
- ✅ 无需修改任何配置
- ✅ 自动使用 DownloadDelayMiddleware
- ✅ RANDOMNESS=True 启用随机延迟

---

### 示例 2：添加域名级控制

**旧配置**（功能有限）：

```python
custom_settings = {
    'DOWNLOAD_DELAY': 1.0,  # 所有网站统一延迟
    'CONCURRENCY': 8,
}
```

**新配置**（增强功能）：

```python
custom_settings = {
    'DOWNLOAD_DELAY': 1.0,  # 全局默认
    'CONCURRENCY': 8,
    
    # 新增：域名级控制
    'DOWNLOAD_DELAY_OVERRIDES': {
        'fast-api.com': {
            'delay': 0.1,  # 快速 API
        },
        'slow-site.com': {
            'delay': 3.0,  # 慢速网站
        },
    },
}
```

**提升**：
- ✅ 快速 API：0.1s 延迟
- ✅ 慢速网站：3s 延迟
- ✅ 其他网站：1s 延迟（默认）

---

### 示例 3：启用智能调节

**旧配置**（固定延迟）：

```python
custom_settings = {
    'DOWNLOAD_DELAY': 2.0,
    'RANDOMNESS': True,
    'RANDOM_RANGE': [0.5, 1.5],
}
```

**新配置**（保持相同）：

```python
custom_settings = {
    'DOWNLOAD_DELAY': 2.0,
    'RANDOMNESS': True,
    'RANDOM_RANGE': [0.5, 1.5],
}
```

**说明**：
- ✅ 随机延迟：1-3 秒
- ✅ 配置完全兼容，无需修改

---

## 📊 功能对比

| 功能 | 旧 ThrottleMiddleware | 新 DownloadDelayMiddleware | 说明 |
|------|----------------------|---------------------------|------|
| **固定延迟** | ✅ | ✅ | 每个请求固定间隔 |
| **随机延迟** | ✅ | ✅ | RANDOMNESS 控制 |
| **域名级控制** | ✅ | ✅ | 不同域名不同延迟 |
| **QPS 限制** | ✅ | ❌ | 已移至下载器层 |
| **并发控制** | ✅ | ❌ | 已移至下载器层 |
| **智能调节** | ✅ | ❌ | 已简化 |
| **突发控制** | ✅ | ❌ | 已简化 |
| **统计记录** | ✅ 完整 | ✅ 基础 | 简化实现 |

**设计原则**：限流中间件专注于**延迟控制**，**并发控制**由下载器层负责。

---

## ⚠️ 注意事项

### 1. 统一使用 DOWNLOAD_DELAY

**旧版**（已废弃）：
```python
# ❌ 不要使用（已移除）
THROTTLE_DEFAULT_DELAY = 1.0
THROTTLE_MAX_RATE = 5.0
THROTTLE_AUTO_THROTTLE = True
THROTTLE_DOMAIN_OVERRIDES = {...}
```

**新版**（统一配置）：
```python
# ✅ 正确：统一使用 DOWNLOAD_DELAY
DOWNLOAD_DELAY = 1.0
DOWNLOAD_DELAY_OVERRIDES = {...}
```

---

---

### 2. RANDOMNESS 的行为

**配置**：
```python
RANDOMNESS = True
RANDOM_RANGE = [0.5, 1.5]
# 效果：延迟在 DOWNLOAD_DELAY × 0.5 到 DOWNLOAD_DELAY × 1.5 之间随机
```

**说明**：
- `RANDOMNESS` 控制是否启用随机延迟
- `RANDOM_RANGE` 定义随机范围倍数
- 实际延迟 = `DOWNLOAD_DELAY × random(RANDOM_RANGE[0], RANDOM_RANGE[1])`

---

### 3. 默认配置中的 RANDOMNESS

框架默认配置：
```python
RANDOMNESS = True  # 默认启用
```

这意味着：
- ✅ 默认启用随机延迟
- ✅ 如果不需要，需显式设置为 `False`

```python
# 关闭随机延迟
RANDOMNESS = False
```

---

### 4. RANDOM_RANGE 参数

**作用**：定义随机延迟的范围倍数

```python
RANDOM_RANGE = [0.5, 1.5]
# 实际延迟范围：DOWNLOAD_DELAY × 0.5 到 DOWNLOAD_DELAY × 1.5
# 例如 DOWNLOAD_DELAY=2.0，则延迟在 1.0s - 3.0s 之间
```

**注意**：实际随机延迟由 `DownloadDelayMiddleware` 控制，不是仅用于日志显示。

---

## 🎯 最佳实践

### ✅ 推荐做法

1. **小型项目**：只配置 `DOWNLOAD_DELAY`
   ```python
   DOWNLOAD_DELAY = 1.0
   ```

2. **中型项目**：添加域名级控制
   ```python
   DOWNLOAD_DELAY = 1.0
   DOWNLOAD_DELAY_OVERRIDES = {
       'example.com': {'delay': 2.0},
   }
   ```

3. **大型项目**：启用随机延迟
   ```python
   DOWNLOAD_DELAY = 1.0
   RANDOMNESS = True
   RANDOM_RANGE = [0.5, 1.5]
   ```

### ❌ 不推荐做法

1. **使用已废弃的 THROTTLE_* 参数**
   ```python
   # ❌ 错误：THROTTLE_* 参数已移除
   THROTTLE_DEFAULT_DELAY = 1.0
   THROTTLE_MAX_RATE = 5.0
   THROTTLE_AUTO_THROTTLE = True
   THROTTLE_DOMAIN_OVERRIDES = {...}
   
   # ✅ 正确：使用 DOWNLOAD_DELAY 相关参数
   DOWNLOAD_DELAY = 1.0
   DOWNLOAD_DELAY_OVERRIDES = {...}
   ```

2. **设置 DOWNLOAD_DELAY = 0 而不禁用中间件**
   ```python
   # ❌ 不推荐：虽然延迟为0，但中间件仍在运行
   DOWNLOAD_DELAY = 0
   
   # ✅ 正确：显式禁用中间件
   DOWNLOAD_DELAY_ENABLED = False
   ```

---

## 🔍 故障排查

### 问题 1：延迟不生效

**检查**：
```python
# 确保 DOWNLOAD_DELAY_ENABLED 为 True（默认就是）
DOWNLOAD_DELAY_ENABLED = True

# 检查 DOWNLOAD_DELAY 是否 > 0
DOWNLOAD_DELAY = 1.0  # 不能为 0 或 None

# 确保没有使用已废弃的配置
# THROTTLE_DEFAULT_DELAY = 1.0  # ← 已移除，不要使用
```

---

### 问题 2：RANDOMNESS 不工作

**原因**：可能是 RANDOMNESS 被禁用

**解决**：
```python
# 确保 RANDOMNESS 为 True
RANDOMNESS = True

# 检查 RANDOM_RANGE 是否合理
RANDOM_RANGE = [0.5, 1.5]  # 默认范围
```

---

### 问题 3：域名配置不生效

**检查**：
```python
# 确保域名格式正确
DOWNLOAD_DELAY_OVERRIDES = {
    'example.com': {'delay': 2.0},  # ✅ 正确
    # 'http://example.com': ...     # ❌ 错误：不要带协议
}
```

---

## 📝 总结

| 迁移项 | 状态 | 说明 |
|--------|------|------|
| **配置修改** | ✅ 不需要 | 旧配置继续有效 |
| **代码修改** | ✅ 不需要 | 自动使用新中间件 |
| **功能简化** | ✅ 更清晰 | 职责分离，延迟控制更专注 |
| **向后兼容** | ✅ 100% | 零迁移成本 |
| **文档更新** | ✅ 已完成 | 本指南 |

**结论**：您无需修改任何现有配置，`DownloadDelayMiddleware` 会自动兼容并保持功能！

**重要变更**：
- `ThrottleMiddleware` → `DownloadDelayMiddleware`（简化实现）
- `THROTTLE_*` 参数 → `DOWNLOAD_DELAY_*` 参数（统一命名）
- 并发控制 → 移至下载器层（职责分离）

---

## 🆘 获取帮助

- 📖 完整配置文档：[configuration.md](configuration.md)
- 💬 问题反馈：GitHub Issues
- 📧 技术支持：查看框架文档
