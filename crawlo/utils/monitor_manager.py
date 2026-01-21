"""
监控管理器
用于管理监控扩展的生命周期，避免实例重复创建
"""
import asyncio
import threading
from typing import Dict, Optional, Any


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
        """停止所有监控实例"""
        for monitor in self.monitors.values():
            if hasattr(monitor, 'stop'):
                try:
                    monitor.stop()
                except Exception as e:
                    print(f"Error stopping monitor: {e}")
        self.monitors.clear()
    
    def cleanup(self):
        """清理所有监控实例，用于程序退出时"""
        for monitor_type, monitor in list(self.monitors.items()):
            if hasattr(monitor, 'task') and monitor.task:
                # 取消监控任务
                monitor.task.cancel()
            # 从监控管理器中移除
            self.unregister_monitor(monitor_type)


# 全局监控管理器实例
monitor_manager = MonitorManager()