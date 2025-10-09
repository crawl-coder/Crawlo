# run 命令

`run` 命令用于运行指定的爬虫，是执行爬虫任务的主要命令。

## 命令语法

```bash
crawlo run <spider_name> [options]
```

### 参数说明

- `spider_name` - 要运行的爬虫名称（必需）
- `options` - 可选参数

## 使用示例

### 基本使用

```bash
# 运行爬虫
crawlo run myspider

# 指定配置文件
crawlo run myspider --config settings.py

# 设置日志级别
crawlo run myspider --log-level DEBUG
```

### 高级配置

```bash
# 设置并发数
crawlo run myspider --concurrency 32

# 设置下载延迟
crawlo run myspider --download-delay 1.0

# 设置超时时间
crawlo run myspider --download-timeout 60
```

## 配置选项

`run` 命令支持以下选项：

| 选项 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| --config | string | 'settings.py' | 配置文件路径 |
| --log-level | string | 'INFO' | 日志级别 (DEBUG, INFO, WARNING, ERROR) |
| --log-file | string | None | 日志文件路径 |
| --concurrency | int | 16 | 并发请求数 |
| --download-delay | float | 0.5 | 下载延迟（秒） |
| --download-timeout | int | 30 | 下载超时时间（秒） |
| --max-retry-times | int | 3 | 最大重试次数 |
| --output-format | string | 'json' | 输出格式 (json, csv, xml) |
| --output-file | string | None | 输出文件路径 |
| --stats | flag | - | 显示统计信息 |
| --dry-run | flag | - | 预演模式，不实际执行请求 |

## 环境变量

`run` 命令支持以下环境变量：

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| CRAWLO_CONFIG | 'settings.py' | 配置文件路径 |
| CRAWLO_LOG_LEVEL | 'INFO' | 日志级别 |
| CRAWLO_CONCURRENCY | 16 | 并发请求数 |
| CRAWLO_DOWNLOAD_DELAY | 0.5 | 下载延迟 |
| CRAWLO_PROJECT_DIR | 当前目录 | 项目目录路径 |

## 使用场景

### 1. 开发测试

```bash
# 开发阶段运行爬虫
crawlo run myspider --log-level DEBUG --concurrency 1

# 测试特定功能
crawlo run myspider --dry-run --stats
```

### 2. 生产部署

```bash
# 生产环境运行爬虫
crawlo run myspider --config production_settings.py --log-file logs/myspider.log

# 高性能模式
crawlo run myspider --concurrency 50 --download-delay 0.1
```

### 3. 定时任务

```bash
# 在 crontab 中使用
0 2 * * * cd /path/to/project && crawlo run myspider --config daily_settings.py

# 带输出的定时任务
0 3 * * * cd /path/to/project && crawlo run myspider --output-file data/$(date +\%Y-\%m-\%d).json
```

## 输出格式

### JSON 格式

```bash
# 输出到 JSON 文件
crawlo run myspider --output-format json --output-file output.json
```

### CSV 格式

```bash
# 输出到 CSV 文件
crawlo run myspider --output-format csv --output-file output.csv
```

### 自定义格式

```bash
# 使用自定义管道
crawlo run myspider --pipeline myproject.pipelines.CustomPipeline
```

## 监控和统计

### 实时统计

```bash
# 显示实时统计信息
crawlo run myspider --stats

# 定期输出统计信息
crawlo run myspider --stats-interval 30
```

### 性能监控

```bash
# 启用性能监控
crawlo run myspider --monitor-performance

# 设置内存使用警告阈值
crawlo run myspider --memory-warning-threshold 500
```

## 最佳实践

### 1. 配置管理

```bash
# 不同环境使用不同配置
crawlo run myspider --config settings_dev.py      # 开发环境
crawlo run myspider --config settings_test.py     # 测试环境
crawlo run myspider --config settings_prod.py     # 生产环境
```

### 2. 日志管理

```bash
# 合理配置日志
crawlo run myspider --log-level INFO --log-file logs/myspider.log --log-max-bytes 10485760 --log-backup-count 5
```

### 3. 资源控制

```bash
# 根据目标网站调整资源
crawlo run myspider --concurrency 5 --download-delay 2.0      # 对敏感网站友好
crawlo run myspider --concurrency 50 --download-delay 0.1     # 对高性能网站
```

### 4. 错误处理

```bash
# 设置重试机制
crawlo run myspider --max-retry-times 5 --retry-http-codes 500,502,503,504,429
```

## 故障排除

### 常见问题

1. **爬虫未找到**
   ```bash
   # 错误: Spider not found
   # 解决: 检查爬虫名称和项目结构
   crawlo list  # 查看可用爬虫
   ```

2. **配置文件错误**
   ```bash
   # 错误: Configuration error
   # 解决: 检查配置文件语法
   python -m py_compile settings.py
   ```

3. **权限错误**
   ```bash
   # 错误: Permission denied
   # 解决: 检查文件权限
   chmod 644 settings.py
   ```

### 调试技巧

```bash
# 启用详细日志
crawlo run myspider --log-level DEBUG

# 预演模式检查配置
crawlo run myspider --dry-run --stats

# 单并发调试
crawlo run myspider --concurrency 1 --log-level DEBUG
```

## 命令行参数

`crawlo run` 命令支持以下参数：

- `<spider_name>` - 要运行的爬虫名称，使用 `all` 运行所有爬虫
- `--json` - 以 JSON 格式输出结果
- `--no-stats` - 不记录统计信息
- `--log-level LEVEL` - 设置日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `--concurrency NUM` - 设置并发数

## 使用示例

```bash
# 运行指定爬虫
crawlo run myspider

# 运行所有爬虫
crawlo run all

# 以JSON格式输出结果
crawlo run myspider --json

# 设置日志级别为DEBUG
crawlo run myspider --log-level DEBUG

# 设置并发数为32
crawlo run myspider --concurrency 32

# 组合使用多个参数
crawlo run myspider --log-level DEBUG --concurrency 32 --json