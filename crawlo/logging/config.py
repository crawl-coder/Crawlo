#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
日志配置管理
"""

import os
from dataclasses import dataclass, field
from typing import Optional, Dict, Any


@dataclass
class LogConfig:
    """日志配置数据类 - 简单明确的配置结构"""
    
    # 基本配置
    level: str = "INFO"
    format: str = "%(asctime)s - [%(name)s] - %(levelname)s: %(message)s"
    encoding: str = "utf-8"
    
    # 文件配置
    file_path: Optional[str] = None
    max_bytes: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    
    # 控制台配置
    console_enabled: bool = True
    file_enabled: bool = True
    
    # 模块级别配置
    module_levels: Dict[str, str] = field(default_factory=dict)
    
    @classmethod
    def from_settings(cls, settings) -> 'LogConfig':
        """从settings对象创建配置"""
        if not settings:
            return cls()
            
        # 使用settings的get方法而不是getattr
        if hasattr(settings, 'get'):
            get_val = settings.get
        else:
            get_val = lambda k, d=None: getattr(settings, k, d)
        
        # 获取默认值
        format_default_value = "%(asctime)s - [%(name)s] - %(levelname)s: %(message)s"
        
        return cls(
            level=get_val('LOG_LEVEL', 'INFO'),
            format=get_val('LOG_FORMAT', format_default_value),
            encoding=get_val('LOG_ENCODING', 'utf-8'),
            file_path=get_val('LOG_FILE'),
            max_bytes=get_val('LOG_MAX_BYTES', 10 * 1024 * 1024),
            backup_count=get_val('LOG_BACKUP_COUNT', 5),
            console_enabled=get_val('LOG_CONSOLE_ENABLED', True),
            file_enabled=get_val('LOG_FILE_ENABLED', True),
            module_levels=get_val('LOG_LEVELS', {})
        )
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'LogConfig':
        """从字典创建配置"""
        return cls(**{k: v for k, v in config_dict.items() if k in cls.__annotations__})
    
    def get_module_level(self, module_name: str) -> str:
        """获取模块的日志级别"""
        # 先查找精确匹配
        if module_name in self.module_levels:
            return self.module_levels[module_name]
        
        # 查找父模块匹配
        parts = module_name.split('.')
        for i in range(len(parts) - 1, 0, -1):
            parent_module = '.'.join(parts[:i])
            if parent_module in self.module_levels:
                return self.module_levels[parent_module]
        
        # 返回默认级别
        return self.level
    
    def validate(self) -> bool:
        """验证配置有效性"""
        valid_levels = {'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'}
        
        if self.level.upper() not in valid_levels:
            return False
        
        # 确保日志目录存在
        if self.file_path and self.file_enabled:
            try:
                log_dir = os.path.dirname(self.file_path)
                if log_dir and not os.path.exists(log_dir):
                    os.makedirs(log_dir, exist_ok=True)
            except (OSError, PermissionError):
                return False
        
        return True