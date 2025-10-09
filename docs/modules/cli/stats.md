# stats 命令

`stats` 命令用于查看爬虫运行统计信息，帮助监控爬虫性能和状态。

## 命令语法

```bash
crawlo stats [spider_name] [options]
```

### 参数说明

- `spider_name` - 要查看统计信息的爬虫名称（可选，不指定则显示所有爬虫）
- `options` - 可选参数

## 使用示例

### 基本使用

```bash
# 查看所有爬虫统计信息
crawlo stats

# 查看特定爬虫统计信息
crawlo stats myspider

# 实时监控统计信息
crawlo stats --follow
```

### 详细统计

```bash
# 显示详细统计信息
crawlo stats --verbose

# 以 JSON 格式输出
crawlo stats --format json

# 保存统计信息到文件
crawlo stats --output stats.json
```

## 统计信息类型

### 1. 基础统计

```bash
# 基础统计信息
请求总数: 1000
成功请求数: 950
失败请求数: 50
数据项数: 800
运行时间: 02:30:15
```

### 2. 性能统计

```bash
# 性能相关统计
平均响应时间: 1.25 秒
请求速率: 25.5 请求/秒
数据项速率: 20.3 项/秒
内存使用: 125.5 MB
CPU 使用率: 45.2%
```

### 3. 错误统计

```bash
# 错误相关统计
HTTP 错误:
  - 404: 20 次
  - 500: 15 次
  - 403: 10 次
  - 超时: 5 次
重试统计:
  - 重试次数: 100 次
  - 成功重试: 85 次
```

## 配置选项

`stats` 命令支持以下选项：

| 选项 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| --project-dir | string | 当前目录 | 项目目录路径 |
| --format | string | 'table' | 输出格式 (table, json, csv) |
| --verbose | flag | - | 显示详细信息 |
| --follow | flag | - | 实时监控统计信息 |
| --interval | int | 5 | 实时监控间隔（秒） |
| --output | string | None | 输出文件路径 |
| --reset | flag | - | 重置统计信息 |
| --history | flag | - | 显示历史统计信息 |
| --limit | int | 10 | 历史记录限制 |

## 输出格式

### 表格格式（默认）

```bash
$ crawlo stats myspider
爬虫统计信息: myspider
+------------------+-------------------+
| 统计项           | 值                |
+------------------+-------------------+
| 请求总数         | 1000              |
| 成功请求数       | 950               |
| 失败请求数       | 50                |
| 数据项数         | 800               |
| 运行时间         | 02:30:15          |
| 平均响应时间     | 1.25 秒           |
| 请求速率         | 25.5 请求/秒      |
| 内存使用         | 125.5 MB          |
+------------------+-------------------+
```

### JSON 格式

```bash
$ crawlo stats myspider --format json
{
  "spider": "myspider",
  "timestamp": "2023-01-01T12:00:00Z",
  "basic_stats": {
    "total_requests": 1000,
    "successful_requests": 950,
    "failed_requests": 50,
    "items_scraped": 800,
    "runtime": "02:30:15"
  },
  "performance_stats": {
    "avg_response_time": 1.25,
    "request_rate": 25.5,
    "item_rate": 20.3,
    "memory_usage": 125.5,
    "cpu_usage": 45.2
  },
  "error_stats": {
    "http_errors": {
      "404": 20,
      "500": 15,
      "403": 10
    },
    "timeouts": 5,
    "retries": {
      "total": 100,
      "successful": 85
    }
  }
}
```

### CSV 格式

```bash
$ crawlo stats --format csv
统计项,值
请求总数,1000
成功请求数,950
失败请求数,50
数据项数,800
运行时间,02:30:15
平均响应时间,1.25 秒
请求速率,25.5 请求/秒
内存使用,125.5 MB
```

## 实时监控

### 实时统计

```bash
# 实时监控统计信息
crawlo stats myspider --follow

# 自定义监控间隔
crawlo stats myspider --follow --interval 10
```

### 监控输出示例

```bash
$ crawlo stats myspider --follow --interval 5
爬虫统计信息: myspider (实时监控)
更新时间: 2023-01-01 12:00:00
请求总数: 1000 (+5)
成功请求数: 950 (+3)
失败请求数: 50 (+2)
数据项数: 800 (+4)
平均响应时间: 1.25 秒
请求速率: 25.5 请求/秒
内存使用: 125.5 MB

更新时间: 2023-01-01 12:00:05
请求总数: 1025 (+25)
成功请求数: 970 (+20)
失败请求数: 55 (+5)
数据项数: 820 (+20)
平均响应时间: 1.30 秒
请求速率: 26.8 请求/秒
内存使用: 128.2 MB
```

## 历史统计

### 查看历史记录

```bash
# 查看历史统计信息
crawlo stats myspider --history

# 限制历史记录数量
crawlo stats myspider --history --limit 20
```

### 历史统计输出

```bash
$ crawlo stats myspider --history --limit 3
历史统计信息: myspider
+----+---------------------+--------------+----------------+--------------+
| 序号 | 时间                | 请求总数     | 成功请求数     | 数据项数     |
+----+---------------------+--------------+----------------+--------------+
| 1  | 2023-01-01 10:00:00 | 500          | 475            | 400          |
| 2  | 2023-01-01 11:00:00 | 750          | 710            | 600          |
| 3  | 2023-01-01 12:00:00 | 1000         | 950            | 800          |
+----+---------------------+--------------+----------------+--------------+
```

## 统计信息重置

### 重置统计

```bash
# 重置统计信息
crawlo stats myspider --reset

# 重置所有爬虫统计信息
crawlo stats --reset
```

## 最佳实践

### 1. 性能监控

```bash
# 定期监控性能
crawlo stats myspider --format json --output stats_$(date +%s).json

# 设置性能告警
crawlo stats myspider --verbose | grep "请求速率" | awk '{if ($3 < 10) print "警告: 请求速率过低"}'
```

### 2. 错误分析

```bash
# 分析错误统计
crawlo stats myspider --format json | jq '.error_stats'

# 监控特定错误类型
crawlo stats myspider --follow | grep "404"
```

### 3. 资源监控

```bash
# 监控资源使用
crawlo stats myspider --follow --interval 30

# 设置资源使用告警
crawlo stats myspider --verbose | grep "内存使用" | awk '{if ($3 > 500) print "警告: 内存使用过高"}'
```

### 4. 自动化监控

```bash
# 在脚本中使用统计信息
#!/bin/bash
stats=$(crawlo stats myspider --format json)
requests=$(echo $stats | jq '.basic_stats.total_requests')
if [ $requests -gt 10000 ]; then
    echo "请求量达到阈值，准备重启爬虫"
    # 重启逻辑
fi
```

## 自定义统计

### 添加自定义统计项

```python
# custom_stats.py
from crawlo.stats import BaseStatsCollector

class CustomStatsCollector(BaseStatsCollector):
    def collect(self, spider):
        """收集自定义统计信息"""
        stats = super().collect(spider)
        
        # 添加自定义统计项
        stats['custom_metric'] = self.calculate_custom_metric()
        stats['business_stats'] = self.get_business_stats()
        
        return stats
    
    def calculate_custom_metric(self):
        # 自定义指标计算逻辑
        return 42
    
    def get_business_stats(self):
        # 业务相关统计
        return {'processed_orders': 100, 'revenue': 5000}
```

### 注册自定义统计收集器

```python
# settings.py
STATS_COLLECTORS = [
    'myproject.stats.CustomStatsCollector'
]
```

## 故障排除

### 常见问题

1. **统计信息为空**
   ```bash
   # 问题: No statistics found
   # 解决: 检查爬虫是否正在运行
   crawlo list  # 确认爬虫存在
   ps aux | grep crawlo  # 检查进程
   ```

2. **权限问题**
   ```bash
   # 问题: Permission denied
   # 解决: 检查统计文件权限
   ls -la ~/.crawlo/stats/
   chmod 644 ~/.crawlo/stats/*
   ```

3. **格式错误**
   ```bash
   # 问题: Invalid output format
   # 解决: 检查格式参数
   crawlo stats --format table  # 使用支持的格式
   ```

### 调试技巧

```bash
# 显示详细统计信息
crawlo stats myspider --verbose

# 检查统计文件
cat ~/.crawlo/stats/myspider.json

# 实时监控调试
crawlo stats myspider --follow --verbose --interval 1
```