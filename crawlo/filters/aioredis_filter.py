#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
Redis 过滤器实现
=================
提供基于 Redis 的分布式请求去重功能。

特点:
- 分布式支持: 多节点共享去重数据
- TTL 支持: 自动过期清理
- 高性能: 使用 Redis pipeline 优化
- 容错设计: 网络异常自动重试
"""
import redis.asyncio as aioredis
from typing import Optional
from crawlo.filters import BaseFilter
from crawlo.utils.log import get_logger
from crawlo.utils.request import request_fingerprint
from crawlo.utils.redis_connection_pool import get_redis_pool


class AioRedisFilter(BaseFilter):
    """
    基于Redis集合实现的异步请求去重过滤器
    
    支持特性:
    - 分布式爬虫多节点共享去重数据
    - TTL 自动过期清理机制
    - Pipeline 批量操作优化性能
    - 容错设计和连接池管理
    
    适用场景:
    - 分布式爬虫系统
    - 大规模数据处理
    - 需要持久化去重的场景
    """

    def __init__(
            self,
            redis_key: str,
            client: aioredis.Redis,
            stats: dict,
            debug: bool = False,
            log_level: str = 'INFO',
            cleanup_fp: bool = False,
            ttl: Optional[int] = None
    ):
        """
        初始化Redis过滤器
        
        :param redis_key: Redis中存储指纹的键名
        :param client: Redis客户端实例（可以为None，稍后初始化）
        :param stats: 统计信息存储
        :param debug: 是否启用调试模式
        :param log_level: 日志级别
        :param cleanup_fp: 关闭时是否清理指纹
        :param ttl: 指纹过期时间（秒）
        """
        self.logger = get_logger(self.__class__.__name__, log_level)
        super().__init__(self.logger, stats, debug)

        self.redis_key = redis_key
        self.redis = client
        self.cleanup_fp = cleanup_fp
        self.ttl = ttl
        
        # 保存连接池引用（用于延迟初始化）
        self._redis_pool = None
        
        # 性能计数器
        self._redis_operations = 0
        self._pipeline_operations = 0

    @classmethod
    def create_instance(cls, crawler) -> 'BaseFilter':
        """从爬虫配置创建过滤器实例"""
        redis_url = crawler.settings.get('REDIS_URL', 'redis://localhost:6379')
        # 确保 decode_responses=False 以避免编码问题
        decode_responses = False  # crawler.settings.get_bool('DECODE_RESPONSES', False)
        ttl_setting = crawler.settings.get_int('REDIS_TTL')

        # 处理TTL设置
        ttl = None
        if ttl_setting is not None:
            ttl = max(0, int(ttl_setting)) if ttl_setting > 0 else None

        try:
            # 使用优化的连接池，确保 decode_responses=False
            redis_pool = get_redis_pool(
                redis_url,
                max_connections=20,
                socket_connect_timeout=5,
                socket_timeout=30,
                health_check_interval=30,
                retry_on_timeout=True,
                decode_responses=decode_responses,  # 确保不自动解码响应
                encoding='utf-8'
            )
            
            # 注意：这里不应该使用 await，因为 create_instance 不是异步方法
            # 我们将在实际使用时获取连接
            redis_client = None  # 延迟初始化
        except Exception as e:
            raise RuntimeError(f"Redis连接池初始化失败: {redis_url} - {str(e)}")

        # 使用统一的Redis key命名规范: crawlo:{project_name}:filter:fingerprint
        project_name = crawler.settings.get('PROJECT_NAME', 'default')
        redis_key = f"crawlo:{project_name}:filter:fingerprint"

        instance = cls(
            redis_key=redis_key,
            client=redis_client,
            stats=crawler.stats,
            cleanup_fp=crawler.settings.get_bool('CLEANUP_FP', False),
            ttl=ttl,
            debug=crawler.settings.get_bool('FILTER_DEBUG', False),
            log_level=crawler.settings.get('LOG_LEVEL', 'INFO')
        )
        
        # 保存连接池引用，以便在需要时获取连接
        instance._redis_pool = redis_pool
        return instance

    async def _get_redis_client(self):
        """获取Redis客户端实例（延迟初始化）"""
        if self.redis is None and self._redis_pool is not None:
            self.redis = await self._redis_pool.get_connection()
        return self.redis

    async def requested(self, request) -> bool:
        """
        检查请求是否已存在（优化版本）
        
        :param request: 请求对象
        :return: True 表示重复，False 表示新请求
        """
        try:
            # 确保Redis客户端已初始化
            await self._get_redis_client()
            
            fp = str(request_fingerprint(request))
            self._redis_operations += 1

            # 使用 pipeline 优化性能
            pipe = self.redis.pipeline()
            pipe.sismember(self.redis_key, fp)
            
            results = await pipe.execute()
            exists = results[0]
            
            self._pipeline_operations += 1

            if exists:
                if self.debug:
                    self.logger.debug(f"发现重复请求: {fp[:20]}...")
                return True

            # 如果不存在，添加指纹并设置TTL
            await self.add_fingerprint(fp)
            return False

        except Exception as e:
            self.logger.error(f"请求检查失败: {getattr(request, 'url', '未知URL')} - {e}")
            # 在网络异常时返回False，避免丢失请求
            return False

    async def add_fingerprint(self, fp: str) -> bool:
        """
        添加新指纹到Redis集合（优化版本）
        
        :param fp: 请求指纹字符串
        :return: 是否成功添加（True 表示新添加，False 表示已存在）
        """
        try:
            # 确保Redis客户端已初始化
            await self._get_redis_client()
            
            fp = str(fp)
            
            # 使用 pipeline 优化性能
            pipe = self.redis.pipeline()
            pipe.sadd(self.redis_key, fp)
            
            if self.ttl and self.ttl > 0:
                pipe.expire(self.redis_key, self.ttl)
            
            results = await pipe.execute()
            added = results[0] == 1  # sadd 返回 1 表示新添加
            
            self._pipeline_operations += 1
            
            if self.debug and added:
                self.logger.debug(f"添加新指纹: {fp[:20]}...")
            
            return added
            
        except Exception as e:
            self.logger.error(f"添加指纹失败: {fp[:20]}... - {e}")
            return False
    
    def __contains__(self, item: str) -> bool:
        """
        同步版本的包含检查（不推荐在异步环境中使用）
        
        :param item: 要检查的指纹
        :return: 是否已存在
        """
        # 这是一个同步方法，不能直接调用异步Redis操作
        # 建议使用 requested() 方法替代
        raise NotImplementedError("请使用 requested() 方法进行异步检查")

    async def get_stats(self) -> dict:
        """获取过滤器详细统计信息"""
        try:
            # 确保Redis客户端已初始化
            await self._get_redis_client()
            
            count = await self.redis.scard(self.redis_key)
            
            # 获取TTL信息
            ttl_info = "TTL未设置"
            if self.ttl:
                remaining_ttl = await self.redis.ttl(self.redis_key)
                if remaining_ttl > 0:
                    ttl_info = f"剩余 {remaining_ttl} 秒"
                else:
                    ttl_info = f"配置 {self.ttl} 秒"
            
            stats = {
                'filter_type': 'AioRedisFilter',
                '指纹总数': count,
                'Redis键名': self.redis_key,
                'TTL配置': ttl_info,
                'Redis操作数': self._redis_operations,
                'Pipeline操作数': self._pipeline_operations,
                '性能优化率': f"{self._pipeline_operations / max(1, self._redis_operations) * 100:.1f}%"
            }
            
            # 合并基类统计
            base_stats = super().get_stats()
            stats.update(base_stats)
            
            return stats
            
        except Exception as e:
            self.logger.error(f"获取统计信息失败: {e}")
            return super().get_stats()

    async def clear_all(self) -> int:
        """清空所有指纹数据"""
        try:
            # 确保Redis客户端已初始化
            await self._get_redis_client()
            
            deleted = await self.redis.delete(self.redis_key)
            self.logger.info(f"已清除指纹数: {deleted}")
            return deleted
        except Exception as e:
            self.logger.error("清空指纹失败")
            raise

    async def closed(self, reason: Optional[str] = None) -> None:
        """爬虫关闭时的清理操作"""
        try:
            # 确保Redis客户端已初始化
            await self._get_redis_client()
            
            if self.cleanup_fp:
                deleted = await self.redis.delete(self.redis_key)
                self.logger.info(f"爬虫关闭清理: 已删除{deleted}个指纹")
            else:
                count = await self.redis.scard(self.redis_key)
                ttl_info = f"{self.ttl}秒" if self.ttl else "持久化"
                self.logger.info(f"保留指纹数: {count} (TTL: {ttl_info})")
        finally:
            await self._close_redis()

    async def _close_redis(self) -> None:
        """安全关闭Redis连接"""
        # 连接池会自动管理连接，这里不需要显式关闭
        self.logger.debug("Redis连接已释放")