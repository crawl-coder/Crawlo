#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
资源泄露检测器
==============

提供资源泄露检测和分析功能
"""
import gc
import time
import psutil
from typing import Dict, List, Any, Optional
from collections import defaultdict

from crawlo.utils.log import get_logger


class ResourceSnapshot:
    """资源快照"""
    
    def __init__(self, name: str = ""):
        self.name = name
        self.timestamp = time.time()
        
        # 进程信息
        process = psutil.Process()
        self.memory_mb = process.memory_info().rss / 1024 / 1024
        self.cpu_percent = process.cpu_percent()
        self.num_threads = process.num_threads()
        self.num_fds = process.num_fds() if hasattr(process, 'num_fds') else 0
        
        # GC信息
        gc.collect()  # 先触发一次GC
        self.gc_objects = len(gc.get_objects())
        self.gc_stats = gc.get_stats()
        
        # 对象类型统计
        self.object_types = self._count_object_types()
    
    def _count_object_types(self, top_n: int = 20) -> Dict[str, int]:
        """统计前N个对象类型"""
        type_counts = defaultdict(int)
        
        for obj in gc.get_objects():
            type_name = type(obj).__name__
            type_counts[type_name] += 1
        
        # 返回前N个
        sorted_types = sorted(type_counts.items(), key=lambda x: x[1], reverse=True)
        return dict(sorted_types[:top_n])
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'name': self.name,
            'timestamp': self.timestamp,
            'memory_mb': round(self.memory_mb, 2),
            'cpu_percent': self.cpu_percent,
            'num_threads': self.num_threads,
            'num_fds': self.num_fds,
            'gc_objects': self.gc_objects,
            'object_types': self.object_types,
        }


class LeakDetector:
    """
    资源泄露检测器
    
    功能：
    1. 定期记录资源快照
    2. 分析资源增长趋势
    3. 识别可能的泄露点
    4. 生成诊断报告
    """
    
    def __init__(self, name: str = "default"):
        self.name = name
        self._snapshots: List[ResourceSnapshot] = []
        self._logger = get_logger(f"LeakDetector.{name}")
        self._baseline: Optional[ResourceSnapshot] = None
    
    def set_baseline(self, name: str = "baseline"):
        """设置基线快照"""
        self._baseline = ResourceSnapshot(name)
        self._logger.info(f"Baseline set: {self._baseline.memory_mb:.2f}MB")
    
    def snapshot(self, name: str = ""):
        """记录当前资源快照"""
        snapshot = ResourceSnapshot(name or f"snapshot_{len(self._snapshots)}")
        self._snapshots.append(snapshot)
        
        self._logger.debug(
            f"Snapshot '{snapshot.name}': {snapshot.memory_mb:.2f}MB, "
            f"{snapshot.gc_objects} objects"
        )
        
        return snapshot
    
    def analyze(self, threshold_mb: float = 10.0) -> Dict[str, Any]:
        """
        分析资源使用情况
        
        Args:
            threshold_mb: 内存增长阈值（MB），超过视为可能泄露
        
        Returns:
            分析结果
        """
        if len(self._snapshots) < 2:
            return {
                'status': 'insufficient_data',
                'message': 'Need at least 2 snapshots for analysis',
                'snapshot_count': len(self._snapshots),
                'changes': {
                    'memory_mb': 0.0,
                    'memory_percent': 0.0,
                    'objects': 0,
                    'objects_percent': 0.0,
                    'file_descriptors': 0,
                    'threads': 0,
                },
                'potential_leaks': [],
                'type_changes': [],
            }
        
        first = self._baseline or self._snapshots[0]
        latest = self._snapshots[-1]
        
        # 内存增长
        memory_growth_mb = latest.memory_mb - first.memory_mb
        memory_growth_percent = (memory_growth_mb / first.memory_mb) * 100 if first.memory_mb > 0 else 0
        
        # 对象数量增长
        object_growth = latest.gc_objects - first.gc_objects
        object_growth_percent = (object_growth / first.gc_objects) * 100 if first.gc_objects > 0 else 0
        
        # 文件描述符增长
        fd_growth = latest.num_fds - first.num_fds
        
        # 线程数增长
        thread_growth = latest.num_threads - first.num_threads
        
        # 检测泄露
        potential_leaks = []
        
        if memory_growth_mb > threshold_mb:
            potential_leaks.append({
                'type': 'memory',
                'severity': 'high' if memory_growth_mb > threshold_mb * 2 else 'medium',
                'growth_mb': round(memory_growth_mb, 2),
                'growth_percent': round(memory_growth_percent, 2),
            })
        
        if object_growth > 1000:
            potential_leaks.append({
                'type': 'objects',
                'severity': 'medium',
                'growth': object_growth,
                'growth_percent': round(object_growth_percent, 2),
            })
        
        if fd_growth > 10:
            potential_leaks.append({
                'type': 'file_descriptors',
                'severity': 'high',
                'growth': fd_growth,
            })
        
        if thread_growth > 5:
            potential_leaks.append({
                'type': 'threads',
                'severity': 'medium',
                'growth': thread_growth,
            })
        
        # 对象类型变化分析
        type_changes = self._analyze_type_changes(first, latest)
        
        result = {
            'status': 'leak_detected' if potential_leaks else 'healthy',
            'duration_seconds': latest.timestamp - first.timestamp,
            'baseline': first.to_dict(),
            'latest': latest.to_dict(),
            'changes': {
                'memory_mb': round(memory_growth_mb, 2),
                'memory_percent': round(memory_growth_percent, 2),
                'objects': object_growth,
                'objects_percent': round(object_growth_percent, 2),
                'file_descriptors': fd_growth,
                'threads': thread_growth,
            },
            'potential_leaks': potential_leaks,
            'type_changes': type_changes,
            'snapshot_count': len(self._snapshots),
        }
        
        # 记录分析结果
        if potential_leaks:
            self._logger.warning(
                f"Potential leaks detected: {len(potential_leaks)} issue(s), "
                f"memory growth: {memory_growth_mb:.2f}MB ({memory_growth_percent:.1f}%)"
            )
        else:
            self._logger.info(
                f"No leaks detected, memory growth: {memory_growth_mb:.2f}MB "
                f"({memory_growth_percent:.1f}%)"
            )
        
        return result
    
    def _analyze_type_changes(self, first: ResourceSnapshot, latest: ResourceSnapshot, top_n: int = 10) -> List[Dict[str, Any]]:
        """分析对象类型变化"""
        changes = []
        
        # 找出增长最多的类型
        for type_name in set(list(first.object_types.keys()) + list(latest.object_types.keys())):
            old_count = first.object_types.get(type_name, 0)
            new_count = latest.object_types.get(type_name, 0)
            growth = new_count - old_count
            
            if growth > 0:
                changes.append({
                    'type': type_name,
                    'old_count': old_count,
                    'new_count': new_count,
                    'growth': growth,
                    'growth_percent': round((growth / old_count) * 100, 2) if old_count > 0 else float('inf')
                })
        
        # 按增长数量排序
        changes.sort(key=lambda x: x['growth'], reverse=True)
        
        return changes[:top_n]
    
    def get_trend(self, metric: str = 'memory_mb') -> List[float]:
        """获取指标趋势"""
        return [getattr(s, metric) for s in self._snapshots]
    
    def generate_report(self) -> str:
        """生成诊断报告"""
        if not self._snapshots:
            return "No snapshots available"
        
        analysis = self.analyze()
        
        # 如果数据不足，返回简单报告
        if analysis['status'] == 'insufficient_data':
            return (
                "=" * 60 + "\n" +
                "资源泄露检测报告\n" +
                "=" * 60 + "\n" +
                f"检测器: {self.name}\n" +
                f"快照数量: {analysis['snapshot_count']}\n" +
                "\n" +
                "⚠️  数据不足: " + analysis['message'] + "\n" +
                "=" * 60
            )
        
        report = []
        report.append("=" * 60)
        report.append("资源泄露检测报告")
        report.append("=" * 60)
        report.append(f"检测器: {self.name}")
        report.append(f"快照数量: {analysis['snapshot_count']}")
        report.append(f"持续时间: {analysis['duration_seconds']:.2f}秒")
        report.append("")
        
        report.append("资源变化:")
        report.append("-" * 60)
        changes = analysis['changes']
        report.append(f"  内存: {changes['memory_mb']:+.2f}MB ({changes['memory_percent']:+.2f}%)")
        report.append(f"  对象数: {changes['objects']:+d} ({changes['objects_percent']:+.2f}%)")
        report.append(f"  文件描述符: {changes['file_descriptors']:+d}")
        report.append(f"  线程数: {changes['threads']:+d}")
        report.append("")
        
        if analysis['potential_leaks']:
            report.append("⚠️ 潜在泄露:")
            report.append("-" * 60)
            for leak in analysis['potential_leaks']:
                report.append(f"  - {leak['type']}: {leak['severity']} severity")
                if 'growth_mb' in leak:
                    report.append(f"    增长: {leak['growth_mb']:.2f}MB ({leak['growth_percent']:.2f}%)")
                elif 'growth' in leak:
                    report.append(f"    增长: {leak['growth']}")
            report.append("")
        else:
            report.append("✅ 未检测到明显泄露")
            report.append("")
        
        if analysis['type_changes']:
            report.append("对象类型变化（Top 10）:")
            report.append("-" * 60)
            for change in analysis['type_changes'][:10]:
                report.append(
                    f"  {change['type']}: {change['old_count']} -> {change['new_count']} "
                    f"(+{change['growth']})"
                )
            report.append("")
        
        report.append("=" * 60)
        
        return "\n".join(report)
    
    def clear(self):
        """清除所有快照"""
        self._snapshots.clear()
        self._baseline = None
        self._logger.debug("Snapshots cleared")


# 全局检测器注册表
_global_detectors: Dict[str, LeakDetector] = {}


def get_leak_detector(name: str = "default") -> LeakDetector:
    """
    获取泄露检测器实例（单例）
    
    Args:
        name: 检测器名称
    
    Returns:
        LeakDetector实例
    """
    if name not in _global_detectors:
        _global_detectors[name] = LeakDetector(name)
    return _global_detectors[name]


def cleanup_detectors():
    """清理所有检测器"""
    global _global_detectors
    _global_detectors.clear()
