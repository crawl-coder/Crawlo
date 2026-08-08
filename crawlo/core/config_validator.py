#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
配置验证器
==========
- ConfigValidator：确保配置的合理性和一致性
"""
from typing import Dict, Any, List, Tuple


class ConfigValidator:
    """配置验证器 - 确保配置的合理性和一致性"""

    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []

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

        self._validate_basic(config)
        self._validate_network(config)
        self._validate_concurrency(config)
        self._validate_queue(config)
        self._validate_redis(config)
        self._validate_logging(config)

        return len(self.errors) == 0, self.errors, self.warnings

    def _validate_basic(self, config: Dict[str, Any]):
        """验证基本设置"""
        project_name = config.get('PROJECT_NAME', 'crawlo')
        if not isinstance(project_name, str) or not project_name.strip():
            self.errors.append("PROJECT_NAME 必须是非空字符串")

    def _validate_network(self, config: Dict[str, Any]):
        """验证网络设置"""
        timeout = config.get('DOWNLOAD_TIMEOUT', 30)
        if not isinstance(timeout, (int, float)) or timeout <= 0:
            self.errors.append("DOWNLOAD_TIMEOUT 必须是正数")

        delay = config.get('DOWNLOAD_DELAY', 1.0)
        if not isinstance(delay, (int, float)) or delay < 0:
            self.errors.append("DOWNLOAD_DELAY 必须是非负数")

        max_retries = config.get('MAX_RETRY_TIMES', 3)
        if not isinstance(max_retries, int) or max_retries < 0:
            self.errors.append("MAX_RETRY_TIMES 必须是非负整数")

        pool_limit = config.get('CONNECTION_POOL_LIMIT', 50)
        if not isinstance(pool_limit, int) or pool_limit <= 0:
            self.errors.append("CONNECTION_POOL_LIMIT 必须是正整数")

    def _validate_concurrency(self, config: Dict[str, Any]):
        """验证并发设置"""
        concurrency = config.get('CONCURRENCY', 8)
        if not isinstance(concurrency, int) or concurrency <= 0:
            self.errors.append("CONCURRENCY 必须是正整数")

        max_running = config.get('MAX_RUNNING_SPIDERS', 1)
        if not isinstance(max_running, int) or max_running <= 0:
            self.errors.append("MAX_RUNNING_SPIDERS 必须是正整数")

    def _validate_queue(self, config: Dict[str, Any]):
        """验证队列设置"""
        queue_type = config.get('QUEUE_TYPE', 'memory')
        valid_types = ['memory', 'redis', 'redis_stream', 'auto']
        if queue_type not in valid_types:
            self.errors.append(f"QUEUE_TYPE 必须是以下值之一: {valid_types}")

        max_size = config.get('SCHEDULER_MAX_QUEUE_SIZE', 2000)
        if not isinstance(max_size, int) or max_size <= 0:
            self.errors.append("SCHEDULER_MAX_QUEUE_SIZE 必须是正整数")

    def _validate_redis(self, config: Dict[str, Any]):
        """验证Redis设置"""
        if config.get('QUEUE_TYPE') == 'redis':
            host = config.get('REDIS_HOST', '127.0.0.1')
            if not isinstance(host, str) or not host.strip():
                self.errors.append("使用 Redis 模式时 REDIS_HOST 不能为空")

            port = config.get('REDIS_PORT', 6379)
            if not isinstance(port, int) or port <= 0 or port > 65535:
                self.errors.append("REDIS_PORT 必须是 1-65535 之间的整数")

    def _validate_logging(self, config: Dict[str, Any]):
        """验证日志设置"""
        level = config.get('LOG_LEVEL', 'INFO')
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if level not in valid_levels:
            self.errors.append(f"LOG_LEVEL 必须是以下值之一: {valid_levels}")


__all__ = ['ConfigValidator']
