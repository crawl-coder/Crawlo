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
    
    # 分别控制台和文件的日志级别
    console_level: Optional[str] = None
    file_level: Optional[str] = None
    
    # 上下文信息配置
    include_thread_id: bool = False
    include_process_id: bool = False
    include_module_path: bool = False
    
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
            console_level=get_val('LOG_CONSOLE_LEVEL'),  # 允许单独设置控制台级别
            file_level=get_val('LOG_FILE_LEVEL'),  # 允许单独设置文件级别
            include_thread_id=get_val('LOG_INCLUDE_THREAD_ID', False),
            include_process_id=get_val('LOG_INCLUDE_PROCESS_ID', False),
            include_module_path=get_val('LOG_INCLUDE_MODULE_PATH', False),
            module_levels=get_val('LOG_LEVELS', {})
        )
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'LogConfig':
        """从字典创建配置"""
        # 映射字典键到类属性名
        key_mapping = {
            'LOG_LEVEL': 'level',
            'LOG_FORMAT': 'format',
            'LOG_ENCODING': 'encoding',
            'LOG_FILE': 'file_path',
            'LOG_MAX_BYTES': 'max_bytes',
            'LOG_BACKUP_COUNT': 'backup_count',
            'LOG_CONSOLE_ENABLED': 'console_enabled',
            'LOG_FILE_ENABLED': 'file_enabled',
            'LOG_CONSOLE_LEVEL': 'console_level',
            'LOG_FILE_LEVEL': 'file_level',
            'LOG_INCLUDE_THREAD_ID': 'include_thread_id',
            'LOG_INCLUDE_PROCESS_ID': 'include_process_id',
            'LOG_INCLUDE_MODULE_PATH': 'include_module_path',
            'LOG_LEVELS': 'module_levels'
        }
        
        # 应用键映射
        mapped_dict = {}
        for k, v in config_dict.items():
            mapped_key = key_mapping.get(k, k)
            if mapped_key in cls.__annotations__:
                mapped_dict[mapped_key] = v
                
        return cls(**mapped_dict)
    
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
    
    def get_console_level(self) -> str:
        """获取控制台日志级别"""
        return self.console_level or self.level
    
    def get_file_level(self) -> str:
        """获取文件日志级别"""
        return self.file_level or self.level
    
    def get_format(self) -> str:
        """
        获取日志格式，包含上下文信息
        
        Returns:
            日志格式字符串
        """
        base_format = self.format
        
        # 添加线程ID
        if self.include_thread_id:
            if '[%(thread)d]' not in base_format:
                # 在时间戳后添加线程ID
                base_format = base_format.replace(
                    '%(asctime)s', 
                    '%(asctime)s [%(thread)d]'
                )
                
        # 添加进程ID
        if self.include_process_id:
            if '[%(process)d]' not in base_format:
                # 在时间戳后添加进程ID（如果已经有线程ID，则在线程ID后添加）
                if '[%(thread)d]' in base_format:
                    base_format = base_format.replace(
                        '%(asctime)s [%(thread)d]', 
                        '%(asctime)s [%(thread)d] [%(process)d]'
                    )
                else:
                    base_format = base_format.replace(
                        '%(asctime)s', 
                        '%(asctime)s [%(process)d]'
                    )
                
        # 添加模块路径
        if self.include_module_path:
            if '%(pathname)s:%(lineno)d' not in base_format:
                # 在消息前添加文件路径和行号
                base_format = base_format.replace(
                    '%(message)s', 
                    '%(pathname)s:%(lineno)d - %(message)s'
                )
                
        return base_format
    
    def validate(self) -> bool:
        """验证配置有效性"""
        valid_levels = {'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'}
        
        # 验证主级别
        if self.level.upper() not in valid_levels:
            return False
        
        # 验证控制台级别
        if self.console_level and self.console_level.upper() not in valid_levels:
            return False
        
        # 验证文件级别
        if self.file_level and self.file_level.upper() not in valid_levels:
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