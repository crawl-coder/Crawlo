# -*- coding: utf-8 -*-
"""
连接池管理器基类
===============
提供单例模式 + 引用计数 + 自动清理的通用连接池管理。

子类用法：
    class MySQLPoolManager(BasePoolManager):
        _POOL_TYPE = 'mysql'

        @classmethod
        async def _create_pool(cls, **config):
            return await asyncmy.create_pool(**config)

        @classmethod
        async def _close_pool(cls, pool):
            pool.close()
            await pool.wait_closed()

设计文档：docs/internal/db-pipelines-design.md §4.3
"""

import asyncio
from typing import Dict, Any, Optional
from crawlo.logging import get_logger


class BasePoolManager:
    """
    连接池管理器基类

    特性：
    - 单例模式：相同 config 共享同一连接池
    - 引用计数：自动跟踪使用方数量
    - 自动清理：引用计数归零时关闭连接池
    - 线程安全：所有操作通过 asyncio.Lock 保护
    """

    _POOL_TYPE: str = 'base'  # 子类覆盖
    _pool_lock = asyncio.Lock()

    @classmethod
    def _config_key(cls, **config) -> str:
        """生成配置键（用于区分不同的连接配置）"""
        # 排除 minsize/maxsize 等运行时参数，仅用连接参数区分
        key_parts = sorted(
            (k, v) for k, v in config.items()
            if k not in ('minsize', 'maxsize', 'min_size', 'max_size')
        )
        return f"{cls._POOL_TYPE}:" + str(key_parts)

    # ── 子类必须实现 ──

    @classmethod
    async def _create_pool_internal(cls, **config) -> Any:
        """创建连接池（子类实现，处理具体数据库客户端）"""
        raise NotImplementedError

    @classmethod
    async def _close_pool_internal(cls, pool) -> None:
        """关闭连接池（子类实现）"""
        raise NotImplementedError

    # ── 以下为基类实现的通用方法 ──
    # 如需使用，子类应在类变量中初始化 _pools 和 _ref_counts

    _pools: Dict[str, Any] = {}
    _ref_counts: Dict[str, int] = {}

    @classmethod
    async def get_pool(cls, **config) -> Any:
        """
        获取或创建连接池（单例模式）

        相同连接参数返回同一连接池，引用计数 +1。
        """
        logger = get_logger(f'{cls._POOL_TYPE}.pool')
        key = cls._config_key(**config)

        async with cls._pool_lock:
            if key in cls._pools:
                cls._ref_counts[key] = cls._ref_counts.get(key, 0) + 1
                logger.debug(f"Reuse pool [{key}], ref_count={cls._ref_counts[key]}")
                return cls._pools[key]

            pool = await cls._create_pool_internal(**config)
            cls._pools[key] = pool
            cls._ref_counts[key] = 1
            logger.info(f"Create pool [{key}], ref_count=1")
            return pool

    @classmethod
    async def release_pool(cls, **config) -> None:
        """
        释放引用，引用计数归零时关闭连接池
        """
        logger = get_logger(f'{cls._POOL_TYPE}.pool')
        key = cls._config_key(**config)

        async with cls._pool_lock:
            if key not in cls._pools:
                return

            cls._ref_counts[key] -= 1
            logger.debug(f"Release pool [{key}], ref_count={cls._ref_counts[key]}")

            if cls._ref_counts[key] <= 0:
                pool = cls._pools.pop(key, None)
                cls._ref_counts.pop(key, None)
                if pool:
                    await cls._close_pool_internal(pool)
                    logger.info(f"Closed pool [{key}] (ref_count reached 0)")

    @classmethod
    async def close_all(cls) -> None:
        """关闭所有连接池（通常在进程退出时调用）"""
        logger = get_logger(f'{cls._POOL_TYPE}.pool')
        async with cls._pool_lock:
            count = len(cls._pools)
            for key, pool in list(cls._pools.items()):
                try:
                    await cls._close_pool_internal(pool)
                except Exception as e:
                    logger.error(f"Close pool [{key}] failed: {e}")
                cls._ref_counts.pop(key, None)
            cls._pools.clear()
            logger.info(f"All pools closed ({count} total)")

    @classmethod
    def get_pool_stats(cls) -> Dict[str, Any]:
        """获取连接池统计信息"""
        return {
            'pool_type': cls._POOL_TYPE,
            'active_pools': len(cls._pools),
            'pools': {
                key: {'ref_count': cls._ref_counts.get(key, 0)}
                for key in cls._pools
            }
        }
