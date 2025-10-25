#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
基于ofweek_standalone项目的资源管理测试
测试场景：
1. 单次运行
2. 连续运行3次（检测资源累积）
3. 资源清理验证
"""
import sys
import asyncio
import gc
import psutil
from pathlib import Path

# 确保能导入crawlo模块
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from crawlo.crawler import CrawlerProcess
from crawlo.utils.leak_detector import LeakDetector


def get_memory_info():
    """获取当前进程的内存信息"""
    process = psutil.Process()
    memory_info = process.memory_info()
    return {
        'rss_mb': memory_info.rss / 1024 / 1024,
        'vms_mb': memory_info.vms / 1024 / 1024,
        'threads': process.num_threads(),
    }


def print_separator(title):
    """打印分隔线"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


async def test_single_run():
    """场景1：单次运行单个爬虫"""
    print_separator("场景1：单次运行单个爬虫")
    
    detector = LeakDetector(name="single_run")
    detector.set_baseline("启动前")
    
    before = get_memory_info()
    print(f"运行前: RSS={before['rss_mb']:.2f}MB, 线程={before['threads']}")
    
    try:
        process = CrawlerProcess()
        await process.crawl('of_week_standalone')
        
        detector.snapshot("爬虫运行后")
        
        # 垃圾回收
        gc.collect()
        await asyncio.sleep(0.5)
        
        detector.snapshot("垃圾回收后")
        
    except Exception as e:
        print(f"❌ 场景1失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    after = get_memory_info()
    print(f"运行后: RSS={after['rss_mb']:.2f}MB, 线程={after['threads']}")
    
    # 分析资源
    analysis = detector.analyze(threshold_mb=30.0)
    print(f"\n📊 资源变化:")
    changes = analysis.get('changes', {})
    print(f"  内存增长: {changes.get('memory_mb', 0):.2f} MB")
    print(f"  内存百分比: {changes.get('memory_percent', 0):.1f}%")
    print(f"  对象数变化: {changes.get('object_count', 0):+d}")
    print(f"  线程数变化: {changes.get('thread_count', 0):+d}")
    
    if analysis['potential_leaks']:
        print(f"\n⚠️  检测到 {len(analysis['potential_leaks'])} 个潜在问题:")
        for leak in analysis['potential_leaks']:
            severity = leak.get('severity', 'unknown')
            leak_type = leak.get('type', 'unknown')
            growth = leak.get('growth_mb', leak.get('growth', 0))
            print(f"  - {leak_type}: {growth} (严重程度: {severity})")
        return False
    else:
        print("✅ 未检测到明显的资源泄露")
        return True


async def test_continuous_runs():
    """场景2：连续运行3次爬虫"""
    print_separator("场景2：连续运行3次爬虫（检测资源累积）")
    
    detector = LeakDetector(name="continuous_runs")
    detector.set_baseline("初始状态")
    
    memory_records = []
    
    for i in range(3):
        print(f"\n--- 第 {i+1} 次运行 ---")
        
        before = get_memory_info()
        memory_records.append(before['rss_mb'])
        print(f"运行前: {before['rss_mb']:.2f}MB")
        
        try:
            process = CrawlerProcess()
            await process.crawl('of_week_standalone')
            
            detector.snapshot(f"第{i+1}次运行后")
            
            # 垃圾回收
            gc.collect()
            await asyncio.sleep(1)
            
        except Exception as e:
            print(f"❌ 第{i+1}次运行失败: {e}")
            return False
        
        after = get_memory_info()
        print(f"运行后: {after['rss_mb']:.2f}MB (+{after['rss_mb']-before['rss_mb']:.2f}MB)")
    
    # 分析趋势
    print(f"\n📊 内存变化趋势:")
    for i, mem in enumerate(memory_records, 1):
        print(f"  第{i}次: {mem:.2f}MB")
    
    if len(memory_records) >= 3:
        growth_1_2 = memory_records[1] - memory_records[0]
        growth_2_3 = memory_records[2] - memory_records[1]
        
        print(f"\n增长分析:")
        print(f"  第1→2次: +{growth_1_2:.2f}MB")
        print(f"  第2→3次: +{growth_2_3:.2f}MB")
        
        if growth_2_3 > 30:
            print("⚠️  警告: 检测到持续的内存增长")
            return False
        else:
            print("✅ 内存增长趋于稳定")
            return True
    
    return True


async def test_resource_cleanup():
    """场景3：验证资源清理"""
    print_separator("场景3：验证资源清理完整性")
    
    detector = LeakDetector(name="cleanup_test")
    detector.set_baseline("启动前")
    
    try:
        process = CrawlerProcess()
        
        # 检查资源管理器集成
        crawler = getattr(process, '_crawler', None)
        if crawler and hasattr(crawler, '_resource_manager'):
            print("✅ 已集成 ResourceManager")
            rm = crawler._resource_manager  # type: ignore
            if hasattr(rm, 'get_registered_count'):
                count = rm.get_registered_count()
                print(f"📋 注册资源数: {count}")
        else:
            print("⚠️  未集成 ResourceManager")
        
        await process.crawl('of_week_standalone')
        
        detector.snapshot("运行后")
        
        # 强制垃圾回收
        gc.collect()
        await asyncio.sleep(0.5)
        
        detector.snapshot("清理后")
        
    except Exception as e:
        print(f"❌ 场景3失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 分析清理效果
    analysis = detector.analyze(threshold_mb=30.0)
    
    print(f"\n📊 清理效果:")
    changes = analysis.get('changes', {})
    print(f"  内存变化: {changes.get('memory_mb', 0):.2f} MB")
    print(f"  对象数变化: {changes.get('object_count', 0):+d}")
    
    if analysis['potential_leaks']:
        print(f"\n⚠️  发现 {len(analysis['potential_leaks'])} 个清理问题")
        return False
    else:
        print("✅ 资源清理完整")
        return True


async def main():
    """主测试函数"""
    print("🚀 资源管理测试 - ofweek_standalone项目")
    print(f"Python版本: {sys.version}")
    
    results = {}
    
    # 场景1
    results['场景1'] = await test_single_run()
    await asyncio.sleep(2)
    gc.collect()
    
    # 场景2
    results['场景2'] = await test_continuous_runs()
    await asyncio.sleep(2)
    gc.collect()
    
    # 场景3
    results['场景3'] = await test_resource_cleanup()
    
    # 汇总
    print_separator("测试结果汇总")
    
    all_passed = True
    for scenario, passed in results.items():
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{scenario}: {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 80)
    if all_passed:
        print("🎉 所有测试通过！资源管理功能正常。")
        return 0
    else:
        print("⚠️  部分测试失败，需要进一步优化。")
        return 1


if __name__ == '__main__':
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
