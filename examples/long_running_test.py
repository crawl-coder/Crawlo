#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
长期运行场景测试
模拟爬虫持续运行几个月的情况
"""

import asyncio
import time
import psutil
import gc
from typing import Dict, Any
import sys
import os
sys.path.insert(0, '/Users/oscar/projects/Crawlo')

from crawlo.utils.resource_manager import get_resource_manager, ResourceType
from crawlo.crawler import Crawler


class LongRunningMonitor:
    """长期运行监控器"""
    
    def __init__(self, name: str = "long_running_monitor"):
        self.name = name
        self.start_time = time.time()
        self.checkpoints = []
        self.resource_manager = get_resource_manager(name)
        
        # 注册到资源管理器
        self.resource_manager.register(
            self,
            self._cleanup,
            ResourceType.OTHER,
            f"monitor_{name}"
        )
    
    def record_checkpoint(self, description: str):
        """记录检查点"""
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        cpu_percent = process.cpu_percent()
        num_threads = process.num_threads()
        gc_objects = len(gc.get_objects())
        
        checkpoint = {
            'timestamp': time.time(),
            'description': description,
            'runtime_hours': (time.time() - self.start_time) / 3600,
            'memory_mb': memory_mb,
            'cpu_percent': cpu_percent,
            'num_threads': num_threads,
            'gc_objects': gc_objects,
            'active_resources': self.resource_manager._stats['active_resources']
        }
        
        self.checkpoints.append(checkpoint)
        print(f"[{checkpoint['runtime_hours']:.2f}h] {description}")
        print(f"  内存: {memory_mb:.2f}MB, CPU: {cpu_percent:.2f}%, "
              f"线程: {num_threads}, 对象: {gc_objects}, 资源: {checkpoint['active_resources']}")
    
    def analyze_trend(self) -> Dict[str, Any]:
        """分析资源使用趋势"""
        if len(self.checkpoints) < 2:
            return {'status': 'insufficient_data'}
        
        first = self.checkpoints[0]
        last = self.checkpoints[-1]
        
        runtime_hours = last['runtime_hours'] - first['runtime_hours']
        memory_growth = last['memory_mb'] - first['memory_mb']
        object_growth = last['gc_objects'] - first['gc_objects']
        resource_growth = last['active_resources'] - first['active_resources']
        
        # 计算每小时增长率
        memory_growth_rate = memory_growth / runtime_hours if runtime_hours > 0 else 0
        object_growth_rate = object_growth / runtime_hours if runtime_hours > 0 else 0
        
        # 判断是否存在泄漏风险
        has_memory_leak = memory_growth_rate > 1.0  # 每小时增长超过1MB
        has_object_leak = object_growth_rate > 1000  # 每小时增长超过1000个对象
        
        return {
            'status': 'leak_detected' if (has_memory_leak or has_object_leak) else 'healthy',
            'runtime_hours': runtime_hours,
            'memory_growth_mb': memory_growth,
            'memory_growth_rate_mb_per_hour': memory_growth_rate,
            'object_growth': object_growth,
            'object_growth_rate_per_hour': object_growth_rate,
            'resource_growth': resource_growth,
            'has_memory_leak': has_memory_leak,
            'has_object_leak': has_object_leak
        }
    
    def _cleanup(self, resource=None):
        """清理资源"""
        self.checkpoints.clear()
        print(f"监控器 {self.name} 已清理")


class SimulatedLongRunningTask:
    """模拟长期运行任务"""
    
    def __init__(self, task_id: int):
        self.task_id = task_id
        self.resource_manager = get_resource_manager(f"task_{task_id}")
        self.created_at = time.time()
        self.data_cache = {}
        
        # 模拟创建一些资源
        self._create_resources()
    
    def _create_resources(self):
        """创建模拟资源"""
        # 模拟HTTP会话
        class MockSession:
            def __init__(self, session_id):
                self.session_id = session_id
                self.closed = False
            
            def close(self):
                self.closed = True
        
        session = MockSession(f"session_{self.task_id}")
        self.resource_manager.register(
            session,
            lambda s: s.close(),
            ResourceType.SESSION,
            f"http_session_{self.task_id}"
        )
        
        # 模拟Redis连接
        class MockRedisConnection:
            def __init__(self, conn_id):
                self.conn_id = conn_id
                self.closed = False
            
            def close(self):
                self.closed = True
        
        redis_conn = MockRedisConnection(f"redis_{self.task_id}")
        self.resource_manager.register(
            redis_conn,
            lambda r: r.close(),
            ResourceType.REDIS_POOL,
            f"redis_conn_{self.task_id}"
        )
        
        # 模拟缓存数据
        for i in range(100):
            self.data_cache[f"key_{i}"] = f"value_{i}_{self.task_id}"
    
    async def do_work(self):
        """执行工作"""
        # 模拟工作负载
        await asyncio.sleep(0.01)
        
        # 偶尔创建新数据
        if len(self.data_cache) < 1000:
            key = f"dynamic_key_{len(self.data_cache)}_{int(time.time())}"
            self.data_cache[key] = f"dynamic_value_{len(self.data_cache)}"
    
    def get_status(self):
        """获取任务状态"""
        return {
            'task_id': self.task_id,
            'age_hours': (time.time() - self.created_at) / 3600,
            'cache_size': len(self.data_cache),
            'active_resources': len(self.resource_manager._resources)
        }


async def simulate_long_running(hours_to_run: float = 24.0):
    """模拟长期运行"""
    print(f"开始模拟长期运行测试 ({hours_to_run}小时)")
    
    # 创建监控器
    monitor = LongRunningMonitor("long_running_test")
    monitor.record_checkpoint("初始状态")
    
    # 创建任务列表
    tasks = []
    for i in range(10):
        task = SimulatedLongRunningTask(i)
        tasks.append(task)
    
    # 记录初始状态
    monitor.record_checkpoint("创建初始任务")
    
    # 模拟运行
    start_time = time.time()
    cycle_count = 0
    
    try:
        while (time.time() - start_time) < (hours_to_run * 3600):
            cycle_count += 1
            
            # 执行所有任务的工作
            work_tasks = [task.do_work() for task in tasks]
            await asyncio.gather(*work_tasks, return_exceptions=True)
            
            # 定期记录检查点
            if cycle_count % 100 == 0:
                monitor.record_checkpoint(f"运行周期 {cycle_count}")
                
                # 每1000周期清理一些老任务
                if cycle_count % 1000 == 0:
                    # 清理资源
                    for task in tasks:
                        await task.resource_manager.cleanup_all()
                    monitor.record_checkpoint(f"清理资源后")
                    
                    # 强制垃圾回收
                    gc.collect()
                    monitor.record_checkpoint(f"垃圾回收后")
            
            # 小幅延迟以控制运行速度
            await asyncio.sleep(0.1)
            
    except KeyboardInterrupt:
        print("用户中断测试")
    except Exception as e:
        print(f"测试过程中出错: {e}")
    
    # 最终状态检查
    monitor.record_checkpoint("测试结束")
    
    # 分析趋势
    trend = monitor.analyze_trend()
    print("\n资源使用趋势分析:")
    print(f"  运行时间: {trend.get('runtime_hours', 0):.2f} 小时")
    print(f"  内存增长: {trend.get('memory_growth_mb', 0):.2f} MB")
    print(f"  内存增长率: {trend.get('memory_growth_rate_mb_per_hour', 0):.2f} MB/小时")
    print(f"  对象增长: {trend.get('object_growth', 0)} 个")
    print(f"  对象增长率: {trend.get('object_growth_rate_per_hour', 0):.0f} 个/小时")
    print(f"  状态: {trend.get('status', 'unknown')}")
    
    # 清理所有资源
    for task in tasks:
        await task.resource_manager.cleanup_all()
    await monitor.resource_manager.cleanup_all()
    
    print(f"\n测试完成，共运行 {cycle_count} 个周期")
    return trend


if __name__ == "__main__":
    # 运行24小时的测试（可以调整时间）
    hours_to_run = float(os.environ.get('TEST_DURATION_HOURS', '0.1'))  # 默认1小时
    trend = asyncio.run(simulate_long_running(hours_to_run))
    
    # 根据分析结果返回状态码
    if trend.get('status') == 'leak_detected':
        print("⚠️  检测到潜在资源泄漏!")
        sys.exit(1)
    else:
        print("✅ 长期运行测试通过!")
        sys.exit(0)