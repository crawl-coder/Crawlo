#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
统一的队列管理器
提供简洁、一致的队列接口，自动处理不同队列类型的差异
"""
from typing import Optional, Dict, Any, Union
from enum import Enum
import asyncio
import traceback
import os

from crawlo.utils.log import get_logger
from crawlo.utils.request_serializer import RequestSerializer
from crawlo.queue.pqueue import SpiderPriorityQueue
from crawlo import Request

try:
    from crawlo.queue.redis_priority_queue import RedisPriorityQueue
    REDIS_AVAILABLE = True
except ImportError:
    RedisPriorityQueue = None
    REDIS_AVAILABLE = False


class QueueType(Enum):
    """队列类型枚举"""
    MEMORY = "memory"
    REDIS = "redis"
    AUTO = "auto"  # 自动选择


class QueueConfig:
    """队列配置类"""
    
    def __init__(
        self,
        queue_type: Union[QueueType, str] = QueueType.AUTO,
        redis_url: Optional[str] = None,
        redis_host: str = "127.0.0.1",
        redis_port: int = 6379,
        redis_password: Optional[str] = None,
        redis_db: int = 0,
        queue_name: str = "crawlo:requests",
        max_queue_size: int = 1000,
        max_retries: int = 3,
        timeout: int = 300,
        **kwargs
    ):
        self.queue_type = QueueType(queue_type) if isinstance(queue_type, str) else queue_type
        
        # Redis 配置
        if redis_url:
            self.redis_url = redis_url
        else:
            if redis_password:
                self.redis_url = f"redis://:{redis_password}@{redis_host}:{redis_port}/{redis_db}"
            else:
                self.redis_url = f"redis://{redis_host}:{redis_port}/{redis_db}"
        
        self.queue_name = queue_name
        self.max_queue_size = max_queue_size
        self.max_retries = max_retries
        self.timeout = timeout
        self.extra_config = kwargs
    
    @classmethod
    def from_settings(cls, settings) -> 'QueueConfig':
        """从 settings 创建配置"""
        return cls(
            queue_type=settings.get('QUEUE_TYPE', QueueType.AUTO),
            redis_url=settings.get('REDIS_URL'),
            redis_host=settings.get('REDIS_HOST', '127.0.0.1'),
            redis_port=settings.get_int('REDIS_PORT', 6379),
            redis_password=settings.get('REDIS_PASSWORD'),
            redis_db=settings.get_int('REDIS_DB', 0),
            queue_name=settings.get('SCHEDULER_QUEUE_NAME', 'crawlo:requests'),
            max_queue_size=settings.get_int('SCHEDULER_MAX_QUEUE_SIZE', 1000),
            max_retries=settings.get_int('QUEUE_MAX_RETRIES', 3),
            timeout=settings.get_int('QUEUE_TIMEOUT', 300)
        )


class QueueManager:
    """统一的队列管理器"""
    
    def __init__(self, config: QueueConfig):
        self.config = config
        self.logger = get_logger(self.__class__.__name__)
        self.request_serializer = RequestSerializer()
        self._queue = None
        self._queue_semaphore = None
        self._queue_type = None
        self._health_status = "unknown"
    
    async def initialize(self) -> bool:
        """初始化队列"""
        try:
            queue_type = await self._determine_queue_type()
            self._queue = await self._create_queue(queue_type)
            self._queue_type = queue_type
            
            # 测试队列健康状态
            await self._health_check()
            
            self.logger.info(f"✅ 队列初始化成功: {queue_type.value}")
            self.logger.info(f"📊 队列配置: {self._get_queue_info()}")
            return True
            
        except Exception as e:
            # 记录详细的错误信息和堆栈跟踪
            self.logger.error(f"❌ 队列初始化失败: {e}")
            self.logger.error(f"详细错误信息:\n{traceback.format_exc()}")
            self._health_status = "error"
            return False
    
    async def put(self, request: Request, priority: int = 0) -> bool:
        """统一的入队接口"""
        if not self._queue:
            raise RuntimeError("队列未初始化")
        
        try:
            # 序列化处理（仅对 Redis 队列）
            if self._queue_type == QueueType.REDIS:
                request = self.request_serializer.prepare_for_serialization(request)
            
            # 背压控制（仅对内存队列）
            if self._queue_semaphore:
                # 对于大量请求，使用非阻塞式检查
                if not self._queue_semaphore.locked():
                    await self._queue_semaphore.acquire()
                else:
                    # 如果队列已满，返回 False 而不是阻塞
                    self.logger.warning("队列已满，跳过当前请求")
                    return False
            
            # 统一的入队操作
            if hasattr(self._queue, 'put'):
                if self._queue_type == QueueType.REDIS:
                    success = await self._queue.put(request, priority)
                else:
                    await self._queue.put(request)
                    success = True
            else:
                raise RuntimeError(f"队列类型 {self._queue_type} 不支持 put 操作")
            
            if success:
                self.logger.debug(f"✅ 请求入队成功: {request.url}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"❌ 请求入队失败: {e}")
            if self._queue_semaphore:
                self._queue_semaphore.release()
            return False
    
    async def get(self, timeout: float = 5.0) -> Optional[Request]:
        """统一的出队接口"""
        if not self._queue:
            raise RuntimeError("队列未初始化")
        
        try:
            request = await self._queue.get(timeout=timeout)
            
            # 释放信号量（仅对内存队列）
            if self._queue_semaphore and request:
                self._queue_semaphore.release()
            
            # 反序列化处理（仅对 Redis 队列）
            if request and self._queue_type == QueueType.REDIS:
                # 这里需要 spider 实例，暂时返回原始请求
                # 实际的 callback 恢复在 scheduler 中处理
                pass
            
            return request
            
        except Exception as e:
            self.logger.error(f"❌ 请求出队失败: {e}")
            return None
    
    async def size(self) -> int:
        """获取队列大小"""
        if not self._queue:
            return 0
        
        try:
            if hasattr(self._queue, 'qsize'):
                if asyncio.iscoroutinefunction(self._queue.qsize):
                    return await self._queue.qsize()
                else:
                    return self._queue.qsize()
            return 0
        except Exception as e:
            self.logger.warning(f"获取队列大小失败: {e}")
            return 0
    
    def empty(self) -> bool:
        """检查队列是否为空"""
        try:
            # 对于内存队列，可以同步检查
            if self._queue_type == QueueType.MEMORY:
                return self._queue.qsize() == 0
            # 对于 Redis 队列，需要异步操作，这里返回近似值
            return False
        except Exception:
            return True
    
    async def close(self) -> None:
        """关闭队列"""
        if self._queue and hasattr(self._queue, 'close'):
            try:
                await self._queue.close()
                self.logger.info("✅ 队列已关闭")
            except Exception as e:
                self.logger.warning(f"关闭队列时发生错误: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """获取队列状态信息"""
        return {
            "type": self._queue_type.value if self._queue_type else "unknown",
            "health": self._health_status,
            "config": self._get_queue_info(),
            "initialized": self._queue is not None
        }
    
    async def _determine_queue_type(self) -> QueueType:
        """确定队列类型"""
        if self.config.queue_type == QueueType.AUTO:
            # 自动选择：优先使用 Redis（如果可用）
            if REDIS_AVAILABLE and self.config.redis_url:
                # 测试 Redis 连接
                try:
                    test_queue = RedisPriorityQueue(self.config.redis_url)
                    await test_queue.connect()
                    await test_queue.close()
                    self.logger.info("🔍 自动检测: Redis 可用，使用分布式队列")
                    return QueueType.REDIS
                except Exception as e:
                    self.logger.warning(f"🔍 自动检测: Redis 不可用 ({e})，使用内存队列")
                    return QueueType.MEMORY
            else:
                self.logger.info("🔍 自动检测: Redis 未配置，使用内存队列")
                return QueueType.MEMORY
        
        elif self.config.queue_type == QueueType.REDIS:
            if not REDIS_AVAILABLE:
                raise RuntimeError("Redis 队列不可用：未安装 redis 依赖")
            if not self.config.redis_url:
                raise RuntimeError("Redis 队列不可用：未配置 REDIS_URL")
            return QueueType.REDIS
        
        elif self.config.queue_type == QueueType.MEMORY:
            return QueueType.MEMORY
        
        else:
            raise ValueError(f"不支持的队列类型: {self.config.queue_type}")
    
    async def _create_queue(self, queue_type: QueueType):
        """创建队列实例"""
        if queue_type == QueueType.REDIS:
            # 从队列名称中提取项目名称，用于module_name
            # 例如：crawlo:books_distributed:queue:requests -> books_distributed
            project_name = "default"
            if ':' in self.config.queue_name:
                parts = self.config.queue_name.split(':')
                if len(parts) >= 2:
                    project_name = parts[1]  # 取第二个部分作为项目名称
            else:
                project_name = self.config.queue_name or "default"
            
            queue = RedisPriorityQueue(
                redis_url=self.config.redis_url,
                queue_name=self.config.queue_name,
                max_retries=self.config.max_retries,
                timeout=self.config.timeout,
                module_name=project_name  # 传递项目名称作为module_name
            )
            # 不需要立即连接，使用 lazy connect
            return queue
        
        elif queue_type == QueueType.MEMORY:
            queue = SpiderPriorityQueue()
            # 为内存队列设置背压控制
            self._queue_semaphore = asyncio.Semaphore(self.config.max_queue_size)
            return queue
        
        else:
            raise ValueError(f"不支持的队列类型: {queue_type}")
    
    async def _health_check(self) -> None:
        """健康检查"""
        try:
            if self._queue_type == QueueType.REDIS:
                # 测试 Redis 连接
                await self._queue.connect()
                self._health_status = "healthy"
            else:
                # 内存队列总是健康的
                self._health_status = "healthy"
        except Exception as e:
            self.logger.warning(f"队列健康检查失败: {e}")
            self._health_status = "unhealthy"
    
    def _get_queue_info(self) -> Dict[str, Any]:
        """获取队列配置信息"""
        info = {
            "queue_name": self.config.queue_name,
            "max_queue_size": self.config.max_queue_size
        }
        
        if self._queue_type == QueueType.REDIS:
            info.update({
                "redis_url": self.config.redis_url,
                "max_retries": self.config.max_retries,
                "timeout": self.config.timeout
            })
        
        return info