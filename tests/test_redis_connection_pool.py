#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Redis连接池优化工具测试
"""
import asyncio
import sys
import os
import traceback

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.utils.redis_manager import (
    RedisConnectionPool as OptimizedRedisConnectionPool, 
    RedisBatchOperationHelper,
    get_redis_pool,
    close_all_pools
)


async def test_connection_pool():
    """测试连接池基本功能"""
    print("1. 测试连接池基本功能...")
    
    try:
        # 创建连接池
        pool = OptimizedRedisConnectionPool(
            "redis://127.0.0.1:6379/15",  # 使用测试数据库
            max_connections=10,
            socket_connect_timeout=5,
            socket_timeout=30
        )
        
        # 获取连接
        redis_client = await pool.get_connection()
        
        # 测试连接
        await redis_client.ping()
        print("   Redis连接测试成功")
        
        # 获取统计信息
        stats = pool.get_stats()
        print(f"   连接池统计: {stats}")
        
        # 关闭连接池
        await pool.close()
        print("   连接池关闭成功")
        
        return True
        
    except Exception as e:
        print(f"   连接池测试失败: {e}")
        traceback.print_exc()
        return False


async def test_batch_operations():
    """测试批量操作功能"""
    print("2. 测试批量操作功能...")
    
    try:
        # 创建连接池和批量操作助手
        pool = get_redis_pool("redis://127.0.0.1:6379/15")
        redis_client = await pool.get_connection()
        helper = RedisBatchOperationHelper(redis_client, batch_size=5)
        
        # 准备测试数据
        test_key = "test_batch_key"
        await redis_client.delete(test_key)  # 清理旧数据
        
        # 测试批量执行
        operations = [
            ("set", f"{test_key}:1", "value1"),
            ("set", f"{test_key}:2", "value2"),
            ("set", f"{test_key}:3", "value3"),
            ("set", f"{test_key}:4", "value4"),
            ("set", f"{test_key}:5", "value5"),
            ("set", f"{test_key}:6", "value6"),
            ("set", f"{test_key}:7", "value7"),
        ]
        
        results = await helper.batch_execute(operations)
        print(f"   批量执行完成，结果数量: {len(results)}")
        
        # 验证结果
        for i in range(1, 8):
            value = await redis_client.get(f"{test_key}:{i}")
            assert value == f"value{i}", f"值不匹配: {value} != value{i}"
        
        print("   批量执行结果验证成功")
        
        # 测试批量Hash操作
        hash_key = "test_batch_hash"
        await redis_client.delete(hash_key)  # 清理旧数据
        
        # 批量设置Hash字段
        hash_items = {
            "field1": "value1",
            "field2": "value2",
            "field3": "value3",
            "field4": "value4",
            "field5": "value5",
            "field6": "value6",
        }
        
        count = await helper.batch_set_hash(hash_key, hash_items)
        print(f"   批量设置Hash字段，设置数量: {count}")
        
        # 批量获取Hash字段
        fields = ["field1", "field3", "field5", "field7"]  # 包含一个不存在的字段
        hash_values = await helper.batch_get_hash(hash_key, fields)
        print(f"   批量获取Hash字段，获取数量: {len(hash_values)}")
        
        # 验证获取的值
        assert hash_values["field1"] == "value1"
        assert hash_values["field3"] == "value3"
        assert hash_values["field5"] == "value5"
        assert "field7" not in hash_values  # 不存在的字段
        
        print("   批量Hash操作验证成功")
        
        # 清理测试数据
        await redis_client.delete(test_key, hash_key)
        
        return True
        
    except Exception as e:
        print(f"   批量操作测试失败: {e}")
        traceback.print_exc()
        return False


async def test_connection_context():
    """测试连接上下文管理器"""
    print("3. 测试连接上下文管理器...")
    
    try:
        # 创建连接池
        pool = get_redis_pool("redis://127.0.0.1:6379/15")
        
        # 使用上下文管理器
        async with pool.connection_context() as redis_client:
            # 测试连接
            await redis_client.ping()
            print("   连接上下文管理器测试成功")
            
            # 设置测试值
            await redis_client.set("context_test_key", "context_test_value")
            
            # 获取测试值
            value = await redis_client.get("context_test_key")
            assert value == "context_test_value"
            
            print("   上下文管理器操作验证成功")
        
        # 检查统计信息
        stats = pool.get_stats()
        print(f"   连接池统计: {stats}")
        
        # 清理测试数据
        redis_client = await pool.get_connection()
        await redis_client.delete("context_test_key")
        
        return True
        
    except Exception as e:
        print(f"   连接上下文管理器测试失败: {e}")
        traceback.print_exc()
        return False


async def test_singleton_pattern():
    """测试单例模式"""
    print("4. 测试单例模式...")
    
    try:
        # 获取同一个URL的连接池
        pool1 = get_redis_pool("redis://127.0.0.1:6379/15")
        pool2 = get_redis_pool("redis://127.0.0.1:6379/15")
        
        # 验证是否为同一个实例
        assert pool1 is pool2, "单例模式失败"
        print("   单例模式测试成功")
        
        # 获取不同URL的连接池
        pool3 = get_redis_pool("redis://127.0.0.1:6379/14")
        assert pool1 is not pool3, "不同URL应该创建不同实例"
        print("   不同URL创建不同实例测试成功")
        
        return True
        
    except Exception as e:
        print(f"   单例模式测试失败: {e}")
        traceback.print_exc()
        return False


async def test_concurrent_access():
    """测试并发访问"""
    print("5. 测试并发访问...")
    
    try:
        # 创建连接池
        pool = get_redis_pool("redis://127.0.0.1:6379/15", max_connections=20)
        
        async def worker(worker_id: int):
            """工作协程"""
            try:
                # 获取连接
                redis_client = await pool.get_connection()
                
                # 执行一些操作
                key = f"concurrent_test:{worker_id}"
                await redis_client.set(key, f"value_{worker_id}")
                value = await redis_client.get(key)
                
                # 验证操作结果
                assert value == f"value_{worker_id}"
                
                # 等待一小段时间
                await asyncio.sleep(0.1)
                
                # 删除测试键
                await redis_client.delete(key)
                
                return True
            except Exception as e:
                print(f"   工作协程 {worker_id} 失败: {e}")
                return False
        
        # 创建多个并发任务
        tasks = [worker(i) for i in range(10)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 检查结果
        success_count = sum(1 for result in results if result is True)
        print(f"   并发访问测试完成，成功: {success_count}/10")
        
        # 检查连接池统计
        stats = pool.get_stats()
        print(f"   连接池统计: {stats}")
        
        return success_count >= 8  # 允许少量失败
        
    except Exception as e:
        print(f"   并发访问测试失败: {e}")
        traceback.print_exc()
        return False


async def main():
    """主测试函数"""
    print("开始Redis连接池优化工具测试...")
    print("=" * 50)
    
    tests = [
        test_connection_pool,
        test_batch_operations,
        test_connection_context,
        test_singleton_pattern,
        test_concurrent_access
    ]
    
    passed = 0
    total = len(tests)
    
    for test_func in tests:
        try:
            if await test_func():
                passed += 1
                print(f"{test_func.__name__} 通过")
            else:
                print(f"{test_func.__name__} 失败")
        except Exception as e:
            print(f"{test_func.__name__} 异常: {e}")
        print()
    
    # 关闭所有连接池
    await close_all_pools()
    
    print("=" * 50)
    print(f"测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("所有测试通过！Redis连接池优化工具工作正常")
        return 0
    else:
        print("部分测试失败，请检查实现")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)