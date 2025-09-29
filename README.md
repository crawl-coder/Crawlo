# Crawlo 爬虫框架

Crawlo 是一个高性能、可扩展的 Python 爬虫框架，支持单机和分布式部署。

## 特性

- 高性能异步爬取
- 支持多种下载器 (aiohttp, httpx, curl-cffi)
- 内置数据清洗和验证
- 分布式爬取支持
- 灵活的中间件系统
- 强大的配置管理系统
- 详细的日志记录和监控
- Windows 和 Linux 兼容

## 安装

```bash
pip install crawlo
```

或者从源码安装：

```bash
git clone https://github.com/your-username/crawlo.git
cd crawlo
pip install -r requirements.txt
pip install .
```

## 快速开始

```python
from crawlo import Spider

class MySpider(Spider):
    name = 'example'
    
    def parse(self, response):
        # 解析逻辑
        pass

# 运行爬虫
# crawlo run example
```

## 日志系统

Crawlo 拥有一个功能强大的日志系统，支持多种配置选项：

### 基本配置

```python
from crawlo.logging import configure_logging, get_logger

# 配置日志系统
configure_logging(
    LOG_LEVEL='INFO',
    LOG_FILE='logs/app.log',
    LOG_MAX_BYTES=10*1024*1024,  # 10MB
    LOG_BACKUP_COUNT=5
)

# 获取logger
logger = get_logger('my_module')
logger.info('这是一条日志消息')
```

### 高级配置

```python
# 分别配置控制台和文件日志级别
configure_logging(
    LOG_LEVEL='INFO',
    LOG_CONSOLE_LEVEL='WARNING',  # 控制台只显示WARNING及以上级别
    LOG_FILE_LEVEL='DEBUG',       # 文件记录DEBUG及以上级别
    LOG_FILE='logs/app.log',
    LOG_INCLUDE_THREAD_ID=True,   # 包含线程ID
    LOG_INCLUDE_PROCESS_ID=True   # 包含进程ID
)

# 模块特定日志级别
configure_logging(
    LOG_LEVEL='WARNING',
    LOG_LEVELS={
        'my_module.debug': 'DEBUG',
        'my_module.info': 'INFO'
    }
)
```

### 性能监控

```python
from crawlo.logging import get_monitor

# 启用日志性能监控
monitor = get_monitor()
monitor.enable_monitoring()

# 获取性能报告
report = monitor.get_performance_report()
print(report)
```

### 日志采样

```python
from crawlo.logging import get_sampler

# 设置采样率（只记录30%的日志）
sampler = get_sampler()
sampler.set_sample_rate('my_module', 0.3)

# 设置速率限制（每秒最多100条日志）
sampler.set_rate_limit('my_module', 100)
```

## Windows 兼容性说明

在 Windows 系统上使用日志轮转功能时，可能会遇到文件锁定问题。为了解决这个问题，建议安装 `concurrent-log-handler` 库：

```bash
pip install concurrent-log-handler
```

Crawlo 框架会自动检测并使用这个库来提供更好的 Windows 兼容性。

如果未安装 `concurrent-log-handler`，在 Windows 上运行时可能会出现以下错误：
```
PermissionError: [WinError 32] 另一个程序正在使用此文件，进程无法访问。
```

## 文档

请查看 [文档](https://your-docs-url.com) 获取更多信息。

## 许可证

MIT