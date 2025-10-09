# BloomFilter

BloomFilter 是 Crawlo 框架中基于布隆过滤器的高效去重组件，适用于处理大规模 URL 的场景。

## 概述

BloomFilter 使用布隆过滤器算法实现请求去重，具有极低的内存使用和快速的查询速度，特别适合处理超大规模的爬取任务。

### 核心特性

1. **极低内存使用** - 相比其他过滤器内存使用量极小
2. **快速查询** - O(k) 时间复杂度的查询速度
3. **可配置精度** - 支持配置误判率
4. **大规模支持** - 支持处理数亿级别的 URL

## 配置选项

BloomFilter 的行为可以通过以下配置项进行调整：

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| BLOOM_FILTER_CAPACITY | int | 1000000 | 过滤器容量 |
| BLOOM_FILTER_ERROR_RATE | float | 0.001 | 误判率 |
| BLOOM_FILTER_PERSISTENCE | bool | True | 是否持久化 |
| BLOOM_FILTER_FILENAME | str | 'bloom_filter.dat' | 持久化文件名 |

## 使用示例

### 基本使用

```python
from crawlo.config import CrawloConfig

# 配置使用 Bloom 过滤器
config = CrawloConfig.standalone(
    filter_type='bloom',
    bloom_filter_capacity=10000000,  # 1000万容量
    bloom_filter_error_rate=0.0001   # 0.01% 误判率
)
```

### 高级配置

```python
# 配置持久化
config = CrawloConfig.standalone(
    filter_type='bloom',
    bloom_filter_persistence=True,
    bloom_filter_filename='my_filter.dat'
)
```

## 性能特点

### 内存使用对比

| 过滤器类型 | 100万URL内存使用 | 1亿URL内存使用 |
|------------|----------------|---------------|
| MemoryFilter | 100MB | 10GB |
| AioRedisFilter | 50MB | 5GB |
| BloomFilter | 1MB | 100MB |

### 查询性能

```python
# BloomFilter 查询性能
import time

# 测试查询性能
start_time = time.time()
for i in range(1000000):
    filter.check_duplicate(Request(url=f"http://example.com/{i}"))
end_time = time.time()

print(f"BloomFilter 查询100万次耗时: {end_time - start_time:.2f}秒")
# 通常小于1秒
```

## 误判率管理

### 误判率配置

```python
# 不同误判率的内存使用
config_low_error = CrawloConfig.standalone(
    bloom_filter_capacity=1000000,
    bloom_filter_error_rate=0.0001  # 0.01% 误判率，内存使用约 2MB
)

config_high_error = CrawloConfig.standalone(
    bloom_filter_capacity=1000000,
    bloom_filter_error_rate=0.01   # 1% 误判率，内存使用约 1MB
)
```

### 误判处理

```python
class BloomSpider(Spider):
    def parse(self, response):
        # 处理可能的误判
        if self.is_likely_duplicate(response.url):
            # 可能是误判，进行二次验证
            if not self.secondary_check(response.url):
                return
        
        # 正常处理逻辑
        yield Item(data=response.text)
    
    def is_likely_duplicate(self, url):
        # 基于业务逻辑判断是否可能是误判
        return False
    
    def secondary_check(self, url):
        # 二次验证逻辑
        return True
```

## 最佳实践

### 1. 容量规划

```python
# 根据预期URL数量规划容量
expected_urls = 50000000  # 预期5000万URL
config = CrawloConfig.standalone(
    filter_type='bloom',
    bloom_filter_capacity=int(expected_urls * 1.2),  # 预留20%空间
    bloom_filter_error_rate=0.001
)
```

### 2. 误判率选择

```python
# 根据业务需求选择误判率
# 对准确性要求高的场景
config_strict = CrawloConfig.standalone(
    bloom_filter_error_rate=0.0001  # 0.01% 误判率
)

# 对性能要求高的场景
config_performance = CrawloConfig.standalone(
    bloom_filter_error_rate=0.01    # 1% 误判率
)
```

### 3. 持久化配置

```python
# 生产环境启用持久化
config = CrawloConfig.standalone(
    filter_type='bloom',
    bloom_filter_persistence=True,
    bloom_filter_filename=f'bloom_filter_{int(time.time())}.dat'
)

# 定期备份过滤器
import shutil
shutil.copy('bloom_filter.dat', f'backup/bloom_filter_{int(time.time())}.dat')
```

## 故障排除

### 常见问题

1. **内存不足**
   ```python
   # 问题: MemoryError
   # 解决: 降低容量或提高误判率
   config = CrawloConfig.standalone(
       bloom_filter_capacity=5000000,   # 降低容量
       bloom_filter_error_rate=0.01     # 提高误判率
   )
   ```

2. **误判率过高**
   ```python
   # 问题: 过多误判导致数据丢失
   # 解决: 降低误判率或添加二次验证
   config = CrawloConfig.standalone(
       bloom_filter_error_rate=0.0001   # 降低误判率
   )
   ```

3. **持久化文件损坏**
   ```python
   # 问题: 持久化文件损坏
   # 解决: 删除损坏文件重新创建
   import os
   if os.path.exists('bloom_filter.dat'):
       os.remove('bloom_filter.dat')
   # 重启爬虫会自动创建新文件
   ```

### 性能调优

```python
# 监控 BloomFilter 性能
class PerformanceMonitor:
    def __init__(self):
        self.check_count = 0
        self.duplicate_count = 0
    
    def monitor_filter(self, filter):
        # 监控过滤器性能
        stats = filter.get_stats()
        self.logger.info(f"过滤器统计: {stats}")
        
        # 计算实际误判率
        if self.check_count > 0:
            actual_error_rate = self.duplicate_count / self.check_count
            self.logger.info(f"实际误判率: {actual_error_rate:.4f}")
```