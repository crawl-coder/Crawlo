#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
大规模爬虫配置助手
提供针对上万请求场景的优化配置
"""
from typing import Dict, Any

from crawlo.utils.queue_helper import QueueHelper


class LargeScaleConfig:
    """大规模爬虫配置类"""
    
    @staticmethod
    def conservative_config(concurrency: int = 8) -> Dict[str, Any]:
        """
        保守配置 - 适用于资源有限的环境
        
        特点：
        - 较小的队列容量
        - 较低的并发数
        - 较长的延迟
        """
        config = QueueHelper.use_redis_queue(
            queue_name="crawlo:conservative",
            max_retries=3,
            timeout=300
        )
        
        config.update({
            # 并发控制
            'CONCURRENCY': concurrency,
            'SCHEDULER_MAX_QUEUE_SIZE': concurrency * 10,  # 队列容量为并发数的10倍
            'MAX_RUNNING_SPIDERS': 1,
            
            # 请求控制
            'DOWNLOAD_DELAY': 0.2,
            'RANDOMNESS': True,
            'RANDOM_RANGE': (0.8, 1.5),
            
            # 内存控制
            'DOWNLOAD_MAXSIZE': 5 * 1024 * 1024,  # 5MB
            'CONNECTION_POOL_LIMIT': concurrency * 2,
            
            # 重试策略
            'MAX_RETRY_TIMES': 2,
            
            # 使用增强引擎
            'ENGINE_CLASS': 'crawlo.core.enhanced_engine.EnhancedEngine'
        })
        
        return config
    
    @staticmethod
    def balanced_config(concurrency: int = 16) -> Dict[str, Any]:
        """
        平衡配置 - 适用于一般生产环境
        
        特点：
        - 中等的队列容量
        - 平衡的并发数
        - 适中的延迟
        """
        config = QueueHelper.use_redis_queue(
            queue_name="crawlo:balanced",
            max_retries=5,
            timeout=600
        )
        
        config.update({
            # 并发控制
            'CONCURRENCY': concurrency,
            'SCHEDULER_MAX_QUEUE_SIZE': concurrency * 15,
            'MAX_RUNNING_SPIDERS': 2,
            
            # 请求控制
            'DOWNLOAD_DELAY': 0.1,
            'RANDOMNESS': True,
            'RANDOM_RANGE': (0.5, 1.2),
            
            # 内存控制
            'DOWNLOAD_MAXSIZE': 10 * 1024 * 1024,  # 10MB
            'CONNECTION_POOL_LIMIT': concurrency * 3,
            
            # 重试策略
            'MAX_RETRY_TIMES': 3,
            
            # 使用增强引擎
            'ENGINE_CLASS': 'crawlo.core.enhanced_engine.EnhancedEngine'
        })
        
        return config
    
    @staticmethod
    def aggressive_config(concurrency: int = 32) -> Dict[str, Any]:
        """
        激进配置 - 适用于高性能环境
        
        特点：
        - 大的队列容量
        - 高并发数
        - 较短的延迟
        """
        config = QueueHelper.use_redis_queue(
            queue_name="crawlo:aggressive",
            max_retries=10,
            timeout=900
        )
        
        config.update({
            # 并发控制
            'CONCURRENCY': concurrency,
            'SCHEDULER_MAX_QUEUE_SIZE': concurrency * 20,
            'MAX_RUNNING_SPIDERS': 3,
            
            # 请求控制
            'DOWNLOAD_DELAY': 0.05,
            'RANDOMNESS': True,
            'RANDOM_RANGE': (0.3, 1.0),
            
            # 内存控制
            'DOWNLOAD_MAXSIZE': 20 * 1024 * 1024,  # 20MB
            'CONNECTION_POOL_LIMIT': concurrency * 4,
            
            # 重试策略
            'MAX_RETRY_TIMES': 5,
            
            # 使用增强引擎
            'ENGINE_CLASS': 'crawlo.core.enhanced_engine.EnhancedEngine'
        })
        
        return config
    
    @staticmethod
    def memory_optimized_config(concurrency: int = 12) -> Dict[str, Any]:
        """
        内存优化配置 - 适用于大规模但内存受限的场景
        
        特点：
        - 小队列，快速流转
        - 严格的内存控制
        - 使用Redis减少内存压力
        """
        config = QueueHelper.use_redis_queue(
            queue_name="crawlo:memory_optimized",
            max_retries=3,
            timeout=300
        )
        
        config.update({
            # 并发控制
            'CONCURRENCY': concurrency,
            'SCHEDULER_MAX_QUEUE_SIZE': concurrency * 5,  # 小队列
            'MAX_RUNNING_SPIDERS': 1,
            
            # 请求控制
            'DOWNLOAD_DELAY': 0.1,
            'RANDOMNESS': False,  # 减少随机性降低内存使用
            
            # 严格的内存控制
            'DOWNLOAD_MAXSIZE': 2 * 1024 * 1024,  # 2MB
            'DOWNLOAD_WARN_SIZE': 512 * 1024,     # 512KB
            'CONNECTION_POOL_LIMIT': concurrency,
            
            # 重试策略
            'MAX_RETRY_TIMES': 2,
            
            # 使用增强引擎
            'ENGINE_CLASS': 'crawlo.core.enhanced_engine.EnhancedEngine'
        })
        
        return config


def apply_large_scale_config(settings_dict: Dict[str, Any], config_type: str = "balanced", concurrency: int = None):
    """
    应用大规模配置
    
    Args:
        settings_dict: 设置字典
        config_type: 配置类型 ("conservative", "balanced", "aggressive", "memory_optimized")
        concurrency: 并发数（可选，不指定则使用默认值）
    """
    config_map = {
        "conservative": LargeScaleConfig.conservative_config,
        "balanced": LargeScaleConfig.balanced_config,
        "aggressive": LargeScaleConfig.aggressive_config,
        "memory_optimized": LargeScaleConfig.memory_optimized_config
    }
    
    if config_type not in config_map:
        raise ValueError(f"不支持的配置类型: {config_type}")
    
    if concurrency:
        config = config_map[config_type](concurrency)
    else:
        config = config_map[config_type]()
    
    settings_dict.update(config)
    
    return config


# 使用示例和说明
USAGE_GUIDE = """
# 大规模爬虫配置使用指南

## 1. 选择合适的配置类型

### Conservative (保守型)
- 适用场景：资源受限、网络不稳定的环境
- 并发数：8 (默认)
- 队列容量：80
- 延迟：200ms
- 使用场景：个人开发、小规模爬取

### Balanced (平衡型) 
- 适用场景：一般生产环境
- 并发数：16 (默认)
- 队列容量：240
- 延迟：100ms
- 使用场景：中小企业生产环境

### Aggressive (激进型)
- 适用场景：高性能服务器、对速度要求高
- 并发数：32 (默认)
- 队列容量：640
- 延迟：50ms
- 使用场景：大公司、高并发需求

### Memory Optimized (内存优化型)
- 适用场景：大规模爬取但内存受限
- 并发数：12 (默认)
- 队列容量：60 (小队列快速流转)
- 延迟：100ms
- 使用场景：处理数万/数十万请求但内存有限

## 2. 使用方法

```python
# 方法1：在 settings.py 中直接配置
from crawlo.utils.large_scale_config import apply_large_scale_config

# 使用平衡配置，16并发
apply_large_scale_config(locals(), "balanced", 16)

# 方法2：在爬虫代码中动态配置
from crawlo.crawler import CrawlerProcess
from crawlo.utils.large_scale_config import LargeScaleConfig

process = CrawlerProcess()
config = LargeScaleConfig.memory_optimized_config(20)  # 20并发的内存优化配置
process.settings.update(config)

# 方法3：自定义配置
config = LargeScaleConfig.balanced_config(24)  # 24并发
config['DOWNLOAD_DELAY'] = 0.05  # 自定义延迟
process.settings.update(config)
```

## 3. 针对不同场景的建议

### 处理5万+请求
```python
# 推荐内存优化配置
apply_large_scale_config(locals(), "memory_optimized", 20)
```

### 高速爬取但服务器性能好
```python
# 推荐激进配置
apply_large_scale_config(locals(), "aggressive", 40)
```

### 资源受限但要稳定运行
```python
# 推荐保守配置
apply_large_scale_config(locals(), "conservative", 6)
```

### 平衡性能和稳定性
```python
# 推荐平衡配置
apply_large_scale_config(locals(), "balanced", 18)
```
"""