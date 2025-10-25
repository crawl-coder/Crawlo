#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
分布式场景下的多节点去重测试
==========================

测试目标：
1. 验证多个节点同时运行时，Redis 去重机制是否正常工作
2. 确认相同 URL 不会被多个节点重复处理
3. 验证 AioRedisFilter 在分布式场景下的一致性
4. 检查数据项去重管道的有效性

测试方法：
- 启动多个爬虫实例（模拟多节点）
- 使用相同的 Redis 配置
- 爬取相同的 URL 列表
- 统计实际处理的 URL 数量
- 验证是否存在重复处理

使用方式：
    python tests/distributed_dedup_test.py
"""

import asyncio
import sys
import os
import time
import redis
from pathlib import Path
from typing import List, Dict, Set
from collections import defaultdict

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from crawlo import Spider
from crawlo.network.request import Request
from crawlo.crawler import Crawler
from crawlo.settings.setting_manager import SettingManager as Settings


class DedupTestSpider(Spider):
    """专门用于测试去重的爬虫"""
    
    name = 'dedup_test_spider'
    
    # 测试 URL 列表（包含重复）
    test_urls = [
        'http://httpbin.org/delay/1',
        'http://httpbin.org/delay/2',
        'http://httpbin.org/delay/1',  # 重复
        'http://httpbin.org/html',
        'http://httpbin.org/json',
        'http://httpbin.org/html',  # 重复
        'http://httpbin.org/uuid',
        'http://httpbin.org/delay/1',  # 重复
        'http://httpbin.org/json',  # 重复
        'http://httpbin.org/uuid',  # 重复
    ]
    
    def __init__(self, instance_id: int = 0, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance_id = instance_id
        self.processed_urls: Set[str] = set()
        self.duplicate_count = 0
    
    def start_requests(self):
        """生成初始请求"""
        self.logger.info(f"[实例 {self.instance_id}] 开始生成请求")
        for url in self.test_urls:
            yield Request(
                url=url,
                callback=self.parse,
                meta={'instance_id': self.instance_id}
            )
    
    async def parse(self, response):
        """解析响应"""
        url = response.url
        instance_id = response.meta.get('instance_id', self.instance_id)
        
        # 记录处理的 URL
        if url in self.processed_urls:
            self.duplicate_count += 1
            self.logger.warning(
                f"[实例 {instance_id}] ⚠️ 检测到重复处理: {url}"
            )
        else:
            self.processed_urls.add(url)
            self.logger.info(
                f"[实例 {instance_id}] ✓ 处理新URL: {url}"
            )
        
        # 返回数据项
        yield {
            'url': url,
            'instance_id': instance_id,
            'timestamp': time.time(),
            'status': response.status_code,  # 使用 status_code
        }


class DistributedDedupTest:
    """分布式去重测试管理器"""
    
    def __init__(self, num_instances: int = 3):
        """
        初始化测试
        
        :param num_instances: 模拟的节点数量
        """
        self.num_instances = num_instances
        self.redis_config = {
            'host': '127.0.0.1',
            'port': 6379,
            'db': 15,  # 使用独立的数据库避免污染
            'password': '',
        }
        self.project_name = 'dedup_test'
        self.results: Dict[int, Dict] = {}
        
    def _check_redis_connection(self) -> bool:
        """检查 Redis 连接"""
        try:
            r = redis.Redis(
                host=self.redis_config['host'],
                port=self.redis_config['port'],
                db=self.redis_config['db'],
                password=self.redis_config['password'] or None,
                decode_responses=True,
                socket_connect_timeout=5,
            )
            r.ping()
            print(f"✓ Redis 连接正常: {self.redis_config['host']}:{self.redis_config['port']}/{self.redis_config['db']}")
            return True
        except Exception as e:
            print(f"✗ Redis 连接失败: {e}")
            print(f"  请确保 Redis 服务正在运行")
            return False
    
    def _cleanup_redis(self):
        """清理 Redis 中的测试数据"""
        try:
            r = redis.Redis(
                host=self.redis_config['host'],
                port=self.redis_config['port'],
                db=self.redis_config['db'],
                password=self.redis_config['password'] or None,
                decode_responses=True,
            )
            
            # 清理所有与项目相关的 key
            pattern = f"crawlo:{self.project_name}:*"
            keys = list(r.scan_iter(pattern))
            if keys:
                deleted = r.delete(*keys)
                print(f"✓ 清理了 {deleted} 个 Redis 键")
            else:
                print(f"✓ 没有需要清理的 Redis 键")
                
        except Exception as e:
            print(f"⚠ Redis 清理失败: {e}")
    
    def _create_settings(self, instance_id: int) -> Settings:
        """创建爬虫配置"""
        settings = Settings()
        
        # 项目基本配置
        settings.set('PROJECT_NAME', self.project_name)
        settings.set('RUN_MODE', 'distributed')
        
        # Redis 配置
        settings.set('REDIS_HOST', self.redis_config['host'])
        settings.set('REDIS_PORT', self.redis_config['port'])
        settings.set('REDIS_DB', self.redis_config['db'])
        settings.set('REDIS_PASSWORD', self.redis_config['password'])
        
        # 构建 Redis URL
        if self.redis_config['password']:
            redis_url = (
                f"redis://:{self.redis_config['password']}@"
                f"{self.redis_config['host']}:{self.redis_config['port']}/{self.redis_config['db']}"
            )
        else:
            redis_url = (
                f"redis://{self.redis_config['host']}:{self.redis_config['port']}/{self.redis_config['db']}"
            )
        settings.set('REDIS_URL', redis_url)
        
        # 队列和过滤器配置
        settings.set('QUEUE_TYPE', 'redis')
        settings.set('FILTER_CLASS', 'crawlo.filters.aioredis_filter.AioRedisFilter')
        settings.set('DEFAULT_DEDUP_PIPELINE', 'crawlo.pipelines.redis_dedup_pipeline.RedisDedupPipeline')
        
        # 管道配置
        settings.set('PIPELINES', [
            'crawlo.pipelines.redis_dedup_pipeline.RedisDedupPipeline',
        ])
        
        # 并发配置
        settings.set('CONCURRENCY', 5)
        settings.set('DOWNLOAD_DELAY', 0.5)
        
        # 日志配置
        settings.set('LOG_LEVEL', 'INFO')
        settings.set('LOG_FILE', f'logs/dedup_test_instance_{instance_id}.log')
        settings.set('LOG_ENCODING', 'utf-8')
        settings.set('STATS_DUMP', True)
        
        # 禁用某些扩展以简化测试
        settings.set('EXTENSIONS', [])
        
        return settings
    
    async def _run_instance(self, instance_id: int):
        """运行单个爬虫实例"""
        print(f"\n{'='*60}")
        print(f"启动实例 {instance_id}")
        print(f"{'='*60}")
        
        # 创建配置
        settings = self._create_settings(instance_id)
        
        # 创建爬虫实例
        spider = DedupTestSpider(instance_id=instance_id)
        
        # 创建 Crawler（传入爬虫类而不是实例）
        crawler = Crawler(DedupTestSpider, settings)
        # 手动设置spider实例的instance_id
        crawler._spider = spider
        
        try:
            # 运行爬虫
            await crawler.crawl()
            
            # 收集统计信息
            stats = crawler.stats.get_stats() if crawler.stats else {}
            
            self.results[instance_id] = {
                'spider': spider,
                'stats': stats,
                'processed_urls': spider.processed_urls.copy(),
                'duplicate_count': spider.duplicate_count,
            }
            
            print(f"\n[实例 {instance_id}] 完成:")
            print(f"  - 处理的 URL 数量: {len(spider.processed_urls)}")
            print(f"  - 检测到的重复: {spider.duplicate_count}")
            
        except Exception as e:
            print(f"\n[实例 {instance_id}] 运行失败: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # 清理资源
            await crawler.close()
    
    async def run_parallel_test(self):
        """并行运行多个实例（真实的分布式场景）"""
        print(f"\n{'='*60}")
        print(f"并行测试：同时启动 {self.num_instances} 个实例")
        print(f"{'='*60}")
        
        # 创建所有任务
        tasks = [
            self._run_instance(i)
            for i in range(self.num_instances)
        ]
        
        # 并行执行
        await asyncio.gather(*tasks)
    
    async def run_sequential_test(self):
        """顺序运行多个实例（验证基本去重）"""
        print(f"\n{'='*60}")
        print(f"顺序测试：依次运行 {self.num_instances} 个实例")
        print(f"{'='*60}")
        
        for i in range(self.num_instances):
            await self._run_instance(i)
            # 等待一小段时间
            await asyncio.sleep(1)
    
    def _analyze_results(self):
        """分析测试结果"""
        print(f"\n{'='*60}")
        print(f"测试结果分析")
        print(f"{'='*60}")
        
        if not self.results:
            print("⚠ 没有收集到任何结果")
            return
        
        # 统计所有实例处理的 URL
        all_processed_urls: Set[str] = set()
        total_duplicates = 0
        total_requests = 0
        
        print(f"\n各实例统计:")
        for instance_id, result in sorted(self.results.items()):
            spider = result['spider']
            stats = result['stats']
            
            processed_count = len(result['processed_urls'])
            duplicate_count = result['duplicate_count']
            
            all_processed_urls.update(result['processed_urls'])
            total_duplicates += duplicate_count
            total_requests += stats.get('request/success_count', 0)
            
            print(f"\n  实例 {instance_id}:")
            print(f"    - 处理的唯一 URL: {processed_count}")
            print(f"    - 本地检测到的重复: {duplicate_count}")
            print(f"    - 成功的请求: {stats.get('request/success_count', 0)}")
            print(f"    - 失败的请求: {stats.get('request/failed_count', 0)}")
        
        # 检查 Redis 中的数据
        print(f"\n{'='*60}")
        print(f"Redis 数据检查:")
        print(f"{'='*60}")
        
        try:
            r = redis.Redis(
                host=self.redis_config['host'],
                port=self.redis_config['port'],
                db=self.redis_config['db'],
                password=self.redis_config['password'] or None,
                decode_responses=True,
            )
            
            # 检查过滤器指纹
            filter_key = f"crawlo:{self.project_name}:filter:fingerprint"
            filter_count = r.scard(filter_key)
            print(f"  - 过滤器指纹数量: {filter_count}")
            
            # 检查数据项指纹
            item_key = f"crawlo:{self.project_name}:item:fingerprint"
            item_count = r.scard(item_key)
            print(f"  - 数据项指纹数量: {item_count}")
            
            # 检查队列
            queue_key = f"crawlo:{self.project_name}:queue:requests"
            queue_len = r.zcard(queue_key)
            print(f"  - 剩余队列长度: {queue_len}")
            
        except Exception as e:
            print(f"  ⚠ Redis 检查失败: {e}")
        
        # 总体统计
        print(f"\n{'='*60}")
        print(f"总体统计:")
        print(f"{'='*60}")
        
        unique_urls_count = len(all_processed_urls)
        expected_unique_urls = len(set(DedupTestSpider.test_urls))
        
        print(f"  - 实例数量: {len(self.results)}")
        print(f"  - 所有实例处理的唯一 URL: {unique_urls_count}")
        print(f"  - 预期的唯一 URL 数量: {expected_unique_urls}")
        print(f"  - 总请求数: {total_requests}")
        print(f"  - 本地检测到的总重复: {total_duplicates}")
        
        # 验证去重效果
        print(f"\n{'='*60}")
        print(f"去重效果验证:")
        print(f"{'='*60}")
        
        # 关键验证：所有实例处理的 URL 总数应该等于唯一 URL 数
        if unique_urls_count == expected_unique_urls:
            print(f"  ✓ 测试通过！")
            print(f"    所有实例共处理了 {unique_urls_count} 个唯一 URL")
            print(f"    没有任何 URL 被多个节点重复处理")
            return True
        else:
            print(f"  ✗ 测试失败！")
            print(f"    预期处理 {expected_unique_urls} 个唯一 URL")
            print(f"    实际处理 {unique_urls_count} 个唯一 URL")
            
            # 检查是否有 URL 被遗漏或重复
            expected_urls = set(DedupTestSpider.test_urls)
            missing_urls = expected_urls - all_processed_urls
            
            if missing_urls:
                print(f"    遗漏的 URL: {missing_urls}")
            
            if unique_urls_count > expected_unique_urls:
                print(f"    可能存在重复处理")
            
            return False
    
    async def run(self, mode: str = 'parallel'):
        """
        运行测试
        
        :param mode: 测试模式 'parallel' 或 'sequential'
        """
        print(f"\n{'='*70}")
        print(f"分布式去重测试")
        print(f"{'='*70}")
        print(f"测试模式: {mode}")
        print(f"实例数量: {self.num_instances}")
        print(f"Redis: {self.redis_config['host']}:{self.redis_config['port']}/{self.redis_config['db']}")
        
        # 检查 Redis 连接
        if not self._check_redis_connection():
            print("\n⚠ Redis 不可用，测试终止")
            return False
        
        # 清理旧数据
        print(f"\n清理 Redis 旧数据...")
        self._cleanup_redis()
        
        # 运行测试
        try:
            if mode == 'parallel':
                await self.run_parallel_test()
            else:
                await self.run_sequential_test()
            
            # 等待一小段时间确保所有数据都写入 Redis
            await asyncio.sleep(2)
            
            # 分析结果
            return self._analyze_results()
            
        except Exception as e:
            print(f"\n✗ 测试执行失败: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            # 可选：测试后清理数据
            print(f"\n清理测试数据...")
            self._cleanup_redis()


async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='分布式去重测试')
    parser.add_argument(
        '--instances',
        type=int,
        default=3,
        help='模拟的节点数量（默认: 3）'
    )
    parser.add_argument(
        '--mode',
        choices=['parallel', 'sequential'],
        default='parallel',
        help='测试模式: parallel（并行）或 sequential（顺序）'
    )
    
    args = parser.parse_args()
    
    # 创建并运行测试
    test = DistributedDedupTest(num_instances=args.instances)
    success = await test.run(mode=args.mode)
    
    # 返回退出码
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    asyncio.run(main())
