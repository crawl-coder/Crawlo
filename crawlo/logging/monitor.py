#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
日志性能监控器
"""

import time
import threading
from typing import Dict, List
from collections import defaultdict, deque
from .manager import get_config


class LogPerformanceMonitor:
    """
    日志性能监控器
    用于监控日志系统的性能指标
    """
    
    def __init__(self):
        self._lock = threading.Lock()
        self._log_stats: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self._enabled = False
        
    def enable_monitoring(self):
        """启用性能监控"""
        with self._lock:
            self._enabled = True
            
    def disable_monitoring(self):
        """禁用性能监控"""
        with self._lock:
            self._enabled = False
            
    def record_log_event(self, logger_name: str, level: str, message: str):
        """
        记录日志事件
        
        Args:
            logger_name: Logger名称
            level: 日志级别
            message: 日志消息
        """
        if not self._enabled:
            return
            
        with self._lock:
            event = {
                'timestamp': time.time(),
                'level': level,
                'message_length': len(message),
                'thread_id': threading.get_ident()
            }
            self._log_stats[logger_name].append(event)
            
    def get_statistics(self, logger_name: str = None) -> Dict:
        """
        获取日志统计信息
        
        Args:
            logger_name: Logger名称，如果为None则返回所有统计信息
            
        Returns:
            统计信息字典
        """
        with self._lock:
            if logger_name:
                return self._calculate_stats(logger_name, self._log_stats[logger_name])
            else:
                result = {}
                for name, events in self._log_stats.items():
                    result[name] = self._calculate_stats(name, events)
                return result
                
    def _calculate_stats(self, logger_name: str, events: deque) -> Dict:
        """计算统计信息"""
        if not events:
            return {
                'logger_name': logger_name,
                'total_logs': 0,
                'log_rates': {},
                'avg_message_length': 0
            }
            
        # 计算日志级别分布
        level_counts = defaultdict(int)
        total_length = 0
        
        for event in events:
            level_counts[event['level']] += 1
            total_length += event['message_length']
            
        # 计算日志速率（每分钟）
        if len(events) > 1:
            time_span = events[-1]['timestamp'] - events[0]['timestamp']
            if time_span > 0:
                logs_per_minute = len(events) / (time_span / 60)
            else:
                logs_per_minute = len(events) * 60
        else:
            logs_per_minute = 0
            
        return {
            'logger_name': logger_name,
            'total_logs': len(events),
            'log_rates': {
                'per_minute': logs_per_minute
            },
            'level_distribution': dict(level_counts),
            'avg_message_length': total_length / len(events) if events else 0
        }
        
    def get_performance_report(self) -> str:
        """
        获取性能报告
        
        Returns:
            格式化的性能报告字符串
        """
        stats = self.get_statistics()
        
        report = ["=" * 50]
        report.append("日志系统性能报告")
        report.append("=" * 50)
        
        config = get_config()
        if config:
            report.append(f"日志文件: {config.file_path or 'N/A'}")
            report.append(f"文件启用: {config.file_enabled}")
            report.append(f"控制台启用: {config.console_enabled}")
            report.append("-" * 50)
        
        for logger_name, stat in stats.items():
            report.append(f"Logger: {logger_name}")
            report.append(f"  总日志数: {stat['total_logs']}")
            report.append(f"  日志速率: {stat['log_rates']['per_minute']:.2f} 条/分钟")
            report.append(f"  平均消息长度: {stat['avg_message_length']:.2f} 字符")
            
            if 'level_distribution' in stat:
                levels = ", ".join([f"{k}: {v}" for k, v in stat['level_distribution'].items()])
                report.append(f"  级别分布: {levels}")
            report.append("")
            
        return "\n".join(report)


# 全局实例
_log_monitor = LogPerformanceMonitor()


def get_monitor() -> LogPerformanceMonitor:
    """获取日志监控器实例"""
    return _log_monitor