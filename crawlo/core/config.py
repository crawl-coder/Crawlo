#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Crawlo 配置中心
================
面向用户的配置入口，提供链式 API、模式切换、环境变量加载。

核心 API：
    from crawlo.core.config import CrawloConfig
    config = CrawloConfig.auto(project_name='demo', concurrency=12)
    config = CrawloConfig.standalone().set('LOG_LEVEL', 'DEBUG').enable_debug()
    config = CrawloConfig.from_env()
    locals().update(config.to_dict())
"""
from typing import Dict, Any, Optional, List, Tuple

from crawlo.logging import get_logger


class CrawloConfig:
    """
    Crawlo 配置工厂类

    统一管理配置的加载、切换、验证和导出。
    支持链式调用和三种运行模式。
    """

    def __init__(self, settings: Dict[str, Any]) -> None:
        """
        初始化配置

        Args:
            settings: 配置字典
        """
        from crawlo.core.config_validator import ConfigValidator
        self.settings: Dict[str, Any] = settings
        self.logger = get_logger(self.__class__.__name__)
        self.validator = ConfigValidator()
        self._validate_settings()

    def _validate_settings(self, raise_error: bool = True) -> bool:
        """内部验证方法"""
        is_valid, errors, warnings = self.validator.validate(self.settings)

        if warnings:
            for w in warnings:
                self.logger.warning(f"配置警告: {w}")

        if not is_valid and raise_error:
            error_msg = "配置验证失败:\n" + "\n".join([f"  - {e}" for e in errors])
            raise ValueError(error_msg)

        return is_valid

    # ----- 链式操作接口 -----

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置项"""
        return self.settings.get(key, default)

    def set(self, key: str, value: Any) -> 'CrawloConfig':
        """
        设置配置项（链式操作）

        Args:
            key: 配置键
            value: 配置值

        Returns:
            self，支持链式调用
        """
        self.settings[key] = value
        self._validate_settings()
        return self

    def update(self, settings: Dict[str, Any]) -> 'CrawloConfig':
        """
        批量更新配置（链式操作）

        Args:
            settings: 配置字典

        Returns:
            self，支持链式调用
        """
        self.settings.update(settings)
        self._validate_settings()
        return self

    def enable_debug(self) -> 'CrawloConfig':
        """启用调试模式（链式操作）"""
        return self.set('LOG_LEVEL', 'DEBUG')

    def set_concurrency(self, count: int) -> 'CrawloConfig':
        """设置并发数（链式操作）"""
        return self.set('CONCURRENCY', count)

    def to_dict(self) -> Dict[str, Any]:
        """导出为字典"""
        return self.settings.copy()

    def validate(self) -> Tuple[bool, List[str], List[str]]:
        """验证当前配置"""
        return self.validator.validate(self.settings)

    # ----- 运行模式静态工厂 -----

    @classmethod
    def standalone(cls, project_name: str = 'crawlo', **kwargs) -> 'CrawloConfig':
        """单机模式（内存队列，无需外部依赖）"""
        from crawlo.core.config_factories import _make_standalone
        return _make_standalone(cls, project_name, **kwargs)

    @classmethod
    def distributed(cls,
                    project_name: str = 'crawlo',
                    sentinel_urls: Optional[List[str]] = None,
                    sentinel_service: str = 'mymaster',
                    **kwargs) -> 'CrawloConfig':
        """分布式模式（Redis 队列，多节点扩展）"""
        from crawlo.core.config_factories import _make_distributed
        return _make_distributed(cls, project_name, sentinel_urls, sentinel_service, **kwargs)

    @classmethod
    def auto(cls, project_name: str = 'crawlo', **kwargs) -> 'CrawloConfig':
        """自动检测模式（推荐）：运行时探测 Redis 可用性"""
        from crawlo.core.config_factories import _make_auto
        return _make_auto(cls, project_name, **kwargs)

    @classmethod
    def from_env(cls, default_mode: str = 'standalone') -> 'CrawloConfig':
        """从环境变量加载配置（CRAWLO_* 前缀）"""
        from crawlo.core.config_factories import _make_from_env
        return _make_from_env(cls, default_mode)

    def print_summary(self) -> 'CrawloConfig':
        """打印配置摘要（链式操作）"""
        print("\n" + "=" * 20 + " Crawlo Config Summary " + "=" * 20)
        print(f"Project: {self.get('PROJECT_NAME')}")
        print(f"Run Mode: {self.get('RUN_MODE')}")
        print(f"Concurrency: {self.get('CONCURRENCY')}")
        if self.get('REDIS_HOST'):
            print(f"Redis: {self.get('REDIS_HOST')}:{self.get('REDIS_PORT')}")
        print("=" * 63 + "\n")
        return self


__all__ = ['CrawloConfig']
