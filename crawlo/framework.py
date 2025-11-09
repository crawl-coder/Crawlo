#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Crawlo框架统一入口
================

提供简洁、一致的API接口，隐藏内部复杂性
"""

import os
import sys
from typing import Type, Optional, List, Union

from .crawler import Crawler, CrawlerProcess
from .initialization import initialize_framework
from .logging import get_logger
from .utils.config_manager import EnvConfigManager


class CrawloFramework:
    """
    Crawlo框架门面类
    
    提供统一的框架入口点，简化使用复杂度
    """

    def __init__(self, settings=None, **kwargs):
        """
        初始化框架
        
        Args:
            settings: 配置对象
            **kwargs: 额外配置参数
        """
        # 合并配置
        config = {}
        if settings:
            if hasattr(settings, '__dict__'):
                config.update(settings.__dict__)
            elif isinstance(settings, dict):
                config.update(settings)
        config.update(kwargs)
        
        # 如果没有提供配置，尝试自动加载项目配置
        if not config:
            config = self._load_project_config()

        # 初始化框架
        self._settings = initialize_framework(config)
        self._logger = get_logger('crawlo.framework')

        # 获取版本号
        version = EnvConfigManager.get_version()

        # 创建进程管理器
        self._process = CrawlerProcess(self._settings)

        self._logger.info(f"Crawlo Framework Started {version}")
        
        # 获取运行模式和队列类型并记录日志
        run_mode = self._settings.get('RUN_MODE', 'unknown')
        queue_type = self._settings.get('QUEUE_TYPE', 'unknown')
        self._logger.info(f"RunMode: {run_mode}, QueueType: {queue_type}")
        
        # 记录项目名称
        project_name = self._settings.get('PROJECT_NAME', 'unknown')
        self._logger.info(f"Project: {project_name}")

    def _load_project_config(self):
        """
        自动加载项目配置
        """
        try:
            # 查找项目根目录
            project_root = self._find_project_root()
            if not project_root:
                print("警告: 未找到项目根目录，使用默认配置")
                return {}
            
            # 添加项目根目录到Python路径
            if project_root not in sys.path:
                sys.path.insert(0, project_root)
            
            # 读取crawlo.cfg配置文件
            cfg_file = os.path.join(project_root, "crawlo.cfg")
            if not os.path.exists(cfg_file):
                print(f"警告: 未找到配置文件 {cfg_file}，使用默认配置")
                return {}
            
            import configparser
            config_parser = configparser.ConfigParser()
            config_parser.read(cfg_file, encoding="utf-8")
            
            if not config_parser.has_section("settings") or not config_parser.has_option("settings", "default"):
                print("警告: 配置文件缺少 [settings] 部分或 'default' 选项，使用默认配置")
                return {}
            
            # 获取settings模块路径
            settings_module_path = config_parser.get("settings", "default")
            project_package = settings_module_path.split(".")[0]
            
            # 导入项目配置模块
            import importlib
            settings_module = importlib.import_module(settings_module_path)
            
            # 创建配置字典
            project_config = {}
            for key in dir(settings_module):
                if key.isupper():
                    project_config[key] = getattr(settings_module, key)
            
            # print(f"已加载项目配置: {settings_module_path}")
            return project_config
            
        except Exception as e:
            print(f"加载项目配置时出错: {e}")
            return {}

    def _find_project_root(self):
        """
        查找项目根目录（包含crawlo.cfg的目录）
        """
        current_path = os.getcwd()
        
        # 向上查找直到找到crawlo.cfg
        checked_paths = set()
        path = current_path
        
        while path not in checked_paths:
            checked_paths.add(path)
            
            # 检查crawlo.cfg
            cfg_file = os.path.join(path, "crawlo.cfg")
            if os.path.exists(cfg_file):
                return path
            
            # 向上一级目录
            parent = os.path.dirname(path)
            if parent == path:
                break
            path = parent
        
        return None

    @property
    def settings(self):
        """获取配置"""
        return self._settings

    @property
    def logger(self):
        """获取框架日志器"""
        return self._logger

    async def run(self, spider_cls_or_name, settings=None):
        """
        运行单个爬虫
        
        Args:
            spider_cls_or_name: Spider类或名称
            settings: 额外配置
            
        Returns:
            Crawler实例
        """
        # 记录启动的爬虫名称
        if isinstance(spider_cls_or_name, str):
            spider_name = spider_cls_or_name
        else:
            spider_name = getattr(spider_cls_or_name, 'name', spider_cls_or_name.__name__)
        
        self._logger.info(f"Starting spider: {spider_name}")
        
        return await self._process.crawl(spider_cls_or_name, settings)

    async def run_multiple(self, spider_classes_or_names: List[Union[Type, str]],
                           settings=None):
        """
        运行多个爬虫
        
        Args:
            spider_classes_or_names: Spider类或名称列表
            settings: 额外配置
            
        Returns:
            结果列表
        """
        # 记录启动的爬虫名称
        spider_names = []
        for spider_cls_or_name in spider_classes_or_names:
            if isinstance(spider_cls_or_name, str):
                spider_names.append(spider_cls_or_name)
            else:
                spider_names.append(getattr(spider_cls_or_name, 'name', spider_cls_or_name.__name__))
        
        self._logger.info(f"Starting spiders: {', '.join(spider_names)}")
        
        try:
            return await self._process.crawl_multiple(spider_classes_or_names, settings)
        finally:
            # 清理全局Redis连接池
            await self._cleanup_global_resources()

    def create_crawler(self, spider_cls: Type, settings=None) -> Crawler:
        """
        创建Crawler实例
        
        Args:
            spider_cls: Spider类
            settings: 额外配置
            
        Returns:
            Crawler实例
        """
        merged_settings = self._merge_settings(settings)
        return Crawler(spider_cls, merged_settings)

    def _merge_settings(self, additional_settings):
        """合并配置"""
        if not additional_settings:
            return self._settings

        from .settings.setting_manager import SettingManager
        merged = SettingManager()

        # 复制基础配置
        if self._settings:
            merged.update_attributes(self._settings.__dict__)

        # 应用额外配置
        if isinstance(additional_settings, dict):
            merged.update_attributes(additional_settings)
        elif hasattr(additional_settings, '__dict__'):
            merged.update_attributes(additional_settings.__dict__)

        return merged

    def get_metrics(self) -> dict:
        """获取框架指标"""
        return self._process.get_metrics()
    
    async def _cleanup_global_resources(self):
        """清理全局资源（Redis连接池等）"""
        try:
            # 清理全局Redis连接池
            from crawlo.utils.redis_manager import close_all_pools
            await close_all_pools()
            self._logger.debug("Global resources cleaned up")
        except Exception as e:
            self._logger.warning(f"Failed to cleanup global resources: {e}")


# 全局框架实例
_global_framework: Optional[CrawloFramework] = None


def get_framework(settings=None, **kwargs) -> CrawloFramework:
    """
    获取全局框架实例（单例模式）
    
    Args:
        settings: 配置对象
        **kwargs: 额外配置参数
        
    Returns:
        CrawloFramework实例
    """
    global _global_framework

    if _global_framework is None:
        _global_framework = CrawloFramework(settings, **kwargs)

    return _global_framework


def reset_framework():
    """重置全局框架实例（主要用于测试）"""
    global _global_framework
    _global_framework = None


# 便捷函数
async def run_spider(spider_cls_or_name, settings=None, **kwargs):
    """运行单个爬虫的便捷函数"""
    framework = get_framework(settings, **kwargs)
    return await framework.run(spider_cls_or_name)


async def run_spiders(spider_classes_or_names: List[Union[Type, str]],
                      settings=None, **kwargs):
    """运行多个爬虫的便捷函数"""
    framework = get_framework(settings, **kwargs)
    return await framework.run_multiple(spider_classes_or_names)


def create_crawler(spider_cls: Type, settings=None, **kwargs) -> Crawler:
    """创建Crawler的便捷函数"""
    framework = get_framework(settings, **kwargs)
    return framework.create_crawler(spider_cls)


# 配置相关便捷函数
def configure_framework(settings=None, **kwargs):
    """配置框架的便捷函数"""
    if settings or kwargs:
        reset_framework()  # 重置以应用新配置
    return get_framework(settings, **kwargs)