#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Redis 分布式队列测试脚本
用于诊断和修复分布式队列问题
"""
import asyncio
import sys
import traceback
import time
from crawlo.queue.backends.redis_priority import RedisPriorityQueue
from crawlo.http.request import Request


async def test_redis_connection():
    """测试 Redis 连接"""
    print("🔍 1. 测试 Redis 连接...")
    
    # 测试不同的 Redis URL 格式
    test_urls = [
        "redis://localhost:6379/0",
        "redis://:oscar&0503@127.0.0.1:6379/0",  # 带密码
        "redis://127.0.0.1:6379/0",               # 无密码
    ]
    
    for redis_url in test_urls:
        try:
            print(f"   尝试连接: {redis_url}")
            queue = RedisPriorityQueue(redis_url=redis_url)
            await queue.connect()
            print(f"   连接成功: {redis_url}")
            await queue.close()
            return redis_url
        except Exception as e:
            print(f"   连接失败: {redis_url} - {e}")
    
    raise ConnectionError("所有 Redis URL 都连接失败")


async def test_queue_operations(redis_url):
    """测试队列基本操作"""
    print("🔍 2. 测试队列基本操作...")
    
    queue = RedisPriorityQueue(
        redis_url=redis_url,
        queue_name="test:crawlo:requests",
        max_retries=2
    )
    
    try:
        await queue.connect()
        
        # 测试 put 操作
        test_request = Request(url="https://example.com", priority=5)
        print(f"   📤 插入请求: {test_request.url}")
        
        success = await queue.put(test_request, priority=5)
        if success:
            print("   插入成功")
        else:
            print("   插入失败")
            return False
            
        # 测试队列大小
        size = await queue.qsize()
        print(f"   队列大小: {size}")
        
        # 测试 get 操作
        print("   📥 获取请求...")
        retrieved_request = await queue.get(timeout=2.0)
        
        if retrieved_request:
            print(f"   获取成功: {retrieved_request.url}")
            # 测试 ack
            await queue.ack(retrieved_request)
            print("   ACK 成功")
        else:
            print("   获取失败（超时）")
            return False
            
        return True
        
    except Exception as e:
        print(f"   队列操作失败: {e}")
        traceback.print_exc()
        return False
    finally:
        await queue.close()


async def test_serialization():
    """测试序列化问题"""
    print("🔍 3. 测试 Request 序列化...")
    
    try:
        import pickle
        from crawlo.http.request import Request
        
        # 创建测试请求
        request = Request(
            url="https://example.com",
            method="GET",
            headers={"User-Agent": "Test"},
            meta={"test": "data"},
            priority=5
        )
        
        # 测试序列化
        serialized = pickle.dumps(request)
        print(f"   序列化成功，大小: {len(serialized)} bytes")
        
        # 测试反序列化
        deserialized = pickle.loads(serialized)
        print(f"   反序列化成功: {deserialized.url}")
        
        return True
        
    except Exception as e:
        print(f"   序列化失败: {e}")
        traceback.print_exc()
        return False


async def test_concurrent_operations(redis_url):
    """测试并发操作"""
    print("🔍 4. 测试并发操作...")
    
    async def producer(queue, start_id):
        """生产者"""
        try:
            for i in range(5):
                request = Request(url=f"https://example{start_id + i}.com", priority=i)
                await queue.put(request, priority=i)
                await asyncio.sleep(0.1)
            print(f"   生产者 {start_id} 完成")
        except Exception as e:
            print(f"   生产者 {start_id} 失败: {e}")
    
    async def consumer(queue, consumer_id):
        """消费者"""
        consumed = 0
        try:
            for _ in range(3):  # 每个消费者处理3个请求
                request = await queue.get(timeout=5.0)
                if request:
                    await queue.ack(request)
                    consumed += 1
                    await asyncio.sleep(0.05)
                else:
                    break
            print(f"   消费者 {consumer_id} 处理了 {consumed} 个请求")
        except Exception as e:
            print(f"   消费者 {consumer_id} 失败: {e}")
    
    queue = RedisPriorityQueue(
        redis_url=redis_url,
        queue_name="test:concurrent:requests"
    )
    
    try:
        await queue.connect()
        
        # 并发运行生产者和消费者
        tasks = [
            producer(queue, 0),
            producer(queue, 10),
            consumer(queue, 1),
            consumer(queue, 2),
        ]
        
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # 检查剩余队列大小
        final_size = await queue.qsize()
        print(f"   最终队列大小: {final_size}")
        
        return True
        
    except Exception as e:
        print(f"   并发测试失败: {e}")
        return False
    finally:
        await queue.close()


async def main():
    """主测试函数"""
    print("开始 Redis 分布式队列诊断...")
    print("=" * 50)
    
    try:
        # 1. 测试连接
        redis_url = await test_redis_connection()
        
        # 2. 测试序列化
        if not await test_serialization():
            return
            
        # 3. 测试基本操作
        if not await test_queue_operations(redis_url):
            return
            
        # 4. 测试并发操作
        if not await test_concurrent_operations(redis_url):
            return
            
        print("=" * 50)
        print("所有测试通过！Redis 队列工作正常")
        
    except Exception as e:
        print("=" * 50)
        print(f"诊断失败: {e}")
        traceback.print_exc()
        
        # 提供解决建议
        print("\n🔧 可能的解决方案:")
        print("1. 检查 Redis 服务是否启动: redis-server")
        print("2. 检查 Redis 密码配置")
        print("3. 检查防火墙和端口 6379")
        print("4. 安装 Redis: pip install redis")
        print("5. 检查 Redis 配置文件中的 bind 设置")


if __name__ == "__main__":
    asyncio.run(main())