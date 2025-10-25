#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
配置验证器
==========
提供配置项的验证和默认值设置功能，确保配置的合理性和一致性。
"""
from typing import Dict, Any, List, Tuple

from crawlo.logging import get_logger


class ConfigValidator:
    """配置验证器"""
    
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        self.errors = []
        self.warnings = []
    
    def validate(self, config: Dict[str, Any]) -> Tuple[bool, List[str], List[str]]:
        """
        验证配置
        
        Args:
            config: 配置字典
            
        Returns:
            Tuple[bool, List[str], List[str]]: (是否有效, 错误列表, 警告列表)
        """
        self.errors = []
        self.warnings = []
        
        # 验证各个配置项
        self._validate_basic_settings(config)
        self._validate_network_settings(config)
        self._validate_concurrency_settings(config)
        self._validate_queue_settings(config)
        self._validate_storage_settings(config)
        self._validate_redis_settings(config)
        self._validate_middleware_settings(config)
        self._validate_pipeline_settings(config)
        self._validate_extension_settings(config)
        self._validate_logging_settings(config)
        
        is_valid = len(self.errors) == 0
        return is_valid, self.errors, self.warnings
    
    def _validate_basic_settings(self, config: Dict[str, Any]):
        """验证基本设置"""
        project_name = config.get('PROJECT_NAME', 'crawlo')
        if not isinstance(project_name, str) or not project_name.strip():
            self.errors.append("PROJECT_NAME 必须是非空字符串")
        
        version = config.get('VERSION', '1.0')
        if not isinstance(version, str):
            self.errors.append("VERSION 必须是字符串")
    
    def _validate_network_settings(self, config: Dict[str, Any]):
        """验证网络设置"""
        # 下载器验证
        downloader = config.get('DOWNLOADER', 'crawlo.downloader.aiohttp_downloader.AioHttpDownloader')
        if not isinstance(downloader, str):
            self.errors.append("DOWNLOADER 必须是字符串")
        
        # 超时设置验证
        timeout = config.get('DOWNLOAD_TIMEOUT', 30)
        if not isinstance(timeout, (int, float)) or timeout <= 0:
            self.errors.append("DOWNLOAD_TIMEOUT 必须是正数")
        
        # 延迟设置验证
        delay = config.get('DOWNLOAD_DELAY', 1.0)
        if not isinstance(delay, (int, float)) or delay < 0:
            self.errors.append("DOWNLOAD_DELAY 必须是非负数")
        
        # 重试次数验证
        max_retries = config.get('MAX_RETRY_TIMES', 3)
        if not isinstance(max_retries, int) or max_retries < 0:
            self.errors.append("MAX_RETRY_TIMES 必须是非负整数")
        
        # 连接池限制验证
        pool_limit = config.get('CONNECTION_POOL_LIMIT', 50)
        if not isinstance(pool_limit, int) or pool_limit <= 0:
            self.errors.append("CONNECTION_POOL_LIMIT 必须是正整数")
    
    def _validate_concurrency_settings(self, config: Dict[str, Any]):
        """验证并发设置"""
        concurrency = config.get('CONCURRENCY', 8)
        if not isinstance(concurrency, int) or concurrency <= 0:
            self.errors.append("CONCURRENCY 必须是正整数")
        
        max_running_spiders = config.get('MAX_RUNNING_SPIDERS', 3)
        if not isinstance(max_running_spiders, int) or max_running_spiders <= 0:
            self.errors.append("MAX_RUNNING_SPIDERS 必须是正整数")
    
    def _validate_queue_settings(self, config: Dict[str, Any]):
        """验证队列设置"""
        queue_type = config.get('QUEUE_TYPE', 'memory')
        valid_queue_types = ['memory', 'redis', 'auto']
        if queue_type not in valid_queue_types:
            self.errors.append(f"QUEUE_TYPE 必须是以下值之一: {valid_queue_types}")
        
        # 队列大小验证
        max_queue_size = config.get('SCHEDULER_MAX_QUEUE_SIZE', 2000)
        if not isinstance(max_queue_size, int) or max_queue_size <= 0:
            self.errors.append("SCHEDULER_MAX_QUEUE_SIZE 必须是正整数")
        
        # 队列名称验证（如果是Redis队列）
        if queue_type == 'redis':
            queue_name = config.get('SCHEDULER_QUEUE_NAME', '')
            if not queue_name:
                self.errors.append("使用Redis队列时，SCHEDULER_QUEUE_NAME 不能为空")
            elif not self._is_valid_redis_key(queue_name):
                self.warnings.append(f"Redis队列名称 '{queue_name}' 不符合命名规范，建议使用 'crawlo:{config.get('PROJECT_NAME', 'project')}:queue:requests' 格式")
    
    def _validate_storage_settings(self, config: Dict[str, Any]):
        """验证存储设置"""
        # MySQL设置验证
        mysql_host = config.get('MYSQL_HOST')
        if mysql_host is not None and not isinstance(mysql_host, str):
            self.errors.append("MYSQL_HOST 必须是字符串")
        
        mysql_port = config.get('MYSQL_PORT')
        if mysql_port is not None and (not isinstance(mysql_port, int) or mysql_port <= 0 or mysql_port > 65535):
            self.errors.append("MYSQL_PORT 必须是1-65535之间的整数")
        
        # MongoDB设置验证
        mongo_uri = config.get('MONGO_URI')
        if mongo_uri is not None and not isinstance(mongo_uri, str):
            self.errors.append("MONGO_URI 必须是字符串")
    
    def _validate_redis_settings(self, config: Dict[str, Any]):
        """验证Redis设置"""
        queue_type = config.get('QUEUE_TYPE', 'memory')
        if queue_type == 'redis':
            # Redis主机验证
            redis_host = config.get('REDIS_HOST', '127.0.0.1')
            if not isinstance(redis_host, str) or not redis_host.strip():
                self.errors.append("REDIS_HOST 必须是非空字符串")
            
            # Redis端口验证
            redis_port = config.get('REDIS_PORT', 6379)
            if not isinstance(redis_port, int) or redis_port <= 0 or redis_port > 65535:
                self.errors.append("REDIS_PORT 必须是1-65535之间的整数")
            
            # Redis URL验证
            redis_url = config.get('REDIS_URL')
            if redis_url is not None and not isinstance(redis_url, str):
                self.errors.append("REDIS_URL 必须是字符串")
            
            # Redis队列名称验证（提供默认值）
            scheduler_queue_name = config.get('SCHEDULER_QUEUE_NAME')
            project_name = config.get('PROJECT_NAME', 'crawlo')
            if scheduler_queue_name is None:
                # 如果没有设置，使用默认值
                scheduler_queue_name = f'crawlo:{project_name}:queue:requests'
            
            if not scheduler_queue_name:
                self.errors.append("使用Redis队列时，SCHEDULER_QUEUE_NAME 不能为空")
            elif not self._is_valid_redis_key(scheduler_queue_name):
                self.warnings.append(f"Redis队列名称 '{scheduler_queue_name}' 不符合命名规范，建议使用 'crawlo:{project_name}:queue:requests' 格式")
    
    def _validate_middleware_settings(self, config: Dict[str, Any]):
        """验证中间件设置"""
        # 验证 MIDDLEWARES
        middlewares = config.get('MIDDLEWARES', [])
        if not isinstance(middlewares, list):
            self.errors.append("MIDDLEWARES 必须是列表")
        else:
            for i, middleware in enumerate(middlewares):
                if not isinstance(middleware, str):
                    self.errors.append(f"MIDDLEWARES[{i}] 必须是字符串")
    
    def _validate_pipeline_settings(self, config: Dict[str, Any]):
        """验证管道设置"""
        # 验证 PIPELINES
        pipelines = config.get('PIPELINES', [])
        if not isinstance(pipelines, list):
            self.errors.append("PIPELINES 必须是列表")
        else:
            for i, pipeline in enumerate(pipelines):
                if not isinstance(pipeline, str):
                    self.errors.append(f"PIPELINES[{i}] 必须是字符串")
    
    def _validate_extension_settings(self, config: Dict[str, Any]):
        """验证扩展设置"""
        # 验证 EXTENSIONS
        extensions = config.get('EXTENSIONS', [])
        if not isinstance(extensions, list):
            self.errors.append("EXTENSIONS 必须是列表")
        else:
            for i, extension in enumerate(extensions):
                if not isinstance(extension, str):
                    self.errors.append(f"EXTENSIONS[{i}] 必须是字符串")
    
    def _validate_logging_settings(self, config: Dict[str, Any]):
        """验证日志设置"""
        log_level = config.get('LOG_LEVEL', 'INFO')
        valid_log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if log_level not in valid_log_levels:
            self.errors.append(f"LOG_LEVEL 必须是以下值之一: {valid_log_levels}")
        
        log_file = config.get('LOG_FILE')
        if log_file is not None and not isinstance(log_file, str):
            self.errors.append("LOG_FILE 必须是字符串")
    
    def _is_valid_redis_key(self, key: str) -> bool:
        """检查Redis key是否符合命名规范"""
        # 检查是否以 crawlo: 开头
        if not key.startswith('crawlo:'):
            return False
        
        # 检查是否包含必要的部分
        parts = key.split(':')
        if len(parts) < 3:
            return False
        
        # 检查是否包含 queue 部分
        return 'queue' in parts
    
    def get_validation_report(self, config: Dict[str, Any]) -> str:
        """
        获取验证报告
        
        Args:
            config: 配置字典
            
        Returns:
            str: 验证报告
        """
        is_valid, errors, warnings = self.validate(config)
        
        report = []
        report.append("=" * 50)
        report.append("配置验证报告")
        report.append("=" * 50)
        
        if is_valid:
            report.append("配置验证通过")
        else:
            report.append("配置验证失败")
            report.append("错误:")
            for error in errors:
                report.append(f"  - {error}")
        
        if warnings:
            report.append("警告:")
            for warning in warnings:
                report.append(f"  - {warning}")
        
        report.append("=" * 50)
        return "\n".join(report)


# 便利函数
def validate_config(config: Dict[str, Any]) -> Tuple[bool, List[str], List[str]]:
    """
    验证配置
    
    Args:
        config: 配置字典
        
    Returns:
        Tuple[bool, List[str], List[str]]: (是否有效, 错误列表, 警告列表)
    """
    validator = ConfigValidator()
    return validator.validate(config)


def print_validation_report(config: Dict[str, Any]):
    """
    打印验证报告
    
    Args:
        config: 配置字典
    """
    validator = ConfigValidator()
    print(validator.get_validation_report(config))