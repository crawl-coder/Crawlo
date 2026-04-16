# 🔄 下载延迟中间件迁移指南

## 📋 概述

`DownloadDelayMiddleware` 已与 `ThrottleMiddleware` 合并。现在 ThrottleMiddleware 同时支持**简单配置**和**高级配置**，提供更强大的功能。

---

## ✅ 参数兼容性

### 统一使用的参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `DOWNLOAD_DELAY` | float | `0.5` | **统一的延迟配置**（秒） |
| `RANDOMNESS` | bool | `True` | 是否启用随机延迟/智能调节 |
| `RANDOM_RANGE` | list | `[0.5, 1.5]` | 随机延迟范围倍数（仅用于日志） |

### 高级参数（可选）

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `THROTTLE_ENABLED` | bool | `True` | 是否启用限流中间件 |
| `THROTTLE_MAX_RATE` | float | `None` | 最大请求速率（QPS） |
| `THROTTLE_AUTO_THROTTLE` | bool | `False` | 是否启用自动调节 |
| `THROTTLE_DOMAIN_OVERRIDES` | dict | `{}` | 域名级特定配置 |

> ⚠️ **注意**：`THROTTLE_DEFAULT_DELAY` 已移除，统一使用 `DOWNLOAD_DELAY`

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
- ✅ 自动使用 ThrottleMiddleware
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
THROTTLE_DOMAIN_OVERRIDES = {
    'example.com': {
        'delay': 2.0,  # 慢速网站，2秒延迟
    },
    'api.example.com': {
        'delay': 0.1,      # API 接口，快速
        'max_rate': 10,    # 最大 10 QPS
    },
    'slow-site.org': {
        'delay': 3.0,      # 非常慢的网站
        'max_concurrent': 2,  # 最多 2 个并发
    },
}
```

**效果**：
- ✅ 不同域名不同延迟
- ✅ 支持 QPS 限制
- ✅ 支持并发控制

---

### 场景 3：智能自适应调节（大型项目）✅ 推荐

**适用场景**：
- 大规模爬虫
- 目标网站性能波动
- 需要自动适应

**配置示例**：

```python
# settings.py

DOWNLOAD_DELAY = 1.0
THROTTLE_AUTO_THROTTLE = True  # 启用智能调节

# 可选：设置最大速率
THROTTLE_MAX_RATE = 5.0  # 最大 5 QPS
```

**智能调节原理**：
- 监控响应时间
- 响应慢 → 自动增加延迟
- 响应快 → 自动降低延迟
- 始终保持在最优状态

---

### 场景 4：直接使用高级配置（可选）

如果你不需要 `DOWNLOAD_DELAY` 的语义，可以直接配置高级功能：

```python
# settings.py

# 基础延迟
DOWNLOAD_DELAY = 1.0

# 高级功能
THROTTLE_AUTO_THROTTLE = True
THROTTLE_MAX_RATE = 10.0

THROTTLE_DOMAIN_OVERRIDES = {
    'example.com': {'delay': 2.0},
}
```

**效果**：
- ✅ 完整的限流功能
- ✅ 适合大型项目
- ✅ 统一的配置入口

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
- ✅ 自动使用 ThrottleMiddleware
- ✅ RANDOMNESS=True 自动启用智能调节

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
    'THROTTLE_DOMAIN_OVERRIDES': {
        'fast-api.com': {
            'delay': 0.1,
            'max_rate': 20,
        },
        'slow-site.com': {
            'delay': 3.0,
            'max_concurrent': 2,
        },
    },
}
```

**提升**：
- ✅ 快速 API：0.1s 延迟，20 QPS
- ✅ 慢速网站：3s 延迟，2 并发
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

**新配置**（智能调节）：

```python
custom_settings = {
    'DOWNLOAD_DELAY': 2.0,
    'RANDOMNESS': True,
    
    # 新增：智能调节（可选）
    'THROTTLE_AUTO_THROTTLE': True,
    'THROTTLE_MAX_RATE': 5.0,
}
```

**提升**：
- ✅ 随机延迟：1-3 秒
- ✅ 智能调节：根据响应时间动态调整
- ✅ QPS 限制：最大 5 请求/秒

---

## 📊 功能对比

| 功能 | DownloadDelayMiddleware | ThrottleMiddleware | 说明 |
|------|------------------------|-------------------|------|
| **固定延迟** | ✅ | ✅ | 每个请求固定间隔 |
| **随机延迟** | ✅ | ✅ | RANDOMNESS 转换为 auto_throttle |
| **域名级控制** | ❌ | ✅ | 不同域名不同延迟 |
| **QPS 限制** | ❌ | ✅ | 最大请求速率 |
| **并发控制** | ❌ | ✅ | 每域名最大并发 |
| **智能调节** | ❌ | ✅ | 根据响应时间调整 |
| **突发控制** | ❌ | ✅ | 支持 burst_size |
| **统计记录** | ✅ 基础 | ✅ 完整 | 更详细的统计 |

---

## ⚠️ 注意事项

### 1. 统一使用 DOWNLOAD_DELAY

**旧版**（已废弃）：
```python
# ❌ 不要使用
THROTTLE_DEFAULT_DELAY = 1.0
```

**新版**（统一配置）：
```python
# ✅ 正确：统一使用 DOWNLOAD_DELAY
DOWNLOAD_DELAY = 1.0
```

---

---

### 2. RANDOMNESS 的转换

**旧行为**（DownloadDelayMiddleware）：
```python
RANDOMNESS = True
RANDOM_RANGE = [0.5, 1.5]
# 效果：延迟在 0.25s - 0.75s 之间随机
```

**新行为**（ThrottleMiddleware）：
```python
RANDOMNESS = True
# 效果：启用 auto_throttle（智能调节）
# RANDOM_RANGE 仅在日志中显示，不影响实际功能
```

**建议**：
- 如果只需要随机延迟，保持 `RANDOMNESS = True` 即可
- 如果需要更智能的控制，添加 `THROTTLE_AUTO_THROTTLE = True`

---

### 3. 默认配置中的 RANDOMNESS

框架默认配置：
```python
RANDOMNESS = True  # 默认启用
```

这意味着：
- ✅ 默认启用智能调节
- ✅ 如果不需要，需显式设置为 `False`

```python
# 关闭随机延迟/智能调节
RANDOMNESS = False
THROTTLE_AUTO_THROTTLE = False
```

---

### 4. RANDOM_RANGE 参数

**状态**：⚠️ 仅用于日志显示

```python
RANDOM_RANGE = [0.5, 1.5]
# 日志输出：Using simple delay configuration: 2.0s (range: 1.00s - 3.00s)
```

**不影响实际功能**，仅用于提示信息。实际的随机延迟由 ThrottleMiddleware 的令牌桶算法控制。

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
   THROTTLE_DOMAIN_OVERRIDES = {...}
   ```

3. **大型项目**：启用智能调节
   ```python
   DOWNLOAD_DELAY = 1.0
   THROTTLE_AUTO_THROTTLE = True
   THROTTLE_MAX_RATE = 10.0
   ```

### ❌ 不推荐做法

1. **使用已废弃的 THROTTLE_DEFAULT_DELAY**
   ```python
   # ❌ 错误：THROTTLE_DEFAULT_DELAY 已移除
   THROTTLE_DEFAULT_DELAY = 1.0
   
   # ✅ 正确：使用 DOWNLOAD_DELAY
   DOWNLOAD_DELAY = 1.0
   ```

2. **依赖 RANDOM_RANGE 控制随机范围**
   ```python
   # ❌ RANDOM_RANGE 不再控制实际随机范围
   RANDOMNESS = True
   RANDOM_RANGE = [0.1, 2.0]  # ← 仅用于日志显示
   ```

---

## 🔍 故障排查

### 问题 1：延迟不生效

**检查**：
```python
# 确保 THROTTLE_ENABLED 为 True（默认就是）
THROTTLE_ENABLED = True

# 检查 DOWNLOAD_DELAY 是否 > 0
DOWNLOAD_DELAY = 1.0  # 不能为 0 或 None

# 确保没有使用已废弃的配置
# THROTTLE_DEFAULT_DELAY = 1.0  # ← 已移除，不要使用
```

---

### 问题 2：RANDOMNESS 不工作

**原因**：RANDOMNESS 转换为 auto_throttle

**解决**：
```python
# 方式 1：保持 RANDOMNESS
RANDOMNESS = True

# 方式 2：显式启用 auto_throttle
THROTTLE_AUTO_THROTTLE = True
```

---

### 问题 3：域名配置不生效

**检查**：
```python
# 确保域名格式正确
THROTTLE_DOMAIN_OVERRIDES = {
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
| **功能增强** | ✅ 自动获得 | 域名级控制、智能调节 |
| **向后兼容** | ✅ 100% | 零迁移成本 |
| **文档更新** | ✅ 已完成 | 本指南 |

**结论**：您无需修改任何现有配置，ThrottleMiddleware 会自动兼容并增强功能！

---

## 🆘 获取帮助

- 📖 完整配置文档：[configuration.md](configuration.md)
- 💬 问题反馈：GitHub Issues
- 📧 技术支持：查看框架文档
