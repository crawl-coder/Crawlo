#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
域名限流模块
============
提供基于域名的请求速率限制，防止过度请求导致被封禁。

核心组件：
- TokenBucket: 令牌桶算法实现
- DomainThrottler: 域名限流器
- ThrottleMiddleware: 限流中间件

使用示例：
    # 配置限流
    THROTTLE_ENABLED = True
    THROTTLE_DEFAULT_DELAY = 1.0  # 默认延迟1秒
    THROTTLE_DOMAIN_OVERRIDES = {
        'example.com': {'delay': 2.0},  # 特定域名延迟
        'api.example.com': {'delay': 0.5, 'max_rate': 10},  # 速率限制
    }
"""
import asyncio
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, Optional, Any, Set
from urllib.parse import urlparse

from crawlo.logging import get_logger


@dataclass
class TokenBucket:
    """
    令牌桶算法实现
    
    用于精确控制请求速率。
    
    属性：
        rate: 令牌生成速率（令牌/秒）
        capacity: 桶容量
        tokens: 当前令牌数
        last_update: 上次更新时间
    """
    rate: float            # 每秒生成的令牌数
    capacity: float        # 桶的最大容量
    tokens: float = 0.0    # 当前令牌数
    last_update: float = field(default_factory=time.time)
    
    def __post_init__(self):
        """初始化时填满桶"""
        self.tokens = self.capacity
    
    def _refill(self) -> None:
        """补充令牌"""
        now = time.time()
        elapsed = now - self.last_update
        new_tokens = elapsed * self.rate
        self.tokens = min(self.capacity, self.tokens + new_tokens)
        self.last_update = now
    
    def can_consume(self, tokens: float = 1.0) -> bool:
        """
        检查是否可以消费令牌
        
        Args:
            tokens: 需要消费的令牌数
            
        Returns:
            bool: 是否可以消费
        """
        self._refill()
        return self.tokens >= tokens
    
    def consume(self, tokens: float = 1.0) -> bool:
        """
        消费令牌
        
        Args:
            tokens: 需要消费的令牌数
            
        Returns:
            bool: 是否成功消费
        """
        self._refill()
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False
    
    def time_until_available(self, tokens: float = 1.0) -> float:
        """
        计算直到有足够令牌需要等待的时间
        
        Args:
            tokens: 需要的令牌数
            
        Returns:
            float: 等待时间（秒）
        """
        self._refill()
        if self.tokens >= tokens:
            return 0.0
        
        needed = tokens - self.tokens
        return needed / self.rate


@dataclass
class DomainConfig:
    """
    域名限流配置
    
    属性：
        delay: 请求延迟（秒）
        max_rate: 最大请求速率（请求/秒）
        max_concurrent: 最大并发数
        burst_size: 突发请求大小
    """
    delay: float = 1.0
    max_rate: Optional[float] = None
    max_concurrent: int = 8
    burst_size: int = 1


class DomainThrottler:
    """
    域名限流器
    
    为每个域名维护独立的限流状态。
    
    使用示例：
        throttler = DomainThrottler(default_delay=1.0)
        
        # 等待获取许可
        await throttler.acquire('example.com')
        
        # 或检查是否可以立即请求
        if throttler.can_request('example.com'):
            throttler.record_request('example.com')
    """
    
    def __init__(
        self,
        default_delay: float = 1.0,
        default_max_rate: Optional[float] = None,
        default_max_concurrent: int = 8,
        domain_configs: Optional[Dict[str, DomainConfig]] = None
    ):
        """
        初始化域名限流器
        
        Args:
            default_delay: 默认请求延迟（秒）
            default_max_rate: 默认最大速率
            default_max_concurrent: 默认最大并发数
            domain_configs: 域名特定配置
        """
        self.default_delay = default_delay
        self.default_max_rate = default_max_rate
        self.default_max_concurrent = default_max_concurrent
        
        # 域名配置
        self._domain_configs: Dict[str, DomainConfig] = domain_configs or {}
        
        # 域名状态
        self._last_request_time: Dict[str, float] = defaultdict(float)
        self._active_requests: Dict[str, Set] = defaultdict(set)
        self._token_buckets: Dict[str, TokenBucket] = {}
        
        # 统计信息
        self._total_requests = 0
        self._total_waits = 0
        self._total_wait_time = 0.0
        
        self.logger = get_logger(self.__class__.__name__)
    
    def get_domain_config(self, domain: str) -> DomainConfig:
        """
        获取域名配置
        
        Args:
            domain: 域名
            
        Returns:
            DomainConfig: 域名配置
        """
        # 检查精确匹配
        if domain in self._domain_configs:
            return self._domain_configs[domain]
        
        # 检查通配符匹配（如 *.example.com）
        for pattern, config in self._domain_configs.items():
            if pattern.startswith('*.'):
                suffix = pattern[2:]
                if domain.endswith(suffix):
                    return config
        
        # 返回默认配置
        return DomainConfig(
            delay=self.default_delay,
            max_rate=self.default_max_rate,
            max_concurrent=self.default_max_concurrent
        )
    
    def _get_or_create_bucket(self, domain: str) -> TokenBucket:
        """
        获取或创建域名的令牌桶
        
        Args:
            domain: 域名
            
        Returns:
            TokenBucket: 令牌桶
        """
        if domain not in self._token_buckets:
            config = self.get_domain_config(domain)
            if config.max_rate:
                bucket = TokenBucket(
                    rate=config.max_rate,
                    capacity=config.burst_size
                )
            else:
                # 如果没有设置最大速率，使用延迟计算
                # 速率 = 1 / 延迟
                rate = 1.0 / max(config.delay, 0.001)
                bucket = TokenBucket(
                    rate=rate,
                    capacity=config.burst_size
                )
            self._token_buckets[domain] = bucket
        return self._token_buckets[domain]
    
    def can_request(self, domain: str) -> bool:
        """
        检查是否可以立即发送请求
        
        Args:
            domain: 域名
            
        Returns:
            bool: 是否可以发送
        """
        config = self.get_domain_config(domain)
        
        # 检查并发数
        if len(self._active_requests[domain]) >= config.max_concurrent:
            return False
        
        # 检查延迟
        elapsed = time.time() - self._last_request_time[domain]
        if elapsed < config.delay:
            return False
        
        # 检查令牌桶
        bucket = self._get_or_create_bucket(domain)
        return bucket.can_consume()
    
    def time_until_available(self, domain: str) -> float:
        """
        计算直到可以发送请求需要等待的时间
        
        Args:
            domain: 域名
            
        Returns:
            float: 等待时间（秒）
        """
        config = self.get_domain_config(domain)
        
        # 计算延迟等待时间
        elapsed = time.time() - self._last_request_time[domain]
        delay_wait = max(0, config.delay - elapsed)
        
        # 计算令牌等待时间
        bucket = self._get_or_create_bucket(domain)
        token_wait = bucket.time_until_available()
        
        return max(delay_wait, token_wait)
    
    async def acquire(self, domain: str, request_id: Any = None) -> None:
        """
        获取发送许可（异步等待）
        
        Args:
            domain: 域名
            request_id: 请求ID（用于追踪）
        """
        while not self.can_request(domain):
            wait_time = self.time_until_available(domain)
            if wait_time > 0:
                self._total_waits += 1
                self._total_wait_time += wait_time
                await asyncio.sleep(min(wait_time, 0.1))
            else:
                await asyncio.sleep(0.01)
        
        # 记录请求
        self._last_request_time[domain] = time.time()
        self._total_requests += 1
        
        # 消费令牌
        bucket = self._get_or_create_bucket(domain)
        bucket.consume()
        
        # 记录活跃请求
        if request_id is not None:
            self._active_requests[domain].add(request_id)
    
    def release(self, domain: str, request_id: Any = None) -> None:
        """
        释放请求（从活跃列表移除）
        
        Args:
            domain: 域名
            request_id: 请求ID
        """
        if request_id is not None:
            self._active_requests[domain].discard(request_id)
    
    def record_request(self, domain: str) -> None:
        """
        记录请求（不等待）
        
        Args:
            domain: 域名
        """
        self._last_request_time[domain] = time.time()
        self._total_requests += 1
        
        bucket = self._get_or_create_bucket(domain)
        bucket.consume()
    
    def set_domain_config(self, domain: str, config: DomainConfig) -> None:
        """
        设置域名配置
        
        Args:
            domain: 域名
            config: 配置
        """
        self._domain_configs[domain] = config
        # 清除旧的令牌桶以使用新配置
        self._token_buckets.pop(domain, None)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        return {
            'total_requests': self._total_requests,
            'total_waits': self._total_waits,
            'total_wait_time': self._total_wait_time,
            'avg_wait_time': self._total_wait_time / max(1, self._total_waits),
            'domains_tracked': len(self._last_request_time),
            'active_domains': [d for d, s in self._active_requests.items() if s],
        }
    
    def clear(self) -> None:
        """清除所有状态"""
        self._last_request_time.clear()
        self._active_requests.clear()
        self._token_buckets.clear()
        self._total_requests = 0
        self._total_waits = 0
        self._total_wait_time = 0.0
    
    @staticmethod
    def extract_domain(url: str) -> str:
        """
        从 URL 提取域名
        
        Args:
            url: URL 字符串
            
        Returns:
            str: 域名
        """
        try:
            parsed = urlparse(url)
            return parsed.netloc.lower() or 'unknown'
        except Exception:
            return 'unknown'


# ==================== 导出 ====================

__all__ = [
    'TokenBucket',
    'DomainConfig',
    'DomainThrottler',
]
