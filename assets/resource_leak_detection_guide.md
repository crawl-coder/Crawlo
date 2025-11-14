# Crawlo框架资源泄漏检测指南

## 概述

Crawlo框架提供了一套完整的资源泄漏检测机制，帮助开发者识别和解决爬虫运行过程中可能出现的资源泄漏问题。本指南将详细介绍如何使用这些工具来检测和预防资源泄漏。

## 核心组件

### 1. ResourceManager（资源管理器）
统一管理所有可清理资源，确保资源正确释放。

### 2. LeakDetector（泄漏检测器）
监控资源使用情况，检测潜在的资源泄漏。

### 3. ResourceLeakMonitor（资源泄漏监控器）
提供装饰器和API，方便在代码中集成资源泄漏监控。

## 使用方法

### 1. 自动监控爬虫运行

Crawlo框架已自动集成资源泄漏监控，每次运行爬虫时都会自动记录资源使用情况。

### 2. 手动添加监控

在代码中手动添加资源泄漏监控：

```python
from crawlo.utils.resource_leak_monitor import monitor_crawler

@monitor_crawler("my_spider")
async def run_my_spider():
    # 爬虫逻辑
    pass
```

### 3. 使用命令行工具检测

使用专门的命令行工具检测资源泄漏：

```bash
python -m crawlo.tools.leak_check myproject.spiders MySpider --duration 600 --interval 60
```

### 4. 编写自定义检测逻辑

```python
from crawlo.utils.leak_detector import get_leak_detector
from crawlo.utils.resource_manager import get_resource_manager

# 获取检测器实例
leak_detector = get_leak_detector("my_detector")
resource_manager = get_resource_manager("my_manager")

# 设置基线
leak_detector.set_baseline("start")

# 执行操作
# ... 你的代码 ...

# 记录快照
leak_detector.snapshot("after_operation")

# 分析结果
analysis = leak_detector.analyze()
print(analysis)
```

## 检测场景覆盖

### 1. 内存泄漏检测
- 监控内存使用量变化
- 分析对象数量增长趋势
- 识别特定对象类型的异常增长

### 2. 文件句柄泄漏检测
- 监控打开的文件句柄数量
- 检测未正确关闭的文件

### 3. 网络连接泄漏检测
- 监控网络连接状态
- 检测未正确关闭的网络连接

### 4. 线程/协程泄漏检测
- 监控线程数量变化
- 检测未正确结束的线程或协程

### 5. 数据库连接泄漏检测
- 监控数据库连接池使用情况
- 检测未正确释放的数据库连接

### 6. Redis连接泄漏检测
- 监控Redis连接池使用情况
- 检测未正确释放的Redis连接

## 最佳实践

### 1. 定期检测
建议在开发阶段和生产环境定期运行资源泄漏检测。

### 2. 长时间运行测试
对于长时间运行的爬虫，应进行专门的资源泄漏测试。

### 3. 多实例运行测试
在多实例并发运行场景下测试资源泄漏情况。

### 4. 集成到CI/CD流程
将资源泄漏检测集成到持续集成流程中，确保每次代码变更都不会引入新的资源泄漏问题。

## 常见问题和解决方案

### 1. 内存持续增长
可能原因：
- 对象未正确释放
- 缓存未清理
- 循环引用

解决方案：
- 检查对象生命周期管理
- 实现正确的清理逻辑
- 使用弱引用避免循环引用

### 2. 文件句柄未释放
可能原因：
- 文件未正确关闭
- 异常处理不完整

解决方案：
- 使用上下文管理器确保文件正确关闭
- 完善异常处理逻辑

### 3. 网络连接未释放
可能原因：
- HTTP会话未正确关闭
- 连接池配置不当

解决方案：
- 确保HTTP会话正确关闭
- 合理配置连接池参数

## 报告解读

泄漏检测报告包含以下关键信息：

1. **资源变化统计**：内存、对象数、文件句柄、线程等的变化情况
2. **潜在泄漏点**：识别出的可能泄漏资源类型和严重程度
3. **对象类型变化**：分析对象类型的增长情况
4. **趋势分析**：资源使用趋势图

通过这些信息，开发者可以快速定位和解决资源泄漏问题。