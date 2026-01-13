#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
数据库连接池聚合模块
====================

此模块提供向后兼容的聚合功能，用于支持现有代码和测试。
实际的连接池管理器位于专用模块中：
- MySQL 连接池: crawlo.utils.mysql_connection_pool
- MongoDB 连接池: crawlo.utils.mongo_connection_pool
"""

from typing import Dict, Any
from crawlo.logging import get_logger

# 导入已拆分的连接池管理器
from .mysql_connection_pool import (
    AiomysqlConnectionPoolManager,
    AsyncmyConnectionPoolManager,
    get_aiomysql_pool,
    get_asyncmy_pool,
    close_all_mysql_pools,
    get_mysql_pool_stats
)

from .mongo_connection_pool import (
    MongoConnectionPoolManager,
    get_mongo_client,
    close_all_mongo_clients,
    get_mongo_pool_stats
)


# 保留向后兼容性的便捷函数
async def get_mysql_pool(
    pool_type: str = 'asyncmy',
    host: str = 'localhost',
    port: int = 3306,
    user: str = 'root',
    password: str = '',
    db: str = 'crawlo',
    minsize: int = 3,
    maxsize: int = 10,
    **kwargs
):
    """
    获取 MySQL 连接池实例（便捷函数）
    
    Args:
        pool_type: 连接池类型 ('asyncmy' 或 'aiomysql')
        host: 数据库主机
        port: 数据库端口
        user: 数据库用户名
        password: 数据库密码
        db: 数据库名
        minsize: 最小连接数
        maxsize: 最大连接数
        **kwargs: 其他连接参数
        
    Returns:
        连接池实例
    """
    if pool_type == 'asyncmy':
        return await get_asyncmy_pool(
            host=host,
            port=port,
            user=user,
            password=password,
            db=db,
            minsize=minsize,
            maxsize=maxsize,
            **kwargs
        )
    elif pool_type == 'aiomysql':
        return await get_aiomysql_pool(
            host=host,
            port=port,
            user=user,
            password=password,
            db=db,
            minsize=minsize,
            maxsize=maxsize,
            **kwargs
        )
    else:
        raise ValueError(f"不支持的MySQL连接池类型: {pool_type}")


async def close_all_database_pools():
    """关闭所有数据库连接池"""
    logger = get_logger('DatabasePool')
    logger.info("开始关闭所有数据库连接池")
    
    # 关闭所有 MySQL 连接池
    await close_all_mysql_pools()
    
    # 关闭所有 MongoDB 客户端
    await close_all_mongo_clients()
    
    logger.info("所有数据库连接池已关闭")


def get_database_pool_stats() -> Dict[str, Any]:
    """获取所有数据库连接池的统计信息"""
    stats = {
        'mysql': get_mysql_pool_stats(),
        'mongo': get_mongo_pool_stats()
    }
    return stats