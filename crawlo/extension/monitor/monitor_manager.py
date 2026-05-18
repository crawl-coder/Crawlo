"""
Monitor Manager
Manages the lifecycle of monitoring extensions to avoid duplicate instance creation
"""
import threading
from typing import Dict, Optional, Any

from crawlo.logging import get_logger


class MonitorManager:
    """
    监控管理器，确保每个类型的监控在进程中只运行一个实例。
    所有 register/unregister/get 操作均受 Lock 保护，支持 asyncio 多协程并发安全。
    """

    _instance: Optional['MonitorManager'] = None
    _class_lock: threading.Lock = threading.Lock()

    def __new__(cls) -> 'MonitorManager':
        if cls._instance is None:
            with cls._class_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if not self._initialized:
            self._op_lock: threading.Lock = threading.Lock()
            self._monitors: Dict[str, Any] = {}
            self._initialized = True

    # ---- 线程安全的核心操作 ----

    def register_monitor(self, monitor_type: str, monitor_instance: Any) -> bool:
        """
        注册监控实例（线程安全），如果已存在则返回 False。

        Args:
            monitor_type: 监控类型标识
            monitor_instance: 监控实例

        Returns:
            bool: True 表示新注册，False 表示已存在
        """
        with self._op_lock:
            if monitor_type in self._monitors:
                return False
            self._monitors[monitor_type] = monitor_instance
            return True

    def unregister_monitor(self, monitor_type: str) -> bool:
        """
        注销监控实例（线程安全）。

        Args:
            monitor_type: 监控类型标识

        Returns:
            bool: True 表示成功注销，False 表示不存在
        """
        with self._op_lock:
            if monitor_type in self._monitors:
                del self._monitors[monitor_type]
                return True
            return False

    def get_monitor(self, monitor_type: str) -> Optional[Any]:
        """
        获取监控实例（线程安全）。

        Args:
            monitor_type: 监控类型标识

        Returns:
            监控实例或 None
        """
        with self._op_lock:
            return self._monitors.get(monitor_type)

    # ---- 批量操作 ----

    def stop_all_monitors(self) -> None:
        """Stop all monitor instances (thread-safe)."""
        logger = get_logger(__name__)
        with self._op_lock:
            monitors = list(self._monitors.values())
            self._monitors.clear()
        for monitor in monitors:
            if hasattr(monitor, 'stop'):
                try:
                    monitor.stop()
                except Exception as e:
                    logger.error(f"Error stopping monitor: {e}")

    def cleanup(self) -> None:
        """Clean up all monitor instances (thread-safe), used when program exits."""
        with self._op_lock:
            monitors = list(self._monitors.items())
            self._monitors.clear()
        for monitor_type, monitor in monitors:
            if hasattr(monitor, 'task') and monitor.task:
                try:
                    monitor.task.cancel()
                except Exception:
                    pass


def get_monitor_manager() -> MonitorManager:
    """获取全局 MonitorManager 单例（存储于 ApplicationContext）"""
    from crawlo.core.application import get_global_context
    ctx = get_global_context()
    if ctx._monitor_manager is None:
        ctx._monitor_manager = MonitorManager()
    return ctx._monitor_manager


# 向后兼容：模块级 monitor_manager 别名（惰性初始化）
def __getattr__(name: str):
    if name == 'monitor_manager':
        return get_monitor_manager()
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
