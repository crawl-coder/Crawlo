#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Log Configuration Management
"""

import os
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Tuple


@dataclass
class LogConfig:
    """Log configuration dataclass - simple and clear config structure"""
    
    # Preset configuration templates
    TEMPLATES = {
        'minimal': {
            'level': 'INFO',
            'format': '%(asctime)s - %(levelname)s: %(message)s',
            'console_enabled': True,
            'file_enabled': False
        },
        'standard': {
            'level': 'INFO',
            'format': '%(asctime)s - [%(name)s] - %(levelname)s: %(message)s',
            'console_enabled': True,
            'file_enabled': True,
            'file_path': 'logs/crawlo.log'
        },
        'detailed': {
            'level': 'DEBUG',
            'format': '%(asctime)s - [%(name)s] - %(levelname)s - %(pathname)s:%(lineno)d: %(message)s',
            'console_enabled': True,
            'file_enabled': True,
            'file_path': 'logs/crawlo.log'
        },
        'production': {
            'level': 'WARNING',
            'format': '%(asctime)s - [%(name)s] - %(levelname)s: %(message)s',
            'console_enabled': False,  # 生产环境通常禁用控制台输出
            'file_enabled': True,
            'file_path': 'logs/crawlo.log'
        }
    }
    
    # Basic configuration
    level: str = "INFO"
    format: str = "%(asctime)s - [%(name)s] - %(levelname)s: %(message)s"
    encoding: str = "utf-8"
    
    # File configuration
    file_path: Optional[str] = None
    
    # Console configuration
    console_enabled: bool = True
    file_enabled: bool = True
    
    # Separate log levels for console and file
    console_level: Optional[str] = None
    file_level: Optional[str] = None
    
    # Context information configuration
    include_thread_id: bool = False
    include_process_id: bool = False
    include_module_path: bool = False
    
    # Module level configuration
    module_levels: Dict[str, str] = field(default_factory=dict)
    
    @classmethod
    def from_settings(cls, settings) -> 'LogConfig':
        """Create configuration from settings object"""
        if not settings:
            return cls()
            
        # Use settings' get method instead of getattr
        if hasattr(settings, 'get'):
            get_val = settings.get
        else:
            def get_val(key: str, default=None):
                return getattr(settings, key, default)
        
        # Get default value
        format_default_value = "%(asctime)s - [%(name)s] - %(levelname)s: %(message)s"
        
        # Ensure type safety
        def safe_get_str(key: str, default: str = '') -> str:
            value = get_val(key, default)
            return str(value) if value is not None else default
        
        def safe_get_int(key: str, default: int) -> int:
            value = get_val(key, default)
            try:
                return int(value) if value is not None else default
            except (ValueError, TypeError):
                return default
        
        def safe_get_bool(key: str, default: bool) -> bool:
            value = get_val(key, default)
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                return value.lower() in ('1', 'true', 'yes', 'on')
            return bool(value) if value is not None else default
        
        def safe_get_dict(key: str, default: dict) -> dict:
            value = get_val(key, default)
            return value if isinstance(value, dict) else default
        
        return cls(
            level=safe_get_str('LOG_LEVEL', 'INFO'),
            format=safe_get_str('LOG_FORMAT', format_default_value),
            encoding=safe_get_str('LOG_ENCODING', 'utf-8'),
            file_path=safe_get_str('LOG_FILE'),
            console_enabled=safe_get_bool('LOG_CONSOLE_ENABLED', True),
            file_enabled=safe_get_bool('LOG_FILE_ENABLED', True),
            console_level=safe_get_str('LOG_CONSOLE_LEVEL'),  # 允许单独设置控制台级别
            file_level=safe_get_str('LOG_FILE_LEVEL'),  # 允许单独设置文件级别
            include_thread_id=safe_get_bool('LOG_INCLUDE_THREAD_ID', False),
            include_process_id=safe_get_bool('LOG_INCLUDE_PROCESS_ID', False),
            include_module_path=safe_get_bool('LOG_INCLUDE_MODULE_PATH', False),
            module_levels=safe_get_dict('LOG_LEVELS', {})
        )
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'LogConfig':
        """Create configuration from dictionary"""
        # Map dictionary keys to class attribute names
        key_mapping = {
            'LOG_LEVEL': 'level',
            'LOG_FORMAT': 'format',
            'LOG_ENCODING': 'encoding',
            'LOG_FILE': 'file_path',
            'LOG_CONSOLE_ENABLED': 'console_enabled',
            'LOG_FILE_ENABLED': 'file_enabled',
            'LOG_CONSOLE_LEVEL': 'console_level',
            'LOG_FILE_LEVEL': 'file_level',
            'LOG_INCLUDE_THREAD_ID': 'include_thread_id',
            'LOG_INCLUDE_PROCESS_ID': 'include_process_id',
            'LOG_INCLUDE_MODULE_PATH': 'include_module_path',
            'LOG_LEVELS': 'module_levels'
        }
        
        # Apply key mapping
        mapped_dict = {}
        for k, v in config_dict.items():
            mapped_key = key_mapping.get(k, k)
            if mapped_key in cls.__annotations__:
                mapped_dict[mapped_key] = v
                
        return cls(**mapped_dict)
    
    @classmethod
    def from_template(cls, template_name: str) -> 'LogConfig':
        """Create configuration from template
        
        Args:
            template_name: Template name (minimal, standard, detailed, production)
            
        Returns:
            LogConfig: Configuration object
        """
        if template_name not in cls.TEMPLATES:
            raise ValueError(f"未知的模板名称: {template_name}，可用模板: {', '.join(cls.TEMPLATES.keys())}")
            
        template_config = cls.TEMPLATES[template_name]
        return cls(**template_config)
    
    def get_module_level(self, module_name: str) -> str:
        """Get log level for a specific module"""
        # First, find exact match
        if module_name in self.module_levels:
            return self.module_levels[module_name]
        
        # Find parent module match
        parts = module_name.split('.')
        for i in range(len(parts) - 1, 0, -1):
            parent_module = '.'.join(parts[:i])
            if parent_module in self.module_levels:
                return self.module_levels[parent_module]
        
        # Return default level
        return self.level
    
    def get_console_level(self) -> str:
        """Get console log level"""
        return self.console_level or self.level
    
    def get_file_level(self) -> str:
        """Get file log level"""
        return self.file_level or self.level
    
    def get_format(self) -> str:
        """
        Get log format with context information
        
        Returns:
            Log format string
        """
        base_format = self.format
        
        # Add thread ID
        if self.include_thread_id:
            if '[%(thread)d]' not in base_format:
                # Add thread ID after timestamp
                base_format = base_format.replace(
                    '%(asctime)s', 
                    '%(asctime)s [%(thread)d]'
                )
                
        # Add process ID
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
                
        # Add module path
        if self.include_module_path:
            if '%(pathname)s:%(lineno)d' not in base_format:
                # Add file path and line number before message
                base_format = base_format.replace(
                    '%(message)s', 
                    '%(pathname)s:%(lineno)d - %(message)s'
                )
                
        return base_format
    
    def validate(self) -> Tuple[bool, str]:
        """Validate configuration effectiveness
        
        Returns:
            Tuple[bool, str]: (is_valid, error_message)
        """
        valid_levels = {'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'}
        
        # Validate main level
        if self.level.upper() not in valid_levels:
            return False, f"Invalid log level: {self.level}, valid levels are: {', '.join(valid_levels)}"
        
        # Validate console level
        if self.console_level and self.console_level.upper() not in valid_levels:
            return False, f"Invalid console log level: {self.console_level}, valid levels are: {', '.join(valid_levels)}"
        
        # Validate file level
        if self.file_level and self.file_level.upper() not in valid_levels:
            return False, f"Invalid file log level: {self.file_level}, valid levels are: {', '.join(valid_levels)}"
        
        # Ensure log directory exists
        if self.file_path and self.file_enabled:
            try:
                log_dir = os.path.dirname(self.file_path)
                if log_dir and not os.path.exists(log_dir):
                    os.makedirs(log_dir, exist_ok=True)
            except (OSError, PermissionError) as e:
                log_dir = os.path.dirname(self.file_path) if self.file_path else "未知"
                return False, f"无法创建日志目录 {log_dir}: {e}"
        
        return True, "配置有效"