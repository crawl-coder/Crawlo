"""
Monitor Manager
Manages the lifecycle of monitoring extensions to avoid duplicate instance creation
"""
import asyncio
import threading
from typing import Dict, Optional, Any

from crawlo.logging import get_logger


class MonitorManager:
    """
    监控管理器，确保每个类型的监控在进程中只运行一个实例
    """
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.monitors: Dict[str, Any] = {}
            self._initialized = True
    
    def register_monitor(self, monitor_type: str, monitor_instance: Any) -> bool:
        """
        注册监控实例，如果已存在则返回False
        
        Args:
            monitor_type: 监控类型标识
            monitor_instance: 监控实例
            
        Returns:
            bool: True表示新注册，False表示已存在
        """
        if monitor_type in self.monitors:
            return False
        self.monitors[monitor_type] = monitor_instance
        return True
    
    def unregister_monitor(self, monitor_type: str) -> bool:
        """
        注销监控实例
        
        Args:
            monitor_type: 监控类型标识
            
        Returns:
            bool: True表示成功注销，False表示不存在
        """
        if monitor_type in self.monitors:
            del self.monitors[monitor_type]
            return True
        return False
    
    def get_monitor(self, monitor_type: str) -> Optional[Any]:
        """
        获取监控实例
        
        Args:
            monitor_type: 监控类型标识
            
        Returns:
            监控实例或None
        """
        return self.monitors.get(monitor_type)
    
    def stop_all_monitors(self):
        """Stop all monitor instances"""
        logger = get_logger(__name__)
        for monitor in self.monitors.values():
            if hasattr(monitor, 'stop'):
                try:
                    monitor.stop()
                except Exception as e:
                    logger.error(f"Error stopping monitor: {e}")
        self.monitors.clear()
    
    def cleanup(self):
        """Clean up all monitor instances, used when program exits"""
        for monitor_type, monitor in list(self.monitors.items()):
            if hasattr(monitor, 'task') and monitor.task:
                # Cancel monitor task
                monitor.task.cancel()
            # Remove from monitor manager
            self.unregister_monitor(monitor_type)


# 全局监控管理器实例
monitor_manager = MonitorManager()
