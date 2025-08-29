#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
自动发现项目并创建 SettingManager 实例

该模块负责：
1.  向上搜索项目根目录（通过 crawlo.cfg 或 settings.py）
2.  将项目根目录加入 Python 路径 (sys.path)
3.  加载指定的 settings 模块
4.  返回一个已配置好的 SettingManager 实例
"""
import os
import sys
import configparser
from importlib import import_module
from inspect import iscoroutinefunction
from typing import Callable, Optional

from crawlo.utils.log import get_logger
from crawlo.settings.setting_manager import SettingManager


logger =get_logger(__name__)


def _find_project_root(start_path: str = '.') -> Optional[str]:
    """
    从指定的起始路径开始，向上级目录递归搜索，寻找项目根目录。
    搜索依据：
        1. 优先查找 'crawlo.cfg' 文件。
        2. 如果未找到 cfg 文件，则查找位于 Python 包内（即包含 __init__.py 的目录）的 'settings.py' 文件。

    Args:
        start_path (str): 搜索的起始路径，默认为当前工作目录 '.'。

    Returns:
        Optional[str]: 找到的项目根目录的绝对路径，如果未找到则返回 None。
    """
    path = os.path.abspath(start_path)
    logger.info(f"开始向上搜索项目根目录，起始路径: {path}")

    while True:
        # 1. 检查是否存在 crawlo.cfg 文件
        cfg_file = os.path.join(path, 'crawlo.cfg')
        if os.path.isfile(cfg_file):
            logger.info(f"在路径 {path} 找到 'crawlo.cfg' 文件，确定为项目根目录。")
            return path

        # 2. 检查是否存在 settings.py 文件，并且它位于一个 Python 包中
        settings_file = os.path.join(path, 'settings.py')
        if os.path.isfile(settings_file):
            init_file = os.path.join(path, '__init__.py')
            if os.path.isfile(init_file):
                logger.info(f"在路径 {path} 找到 'settings.py' 文件，确定为项目根目录。")
                return path
            else:
                logger.debug(f"在路径 {path} 找到 'settings.py'，但缺少 '__init__.py'，忽略。")

        # 移动到上一级目录
        parent = os.path.dirname(path)
        if parent == path:
            # 已经到达文件系统根目录
            break
        path = parent

    logger.warning("向上搜索完毕，未找到项目根目录。")
    return None


def _get_settings_module_from_cfg(cfg_path: str) -> str:
    """
    从 crawlo.cfg 配置文件中读取 settings 模块的路径。

    Args:
        cfg_path (str): crawlo.cfg 文件的完整路径。

    Returns:
        str: settings 模块的导入路径，例如 'myproject.settings'。

    Raises:
        RuntimeError: 当读取文件或解析配置出错时抛出。
    """
    logger.info(f"正在读取配置文件: {cfg_path}")
    config = configparser.ConfigParser()
    try:
        config.read(cfg_path, encoding='utf-8')
        if config.has_section('settings') and config.has_option('settings', 'default'):
            module_path = config.get('settings', 'default')
            logger.info(f"从 'crawlo.cfg' 中读取到 settings 模块路径: {module_path}")
            return module_path
        else:
            error_msg = f"配置文件 '{cfg_path}' 缺少 '[settings]' 或 'default' 配置项。"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
    except (configparser.Error, OSError) as e:
        error_msg = f"读取或解析配置文件 '{cfg_path}' 时出错: {e}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)


def get_settings(custom_settings=None):
    """
    获取配置管理器实例的主函数。
    此函数会自动发现项目，加载配置，并返回一个配置好的 SettingManager。

    Args:
        custom_settings (dict, optional): 运行时传入的自定义设置字典，会覆盖 settings.py 中的同名配置。

    Returns:
        SettingManager: 一个已加载所有配置的 SettingManager 实例。

    Raises:
        RuntimeError: 当无法找到项目或配置文件时。
        ImportError: 当无法导入指定的 settings 模块时。
    """
    logger.info("正在初始化配置管理器...")

    # 1. 发现项目根目录
    project_root = _find_project_root()
    if not project_root:
        error_msg = "未找到 Crawlo 项目。请确保您正在包含 'crawlo.cfg' 或 'settings.py' 的项目目录中运行。"
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    logger.info(f"项目根目录已确定: {project_root}")

    # 2. 确定 settings 模块的导入路径
    settings_module_path = None

    # 优先从 crawlo.cfg 中读取
    cfg_file = os.path.join(project_root, 'crawlo.cfg')
    if os.path.isfile(cfg_file):
        settings_module_path = _get_settings_module_from_cfg(cfg_file)
    else:
        logger.info("未找到 'crawlo.cfg'，尝试推断 settings 模块路径...")
        # 推断：项目目录名.settings
        project_name = os.path.basename(project_root)
        settings_module_path = f"{project_name}.settings"
        logger.info(f"推断 settings 模块路径为: {settings_module_path}")

    # 3. 将项目根目录添加到 Python 路径，确保可以成功导入
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
        logger.info(f"已将项目根目录 '{project_root}' 添加到 Python 路径。")
    else:
        logger.debug(f"项目根目录 '{project_root}' 已在 Python 路径中。")

    # 4. 创建 SettingManager 并加载配置
    logger.info(f"正在加载 settings 模块: {settings_module_path}")
    settings = SettingManager()

    try:
        # 这会触发 SettingManager.set_settings()，从模块中加载所有大写常量
        settings.set_settings(settings_module_path)
        logger.info("settings 模块加载成功。")
    except Exception as e:
        error_msg = f"加载 settings 模块 '{settings_module_path}' 失败: {e}"
        logger.error(error_msg)
        raise ImportError(error_msg)

    # 5. 应用运行时自定义设置
    if custom_settings:
        logger.info(f"正在应用运行时自定义设置: {custom_settings}")
        settings.update_attributes(custom_settings)
        logger.info("运行时自定义设置已应用。")

    logger.info("配置管理器初始化完成。")
    return settings

def load_class(_path):
    if not isinstance(_path, str):
        if callable(_path):
            return _path
        else:
            raise TypeError(f"args expect str or object, got {_path}")

    module_name, class_name = _path.rsplit('.', 1)
    module = import_module(module_name)

    try:
        cls = getattr(module, class_name)
    except AttributeError:
        raise NameError(f"Module {module_name!r} has no class named {class_name!r}")
    return cls

def merge_settings(spider, settings):
    spider_name = getattr(spider, 'name', 'UnknownSpider')
    if hasattr(spider, 'custom_settings'):
        custom_settings = getattr(spider, 'custom_settings')
        settings.update_attributes(custom_settings)
    else:
        logger.debug(f"爬虫 '{spider_name}' 无 custom_settings，跳过合并") # 添加日志


async def common_call(func: Callable, *args, **kwargs):
    if iscoroutinefunction(func):
        return await func(*args, **kwargs)
    else:
        return func(*args, **kwargs)
