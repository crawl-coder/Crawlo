#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
简化版Redis队列实现
避免复杂的循环依赖问题，提供基础的Redis队列功能
"""
import asyncio
import pickle
import time
from typing import Optional

import redis.asyncio as aioredis


class SimpleRedisQueue:
    """简化版Redis队列，避免循环依赖"""
    
    def __init__(self, redis_url: str, queue_name: str = "crawlo:requests"):
        self.redis_url = redis_url
        self.queue_name = queue_name
        self.data_key = f"{queue_name}:data"
        self._redis = None
        self._lock = asyncio.Lock()
    
    async def connect(self):
        """连接Redis"""
        if self._redis is None:
            self._redis = aioredis.from_url(self.redis_url, decode_responses=False)
            await self._redis.ping()
    
    async def _ensure_connection(self):
        """确保连接有效"""
        if self._redis is None:
            await self.connect()
        try:
            await self._redis.ping()
        except Exception:
            self._redis = None
            await self.connect()
    
    async def put(self, request, priority: int = 0) -> bool:
        """入队"""
        try:
            await self._ensure_connection()
            
            # 生成请求键
            key = f"req:{hash(request.url) & 0x7FFFFFFF}:{int(time.time() * 1000000)}"
            score = -priority  # 负数确保高优先级在前
            
            # 序列化请求
            try:
                # 简化的序列化：只保留必要字段
                request_data = {
                    'url': request.url,
                    'method': getattr(request, 'method', 'GET'),
                    'headers': dict(getattr(request, 'headers', {})),
                    'body': getattr(request, 'body', None),
                    'meta': getattr(request, 'meta', {}),
                    'callback_name': getattr(request.callback, '__name__', None) if hasattr(request, 'callback') and request.callback else None,
                }
                serialized = pickle.dumps(request_data)
            except Exception as e:
                print(f"序列化请求失败: {e}")
                return False
            
            # 使用事务
            pipe = self._redis.pipeline()
            pipe.zadd(self.queue_name, {key: score})
            pipe.hset(self.data_key, key, serialized)
            await pipe.execute()
            
            return True
            
        except Exception as e:
            print(f"入队失败: {e}")
            return False
    
    async def get(self, timeout: float = 5.0):
        """出队"""
        try:
            await self._ensure_connection()
            
            # 获取最高优先级的请求
            result = await self._redis.zpopmin(self.queue_name, count=1)
            if not result:
                return None
            
            key, score = result[0]
            key = key.decode() if isinstance(key, bytes) else key
            
            # 获取请求数据
            serialized = await self._redis.hget(self.data_key, key)
            if not serialized:
                return None
            
            # 删除数据
            await self._redis.hdel(self.data_key, key)
            
            # 反序列化
            try:
                request_data = pickle.loads(serialized)
                # 这里返回简化的数据，上层代码需要重构为Request对象
                return request_data
            except Exception as e:
                print(f"反序列化失败: {e}")
                return None
                
        except Exception as e:
            print(f"出队失败: {e}")
            return None
    
    async def qsize(self) -> int:
        """获取队列大小"""
        try:
            await self._ensure_connection()
            return await self._redis.zcard(self.queue_name)
        except Exception:
            return 0
    
    async def close(self):
        """关闭连接"""
        if self._redis:
            try:
                await self._redis.aclose()
            except Exception:
                pass
            self._redis = None