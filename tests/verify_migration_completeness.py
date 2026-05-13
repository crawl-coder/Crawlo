#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
ApplicationContext 迁移 - 优化点验证脚本
检查文档中的所有优化点是否实现，是否产生新问题
"""
import sys
from crawlo.core.application import get_global_context, reset_global_context


def check_phase0():
    """检查 Phase 0: 基础设施加固"""
    print("\n" + "="*60)
    print("Phase 0: 基础设施加固")
    print("="*60)
    
    issues = []
    
    # 1. DCL 线程安全
    print("\n[1] DCL 线程安全检查...")
    import threading
    contexts = []
    def create_ctx():
        contexts.append(get_global_context())
    
    threads = [threading.Thread(target=create_ctx) for _ in range(10)]
    for t in threads: t.start()
    for t in threads: t.join()
    
    if all(c is contexts[0] for c in contexts):
        print("   ✅ DCL 线程安全：10 线程获取同一实例")
    else:
        issues.append("❌ DCL 失败：创建了多个实例")
        print("   ❌ DCL 失败")
    
    # 2. SpiderMeta 方案 A
    print("\n[2] SpiderMeta 方案 A 检查...")
    try:
        from crawlo.spider.spider import _DEFAULT_SPIDER_REGISTRY, get_global_spider_registry
        reset_global_context()
        ctx_registry = get_global_spider_registry()
        
        # 检查是否指向同一对象
        if ctx_registry is _DEFAULT_SPIDER_REGISTRY:
            print("   ✅ Spider registry 指向模块级 dict（完美）")
        elif ctx_registry == _DEFAULT_SPIDER_REGISTRY:
            print("   ⚠️ Spider registry 返回副本（向后兼容但测试困难）")
            issues.append("⚠️ Spider registry 返回副本，非原始对象")
        else:
            issues.append("❌ Spider registry 既不同一也不相等")
            print("   ❌ Spider registry 异常")
    except Exception as e:
        issues.append(f"❌ Spider registry 检查失败: {e}")
        print(f"   ❌ 检查失败: {e}")
    
    return issues


def check_phase1():
    """检查 Phase 1: 核心注册表"""
    print("\n" + "="*60)
    print("Phase 1: 核心注册表")
    print("="*60)
    
    issues = []
    
    # 1. ComponentRegistry
    print("\n[1] ComponentRegistry...")
    try:
        from crawlo.factories import get_component_registry
        reset_global_context()
        registry = get_component_registry()
        print(f"   ✅ 成功: {type(registry).__name__}")
    except ImportError as e:
        issues.append(f"❌ ComponentRegistry 导入失败: {e}")
        print(f"   ❌ 导入失败: {e}")
    except Exception as e:
        issues.append(f"❌ ComponentRegistry 异常: {e}")
        print(f"   ❌ 异常: {e}")
    
    # 2. InitializerRegistry
    print("\n[2] InitializerRegistry...")
    try:
        from crawlo.initialization.registry import get_initializer_registry
        reset_global_context()
        registry = get_initializer_registry()
        print(f"   ✅ 成功: {type(registry).__name__}")
    except ImportError:
        # 检查实际函数名
        try:
            from crawlo.initialization.registry import get_registry
            print("   ⚠️ 函数名为 get_registry()，非 get_initializer_registry()")
            issues.append("⚠️ InitializerRegistry 函数名不一致")
        except Exception as e:
            issues.append(f"❌ InitializerRegistry 完全失败: {e}")
            print(f"   ❌ 失败: {e}")
    except Exception as e:
        issues.append(f"❌ InitializerRegistry 异常: {e}")
        print(f"   ❌ 异常: {e}")
    
    # 3. JobRegistry
    print("\n[3] JobRegistry...")
    try:
        from crawlo.scheduling.registry import get_job_registry
        reset_global_context()
        registry = get_job_registry()
        print(f"   ✅ 成功: {type(registry).__name__}")
    except Exception as e:
        issues.append(f"❌ JobRegistry 异常: {e}")
        print(f"   ❌ 异常: {e}")
    
    # 4. CrawloFramework
    print("\n[4] CrawloFramework...")
    try:
        from crawlo.framework import get_framework
        reset_global_context()
        framework = get_framework()
        print(f"   ✅ 成功: {type(framework).__name__}")
    except Exception as e:
        issues.append(f"❌ CrawloFramework 异常: {e}")
        print(f"   ❌ 异常: {e}")
    
    return issues


def check_phase2():
    """检查 Phase 2: 框架管理器"""
    print("\n" + "="*60)
    print("Phase 2: 框架管理器")
    print("="*60)
    
    issues = []
    
    # 1. LogManager
    print("\n[1] LogManager...")
    try:
        from crawlo.logging.manager import configure
        print("   ✅ configure() 可用")
    except Exception as e:
        issues.append(f"❌ LogManager 异常: {e}")
        print(f"   ❌ 异常: {e}")
    
    # 2. MonitorManager
    print("\n[2] MonitorManager...")
    try:
        from crawlo.extension.monitor.monitor_manager import get_monitor_manager
        reset_global_context()
        manager = get_monitor_manager()
        print(f"   ✅ 成功: {type(manager).__name__}")
    except Exception as e:
        issues.append(f"❌ MonitorManager 异常: {e}")
        print(f"   ❌ 异常: {e}")
    
    # 3. ErrorHandler
    print("\n[3] ErrorHandler...")
    try:
        from crawlo.utils.error_handler import _get_global_error_handler
        reset_global_context()
        handler = _get_global_error_handler()
        print(f"   ✅ 成功: {type(handler).__name__}")
        
        # 检查向后兼容
        try:
            from crawlo.utils.error_handler import error_handler
            print("   ✅ 向后兼容：error_handler 变量存在")
        except ImportError:
            print("   ⚠️ 向后兼容：error_handler 变量不存在")
            issues.append("⚠️ ErrorHandler 缺少向后兼容变量")
    except Exception as e:
        issues.append(f"❌ ErrorHandler 异常: {e}")
        print(f"   ❌ 异常: {e}")
    
    # 4. PerformanceMonitor
    print("\n[4] PerformanceMonitor...")
    try:
        from crawlo.extension.monitor.performance_monitor import get_performance_monitor
        reset_global_context()
        monitor = get_performance_monitor()
        print(f"   ✅ 成功: {type(monitor).__name__}")
    except ImportError:
        try:
            from crawlo.extension.monitor.performance_monitor import get_monitor
            print("   ⚠️ 函数名为 get_monitor()，非 get_performance_monitor()")
            issues.append("⚠️ PerformanceMonitor 函数名不一致")
        except Exception as e:
            issues.append(f"❌ PerformanceMonitor 完全失败: {e}")
            print(f"   ❌ 失败: {e}")
    except Exception as e:
        issues.append(f"❌ PerformanceMonitor 异常: {e}")
        print(f"   ❌ 异常: {e}")
    
    return issues


def check_phase3():
    """检查 Phase 3: Bot 通知模块"""
    print("\n" + "="*60)
    print("Phase 3: Bot 通知模块")
    print("="*60)
    
    issues = []
    
    modules = [
        ("Notifier", "crawlo.bot.core.notifier", "get_notifier"),
        ("Deduplicator", "crawlo.bot.utils.deduplicator", "get_deduplicator"),
        ("TemplateManager", "crawlo.bot.templates.manager", "get_template_manager"),
        ("NotificationHandler", "crawlo.bot.core.handlers", "get_notification_handler"),
    ]
    
    for name, module, func in modules:
        print(f"\n[{name}]...")
        try:
            mod = __import__(module, fromlist=[func])
            getter = getattr(mod, func)
            reset_global_context()
            instance = getter()
            print(f"   ✅ 成功: {type(instance).__name__}")
        except Exception as e:
            issues.append(f"❌ {name} 异常: {e}")
            print(f"   ❌ 异常: {e}")
    
    return issues


def check_phase4():
    """检查 Phase 4: MCP/工具类"""
    print("\n" + "="*60)
    print("Phase 4: MCP/工具类")
    print("="*60)
    
    issues = []
    
    # 1. QuickFetcher
    print("\n[1] QuickFetcher...")
    try:
        from crawlo.mcp.quick_fetcher import get_fetcher
        reset_global_context()
        fetcher = get_fetcher()
        # 检查是否是协程
        import asyncio
        if asyncio.iscoroutine(fetcher):
            print("   ⚠️ get_fetcher() 是协程，需要 await")
            issues.append("⚠️ QuickFetcher get_fetcher() 是 async 函数")
        else:
            print(f"   ✅ 成功: {type(fetcher).__name__}")
    except Exception as e:
        issues.append(f"❌ QuickFetcher 异常: {e}")
        print(f"   ❌ 异常: {e}")
    
    # 2. RedisManager
    print("\n[2] RedisManager...")
    try:
        from crawlo.utils.redis.pool import get_redis_manager
        reset_global_context()
        manager = get_redis_manager()
        print(f"   ✅ 成功: {type(manager).__name__}")
    except Exception as e:
        issues.append(f"❌ RedisManager 异常: {e}")
        print(f"   ❌ 异常: {e}")
    
    return issues


def check_new_issues():
    """检查是否产生新问题"""
    print("\n" + "="*60)
    print("新问题检查")
    print("="*60)
    
    issues = []
    
    # 1. 核心导入
    print("\n[1] 核心导入测试...")
    try:
        import crawlo.crawler
        print("   ✅ import crawlo.crawler 成功")
    except Exception as e:
        issues.append(f"❌ 核心导入失败: {e}")
        print(f"   ❌ 失败: {e}")
    
    # 2. 循环导入
    print("\n[2] 循环导入检查...")
    import subprocess
    result = subprocess.run(
        [sys.executable, "-c", "import crawlo.crawler"],
        capture_output=True,
        text=True
    )
    if result.returncode == 0:
        print("   ✅ 无循环导入")
    else:
        issues.append(f"❌ 可能存在循环导入: {result.stderr}")
        print(f"   ❌ 错误: {result.stderr[:100]}")
    
    # 3. 性能回退
    print("\n[3] 启动性能检查...")
    import time
    start = time.time()
    import importlib
    importlib.reload(sys.modules.get('crawlo.crawler', sys.modules['crawlo.crawler']))
    elapsed = time.time() - start
    if elapsed < 1.5:
        print(f"   ✅ 启动时间: {elapsed:.2f}s (< 1.5s)")
    else:
        issues.append(f"⚠️ 启动性能回退: {elapsed:.2f}s")
        print(f"   ⚠️ 启动时间: {elapsed:.2f}s (可能回退)")
    
    # 4. 旧测试兼容性
    print("\n[4] 旧测试兼容性检查...")
    try:
        from crawlo.utils.error_handler import ErrorHandler, error_handler
        print("   ✅ 旧测试导入兼容")
    except ImportError as e:
        issues.append(f"⚠️ 旧测试不兼容: {e}")
        print(f"   ⚠️ 不兼容: {e}")
    
    return issues


def main():
    """主函数"""
    print("="*60)
    print("ApplicationContext 迁移 - 优化点验证")
    print("="*60)
    
    all_issues = []
    
    # 检查各 Phase
    all_issues.extend(check_phase0())
    all_issues.extend(check_phase1())
    all_issues.extend(check_phase2())
    all_issues.extend(check_phase3())
    all_issues.extend(check_phase4())
    
    # 检查新问题
    all_issues.extend(check_new_issues())
    
    # 汇总
    print("\n" + "="*60)
    print("汇总报告")
    print("="*60)
    
    if not all_issues:
        print("\n✅ 所有优化点已实现，未产生新问题！")
        return 0
    else:
        print(f"\n发现 {len(all_issues)} 个问题：\n")
        for i, issue in enumerate(all_issues, 1):
            print(f"{i}. {issue}")
        
        # 分类
        errors = [i for i in all_issues if i.startswith("❌")]
        warnings = [i for i in all_issues if i.startswith("⚠️")]
        
        print(f"\n错误: {len(errors)} 个")
        print(f"警告: {len(warnings)} 个")
        
        return len(errors)


if __name__ == "__main__":
    sys.exit(main())
