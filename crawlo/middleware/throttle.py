#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
域名限流中间件
==============
基于域名的请求速率限制中间件，自动控制请求频率。

配置项：
    THROTTLE_ENABLED: 是否启用限流（默认 True）
    THROTTLE_DEFAULT_DELAY: 默认请求延迟（默认 1.0 秒）
    THROTTLE_MAX_RATE: 默认最大速率（默认 None，不限制）
    THROTTLE_DOMAIN_OVERRIDES: 域名特定配置
    THROTTLE_AUTO_THROTTLE: 是否启用自动限流（根据响应时间调整）

使用示例：
    # settings.py
    THROTTLE_ENABLED = True
    THROTTLE_DEFAULT_DELAY = 1.0
    
    # 针对特定域名配置
    THROTTLE_DOMAIN_OVERRIDES = {
        'example.com': {'delay': 2.0},
        'api.example.com': {'max_rate': 10, 'delay': 0.1},
    }
"""
import time
from typing import Optional, Dict, Any

from crawlo.logging import get_logger
from crawlo.middleware import BaseMiddleware
from crawlo.utils.throttle import DomainThrottler, DomainConfig


class ThrottleMiddleware(BaseMiddleware):
    """
    域名限流中间件
    
    在请求发送前根据域名进行速率限制。
    
    特性：
    - 基于令牌桶算法
    - 支持域名特定配置
    - 支持自动限流（根据响应时间动态调整）
    - 支持突发请求
    """
    
    @classmethod
    def create_instance(cls, crawler):
        """创建中间件实例"""
        settings = crawler.settings
        
        # 读取配置
        enabled = settings.get_bool('THROTTLE_ENABLED', True)
        if not enabled:
            return None
        
        default_delay = settings.get_float('THROTTLE_DEFAULT_DELAY', 1.0)
        max_rate = settings.get_float('THROTTLE_MAX_RATE', None)
        auto_throttle = settings.get_bool('THROTTLE_AUTO_THROTTLE', False)
        
        # 解析域名特定配置
        domain_overrides = settings.get_dict('THROTTLE_DOMAIN_OVERRIDES', {})
        domain_configs = {}
        
        for domain, config in domain_overrides.items():
            if isinstance(config, dict):
                domain_configs[domain] = DomainConfig(
                    delay=config.get('delay', default_delay),
                    max_rate=config.get('max_rate'),
                    max_concurrent=config.get('max_concurrent', 8),
                    burst_size=config.get('burst_size', 1)
                )
        
        return cls(
            default_delay=default_delay,
            max_rate=max_rate,
            auto_throttle=auto_throttle,
            domain_configs=domain_configs
        )
    
    def __init__(
        self,
        default_delay: float = 1.0,
        max_rate: Optional[float] = None,
        auto_throttle: bool = False,
        domain_configs: Optional[Dict[str, DomainConfig]] = None
    ):
        """
        初始化限流中间件
        
        Args:
            default_delay: 默认请求延迟
            max_rate: 默认最大速率
            auto_throttle: 是否启用自动限流
            domain_configs: 域名特定配置
        """
        self.default_delay = default_delay
        self.max_rate = max_rate
        self.auto_throttle = auto_throttle
        
        self.throttler = DomainThrottler(
            default_delay=default_delay,
            default_max_rate=max_rate,
            domain_configs=domain_configs
        )
        
        # 响应时间追踪（用于自动限流）
        self._response_times: Dict[str, list] = {}
        
        self.logger = get_logger(self.__class__.__name__)
        self.logger.info(
            f"ThrottleMiddleware enabled: delay={default_delay}s, "
            f"auto_throttle={auto_throttle}"
        )
    
    async def process_request(self, request, spider):
        """
        处理请求 - 应用限流
        
        Args:
            request: 请求对象
            spider: 爬虫实例
            
        Returns:
            None: 继续处理
        """
        # 获取域名
        domain = DomainThrottler.extract_domain(request.url)
        
        # 生成请求ID（用于追踪）
        request_id = id(request)
        
        # 获取许可
        await self.throttler.acquire(domain, request_id)
        
        # 记录开始时间（用于自动限流）
        if self.auto_throttle:
            request.meta['_throttle_start_time'] = time.time()
        
        return None
    
    async def process_response(self, request, response, spider):
        """
        处理响应 - 记录响应时间
        
        Args:
            request: 请求对象
            response: 响应对象
            spider: 爬虫实例
            
        Returns:
            Response: 响应对象
        """
        domain = DomainThrottler.extract_domain(request.url)
        
        # 释放请求
        request_id = id(request)
        self.throttler.release(domain, request_id)
        
        # 自动限流：根据响应时间调整
        if self.auto_throttle:
            start_time = request.meta.get('_throttle_start_time')
            if start_time:
                response_time = time.time() - start_time
                self._adjust_throttle(domain, response_time)
        
        return response
    
    async def process_exception(self, request, exception, spider):
        """
        处理异常 - 释放请求
        
        Args:
            request: 请求对象
            exception: 异常
            spider: 爬虫实例
            
        Returns:
            None: 继续传递异常
        """
        domain = DomainThrottler.extract_domain(request.url)
        request_id = id(request)
        self.throttler.release(domain, request_id)
        
        return None
    
    def _adjust_throttle(self, domain: str, response_time: float) -> None:
        """
        根据响应时间自动调整限流
        
        Args:
            domain: 域名
            response_time: 响应时间
        """
        # 记录响应时间
        if domain not in self._response_times:
            self._response_times[domain] = []
        
        times = self._response_times[domain]
        times.append(response_time)
        
        # 只保留最近 10 次响应时间
        if len(times) > 10:
            times.pop(0)
        
        # 计算平均响应时间
        avg_time = sum(times) / len(times)
        
        # 根据响应时间调整延迟
        # 响应快则减少延迟，响应慢则增加延迟
        config = self.throttler.get_domain_config(domain)
        
        if avg_time < 0.5:
            # 响应很快，减少延迟
            new_delay = max(0.1, config.delay * 0.9)
        elif avg_time > 2.0:
            # 响应很慢，增加延迟
            new_delay = min(5.0, config.delay * 1.1)
        else:
            # 响应正常，保持当前延迟
            new_delay = config.delay
        
        if new_delay != config.delay:
            new_config = DomainConfig(
                delay=new_delay,
                max_rate=config.max_rate,
                max_concurrent=config.max_concurrent,
                burst_size=config.burst_size
            )
            self.throttler.set_domain_config(domain, new_config)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取限流统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        return self.throttler.get_stats()


# ==================== 导出 ====================

__all__ = ['ThrottleMiddleware']
