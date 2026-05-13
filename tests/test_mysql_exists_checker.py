#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
MySQLExistsChecker 独立测试脚本
测试连接池、并发查询、性能等
"""
import asyncio
import time
from crawlo.helpers.mysql_exists_checker import MySQLExistsChecker


async def test_basic_functionality():
    """测试基本功能"""
    print("\n" + "="*60)
    print("测试 1: 基本功能")
    print("="*60)
    
    # 创建检查器
    config = {
        'host': '127.0.0.1',
        'port': 3306,
        'user': 'root',
        'password': 'oscar&0503',
        'db': 'crawlo_db',
        'minsize': 2,
        'maxsize': 10,
    }
    
    checker = MySQLExistsChecker(config)
    
    try:
        # 测试查询
        sql = "SELECT 1 FROM ofweek_news LIMIT 1"
        exists = await checker.exists(sql)
        print(f"✅ 基本查询成功: exists={exists}")
        
        # 测试带参数的查询
        sql = "SELECT 1 FROM ofweek_news WHERE url = %s LIMIT 1"
        exists = await checker.exists(sql, ("https://example.com",))
        print(f"✅ 参数查询成功: exists={exists}")
        
    except Exception as e:
        print(f"❌ 查询失败: {e}")
    finally:
        await checker.close()


async def test_concurrent_queries():
    """测试并发查询"""
    print("\n" + "="*60)
    print("测试 2: 并发查询性能")
    print("="*60)
    
    config = {
        'host': '127.0.0.1',
        'port': 3306,
        'user': 'root',
        'password': 'oscar&0503',
        'db': 'crawlo_db',
        'minsize': 5,
        'maxsize': 20,  # 连接池大小
    }
    
    checker = MySQLExistsChecker(config)
    
    # 模拟 100 个并发查询
    total_queries = 100
    sql = "SELECT 1 FROM ofweek_news WHERE url = %s LIMIT 1"
    
    async def single_query(idx):
        url = f"https://example.com/test-{idx}"
        return await checker.exists(sql, (url,))
    
    start_time = time.time()
    
    try:
        # 并发执行所有查询
        tasks = [single_query(i) for i in range(total_queries)]
        results = await asyncio.gather(*tasks)
        
        elapsed = time.time() - start_time
        success_count = sum(1 for r in results if r is not None)
        
        print(f"✅ 并发查询完成:")
        print(f"   - 总查询数: {total_queries}")
        print(f"   - 成功数: {success_count}")
        print(f"   - 耗时: {elapsed:.2f}s")
        print(f"   - QPS: {total_queries / elapsed:.2f}")
        print(f"   - 连接池大小: {config['maxsize']}")
        
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"❌ 并发查询失败: {e}")
        print(f"   - 耗时: {elapsed:.2f}s")
    finally:
        await checker.close()


async def test_connection_pool_limits():
    """测试连接池限制"""
    print("\n" + "="*60)
    print("测试 3: 连接池限制测试")
    print("="*60)
    
    pool_sizes = [5, 10, 20, 30]
    total_queries = 50
    
    for pool_size in pool_sizes:
        config = {
            'host': '127.0.0.1',
            'port': 3306,
            'user': 'root',
            'password': 'oscar&0503',
            'db': 'crawlo_db',
            'minsize': 2,
            'maxsize': pool_size,
        }
        
        checker = MySQLExistsChecker(config)
        sql = "SELECT 1 FROM ofweek_news WHERE url = %s LIMIT 1"
        
        async def single_query(idx):
            url = f"https://example.com/pool-{pool_size}-{idx}"
            return await checker.exists(sql, (url,))
        
        start_time = time.time()
        
        try:
            tasks = [single_query(i) for i in range(total_queries)]
            results = await asyncio.gather(*tasks)
            
            elapsed = time.time() - start_time
            print(f"✅ 连接池={pool_size:2d}: {total_queries} queries, {elapsed:.2f}s, QPS={total_queries/elapsed:.2f}")
            
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"❌ 连接池={pool_size:2d}: 失败, {elapsed:.2f}s, error={e}")
        finally:
            await checker.close()


async def test_stress_test():
    """压力测试：模拟真实爬虫场景"""
    print("\n" + "="*60)
    print("测试 4: 压力测试（模拟爬虫场景）")
    print("="*60)
    
    # 模拟爬虫配置
    config = {
        'host': '127.0.0.1',
        'port': 3306,
        'user': 'root',
        'password': 'oscar&0503',
        'db': 'crawlo_db',
        'minsize': 10,
        'maxsize': 30,
    }
    
    checker = MySQLExistsChecker(config)
    
    # 模拟 12 个并发（爬虫并发度）× 20 个条目 = 240 个查询
    concurrency = 12
    items_per_page = 20
    total_pages = 5
    total_queries = concurrency * items_per_page
    
    sql = "SELECT 1 FROM ofweek_news WHERE url = %s LIMIT 1"
    
    async def process_page(page_idx):
        """处理一个页面的所有条目"""
        tasks = []
        for item_idx in range(items_per_page):
            url = f"https://ee.ofweek.com/test-page{page_idx}-item{item_idx}"
            tasks.append(checker.exists(sql, (url,)))
        return await asyncio.gather(*tasks)
    
    start_time = time.time()
    
    try:
        # 模拟并发处理多个页面
        page_tasks = [process_page(i) for i in range(total_pages)]
        all_results = await asyncio.gather(*page_tasks)
        
        elapsed = time.time() - start_time
        total_checked = sum(len(results) for results in all_results)
        
        print(f"✅ 压力测试完成:")
        print(f"   - 爬虫并发度: {concurrency}")
        print(f"   - 每页条目数: {items_per_page}")
        print(f"   - 总页数: {total_pages}")
        print(f"   - 总查询数: {total_checked}")
        print(f"   - 连接池大小: {config['maxsize']}")
        print(f"   - 耗时: {elapsed:.2f}s")
        print(f"   - QPS: {total_checked / elapsed:.2f}")
        
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"❌ 压力测试失败: {e}")
        print(f"   - 耗时: {elapsed:.2f}s")
    finally:
        await checker.close()


async def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("MySQLExistsChecker 测试套件")
    print("="*60)
    
    # 测试 1: 基本功能
    await test_basic_functionality()
    
    # 测试 2: 并发查询
    await test_concurrent_queries()
    
    # 测试 3: 连接池限制
    await test_connection_pool_limits()
    
    # 测试 4: 压力测试
    await test_stress_test()
    
    print("\n" + "="*60)
    print("所有测试完成！")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
