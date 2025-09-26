#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Crawlo高级工具独立演示脚本
=====================

此脚本演示了Crawlo框架中各种高级工具的独立使用方法，
无需运行完整的爬虫即可了解工具的使用方式。
"""

import asyncio
import sys
import os

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from crawlo.utils.log import get_logger


def demo_factory_pattern():
    """演示工厂模式工具"""
    print("=== 工厂模式工具演示 ===")
    
    # 导入相关模块
    from crawlo.factories import (
        ComponentRegistry, 
        ComponentSpec, 
        get_component_registry,
        create_component
    )
    
    # logger = get_logger("FactoryDemo")
    
    # 定义组件类
    class DataProcessor:
        def __init__(self, processor_name="默认处理器"):
            self.name = processor_name
            # logger.info(f"创建数据处理器: {self.name}")
        
        def process(self, data):
            return f"{self.name} 处理了: {data}"
    
    # 获取全局组件注册表
    registry = get_component_registry()
    
    # 注册组件
    def create_processor(**kwargs):
        return DataProcessor(**kwargs)
    
    registry.register(ComponentSpec(
        name='data_processor',
        component_type=DataProcessor,
        factory_func=create_processor,
        dependencies=[],
        singleton=True
    ))
    
    # 使用工厂创建组件
    processor1 = create_component('data_processor', processor_name="处理器1")
    processor2 = create_component('data_processor', processor_name="处理器2")
    
    # 由于是单例模式，两个实例应该是相同的
    print(f"处理器1: {processor1.process('数据A')}")
    print(f"处理器2: {processor2.process('数据B')}")
    print(f"是否为同一实例: {processor1 is processor2}")
    
    print()


def demo_batch_processor():
    """演示批处理工具"""
    print("=== 批处理工具演示 ===")
    
    from crawlo.utils.batch_processor import BatchProcessor, batch_process
    import time
    
    # logger = get_logger("BatchDemo")
    
    # 定义处理函数
    def process_item(item):
        time.sleep(0.01)  # 模拟处理时间
        return f"处理完成: {item}"
    
    # 创建大量数据
    data = [f"项目_{i}" for i in range(200)]
    
    # 使用便捷函数进行批处理
    print("使用便捷函数进行批处理...")
    start_time = time.time()
    results = batch_process(
        items=data,
        processor_func=process_item,
        batch_size=50,
        max_concurrent_batches=3
    )
    end_time = time.time()
    
    print(f"处理了 {len(results)} 个项目，耗时: {end_time - start_time:.2f}秒")
    print(f"前5个结果: {results[:5]}")
    
    print()


async def demo_controlled_spider():
    """演示受控爬虫工具"""
    print("=== 受控爬虫工具演示 ===")
    
    from crawlo.utils.controlled_spider_mixin import ControlledRequestMixin
    from crawlo.network import Request
    
    class MockSpider(ControlledRequestMixin):
        def __init__(self):
            ControlledRequestMixin.__init__(self)
            self.name = "mock_spider"
            self.processed_requests = []
            
            # 配置受控生成参数
            self.max_pending_requests = 10
            self.batch_size = 5
            self.generation_interval = 0.01
        
        def _original_start_requests(self):
            """提供原始的大量请求"""
            for i in range(50):
                yield Request(url=f'https://example.com/page/{i}', meta={'id': i})
    
    spider = MockSpider()
    
    # 模拟处理请求
    print("开始受控请求生成...")
    count = 0
    for request in spider.start_requests():
        count += 1
        spider.processed_requests.append(request)
        if count >= 20:  # 只处理前20个
            break
    
    print(f"生成了 {len(spider.processed_requests)} 个请求")
    print(f"前5个请求URL: {[r.url for r in spider.processed_requests[:5]]}")
    
    print()


def demo_large_scale_config():
    """演示大规模配置工具"""
    print("=== 大规模配置工具演示 ===")
    
    from crawlo.utils.large_scale_config import LargeScaleConfig, apply_large_scale_config
    
    # 演示不同配置类型
    configs = {
        "保守配置": LargeScaleConfig.conservative_config(concurrency=8),
        "平衡配置": LargeScaleConfig.balanced_config(concurrency=16),
        "激进配置": LargeScaleConfig.aggressive_config(concurrency=32),
        "内存优化配置": LargeScaleConfig.memory_optimized_config(concurrency=12)
    }
    
    for config_name, config in configs.items():
        print(f"\n{config_name}:")
        print(f"  并发数: {config['CONCURRENCY']}")
        print(f"  队列容量: {config['SCHEDULER_MAX_QUEUE_SIZE']}")
        print(f"  下载延迟: {config['DOWNLOAD_DELAY']}秒")
    
    # 演示在字典中应用配置
    settings = {}
    apply_large_scale_config(settings, "balanced", 20)
    print(f"\n应用平衡配置(20并发)后的设置:")
    print(f"  并发数: {settings['CONCURRENCY']}")
    print(f"  队列容量: {settings['SCHEDULER_MAX_QUEUE_SIZE']}")
    
    print()


def demo_large_scale_helper():
    """演示大规模爬虫辅助工具"""
    print("=== 大规模爬虫辅助工具演示 ===")
    
    from crawlo.utils.large_scale_helper import (
        LargeScaleHelper, 
        ProgressManager, 
        MemoryOptimizer
    )
    import tempfile
    import json
    
    # 1. LargeScaleHelper 演示
    print("1. LargeScaleHelper 演示:")
    helper = LargeScaleHelper(batch_size=25, checkpoint_interval=100)
    
    # 处理大量数据
    large_data = list(range(150))
    batch_count = 0
    total_items = 0
    
    for batch in helper.batch_iterator(large_data):
        batch_count += 1
        total_items += len(batch)
        print(f"  批次 {batch_count}: 处理 {len(batch)} 个项目")
    
    print(f"  总共处理 {batch_count} 个批次，{total_items} 个项目")
    
    # 2. ProgressManager 演示
    print("\n2. ProgressManager 演示:")
    with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as tmp:
        progress_file = tmp.name
    
    progress_manager = ProgressManager(progress_file=progress_file)
    
    # 保存进度
    progress_data = {
        'processed_count': 1250,
        'timestamp': __import__('time').time(),
        'checkpoint': 'middle'
    }
    progress_manager.save_progress(progress_data)
    print(f"  进度已保存: {progress_data}")
    
    # 加载进度
    loaded_progress = progress_manager.load_progress()
    print(f"  进度已加载: {loaded_progress}")
    
    # 清理进度文件
    try:
        os.unlink(progress_file)
        print("  进度文件已清理")
    except:
        pass
    
    # 3. MemoryOptimizer 演示
    print("\n3. MemoryOptimizer 演示:")
    memory_optimizer = MemoryOptimizer(max_memory_mb=500)
    
    current_memory = memory_optimizer.get_current_memory_usage()
    print(f"  当前内存使用: {current_memory:.2f} MB")
    
    should_pause = memory_optimizer.should_pause_for_memory()
    print(f"  是否应该暂停: {should_pause}")
    
    print()


def main():
    """主函数"""
    print("Crawlo高级工具独立演示")
    print("=" * 50)
    
    # 获取要演示的工具
    if len(sys.argv) > 1:
        tool_name = sys.argv[1]
        tools = {
            'factory': demo_factory_pattern,
            'batch': demo_batch_processor,
            'controlled': demo_controlled_spider,
            'large_scale_config': demo_large_scale_config,
            'large_scale_helper': demo_large_scale_helper
        }
        
        if tool_name in tools:
            if tool_name == 'controlled':
                asyncio.run(tools[tool_name]())
            else:
                tools[tool_name]()
        else:
            print(f"未知工具: {tool_name}")
            print("可用工具: factory, batch, controlled, large_scale_config, large_scale_helper")
    else:
        # 演示所有工具
        demo_factory_pattern()
        demo_batch_processor()
        asyncio.run(demo_controlled_spider())
        demo_large_scale_config()
        demo_large_scale_helper()
        
        print("所有工具演示完成!")


if __name__ == '__main__':
    main()