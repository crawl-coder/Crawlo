# -*- coding: UTF-8 -*-
"""修复 Redis 队列编码问题的脚本"""

import sys
import os
import asyncio
import pickle

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from crawlo.utils.redis_connection_pool import get_redis_pool


async def fix_redis_encoding():
    """修复 Redis 编码问题"""
    print("正在修复 Redis 编码问题...")
    
    # 使用正确的配置连接 Redis
    redis_url = "redis://127.0.0.1:6379/2"
    
    try:
        # 获取连接池
        pool = get_redis_pool(
            redis_url,
            encoding='utf-8',
            decode_responses=False  # 重要：不自动解码响应
        )
        
        # 获取连接
        redis_client = await pool.get_connection()
        
        # 测试连接
        await redis_client.ping()
        print("✅ Redis 连接成功")
        
        # 清理可能存在的错误数据
        print("正在清理可能存在的错误数据...")
        
        # 获取所有相关的 keys
        keys = await redis_client.keys("crawlo:*")
        print(f"找到 {len(keys)} 个相关的 keys")
        
        # 删除所有相关的 keys
        if keys:
            await redis_client.delete(*keys)
            print("✅ 已清理所有相关的 Redis 数据")
        else:
            print("✅ 没有需要清理的数据")
            
        print("Redis 编码问题修复完成")
        return True
        
    except Exception as e:
        print(f"❌ 修复过程中出现错误: {e}")
        return False


if __name__ == '__main__':
    asyncio.run(fix_redis_encoding())