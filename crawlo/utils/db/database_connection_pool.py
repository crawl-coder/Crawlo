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
    MySQLConnectionPoolManager,
    get_mysql_pool,
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
# 注意：get_mysql_pool 已从 mysql_connection_pool 模块导入，此处不再重复定义


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