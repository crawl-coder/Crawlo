#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
ApplicationContext — 框架全局状态统一容器
==========================================

通过 get_global_context() 访问单例上下文，替代分散的模块级全局变量。
reset_global_context() / set_global_context() 用于测试隔离和高级用例。
"""
import asyncio
import threading
import uuid
from typing import Dict, Type, Optional, Set, Any
from dataclasses import dataclass, field

from crawlo.logging import get_logger


@dataclass
class ApplicationContext:
    """框架全局状态容器，持有所有组件单例引用，支持上下文隔离。"""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # ---- 核心注册表 ----
    spider_registry: Dict[str, Type['Spider']] = field(default_factory=dict)
    component_registry: Optional['ComponentRegistry'] = None
    initializer_registry: Optional['InitializerRegistry'] = None
    job_registry: Optional['JobRegistry'] = None
    framework: Optional['CrawloFramework'] = None
    components_registered: bool = False

    # ---- 框架管理器 ----
    error_handler_instance: Optional['ErrorHandler'] = None
    performance_monitor: Optional['PerformanceMonitor'] = None
    resource_managers: Dict[str, Any] = field(default_factory=dict)
    _monitor_manager: Optional['MonitorManager'] = None

    # ---- Bot 通知 ----
    notifier: Optional['NotificationDispatcher'] = None
    notifier_lock: Any = field(default_factory=threading.Lock)
    notification_handler: Optional['CrawlerNotificationHandler'] = None
    notification_handler_lock: Any = field(default_factory=threading.Lock)
    template_manager: Optional['MessageTemplateManager'] = None
    resource_monitor_manager: Optional['ResourceMonitorTemplateManager'] = None
    deduplicator: Optional['MessageDeduplicator'] = None
    deduplicator_lock: Any = field(default_factory=threading.Lock)
    bot_config_loaded: bool = False
    dingtalk_channel: Optional['DingTalkChannel'] = None
    feishu_channel: Optional['FeishuChannel'] = None
    wecom_channel: Optional['WeComChannel'] = None
    email_channel: Optional['EmailChannel'] = None
    sms_channel: Optional['SmsChannel'] = None

    # ---- MCP / 工具 ----
    quick_fetcher: Optional['QuickFetcher'] = None
    mcp_fetcher: Optional['QuickFetcher'] = None
    mcp_fetcher_lock: Any = field(default_factory=threading.Lock)
    redis_manager: Optional['GlobalRedisManager'] = None
    connection_pools: Dict[str, Any] = field(default_factory=dict)
    queue_error_handler: Optional['ErrorHandler'] = None

    # ---- 通用 ----
    resources: Set[Any] = field(default_factory=set)
    crawlers: Dict[str, Any] = field(default_factory=dict)

    # === Spider 注册表方法 ===

    def register_spider(self, name: str, spider_cls: Type['Spider']):
        """注册爬虫"""
        if name in self.spider_registry:
            raise ValueError(f"Spider '{name}' already registered")
        self.spider_registry[name] = spider_cls

    def get_spider(self, name: str) -> Optional[Type['Spider']]:
        """获取爬虫类"""
        return self.spider_registry.get(name)

    def unregister_spider(self, name: str) -> bool:
        """取消注册爬虫"""
        if name in self.spider_registry:
            del self.spider_registry[name]
            return True
        return False

    # === 资源追踪 ===

    def add_resource(self, resource: Any):
        """添加资源追踪"""
        self.resources.add(resource)

    def remove_resource(self, resource: Any) -> bool:
        """移除资源追踪"""
        if resource in self.resources:
            self.resources.discard(resource)
            return True
        return False

    async def cleanup(self):
        """清理上下文资源"""
        logger = get_logger(__name__)
        for resource in list(self.resources):
            try:
                if hasattr(resource, 'close'):
                    close_method = resource.close
                    if asyncio.iscoroutinefunction(close_method):
                        await close_method()
                    else:
                        close_method()
                elif hasattr(resource, 'cleanup'):
                    cleanup_method = resource.cleanup
                    if asyncio.iscoroutinefunction(cleanup_method):
                        await cleanup_method()
                    else:
                        cleanup_method()
            except asyncio.CancelledError:
                logger.warning(f"Resource cleanup cancelled for {type(resource).__name__}")
                break
            except Exception as e:
                logger.error(f"Error cleaning up resource {type(resource).__name__}: {e}", exc_info=True)

        self.resources.clear()
        self.spider_registry.clear()
        self.crawlers.clear()


# === 全局上下文访问（DCL 线程安全） ===

_global_context: Optional[ApplicationContext] = None
_context_lock = threading.Lock()


def get_global_context() -> ApplicationContext:
    """
    获取全局上下文（DCL 模式，线程安全，首次惰性创建）。

    DCL (Double-Checked Locking) 保证多线程并发首次调用时只创建一个实例：
    - 第一次检查（无锁）：99%+ 调用走此快速路径
    - 第二次检查（持锁）：确保只有一个线程创建实例
    """
    global _global_context
    if _global_context is None:
        with _context_lock:
            if _global_context is None:
                _global_context = ApplicationContext()
    return _global_context


def reset_global_context() -> None:
    """
    重置全局上下文（线程安全，仅用于测试隔离）。

    生产环境不应调用。
    """
    global _global_context
    with _context_lock:
        _global_context = ApplicationContext()


def set_global_context(ctx: ApplicationContext) -> None:
    """设置指定上下文（线程安全，高级用例）"""
    global _global_context
    with _context_lock:
        _global_context = ctx


async def create_context() -> ApplicationContext:
    """创建新的隔离上下文"""
    ctx = ApplicationContext()
    set_global_context(ctx)
    return ctx
