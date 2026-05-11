"""
长时间压力测试脚本
测试 Crawlo 框架在长时间运行和高负载下的稳定性

测试场景:
1. 持续运行 24 小时 (可配置)
2. 处理 100 万请求 (可配置)
3. 监控资源使用 (CPU/内存/队列深度)
4. 检测性能退化

使用方法:
    python tests/stress_test_long_running.py --duration 24 --requests 1000000
    python tests/stress_test_long_running.py --quick  # 快速测试模式 (5分钟, 10000请求)
"""

import asyncio
import time
import json
import os
import sys
import psutil
import argparse
from datetime import datetime, timedelta
from typing import Dict, Any, List
from dataclasses import dataclass, field
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from crawlo.network.request import Request
from crawlo.queue.memory_queue import SpiderPriorityQueue
from crawlo.items import Item
from crawlo.logging import get_logger

logger = get_logger("StressTest")


@dataclass
class StressTestMetrics:
    """压力测试指标"""
    start_time: float = 0.0
    end_time: float = 0.0
    total_requests: int = 0
    processed_requests: int = 0
    failed_requests: int = 0
    items_generated: int = 0
    
    # 资源监控
    memory_samples: List[Dict[str, Any]] = field(default_factory=list)
    cpu_samples: List[Dict[str, Any]] = field(default_factory=list)
    queue_depth_samples: List[Dict[str, Any]] = field(default_factory=list)
    
    # 性能指标
    processing_times: List[float] = field(default_factory=list)
    throughput_samples: List[Dict[str, Any]] = field(default_factory=list)
    
    # 错误追踪
    errors: List[Dict[str, Any]] = field(default_factory=list)
    
    def record_memory(self, process: psutil.Process):
        """记录内存使用"""
        mem = process.memory_info()
        self.memory_samples.append({
            'timestamp': time.time(),
            'rss_mb': mem.rss / 1024 / 1024,
            'vms_mb': mem.vms / 1024 / 1024,
            'percent': process.memory_percent(),
        })
    
    def record_cpu(self, process: psutil.Process):
        """记录 CPU 使用"""
        self.cpu_samples.append({
            'timestamp': time.time(),
            'cpu_percent': process.cpu_percent(),
        })
    
    def record_queue_depth(self, queue_size: int):
        """记录队列深度"""
        self.queue_depth_samples.append({
            'timestamp': time.time(),
            'size': queue_size,
        })
    
    def record_processing_time(self, duration: float):
        """记录处理时间"""
        self.processing_times.append(duration)
    
    def get_avg_processing_time(self) -> float:
        """获取平均处理时间"""
        if not self.processing_times:
            return 0.0
        return sum(self.processing_times) / len(self.processing_times)
    
    def get_p95_processing_time(self) -> float:
        """获取 P95 处理时间"""
        if not self.processing_times:
            return 0.0
        sorted_times = sorted(self.processing_times)
        idx = int(len(sorted_times) * 0.95)
        return sorted_times[idx]
    
    def get_p99_processing_time(self) -> float:
        """获取 P99 处理时间"""
        if not self.processing_times:
            return 0.0
        sorted_times = sorted(self.processing_times)
        idx = int(len(sorted_times) * 0.99)
        return sorted_times[idx]
    
    def get_throughput(self) -> float:
        """获取吞吐量 (requests/sec)"""
        if self.end_time <= self.start_time:
            return 0.0
        duration = self.end_time - self.start_time
        return self.processed_requests / duration
    
    def get_memory_trend(self) -> str:
        """分析内存趋势"""
        if len(self.memory_samples) < 2:
            return "insufficient_data"
        
        first = self.memory_samples[0]['rss_mb']
        last = self.memory_samples[-1]['rss_mb']
        diff = last - first
        
        if diff > 100:  # 增长超过 100MB
            return f"increasing (+{diff:.2f}MB)"
        elif diff < -50:  # 减少超过 50MB
            return f"decreasing ({diff:.2f}MB)"
        else:
            return f"stable (diff: {diff:.2f}MB)"
    
    def generate_report(self) -> Dict[str, Any]:
        """生成测试报告"""
        duration = self.end_time - self.start_time if self.end_time > self.start_time else 0
        
        return {
            'test_duration': {
                'seconds': duration,
                'formatted': str(timedelta(seconds=int(duration))),
            },
            'requests': {
                'total': self.total_requests,
                'processed': self.processed_requests,
                'failed': self.failed_requests,
                'success_rate': f"{(self.processed_requests / max(self.total_requests, 1) * 100):.2f}%",
            },
            'throughput': {
                'requests_per_second': f"{self.get_throughput():.2f}",
                'requests_per_minute': f"{self.get_throughput() * 60:.2f}",
                'requests_per_hour': f"{self.get_throughput() * 3600:.2f}",
            },
            'latency': {
                'avg_ms': f"{self.get_avg_processing_time() * 1000:.2f}",
                'p95_ms': f"{self.get_p95_processing_time() * 1000:.2f}",
                'p99_ms': f"{self.get_p99_processing_time() * 1000:.2f}",
            },
            'memory': {
                'trend': self.get_memory_trend(),
                'initial_mb': f"{self.memory_samples[0]['rss_mb']:.2f}" if self.memory_samples else "N/A",
                'final_mb': f"{self.memory_samples[-1]['rss_mb']:.2f}" if self.memory_samples else "N/A",
                'peak_mb': f"{max(s['rss_mb'] for s in self.memory_samples):.2f}" if self.memory_samples else "N/A",
            },
            'items_generated': self.items_generated,
            'errors_count': len(self.errors),
        }


class StressTestRunner:
    """压力测试运行器"""
    
    def __init__(self, duration_hours: float = 24, total_requests: int = 1000000, 
                 concurrency: int = 100, report_interval: int = 60):
        """
        初始化压力测试
        
        Args:
            duration_hours: 测试持续时间 (小时)
            total_requests: 总请求数
            concurrency: 并发数
            report_interval: 报告间隔 (秒)
        """
        self.duration_hours = duration_hours
        self.total_requests = total_requests
        self.concurrency = concurrency
        self.report_interval = report_interval
        
        self.metrics = StressTestMetrics()
        self.queue = SpiderPriorityQueue(maxsize=total_requests)
        self.process = psutil.Process(os.getpid())
        
        self._stop_event = asyncio.Event()
        self._request_counter = 0
        
        logger.info(f"压力测试配置:")
        logger.info(f"  持续时间: {duration_hours} 小时")
        logger.info(f"  总请求数: {total_requests:,}")
        logger.info(f"  并发数: {concurrency}")
        logger.info(f"  报告间隔: {report_interval} 秒")
    
    async def generate_requests(self):
        """生成测试请求"""
        logger.info("开始生成请求...")
        
        for i in range(self.total_requests):
            if self._stop_event.is_set():
                break
            
            # 创建不同类型的请求
            request_type = i % 5
            if request_type == 0:
                req = Request(
                    url=f"http://example.com/api/data?page={i}",
                    method='GET',
                    meta={'request_id': i, 'type': 'api'},
                    priority=0,
                )
            elif request_type == 1:
                req = Request(
                    url=f"http://example.com/page/{i}",
                    method='GET',
                    meta={'request_id': i, 'type': 'page'},
                    priority=1,
                )
            elif request_type == 2:
                req = Request(
                    url=f"http://example.com/search?q=query{i}",
                    method='GET',
                    meta={'request_id': i, 'type': 'search'},
                    priority=2,
                )
            elif request_type == 3:
                req = Request(
                    url=f"http://api.example.com/submit",
                    method='POST',
                    meta={'request_id': i, 'type': 'form'},
                    priority=0,
                )
            else:
                req = Request(
                    url=f"http://example.com/item/{i}",
                    method='GET',
                    meta={'request_id': i, 'type': 'item'},
                    priority=3,
                )
            
            await self.queue.put((req.priority, req))
            self._request_counter += 1
            
            # 每 10000 个请求记录一次
            if (i + 1) % 10000 == 0:
                logger.info(f"已生成 {i + 1:,} / {self.total_requests:,} 请求")
        
        logger.info(f"请求生成完成: {self._request_counter:,} 个")
    
    async def process_request(self, worker_id: int):
        """处理单个请求"""
        while not self._stop_event.is_set():
            try:
                # 从队列获取请求
                try:
                    priority, request = await asyncio.wait_for(
                        self.queue.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    # 队列为空,检查是否完成
                    if self.metrics.processed_requests + self.metrics.failed_requests >= self.total_requests:
                        break
                    continue
                
                start_time = time.time()
                
                # 模拟请求处理 (网络延迟)
                await asyncio.sleep(0.001)  # 1ms 模拟延迟
                
                # 模拟生成 Item (20% 概率)
                if self._request_counter % 5 == 0:
                    item = Item()
                    item['url'] = request.url
                    item['data'] = f"Processed data for request {request.meta.get('request_id', 0)}"
                    item['timestamp'] = datetime.now().isoformat()
                    self.metrics.items_generated += 1
                
                # 模拟成功率 (99%)
                if self._request_counter % 100 != 0:
                    self.metrics.processed_requests += 1
                else:
                    self.metrics.failed_requests += 1
                    self.metrics.errors.append({
                        'timestamp': time.time(),
                        'error': 'Simulated failure',
                        'request_id': request.meta.get('request_id', 0),
                    })
                
                processing_time = time.time() - start_time
                self.metrics.record_processing_time(processing_time)
                
                self.queue.task_done()
                
            except Exception as e:
                self.metrics.failed_requests += 1
                self.metrics.errors.append({
                    'timestamp': time.time(),
                    'error': str(e),
                    'worker_id': worker_id,
                })
    
    async def monitor_resources(self):
        """监控资源使用"""
        logger.info("资源监控启动")
        
        while not self._stop_event.is_set():
            try:
                self.metrics.record_memory(self.process)
                self.metrics.record_cpu(self.process)
                
                queue_size = self.queue.qsize()
                self.metrics.record_queue_depth(queue_size)
                
                # 记录吞吐量
                if self.metrics.processed_requests > 0:
                    elapsed = time.time() - self.metrics.start_time
                    if elapsed > 0:
                        throughput = self.metrics.processed_requests / elapsed
                        self.metrics.throughput_samples.append({
                            'timestamp': time.time(),
                            'throughput': throughput,
                            'processed': self.metrics.processed_requests,
                        })
                
                await asyncio.sleep(self.report_interval)
            except Exception as e:
                logger.error(f"资源监控错误: {e}")
    
    async def print_progress(self):
        """打印进度报告"""
        logger.info("进度报告启动")
        
        while not self._stop_event.is_set():
            try:
                elapsed = time.time() - self.metrics.start_time
                progress = (self.metrics.processed_requests + self.metrics.failed_requests) / max(self.total_requests, 1) * 100
                
                logger.info(
                    f"\n{'='*60}\n"
                    f"进度报告 (运行时间: {timedelta(seconds=int(elapsed))})\n"
                    f"{'='*60}\n"
                    f"  请求处理: {self.metrics.processed_requests:,} / {self.total_requests:,} ({progress:.1f}%)\n"
                    f"  失败请求: {self.metrics.failed_requests:,}\n"
                    f"  生成 Items: {self.metrics.items_generated:,}\n"
                    f"  吞吐量: {self.metrics.get_throughput():.2f} req/s\n"
                    f"  平均延迟: {self.metrics.get_avg_processing_time() * 1000:.2f} ms\n"
                    f"  P95 延迟: {self.metrics.get_p95_processing_time() * 1000:.2f} ms\n"
                    f"  内存使用: {self.process.memory_info().rss / 1024 / 1024:.2f} MB\n"
                    f"  CPU 使用: {self.process.cpu_percent():.1f}%\n"
                    f"  队列深度: {self.queue.qsize()}\n"
                    f"{'='*60}"
                )
                
                await asyncio.sleep(self.report_interval)
            except Exception as e:
                logger.error(f"进度报告错误: {e}")
    
    async def run(self):
        """运行压力测试"""
        logger.info("="*60)
        logger.info("开始长时间压力测试")
        logger.info("="*60)
        
        self.metrics.start_time = time.time()
        
        # 初始化 CPU 监控
        self.process.cpu_percent()
        
        # 启动任务
        tasks = []
        
        # 1. 生成请求
        tasks.append(asyncio.create_task(self.generate_requests()))
        
        # 2. 处理请求 (并发 workers)
        for i in range(self.concurrency):
            tasks.append(asyncio.create_task(self.process_request(i)))
        
        # 3. 资源监控
        tasks.append(asyncio.create_task(self.monitor_resources()))
        
        # 4. 进度报告
        tasks.append(asyncio.create_task(self.print_progress()))
        
        # 等待所有任务完成或超时
        timeout_seconds = self.duration_hours * 3600
        try:
            await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=timeout_seconds
            )
        except asyncio.TimeoutError:
            logger.info("测试超时,停止所有任务")
            self._stop_event.set()
            
            # 等待任务完成
            await asyncio.gather(*tasks, return_exceptions=True)
        
        self.metrics.end_time = time.time()
        
        # 生成报告
        self._generate_final_report()
    
    def _generate_final_report(self):
        """生成最终报告"""
        report = self.metrics.generate_report()
        
        logger.info("\n" + "="*60)
        logger.info("压力测试完成 - 最终报告")
        logger.info("="*60)
        logger.info(json.dumps(report, indent=2, ensure_ascii=False))
        logger.info("="*60)
        
        # 保存报告
        report_file = f"stress_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_path = Path(__file__).parent / report_file
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"\n报告已保存到: {report_path}")
        
        # 检查内存泄漏
        memory_trend = self.metrics.get_memory_trend()
        if 'increasing' in memory_trend:
            logger.warning("\n⚠️  检测到内存增长趋势,可能存在内存泄漏!")
            logger.warning(f"   内存趋势: {memory_trend}")
        else:
            logger.info(f"\n✅ 内存使用正常: {memory_trend}")
        
        # 检查成功率
        success_rate = (self.metrics.processed_requests / max(self.metrics.total_requests, 1) * 100)
        if success_rate < 95:
            logger.warning(f"\n⚠️  成功率较低: {success_rate:.2f}%")
        else:
            logger.info(f"\n✅ 成功率正常: {success_rate:.2f}%")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Crawlo 长时间压力测试")
    parser.add_argument('--duration', type=float, default=24, help='测试持续时间 (小时)')
    parser.add_argument('--requests', type=int, default=1000000, help='总请求数')
    parser.add_argument('--concurrency', type=int, default=100, help='并发 workers 数')
    parser.add_argument('--interval', type=int, default=60, help='报告间隔 (秒)')
    parser.add_argument('--quick', action='store_true', help='快速测试模式 (5分钟, 10000请求)')
    
    args = parser.parse_args()
    
    if args.quick:
        args.duration = 5 / 60  # 5 分钟
        args.requests = 10000
        args.concurrency = 10
        args.interval = 30
        logger.info("使用快速测试模式")
    
    runner = StressTestRunner(
        duration_hours=args.duration,
        total_requests=args.requests,
        concurrency=args.concurrency,
        report_interval=args.interval,
    )
    
    try:
        asyncio.run(runner.run())
    except KeyboardInterrupt:
        logger.info("\n测试被用户中断")


if __name__ == "__main__":
    main()
