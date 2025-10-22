#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Redis可用性检查工具
==================
提供Redis连接可用性检测功能，用于自动模式下的运行时决策。
"""

import asyncio
import logging
from typing import Optional
import redis.asyncio as aioredis


class RedisChecker:
    """Redis可用性检查器"""
    
    def __init__(self, redis_url: str, timeout: float = 5.0):
        """
        初始化Redis检查器
        
        Args:
            redis_url: Redis连接URL
            timeout: 连接超时时间（秒）
        """
        self.redis_url = redis_url
        self.timeout = timeout
        self.logger = logging.getLogger(self.__class__.__name__)
    
    async def is_redis_available(self) -> bool:
        """
        检查Redis是否可用
        
        Returns:
            Redis是否可用
        """
        try:
            # 创建Redis连接
            redis_client = aioredis.from_url(
                self.redis_url,
                socket_connect_timeout=self.timeout,
                socket_timeout=self.timeout,
                retry_on_timeout=False
            )
            
            # 尝试执行ping命令
            await asyncio.wait_for(redis_client.ping(), timeout=self.timeout)
            
            # 关闭连接
            await redis_client.close()
            
            self.logger.debug(f"Redis连接测试成功: {self.redis_url}")
            return True
            
        except asyncio.TimeoutError:
            self.logger.warning(f"Redis连接超时: {self.redis_url}")
            return False
            
        except Exception as e:
            self.logger.warning(f"Redis连接失败: {self.redis_url} - {e}")
            return False
    
    @staticmethod
    async def check_redis_availability(redis_url: str, timeout: float = 5.0) -> bool:
        """
        便捷函数：检查Redis是否可用
        
        Args:
            redis_url: Redis连接URL
            timeout: 连接超时时间（秒）
            
        Returns:
            Redis是否可用
        """
        checker = RedisChecker(redis_url, timeout)
        return await checker.is_redis_available()


# 便捷函数
async def is_redis_available(redis_url: str, timeout: float = 5.0) -> bool:
    """
    检查Redis是否可用
    
    Args:
        redis_url: Redis连接URL
        timeout: 连接超时时间（秒）
        
    Returns:
        Redis是否可用
    """
    return await RedisChecker.check_redis_availability(redis_url, timeout)