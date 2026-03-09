#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
性能监控工具
提供系统性能监控和资源使用情况跟踪
"""
import asyncio
import time
from functools import wraps
from typing import Dict, Any

import psutil

from crawlo.utils.error_handler import ErrorHandler
from crawlo.logging import get_logger


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self, logger_name: str = __name__):
        self.logger = get_logger(logger_name)
        self.error_handler = ErrorHandler(logger_name)
        self.process = psutil.Process()
        self.start_time = time.time()
        
        # 性能指标
        self.metrics = {
            'cpu_usage': [],
            'memory_usage': [],
            'network_io': [],
            'disk_io': []
        }
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """
        获取系统性能指标
        
        Returns:
            包含各种性能指标的字典
        """
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # 内存使用情况
            memory = psutil.virtual_memory()
            
            # 网络IO
            net_io = psutil.net_io_counters()
            
            # 磁盘IO
            disk_io = psutil.disk_io_counters()
            
            # 进程特定信息
            process_memory = self.process.memory_info()
            process_cpu = self.process.cpu_percent()
            
            return {
                'timestamp': time.time(),
                'uptime': time.time() - self.start_time,
                'cpu': {
                    'percent': cpu_percent,
                    'count': psutil.cpu_count(),
                    'freq': psutil.cpu_freq()._asdict() if psutil.cpu_freq() else {}
                },
                'memory': {
                    'total': memory.total,
                    'available': memory.available,
                    'percent': memory.percent,
                    'used': memory.used,
                    'free': memory.free
                },
                'process': {
                    'memory_rss': process_memory.rss,
                    'memory_vms': process_memory.vms,
                    'cpu_percent': process_cpu,
                    'num_threads': self.process.num_threads(),
                    'num_fds': self.process.num_fds() if hasattr(self.process, 'num_fds') else 0
                },
                'network': {
                    'bytes_sent': net_io.bytes_sent,
                    'bytes_recv': net_io.bytes_recv,
                    'packets_sent': net_io.packets_sent,
                    'packets_recv': net_io.packets_recv
                },
                'disk': {
                    'read_bytes': disk_io.read_bytes,
                    'write_bytes': disk_io.write_bytes,
                    'read_count': disk_io.read_count,
                    'write_count': disk_io.write_count
                }
            }
        except Exception as e:
            self.error_handler.handle_error(
                e, 
                context="获取系统性能指标失败", 
                raise_error=False
            )
            return {}
    
    def log_system_metrics(self, detailed: bool = False):
        """
        记录系统性能指标
        
        Args:
            detailed: 是否记录详细信息
        """
        try:
            metrics = self.get_system_metrics()
            if not metrics:
                return
            
            # 基本信息
            basic_info = (
                f"系统性能指标 | "
                f"CPU: {metrics['cpu']['percent']:.1f}% | "
                f"内存: {metrics['memory']['percent']:.1f}% | "
                f"进程CPU: {metrics['process']['cpu_percent']:.1f}% | "
                f"进程内存: {metrics['process']['memory_rss'] / 1024 / 1024:.1f}MB"
            )
            self.logger.info(basic_info)
            
            # 详细信息
            if detailed:
                detailed_info = (
                    f"   详细信息:\n"
                    f"   - CPU: {metrics['cpu']['count']} 核心\n"
                    f"   - 内存: 总计 {metrics['memory']['total'] / 1024 / 1024 / 1024:.1f}GB, "
                    f"可用 {metrics['memory']['available'] / 1024 / 1024 / 1024:.1f}GB\n"
                    f"   - 网络: 发送 {metrics['network']['bytes_sent'] / 1024 / 1024:.1f}MB, "
                    f"接收 {metrics['network']['bytes_recv'] / 1024 / 1024:.1f}MB\n"
                    f"   - 磁盘: 读取 {metrics['disk']['read_bytes'] / 1024 / 1024:.1f}MB, "
                    f"写入 {metrics['disk']['write_bytes'] / 1024 / 1024:.1f}MB"
                )
                self.logger.debug(detailed_info)
        except Exception as e:
            self.error_handler.handle_error(
                e, 
                context="记录系统性能指标失败", 
                raise_error=False
            )
    
    def start_monitoring(self, interval: int = 60, detailed: bool = False):
        """
        开始定期监控
        
        Args:
            interval: 监控间隔（秒）
            detailed: 是否记录详细信息
        """
        async def monitor_loop():
            while True:
                try:
                    self.log_system_metrics(detailed)
                    await asyncio.sleep(interval)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    self.logger.error(f"监控循环错误: {e}")
        
        # 启动监控任务
        self.monitor_task = asyncio.create_task(monitor_loop())
        self.logger.info(f"开始性能监控，间隔: {interval}秒")
    
    async def stop_monitoring(self):
        """停止监控"""
        if hasattr(self, 'monitor_task') and self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
            self.logger.info("性能监控已停止")


class PerformanceTimer:
    """性能计时器"""
    
    def __init__(self, name: str = "timer"):
        self.name = name
        self.start_time = None
        self.end_time = None
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")
        self.error_handler = ErrorHandler(f"{__name__}.{self.__class__.__name__}")
    
    def start(self):
        """开始计时"""
        self.start_time = time.time()
        self.logger.debug(f"开始计时: {self.name}")
    
    def stop(self) -> float:
        """
        停止计时并返回耗时
        
        Returns:
            耗时（秒）
        """
        self.end_time = time.time()
        if self.start_time is None:
            raise RuntimeError("计时器未启动")
        
        elapsed = self.end_time - self.start_time
        self.logger.debug(f"停止计时: {self.name}, 耗时: {elapsed:.3f}秒")
        return elapsed
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            elapsed = self.stop()
            if exc_type is None:
                self.logger.info(f"{self.name} 执行成功，耗时: {elapsed:.3f}秒")
            else:
                self.logger.error(f"{self.name} 执行失败，耗时: {elapsed:.3f}秒")
        except Exception as e:
            self.error_handler.handle_error(
                e, 
                context=f"计时器退出时发生错误: {self.name}", 
                raise_error=False
            )


def performance_monitor_decorator(name: str = None, log_level: str = "INFO"):
    """
    装饰器：监控函数性能
    
    Args:
        name: 函数名称（如果为None则使用函数名）
        log_level: 日志级别
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            timer_name = name or f"{func.__module__}.{func.__name__}"
            logger = get_logger(timer_name)
            
            with PerformanceTimer(timer_name) as timer:
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            timer_name = name or f"{func.__module__}.{func.__name__}"
            logger = get_logger(timer_name)
            
            with PerformanceTimer(timer_name) as timer:
                return func(*args, **kwargs)
        
        # 根据函数是否为异步函数返回相应的包装器
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# 全局性能监控器实例
default_performance_monitor = PerformanceMonitor()


def monitor_performance(interval: int = 60, detailed: bool = False):
    """
    便捷函数：开始性能监控
    
    Args:
        interval: 监控间隔（秒）
        detailed: 是否记录详细信息
    """
    default_performance_monitor.start_monitoring(interval, detailed)


def get_current_metrics() -> Dict[str, Any]:
    """
    便捷函数：获取当前性能指标
    
    Returns:
        性能指标字典
    """
    return default_performance_monitor.get_system_metrics()