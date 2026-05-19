#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
DownloadDelayMiddleware
=======================
Simple request delay control middleware.

Configuration:
    DOWNLOAD_DELAY = 2.0  # Delay between requests (seconds)
    RANDOMNESS = True     # Enable random delay
    RANDOM_RANGE = [0.5, 1.5]  # Random delay range multiplier

Domain-specific delays:
    DOWNLOAD_DELAY_OVERRIDES = {
        'example.com': 3.0,
        'api.example.com': 0.5,
    }
"""
import asyncio
import time
from random import uniform
from typing import Dict, Optional
from urllib.parse import urlparse

from crawlo.logging import get_logger
from crawlo.middleware import BaseMiddleware


class DownloadDelayMiddleware(BaseMiddleware):
    """
    DownloadDelayMiddleware - Simple request delay control
    
    Controls the delay between requests to avoid overwhelming target servers.
    Each domain has independent delay tracking.
    """
    
    def __init__(
        self,
        delay: float = 1.0,
        randomness: bool = False,
        random_range: tuple = (0.5, 1.5),
        domain_overrides: Optional[Dict[str, float]] = None
    ):
        """
        Initialize middleware
        
        Args:
            delay: Default delay between requests (seconds)
            randomness: Enable random delay
            random_range: (min, max) multiplier for random delay
            domain_overrides: Domain-specific delay settings
        """
        self.default_delay = delay
        self.randomness = randomness
        self.random_range = random_range
        self.domain_overrides = domain_overrides or {}
        
        # Track last request time per domain (LRU, 最多跟踪 1024 个域名)
        self._last_request_time: Dict[str, float] = {}
        self._max_domains = 1024
        
        self.logger = get_logger(self.__class__.__name__)
    
    @classmethod
    def create_instance(cls, crawler):
        """
        Create middleware instance from crawler settings
        
        Args:
            crawler: Crawler instance
            
        Returns:
            DownloadDelayMiddleware: Configured instance
        """
        settings = crawler.settings
        
        delay = settings.get_float('DOWNLOAD_DELAY', 0.0)
        randomness = settings.get_bool('RANDOMNESS', False)
        
        # Parse random range
        random_range = settings.get_list('RANDOM_RANGE', [0.5, 1.5])
        if len(random_range) >= 2:
            try:
                random_range = (float(random_range[0]), float(random_range[1]))
            except (ValueError, TypeError):
                random_range = (0.5, 1.5)
        else:
            random_range = (0.5, 1.5)
        
        # Domain-specific overrides
        domain_overrides = settings.get_dict('DOWNLOAD_DELAY_OVERRIDES', {})
        
        return cls(
            delay=delay,
            randomness=randomness,
            random_range=random_range,
            domain_overrides=domain_overrides
        )
    
    def _get_delay(self, domain: str) -> float:
        """
        Get delay for domain
        
        Args:
            domain: Domain name
            
        Returns:
            float: Delay in seconds
        """
        # Check domain override
        if domain in self.domain_overrides:
            return self.domain_overrides[domain]
        
        # Check wildcard patterns
        for pattern, delay in self.domain_overrides.items():
            if pattern.startswith('*.'):
                suffix = pattern[2:]
                if domain.endswith(suffix):
                    return delay
        
        return self.default_delay
    
    def _calculate_wait_time(self, domain: str) -> float:
        """
        Calculate how long to wait before next request
        
        Args:
            domain: Domain name
            
        Returns:
            float: Wait time in seconds (0 if no wait needed)
        """
        delay = self._get_delay(domain)
        
        # Apply randomness
        if self.randomness:
            delay = uniform(delay * self.random_range[0], delay * self.random_range[1])
        
        # Calculate actual wait time
        last_time = self._last_request_time.get(domain, 0)
        elapsed = time.time() - last_time
        
        wait_time = max(0, delay - elapsed)
        return wait_time
    
    async def process_request(self, request, spider):
        """
        Process request - apply delay if needed
        
        Args:
            request: Request object
            spider: Spider instance
            
        Returns:
            None: Continue processing
        """
        domain = urlparse(request.url).netloc
        
        wait_time = self._calculate_wait_time(domain)
        
        if wait_time > 0:
            await asyncio.sleep(wait_time)
        
        # Record request time (LRU: 超容量时淘汰最早记录的域名)
        if domain not in self._last_request_time and len(self._last_request_time) >= self._max_domains:
            # 移除最早记录的下一个域名（pop 首个插入项）
            self._last_request_time.pop(next(iter(self._last_request_time)))
        self._last_request_time[domain] = time.time()
        
        return None


__all__ = ['DownloadDelayMiddleware']
