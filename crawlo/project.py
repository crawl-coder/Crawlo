import configparser
import os
import sys
from inspect import iscoroutinefunction
from typing import Callable, Optional, Any

from crawlo.settings.setting_manager import SettingManager
from crawlo.logging import get_logger

# 使用全局logger，避免每个模块都创建自己的延迟初始化函数
# 延迟获取logger，确保在日志系统配置之后获取
_logger = None


def logger():
    """延迟获取logger实例，确保在日志系统配置之后获取"""
    global _logger
    if _logger is None:
        _logger = get_logger(__name__)
    return _logger


# 添加一个临时的日志函数，用于在日志系统配置之前输出信息
def _temp_debug(message):
    """临时调试函数，在日志系统配置之前使用"""
    # 直接输出到控制台，避免循环依赖
    import os
    if os.environ.get('CRAWLO_DEBUG'):
        print(f"[CRAWLO_DEBUG] {message}")


def load_class(path: str) -> Any:
    """
    动态加载类
    
    Args:
        path: 类的完整路径，如 'package.module.ClassName'
        
    Returns:
        加载的类对象
    """
    # 使用工具模块的实现，避免循环依赖
    from crawlo.utils.misc import load_object as _load_class
    return _load_class(path)


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
        _temp_debug(f"merge_settings 接收到的 settings 不是 SettingManager 实例: {type(settings)}")
        # 如果是字典，创建一个新的 SettingManager 实例
        if isinstance(settings, dict):
            from crawlo.settings.setting_manager import SettingManager
            new_settings = SettingManager()
            new_settings.update_attributes(settings)
            settings = new_settings
        else:
            _temp_debug("无法处理的 settings 类型")
            return

    if hasattr(spider, 'custom_settings'):
        custom_settings = getattr(spider, 'custom_settings')
        settings.update_attributes(custom_settings)
    else:
        _temp_debug(f"爬虫 '{spider_name}' 无 custom_settings，跳过合并")


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
            _temp_debug(f"📄 从 crawlo.cfg 加载 settings 模块: {module_path}")
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
            _temp_debug(f"✅ 找到项目配置文件: {cfg_path}")
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
            _temp_debug(f"✅ 找到项目配置文件: {cfg_file}")
            return path

        # 检查 settings.py 和 __init__.py
        settings_file = os.path.join(path, "settings.py")
        init_file = os.path.join(path, "__init__.py")
        if os.path.isfile(settings_file) and os.path.isfile(init_file):
            _temp_debug(f"✅ 找到项目模块: {path}")
            # 即使找到了项目模块，也继续向上查找是否有 crawlo.cfg
            parent = os.path.dirname(path)
            if parent != path:
                parent_cfg = os.path.join(parent, "crawlo.cfg")
                if os.path.isfile(parent_cfg):
                    _temp_debug(f"✅ 在上层目录找到项目配置文件: {parent_cfg}")
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
                    _temp_debug(f"✅ 找到项目配置文件: {cfg_file}")
                    return path

                settings_file = os.path.join(path, "settings.py")
                init_file = os.path.join(path, "__init__.py")
                if os.path.isfile(settings_file) and os.path.isfile(init_file):
                    _temp_debug(f"✅ 找到项目模块: {path}")
                    # 即使找到了项目模块，也继续向上查找是否有 crawlo.cfg
                    parent = os.path.dirname(path)
                    if parent != path:
                        parent_cfg = os.path.join(parent, "crawlo.cfg")
                        if os.path.isfile(parent_cfg):
                            _temp_debug(f"✅ 在上层目录找到项目配置文件: {parent_cfg}")
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
                    _temp_debug(f"找到项目配置文件: {cfg_file}")
                    return path

                settings_file = os.path.join(path, "settings.py")
                init_file = os.path.join(path, "__init__.py")
                if os.path.isfile(settings_file) and os.path.isfile(init_file):
                    _temp_debug(f"找到项目模块: {path}")
                    # 即使找到了项目模块，也继续向上查找是否有 crawlo.cfg
                    parent = os.path.dirname(path)
                    if parent != path:
                        parent_cfg = os.path.join(parent, "crawlo.cfg")
                        if os.path.isfile(parent_cfg):
                            _temp_debug(f"在上层目录找到项目配置文件: {parent_cfg}")
                            return parent
                    return path

                parent = os.path.dirname(path)
                if parent == path:
                    break
                path = parent
    except Exception:
        pass

    _temp_debug("未找到 Crawlo 项目根目录。请确保在包含 'crawlo.cfg' 或 'settings.py' 的目录运行。")
    return None


def _load_project_settings(custom_settings: Optional[dict] = None) -> SettingManager:
    """
    内部函数：加载项目配置（不处理日志初始化）
    这个函数专门负责配置加载逻辑，避免与初始化管理器产生循环依赖

    Args:
        custom_settings: 运行时自定义配置，会覆盖 settings.py

    Returns:
        SettingManager: 已加载配置的实例
    """
    _temp_debug("🚀 正在加载 Crawlo 项目配置...")

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
        _temp_debug(f"⚠️ 未找到 crawlo.cfg，推断 settings 模块为: {settings_module_path}")

    # 3. 注入 sys.path
    project_root_str = os.path.abspath(project_root)
    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)
        _temp_debug(f"📁 项目根目录已加入 sys.path: {project_root_str}")

    # 4. 加载 SettingManager
    _temp_debug(f"⚙️ 正在加载配置模块: {settings_module_path}")
    settings = SettingManager()

    try:
        settings.set_settings(settings_module_path)
        _temp_debug("✅ settings 模块加载成功")
    except Exception as e:
        raise ImportError(f"加载 settings 模块失败 '{settings_module_path}': {e}")

    # 5. 根据 RUN_MODE 获取相应配置
    run_mode = settings.get('RUN_MODE', 'standalone')
    if run_mode:
        from crawlo.mode_manager import ModeManager
        mode_manager = ModeManager()
        # 获取项目名称并传递给模式配置
        project_name = settings.get('PROJECT_NAME', 'crawlo')
        mode_settings = mode_manager.resolve_mode_settings(run_mode, project_name=project_name)
        
        # 特殊处理：如果用户在settings.py中明确设置了QUEUE_TYPE，
        # 应该尊重用户的设置，除非是standalone模式下的redis设置
        user_queue_type = settings.get('QUEUE_TYPE')
        if user_queue_type and run_mode == 'standalone' and user_queue_type != 'memory':
            # 在单机模式下，如果用户明确设置了QUEUE_TYPE（且不是memory），应该保留用户的设置
            # 但需要确保配置的一致性
            mode_settings['QUEUE_TYPE'] = user_queue_type
            
            # 根据QUEUE_TYPE更新其他相关配置
            if user_queue_type == 'redis':
                mode_settings['FILTER_CLASS'] = 'crawlo.filters.aioredis_filter.AioRedisFilter'
                mode_settings['DEFAULT_DEDUP_PIPELINE'] = 'crawlo.pipelines.redis_dedup_pipeline.RedisDedupPipeline'
            elif user_queue_type == 'auto':
                mode_settings['FILTER_CLASS'] = settings.get('FILTER_CLASS', 'crawlo.filters.memory_filter.MemoryFilter')
                mode_settings['DEFAULT_DEDUP_PIPELINE'] = settings.get('DEFAULT_DEDUP_PIPELINE', 'crawlo.pipelines.memory_dedup_pipeline.MemoryDedupPipeline')
        
        # 合并模式配置
        for key, value in mode_settings.items():
            # 对于特定的配置项，模式配置应该优先于用户配置
            # 特别是与运行模式密切相关的配置项
            # 但如果用户明确设置了某些关键配置且与运行模式不冲突，则应保留用户设置
            priority_keys = ['QUEUE_TYPE', 'FILTER_CLASS', 'DEFAULT_DEDUP_PIPELINE']
            if key in priority_keys or key not in settings.attributes:
                settings.set(key, value)
        _temp_debug(f"🔧 已应用 {run_mode} 模式配置")

    # 6. 合并运行时配置
    if custom_settings:
        settings.update_attributes(custom_settings)
        _temp_debug(f"🔧 已应用运行时自定义配置: {list(custom_settings.keys())}")

    _temp_debug("🎉 Crawlo 项目配置加载完成！")
    return settings


def get_settings(custom_settings: Optional[dict] = None) -> SettingManager:
    """
    获取配置管理器实例（主入口函数）
    
    注意：这个函数现在作为向后兼容的入口，实际的初始化逻辑已经移到
    crawlo.initialization 模块中。建议使用新的初始化方式：
    
    >>> from crawlo.initialization import initialize_framework
    >>> settings = initialize_framework(custom_settings)

    Args:
        custom_settings: 运行时自定义配置，会覆盖 settings.py

    Returns:
        SettingManager: 已加载配置的实例
    """
    # 使用新的统一初始化管理器
    from crawlo.initialization import initialize_framework
    return initialize_framework(custom_settings)
