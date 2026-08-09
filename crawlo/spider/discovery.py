#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Spider 发现状态模块（P2-6 拆分）
================================
从 spider.py 拆分：爬虫发现过程的错误/模块追踪与诊断报告。
"""
from __future__ import annotations

from typing import List

class SpiderDiscoveryState:
    """
    爬虫发现状态管理器（全局单例）
    
    用于记录爬虫发现过程中的诊断信息，帮助定位问题。
    不针对特定错误类型，通用记录所有导入失败信息。
    
    注意：这是一个全局单例，所有实例共享同一状态。
    测试时应调用 clear() 方法重置状态。
    """
    
    _discovery_errors: List[str] = []
    _discovered_modules: set = set()
    
    @classmethod
    def reset(cls) -> None:
        """重置所有状态（用于测试隔离）"""
        cls.clear()
    
    @classmethod
    def add_discovery_error(cls, error: str) -> None:
        """
        添加发现过程中的错误
        
        Args:
            error: 完整错误信息（含异常类型和消息）
        """
        cls._discovery_errors.append(error)
    
    @classmethod
    def get_discovery_errors(cls) -> List[str]:
        """
        获取发现过程中的所有错误
        
        Returns:
            List[str]: 错误信息列表
        """
        return cls._discovery_errors
    
    @classmethod
    def get_diagnostic_report(cls) -> str:
        """
        获取完整的诊断报告
        
        Returns:
            str: 诊断报告字符串
        """
        lines = ["=== Spider Discovery Diagnostic Report ==="]
        
        if cls._discovery_errors:
            lines.append("\nImport Errors:")
            for error in cls._discovery_errors:
                lines.append(f"  - {error}")
        else:
            lines.append("\nNo issues found.")
        
        return "\n".join(lines)
    
    @classmethod
    def clear(cls) -> None:
        """清除所有诊断信息"""
        cls._discovery_errors.clear()
        cls._discovered_modules.clear()
    
    @classmethod
    def mark_discovered(cls, module_path: str) -> None:
        """标记模块已完成 auto-discover"""
        cls._discovered_modules.add(module_path)
    
    @classmethod
    def is_discovered(cls, module_path: str) -> bool:
        """检查模块是否已完成 auto-discover"""
        return module_path in cls._discovered_modules

