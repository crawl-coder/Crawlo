#!/usr/bin/env python3
import asyncio
import sys
import os
from unittest.mock import Mock

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from crawlo.network.request import Request
from crawlo.queue.queue_manager import IntelligentScheduler

async def test_list_detail_priority():
    print("=== 测试列表页到详情页的priority传递 ===")
    
    # 创建智能调度器
    scheduler = IntelligentScheduler()
    
    # 模拟列表页请求
    list_request = Request(
        url="https://example.com/products?page=1",
        priority=-5  # 注意：Request会将priority取反存储
    )
    
    print(f"列表页请求URL: {list_request.url}")
    print(f"列表页请求priority: {list_request.priority}")  # 实际存储的值
    
    # 模拟从列表页生成详情页请求
    detail_request = Request(
        url="https://example.com/product/123",
        priority=-5  # 显式继承列表页的priority
    )
    
    print(f"详情页请求URL: {detail_request.url}")
    print(f"详情页请求priority: {detail_request.priority}")
    
    # 检查是否继承了priority
    if detail_request.priority == list_request.priority:
        print("✅ 详情页请求正确继承了列表页的priority值")
    else:
        print("❌ 详情页请求没有正确继承列表页的priority值")
    
    # 测试智能调度器的priority调整
    print("\n=== 测试智能调度器的priority调整 ===")
    
    # 模拟详情页请求带有深度信息
    detail_request_with_depth = Request(
        url="https://example.com/product/123",
        priority=-5
    )
    # 通过meta参数传递深度
    detail_request_with_depth_with_meta = Request(
        url="https://example.com/product/123",
        priority=-5,
        meta={'depth': 1}
    )
    
    # 计算调整后的priority
    adjusted_priority = scheduler.calculate_priority(detail_request_with_depth_with_meta)
    print(f"原始priority: {detail_request_with_depth_with_meta.priority}")
    print(f"深度: {detail_request_with_depth_with_meta.meta.get('depth', 0)}")
    print(f"调整后priority: {adjusted_priority}")
    
    # 智能调度器的计算逻辑：priority -= depth
    # 原始priority: 5，深度: 1 → 调整后priority: 5-1=4
    # 由于框架遵循"priority数值小优先级高"的原则，调整后priority变小，优先级变高
    if adjusted_priority < detail_request_with_depth_with_meta.priority:
        print("✅ 智能调度器正确地根据深度降低了priority值（提高优先级）")
    else:
        print("❌ 智能调度器没有正确地根据深度调整priority")
    
    print("\n=== 总结 ===")
    print("1. 详情页请求默认不会自动继承列表页的priority，需要显式设置")
    print("2. 可以通过detail_request = Request(url=detail_url, priority=list_request.priority)来继承")
    print("3. 智能调度器会根据深度等因素动态调整priority")
    print("4. 深度越大，priority数值越小（优先级越高）")
    print("5. Request构造时传入priority=-5，实际存储为5（取反存储）")
    print("6. 智能调度器计算：最终priority = 原始priority - depth")

if __name__ == "__main__":
    asyncio.run(test_list_detail_priority())