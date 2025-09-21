import os
import sys
import importlib
import configparser
from importlib import import_module
from inspect import iscoroutinefunction
from typing import Callable, Optional, Any

from crawlo.settings.setting_manager import SettingManager
from crawlo.utils.log import get_logger

# 延迟初始化logger，在需要时通过get_logger获取
logger = None


def _get_logger():
    """延迟获取logger实例，确保在配置加载后创建"""
    global logger
    if logger is None:
        logger = get_logger(__name__)
    return logger


def load_class(path: str) -> Any:
    """
    动态加载类
    
    Args:
        path: 类的完整路径，如 'package.module.ClassName'
        
    Returns:
        加载的类对象
    """
    try:
        module_path, class_name = path.rsplit('.', 1)
        module = importlib.import_module(module_path)
        return getattr(module, class_name)
    except (ValueError, ImportError, AttributeError) as e:
        raise ImportError(f"无法加载类 '{path}': {e}")


def merge_settings(spider, settings):
    """
    合并爬虫的自定义设置到全局设置中
    
    Args:
        spider: 爬虫实例
        settings: 全局设置管理器
    """
    spider_name = getattr(spider, 'name', 'UnknownSpider')
    # 检查 settings 是否为 SettingManager 实例
    if not hasattr(settings, 'update_attributes'):
        _get_logger().error(f"merge_settings 接收到的 settings 不是 SettingManager 实例: {type(settings)}")
        # 如果是字典，创建一个新的 SettingManager 实例
        if isinstance(settings, dict):
            from crawlo.settings.setting_manager import SettingManager
            new_settings = SettingManager()
            new_settings.update_attributes(settings)
            settings = new_settings
        else:
            _get_logger().error("无法处理的 settings 类型")
            return
            
    if hasattr(spider, 'custom_settings'):
        custom_settings = getattr(spider, 'custom_settings')
        settings.update_attributes(custom_settings)
    else:
        _get_logger().debug(f"爬虫 '{spider_name}' 无 custom_settings，跳过合并")


async def common_call(func: Callable, *args, **kwargs):
    """
    通用调用函数，自动处理同步和异步函数
    
    Args:
        func: 要调用的函数
        *args: 位置参数
        **kwargs: 关键字参数
        
    Returns:
        函数调用结果
    """
    if iscoroutinefunction(func):
        return await func(*args, **kwargs)
    else:
        return func(*args, **kwargs)


def _get_settings_module_from_cfg(cfg_path: str) -> str:
    """从 crawlo.cfg 读取 settings 模块路径"""
    config = configparser.ConfigParser()
    try:
        config.read(cfg_path, encoding="utf-8")
        if config.has_section("settings") and config.has_option("settings", "default"):
            module_path = config.get("settings", "default")
            _get_logger().debug(f"📄 从 crawlo.cfg 加载 settings 模块: {module_path}")
            return module_path
        else:
            raise RuntimeError(f"配置文件缺少 [settings] 或 default 选项: {cfg_path}")
    except Exception as e:
        raise RuntimeError(f"解析 crawlo.cfg 失败: {e}")


def _find_project_root(start_path: str = ".") -> Optional[str]:
    """
    从指定路径向上查找项目根目录。
    识别依据：
        1. 存在 'crawlo.cfg'
        2. 存在 '__init__.py' 和 'settings.py'（即 Python 包）
    """
    path = os.path.abspath(start_path)
    
    # 首先检查当前目录及其子目录
    for root, dirs, files in os.walk(path):
        if "crawlo.cfg" in files:
            cfg_path = os.path.join(root, "crawlo.cfg")
            _get_logger().debug(f"✅ 找到项目配置文件: {cfg_path}")
            return root
    
    # 向上查找直到找到 crawlo.cfg 或包含 settings.py 和 __init__.py 的目录
    original_path = path
    checked_paths = set()
    
    while True:
        # 避免无限循环
        if path in checked_paths:
            break
        checked_paths.add(path)
        
        # 检查 crawlo.cfg
        cfg_file = os.path.join(path, "crawlo.cfg")
        if os.path.isfile(cfg_file):
            _get_logger().debug(f"✅ 找到项目配置文件: {cfg_file}")
            return path

        # 检查 settings.py 和 __init__.py
        settings_file = os.path.join(path, "settings.py")
        init_file = os.path.join(path, "__init__.py")
        if os.path.isfile(settings_file) and os.path.isfile(init_file):
            _get_logger().debug(f"✅ 找到项目模块: {path}")
            # 即使找到了项目模块，也继续向上查找是否有 crawlo.cfg
            parent = os.path.dirname(path)
            if parent != path:
                parent_cfg = os.path.join(parent, "crawlo.cfg")
                if os.path.isfile(parent_cfg):
                    _get_logger().debug(f"✅ 在上层目录找到项目配置文件: {parent_cfg}")
                    return parent
            return path

        parent = os.path.dirname(path)
        if parent == path:
            break
        path = parent

    # 如果向上查找也没找到，尝试从脚本所在目录查找
    # 获取当前脚本文件的路径
    try:
        script_path = os.path.dirname(os.path.abspath(sys.argv[0]))
        if script_path != original_path:
            path = script_path
            checked_paths = set()  # 重置已检查路径
            while True:
                # 避免无限循环
                if path in checked_paths:
                    break
                checked_paths.add(path)
                
                cfg_file = os.path.join(path, "crawlo.cfg")
                if os.path.isfile(cfg_file):
                    _get_logger().debug(f"✅ 找到项目配置文件: {cfg_file}")
                    return path

                settings_file = os.path.join(path, "settings.py")
                init_file = os.path.join(path, "__init__.py")
                if os.path.isfile(settings_file) and os.path.isfile(init_file):
                    _get_logger().debug(f"✅ 找到项目模块: {path}")
                    # 即使找到了项目模块，也继续向上查找是否有 crawlo.cfg
                    parent = os.path.dirname(path)
                    if parent != path:
                        parent_cfg = os.path.join(parent, "crawlo.cfg")
                        if os.path.isfile(parent_cfg):
                            _get_logger().debug(f"✅ 在上层目录找到项目配置文件: {parent_cfg}")
                            return parent
                    return path

                parent = os.path.dirname(path)
                if parent == path:
                    break
                path = parent
    except Exception:
        pass

    # 最后尝试从当前工作目录查找
    try:
        cwd = os.getcwd()
        if cwd != original_path and cwd != script_path:
            path = cwd
            checked_paths = set()  # 重置已检查路径
            while True:
                # 避免无限循环
                if path in checked_paths:
                    break
                checked_paths.add(path)
                
                cfg_file = os.path.join(path, "crawlo.cfg")
                if os.path.isfile(cfg_file):
                    _get_logger().debug(f"找到项目配置文件: {cfg_file}")
                    return path

                settings_file = os.path.join(path, "settings.py")
                init_file = os.path.join(path, "__init__.py")
                if os.path.isfile(settings_file) and os.path.isfile(init_file):
                    _get_logger().debug(f"找到项目模块: {path}")
                    # 即使找到了项目模块，也继续向上查找是否有 crawlo.cfg
                    parent = os.path.dirname(path)
                    if parent != path:
                        parent_cfg = os.path.join(parent, "crawlo.cfg")
                        if os.path.isfile(parent_cfg):
                            _get_logger().debug(f"在上层目录找到项目配置文件: {parent_cfg}")
                            return parent
                    return path

                parent = os.path.dirname(path)
                if parent == path:
                    break
                path = parent
    except Exception:
        pass

    _get_logger().warning("未找到 Crawlo 项目根目录。请确保在包含 'crawlo.cfg' 或 'settings.py' 的目录运行。")
    return None


def get_settings(custom_settings: Optional[dict] = None) -> SettingManager:
    """
    获取配置管理器实例（主入口函数）

    Args:
        custom_settings: 运行时自定义配置，会覆盖 settings.py

    Returns:
        SettingManager: 已加载配置的实例
    """
    # Change INFO level log to DEBUG level to avoid redundant output
    _get_logger().debug("🚀 正在初始化 Crawlo 项目配置...")

    # 1. 查找项目根
    project_root = _find_project_root()
    if not project_root:
        raise RuntimeError("未找到 Crawlo 项目，请检查项目结构")

    # 2. 确定 settings 模块
    settings_module_path = None
    cfg_file = os.path.join(project_root, "crawlo.cfg")

    if os.path.isfile(cfg_file):
        settings_module_path = _get_settings_module_from_cfg(cfg_file)
    else:
        # 推断：项目目录名.settings
        project_name = os.path.basename(project_root)
        settings_module_path = f"{project_name}.settings"
        _get_logger().warning(f"⚠️ 未找到 crawlo.cfg，推断 settings 模块为: {settings_module_path}")

    # 3. 注入 sys.path
    project_root_str = os.path.abspath(project_root)
    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)
        _get_logger().debug(f"📁 项目根目录已加入 sys.path: {project_root_str}")

    # 4. 加载 SettingManager
    _get_logger().debug(f"⚙️ 正在加载配置模块: {settings_module_path}")
    settings = SettingManager()

    try:
        settings.set_settings(settings_module_path)
        _get_logger().debug("✅ settings 模块加载成功")
    except Exception as e:
        raise ImportError(f"加载 settings 模块失败 '{settings_module_path}': {e}")

    # 5. 合并运行时配置
    if custom_settings:
        settings.update_attributes(custom_settings)
        _get_logger().debug(f"🔧 已应用运行时自定义配置: {list(custom_settings.keys())}")

    # 6. 显示核心配置摘要（INFO级别）
    # _log_settings_summary(settings)

    # 将项目初始化完成的消息改为DEBUG级别
    _get_logger().debug("🎉 Crawlo 项目配置初始化完成！")
    return settings