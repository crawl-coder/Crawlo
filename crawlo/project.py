import configparser
import os
import sys
from inspect import iscoroutinefunction
from typing import Callable, Optional, Any

from crawlo.settings.setting_manager import SettingManager
from crawlo.logging import get_logger

# Module-level logger (logging system is configured during framework startup)
_logger = get_logger(__name__)


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
    # Check if settings is SettingManager instance
    if not hasattr(settings, 'update_attributes'):
        _logger.warning(f"merge_settings received non-SettingManager instance: {type(settings)}")
        # If dict, create new SettingManager instance
        if isinstance(settings, dict):
            # SettingManager 已在顶部导入
            new_settings = SettingManager()
            new_settings.update_attributes(settings)
            settings = new_settings
        else:
            _logger.error("Unable to handle settings type")
            return

    if hasattr(spider, 'custom_settings'):
        custom_settings = getattr(spider, 'custom_settings')
        settings.update_attributes(custom_settings)
    else:
        _logger.debug(f"Spider '{spider_name}' has no custom_settings, skipping merge")


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


def read_crawlo_cfg(cfg_path: str) -> Optional[str]:
    """
    读取 crawlo.cfg 配置文件，返回 settings 模块路径
    
    框架统一配置文件读取入口，所有需要解析 crawlo.cfg 的地方应使用此函数。
    
    Args:
        cfg_path: crawlo.cfg 文件的绝对路径
        
    Returns:
        str: settings 模块路径（如 'myproject.settings'），
        None: 文件不存在或格式无效时返回 None
    """
    if not os.path.exists(cfg_path):
        return None
    
    try:
        config = configparser.ConfigParser()
        config.read(cfg_path, encoding='utf-8')
        
        if config.has_section('settings') and config.has_option('settings', 'default'):
            module_path = config.get('settings', 'default').strip()
            if module_path:
                return module_path
    except Exception:
        pass
    
    return None


def _get_settings_module_from_cfg(cfg_path: str) -> str:
    """Read settings module path from crawlo.cfg (internal use, raises on failure)"""
    module_path = read_crawlo_cfg(cfg_path)
    if module_path:
        _logger.debug(f"Loaded settings module from crawlo.cfg: {module_path}")
        return module_path
    raise RuntimeError(f"Failed to parse or invalid crawlo.cfg: {cfg_path}")


def _search_project_in_path(start_path: str, checked_paths: set = None) -> Optional[str]:
    """
    在指定路径中搜索项目根目录
    
    Args:
        start_path: 起始搜索路径
        checked_paths: 已检查的路径集合（避免循环）
        
    Returns:
        项目根目录路径，未找到则返回 None
    """
    if checked_paths is None:
        checked_paths = set()
    
    path = os.path.abspath(start_path)
    
    while True:
        # 避免无限循环
        if path in checked_paths:
            break
        checked_paths.add(path)
        
        # Check crawlo.cfg
        cfg_file = os.path.join(path, "crawlo.cfg")
        if os.path.isfile(cfg_file):
            _logger.debug(f"Found project config file: {cfg_file}")
            return path
        
        # Check settings.py and __init__.py
        settings_file = os.path.join(path, "settings.py")
        init_file = os.path.join(path, "__init__.py")
        if os.path.isfile(settings_file) and os.path.isfile(init_file):
            _logger.debug(f"Found project module: {path}")
            # Continue searching upward for crawlo.cfg
            parent = os.path.dirname(path)
            if parent != path:
                parent_cfg = os.path.join(parent, "crawlo.cfg")
                if os.path.isfile(parent_cfg):
                    _logger.debug(f"Found project config in parent directory: {parent_cfg}")
                    return parent
            return path
        
        parent = os.path.dirname(path)
        if parent == path:
            break
        path = parent
    
    return None


def _find_project_root(start_path: str = ".") -> Optional[str]:
    """
    从指定路径向上查找项目根目录
    
    项目识别依据（按优先级）：
    1. 存在 'crawlo.cfg' 配置文件
    2. 存在 '__init__.py' 和 'settings.py'（Python 包结构）
    
    查找策略：
    1. 首先检查当前目录及其子目录
    2. 向上递归查找父目录
    3. 如果没找到，尝试从脚本所在目录查找
    4. 最后尝试从当前工作目录查找
    
    Args:
        start_path: 起始搜索路径
        
    Returns:
        项目根目录路径，未找到则返回 None
    """
    original_path = os.path.abspath(start_path)
    checked_paths = set()
    
    # First check current directory and subdirectories
    for root, dirs, files in os.walk(original_path):
        if "crawlo.cfg" in files:
            cfg_path = os.path.join(root, "crawlo.cfg")
            _logger.debug(f"Found project config file: {cfg_path}")
            return root
    
    # 向上查找
    result = _search_project_in_path(original_path, checked_paths)
    if result:
        return result
    
    # 如果向上查找也没找到，尝试从脚本所在目录查找
    try:
        script_path = os.path.dirname(os.path.abspath(sys.argv[0]))
        if script_path != original_path:
            result = _search_project_in_path(script_path, set())
            if result:
                return result
    except Exception:
        pass
    
    # 最后尝试从当前工作目录查找
    try:
        cwd = os.getcwd()
        if cwd != original_path and cwd != script_path:
            result = _search_project_in_path(cwd, set())
            if result:
                return result
    except Exception:
        pass
    
    _logger.warning("Crawlo project root directory not found. Ensure you're running in a directory containing 'crawlo.cfg' or 'settings.py'.")
    return None


def _get_mode_settings(settings: SettingManager, run_mode: str) -> dict:
    """
    获取运行模式对应的配置
    
    Args:
        settings: 当前设置管理器
        run_mode: 运行模式
        
    Returns:
        模式配置字典
    """
    from crawlo.config import CrawloConfig
    
    # 获取模式配置
    project_name = settings.get('PROJECT_NAME', 'crawlo')
    
    if run_mode == 'distributed':
        config = CrawloConfig.distributed(project_name=project_name)
    elif run_mode == 'auto':
        config = CrawloConfig.auto(project_name=project_name)
    else:
        config = CrawloConfig.standalone(project_name=project_name)
    
    mode_settings = config.to_dict()
    
    # 注意：不再保留用户的 QUEUE_TYPE 设置
    # 原因：无法区分 default_settings.py 的默认值和用户显式设置
    # 用户应通过修改 RUN_MODE 来切换模式，而不是单独设置 QUEUE_TYPE
    # 这确保了模式配置的完整性和一致性
    
    return mode_settings


def _update_queue_related_settings(mode_settings: dict, queue_type: str, settings: SettingManager) -> None:
    """
    根据队列类型更新相关配置
    
    Args:
        mode_settings: 模式配置字典
        queue_type: 队列类型
        settings: 设置管理器
    """
    queue_config_map = {
        'redis': {
            'FILTER_CLASS': 'crawlo.filters.AioRedisFilter',
            'DEFAULT_DEDUP_PIPELINE': 'crawlo.pipelines.RedisDedupPipeline'
        },
        'auto': {
            'FILTER_CLASS': settings.get('FILTER_CLASS', 'crawlo.filters.MemoryFilter'),
            'DEFAULT_DEDUP_PIPELINE': settings.get('DEFAULT_DEDUP_PIPELINE', 'crawlo.pipelines.MemoryDedupPipeline')
        }
    }
    
    if queue_type in queue_config_map:
        mode_settings.update(queue_config_map[queue_type])


def _load_project_settings(custom_settings: Optional[dict] = None) -> SettingManager:
    """
    内部函数：加载项目配置（不处理日志初始化）
    这个函数专门负责配置加载逻辑，避免与初始化管理器产生循环依赖

    配置加载优先级（从低到高）：
    1. default_settings.py (框架默认配置)
    2. settings.py (用户项目配置)
    3. RUN_MODE 决定的配置
    4. custom_settings (运行时自定义配置 - 最高优先级)

    Args:
        custom_settings: 运行时自定义配置，会覆盖 settings.py

    Returns:
        SettingManager: 已加载配置的实例
    """
    _logger.debug("Loading Crawlo project configuration...")

    # 1. Find project root
    project_root = _find_project_root()
    if not project_root:
        raise RuntimeError("Crawlo project not found, please check project structure")

    # 2. Determine settings module
    settings_module_path = None
    cfg_file = os.path.join(project_root, "crawlo.cfg")
        
    if os.path.isfile(cfg_file):
        settings_module_path = _get_settings_module_from_cfg(cfg_file)
    else:
        # Infer: project_name.settings
        project_name = os.path.basename(project_root)
        settings_module_path = f"{project_name}.settings"
        _logger.warning(f"crawlo.cfg not found, inferring settings module: {settings_module_path}")
        
    # 3. Inject sys.path
    project_root_str = os.path.abspath(project_root)
    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)
        _logger.debug(f"Project root added to sys.path: {project_root_str}")
        
    # 4. Load SettingManager
    _logger.debug(f"Loading configuration module: {settings_module_path}")
    settings = SettingManager()
        
    try:
        settings.set_settings(settings_module_path)
        _logger.debug("Settings module loaded successfully")
    except Exception as e:
        raise ImportError(f"Failed to load settings module '{settings_module_path}': {e}")

    # 5. Apply RUN_MODE configuration
    # RUN_MODE priority: RUN_MODE config > user settings.py config
    run_mode = settings.get('RUN_MODE', 'standalone')
    if run_mode:
        mode_settings = _get_mode_settings(settings, run_mode)
        
        # Merge mode configuration
        # Priority rules:
        # 1. priority_keys: RUN_MODE config takes precedence
        # 2. Other keys: apply RUN_MODE config if not in settings
        priority_keys = ['QUEUE_TYPE', 'FILTER_CLASS', 'DEFAULT_DEDUP_PIPELINE']
        for key, value in mode_settings.items():
            if key in priority_keys or key not in settings.attributes:
                settings.set(key, value)
                _logger.debug(f"Applied {run_mode} mode config: {key} = {value}")
        _logger.debug(f"Applied {run_mode} mode configuration")

    # 6. Merge runtime configuration
    # custom_settings has highest priority, overrides all previous configs
    if custom_settings:
        settings.update_attributes(custom_settings)
        _logger.debug(f"Runtime custom configuration applied: {list(custom_settings.keys())}")
        
    _logger.debug("Crawlo project configuration loading completed")
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
