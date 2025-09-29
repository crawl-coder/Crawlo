#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
日志采样器
用于在高负载时减少日志输出
"""

import random
import time
import threading
from typing import Dict, Set
from collections import defaultdict


class LogSampler:
    """
    日志采样器
    支持多种采样策略以减少日志输出量
    """
    
    def __init__(self):
        self._lock = threading.RLock()
        self._sample_rates: Dict[str, float] = {}  # logger_name -> sample_rate
        self._rate_limiters: Dict[str, TokenBucket] = {}  # logger_name -> rate_limiter
        self._message_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self._time_windows: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
        
    def set_sample_rate(self, logger_name: str, rate: float):
        """
        设置采样率
        
        Args:
            logger_name: Logger名称
            rate: 采样率 (0.0-1.0)，1.0表示全部记录，0.0表示不记录
        """
        with self._lock:
            self._sample_rates[logger_name] = max(0.0, min(1.0, rate))
            
    def set_rate_limit(self, logger_name: str, messages_per_second: float):
        """
        设置速率限制
        
        Args:
            logger_name: Logger名称
            messages_per_second: 每秒最大消息数
        """
        with self._lock:
            self._rate_limiters[logger_name] = TokenBucket(messages_per_second, messages_per_second)
            
    def should_log(self, logger_name: str, message: str = None, level: str = None) -> bool:
        """
        判断是否应该记录日志
        
        Args:
            logger_name: Logger名称
            message: 日志消息（用于去重）
            level: 日志级别
            
        Returns:
            是否应该记录日志
        """
        with self._lock:
            # 检查采样率
            if logger_name in self._sample_rates:
                sample_rate = self._sample_rates[logger_name]
                if random.random() > sample_rate:
                    return False
                    
            # 检查速率限制
            if logger_name in self._rate_limiters:
                if not self._rate_limiters[logger_name].consume(1):
                    return False
                    
            # 检查消息去重（相同消息在短时间内只记录一次）
            if message:
                key = f"{level}:{message}" if level else message
                current_time = time.time()
                
                # 如果距离上次记录超过60秒，重置计数
                if current_time - self._time_windows[logger_name][key] > 60:
                    self._message_counts[logger_name][key] = 0
                    self._time_windows[logger_name][key] = current_time
                    
                # 限制相同消息的记录次数
                if self._message_counts[logger_name][key] >= 5:  # 最多记录5次相同消息
                    return False
                    
                self._message_counts[logger_name][key] += 1
                
            return True
            
    def reset(self):
        """重置采样器状态"""
        with self._lock:
            self._sample_rates.clear()
            self._rate_limiters.clear()
            self._message_counts.clear()
            self._time_windows.clear()


class TokenBucket:
    """
    令牌桶算法实现
    用于速率限制
    """
    
    def __init__(self, rate: float, capacity: float):
        """
        初始化令牌桶
        
        Args:
            rate: 每秒生成的令牌数
            capacity: 桶的最大容量
        """
        self._rate = rate
        self._capacity = capacity
        self._tokens = capacity
        self._last_time = time.time()
        self._lock = threading.Lock()
        
    def consume(self, tokens: float) -> bool:
        """
        消费令牌
        
        Args:
            tokens: 要消费的令牌数
            
        Returns:
            是否消费成功
        """
        with self._lock:
            current_time = time.time()
            # 补充令牌
            elapsed = current_time - self._last_time
            self._tokens = min(self._capacity, self._tokens + elapsed * self._rate)
            self._last_time = current_time
            
            # 尝试消费令牌
            if self._tokens >= tokens:
                self._tokens -= tokens
                return True
            else:
                return False


# 全局实例
_log_sampler = LogSampler()


def get_sampler() -> LogSampler:
    """获取日志采样器实例"""
    return _log_sampler


def should_log(logger_name: str, message: str = None, level: str = None) -> bool:
    """
    判断是否应该记录日志的便捷函数
    
    Args:
        logger_name: Logger名称
        message: 日志消息
        level: 日志级别
        
    Returns:
        是否应该记录日志
    """
    return get_sampler().should_log(logger_name, message, level)