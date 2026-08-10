#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
CrawloFramework 门面类 + 全局便捷函数。

包含：
- CrawloFramework：用户侧主入口（get/run/run_multiple/create_crawler）
- get_framework / reset_framework：全局框架实例管理（DCL）
- run_spider / run_spiders / create_crawler / configure_framework：便捷函数
"""
from __future__ import annotations

import os
import sys
import threading
from typing import TYPE_CHECKING, Any, Dict, List, Type, Union

from crawlo.logging import get_logger
from crawlo.core.application import initialize_framework, is_framework_ready
from crawlo.settings.setting_manager import EnvConfigManager

from crawlo.project import read_crawlo_cfg
from ._crawler import Crawler
from ._process import CrawlerProcess

if TYPE_CHECKING:
    pass


class CrawloFramework:
    """Crawlo 框架门面类"""

    def __init__(self, settings=None, **kwargs):
        config: Dict[str, Any] = {}
        if settings:
            if hasattr(settings, '__dict__'):
                config.update(settings.__dict__)
            elif isinstance(settings, dict):
                config.update(settings)
        config.update(kwargs)

        self._logger = get_logger('crawlo.framework')

        if not config:
            config = self._load_project_config()

        self._settings = initialize_framework(config)
        version = EnvConfigManager.get_version()
        self._process = CrawlerProcess(self._settings)

        self._logger.info(f"Crawlo Framework Started {version}")
        run_mode = self._settings.get('RUN_MODE', 'unknown')
        queue_type = self._settings.get('QUEUE_TYPE', 'unknown')
        self._logger.info(f"RunMode: {run_mode}, QueueType: {queue_type}")
        project_name = self._settings.get('PROJECT_NAME', 'unknown')
        self._logger.info(f"Project: {project_name}")

    def _load_project_config(self):
        try:
            project_root = self._find_project_root()
            if not project_root:
                self._logger.warning("未找到项目根目录，使用默认配置")
                return {}
            if project_root not in sys.path:
                sys.path.insert(0, project_root)
            cfg_file = os.path.join(project_root, "crawlo.cfg")
            settings_module_path = read_crawlo_cfg(cfg_file)
            if not settings_module_path:
                self._logger.warning(f"配置文件 {cfg_file} 无效或不存在，使用默认配置")
                return {}

            settings_module_path.split(".")[0]

            import importlib
            settings_module = importlib.import_module(settings_module_path)

            project_config = {}
            for key in dir(settings_module):
                if key.isupper():
                    project_config[key] = getattr(settings_module, key)
            return project_config

        except Exception as e:
            self._logger.error(f"Error loading project configuration: {e}")
            return {}

    def _find_project_root(self):
        current_path = os.getcwd()
        checked_paths = set()
        path = current_path
        while path not in checked_paths:
            checked_paths.add(path)
            cfg_file = os.path.join(path, "crawlo.cfg")
            if os.path.exists(cfg_file):
                return path
            parent = os.path.dirname(path)
            if parent == path:
                break
            path = parent
        return None

    @property
    def settings(self):
        return self._settings

    @property
    def logger(self):
        return self._logger

    async def run(self, spider_cls_or_name, settings=None):
        if isinstance(spider_cls_or_name, str):
            spider_name = spider_cls_or_name
        else:
            spider_name = getattr(spider_cls_or_name, 'name', spider_cls_or_name.__name__)
        self._logger.info(f"Starting spider: {spider_name}")
        return await self._process.crawl(spider_cls_or_name, settings)

    async def run_multiple(self, spider_classes_or_names: List[Union[Type, str]], settings=None):
        spider_names = []
        for spider_cls_or_name in spider_classes_or_names:
            if isinstance(spider_cls_or_name, str):
                spider_names.append(spider_cls_or_name)
            else:
                spider_names.append(getattr(spider_cls_or_name, 'name', spider_cls_or_name.__name__))
        self._logger.info(f"Starting spiders: {', '.join(spider_names)}")
        try:
            return await self._process.crawl(spider_classes_or_names, settings)
        finally:
            await self._cleanup_global_resources()

    def create_crawler(self, spider_cls: Type, settings=None) -> Crawler:
        merged_settings = self._merge_settings(settings)
        return Crawler(spider_cls, merged_settings)

    def _merge_settings(self, additional_settings):
        if not additional_settings:
            return self._settings
        from crawlo.settings.setting_manager import SettingManager
        merged = SettingManager()
        if self._settings:
            merged.update_attributes(self._settings.__dict__)
        if isinstance(additional_settings, dict):
            merged.update_attributes(additional_settings)
        elif hasattr(additional_settings, '__dict__'):
            merged.update_attributes(additional_settings.__dict__)
        return merged

    def get_metrics(self) -> dict:
        return self._process.get_metrics()

    async def _cleanup_global_resources(self):
        try:
            from crawlo.utils.redis import close_all_pools
            await close_all_pools()
            self._logger.debug("Global resources cleaned up")
        except Exception as e:
            self._logger.warning(f"Failed to cleanup global resources: {e}")


# ------------------------------------------------------------------
# 全局框架实例管理
# ------------------------------------------------------------------
_framework_lock = threading.Lock()


def get_framework(settings=None, **kwargs) -> CrawloFramework:
    """获取全局框架实例（DCL 线程安全）"""
    try:
        from crawlo.core.application import default_container
        if default_container.is_registered(CrawloFramework):
            return default_container.resolve(CrawloFramework)
    except Exception as e:
        get_logger(__name__).debug("Suppressed exception: %s", e)
    reg_ctx = _resolve_registry_context()
    if reg_ctx.framework is None:
        with _framework_lock:
            if reg_ctx.framework is None:
                inst = CrawloFramework(settings, **kwargs)
                reg_ctx.framework = inst
                try:
                    from crawlo.core.application import default_container as _c
                    _c.register_instance(CrawloFramework, inst)
                except Exception as e:
                    get_logger(__name__).debug("Suppressed exception: %s", e)
    return reg_ctx.framework


def _resolve_registry_context():
    """优先从容器拿 RegistryContext，否则 fallback ctx.registries。"""
    try:
        from crawlo.core.application import default_container
        from crawlo.core.application import RegistryContext
        if default_container.is_registered(RegistryContext):
            return default_container.resolve(RegistryContext)
    except Exception as e:
        get_logger(__name__).debug("Suppressed exception: %s", e)
    from crawlo.core.application import get_global_context
    return get_global_context().registries


def reset_framework():
    """重置全局框架实例"""
    reg_ctx = _resolve_registry_context()
    reg_ctx.framework = None
    try:
        from crawlo.core.application import default_container
        default_container._registrations.pop(CrawloFramework, None)
    except Exception as e:
        get_logger(__name__).debug("Suppressed exception: %s", e)
    try:
        from crawlo.core.application import CoreInitializer
        CoreInitializer().reset()
    except Exception as e:
        get_logger(__name__).debug("Suppressed exception: %s", e)


# ------------------------------------------------------------------
# 便捷函数
# ------------------------------------------------------------------
async def run_spider(spider_cls_or_name, settings=None, **kwargs):
    framework = get_framework(settings, **kwargs)
    return await framework.run(spider_cls_or_name)


async def run_spiders(spider_classes_or_names: List[Union[Type, str]], settings=None, **kwargs):
    framework = get_framework(settings, **kwargs)
    return await framework.run_multiple(spider_classes_or_names)


def create_crawler(spider_cls: Type, settings=None, **kwargs) -> Crawler:
    framework = get_framework(settings, **kwargs)
    return framework.create_crawler(spider_cls)


def configure_framework(settings=None, **kwargs):
    if settings or kwargs:
        reset_framework()
    return get_framework(settings, **kwargs)


__all__ = [
    'CrawloFramework',
    'get_framework',
    'reset_framework',
    'run_spider',
    'run_spiders',
    'create_crawler',
    'configure_framework',
    'initialize_framework',
    'is_framework_ready',
]
