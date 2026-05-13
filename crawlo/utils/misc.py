import importlib
import pkgutil
from typing import Iterator, Any, List, Type, Union, Dict, TypeVar, overload

from crawlo.spider import Spider


def walk_modules(module_path: str) -> Iterator[Any]:
    """
    加载模块并递归遍历其所有子模块
    
    Args:
        module_path: 模块路径
        
    Yields:
        导入的模块对象
        
    Raises:
        ImportError: 如果模块无法导入
    """
    # 导入模块
    module = importlib.import_module(module_path)
    yield module
    
    # 如果是包，则递归导入子模块
    if hasattr(module, '__path__'):
        for loader, submodule_name, is_pkg in pkgutil.walk_packages(module.__path__):
            try:
                submodule_path = f"{module_path}.{submodule_name}"
                submodule = importlib.import_module(submodule_path)
                yield submodule
                
                # 如果子模块也是包，递归遍历
                if is_pkg:
                    yield from walk_modules(submodule_path)
            except ImportError:
                # 跳过无法导入的子模块
                continue


def iter_spider_classes(module) -> Iterator[Type[Spider]]:
    """
    遍历模块中的所有Spider子类
    
    Args:
        module: 要遍历的模块
        
    Yields:
        Spider子类
    """
    for attr_name in dir(module):
        attr_value = getattr(module, attr_name)
        if (isinstance(attr_value, type) and
                issubclass(attr_value, Spider) and
                attr_value != Spider and
                hasattr(attr_value, 'name')):
            yield attr_value


def load_object(path: str):
    """
    从路径加载对象
    
    Args:
        path: 对象路径，格式为 module.submodule:object_name 或 module.submodule.object_name
        
    Returns:
        加载的对象
    """
    try:
        # 处理 module.submodule:object_name 格式
        if ':' in path:
            module_path, obj_name = path.split(':', 1)
            module = importlib.import_module(module_path)
            return getattr(module, obj_name)
        else:
            # 处理 module.submodule.object_name 格式
            module_path, obj_name = path.rsplit('.', 1)
            module = importlib.import_module(module_path)
            return getattr(module, obj_name)
    except (ImportError, AttributeError) as e:
        raise ImportError(f"Could not load object from path '{path}': {e}")


T = TypeVar('T')


@overload
def safe_get_config(settings, key: str, default: None = None, value_type: type[bool] = ...) -> bool: ...

@overload
def safe_get_config(settings, key: str, default: None = None, value_type: type[int] = ...) -> int: ...

@overload
def safe_get_config(settings, key: str, default: None = None, value_type: type[float] = ...) -> float: ...

@overload
def safe_get_config(settings, key: str, default: None = None, value_type: type[str] = ...) -> str: ...

@overload
def safe_get_config(settings, key: str, default: T, value_type: type = ...) -> T: ...

@overload
def safe_get_config(settings, key: str, default: None = None, value_type: None = None) -> Any: ...

def safe_get_config(settings, key, default=None, value_type=None):
    """
    安全获取配置值的辅助函数
    
    Args:
        settings: 配置对象
        key: 配置键名
        default: 默认值
        value_type: 值类型（int, float, bool等）
        
    Returns:
        配置值或默认值
    """
    if settings is None:
        return default
        
    try:
        # 优先使用配置对象的方法
        if hasattr(settings, 'get') and callable(getattr(settings, 'get', None)):
            value = settings.get(key, default)
        # 其次处理字典类型
        elif isinstance(settings, dict):
            value = settings.get(key, default)
        # 最后尝试直接属性访问
        else:
            value = getattr(settings, key, default)
        
        # 如果指定了类型，进行类型转换
        if value_type and value is not None:
            if value_type == int:
                return int(value)
            elif value_type == float:
                return float(value)
            elif value_type == bool:
                # 特殊处理bool类型，支持字符串"0"/"1"和数字0/1的转换
                if isinstance(value, str):
                    return value.lower() not in ('0', 'false', 'no', 'off', '')
                elif isinstance(value, (int, float)):
                    return bool(value)
                else:
                    return bool(value)
        
        return value
    except Exception:
        return default


# ----- 浏览器下载器通用配置读取（三级优先级回退） -----

_SENTINEL = object()

def get_browser_config(settings, prefix: str, key: str, default: Any = None) -> Any:
    """
    浏览器配置三级优先级回退读取。
    
    优先级：
    1. {PREFIX}_{KEY}   — 下载器特有覆盖（如 CLOAKBROWSER_HEADLESS）
    2. BROWSER_{KEY}    — 浏览器通用配置（如 BROWSER_HEADLESS）
    3. default          — 硬编码默认值
    
    Args:
        settings: 配置对象（SettingManager）
        prefix: 下载器前缀（如 "PLAYWRIGHT", "CLOAKBROWSER"）
        key: 参数名（如 "HEADLESS", "TIMEOUT"）
        default: 默认值
        
    Returns:
        按优先级解析后的配置值
    """
    # 1. 下载器特有配置（用户显式覆盖）
    specific_key = f"{prefix}_{key}"
    value = settings.get(specific_key, None)
    if value is not None:
        return value

    # 2. 浏览器通用配置
    common_key = f"BROWSER_{key}"
    value = settings.get(common_key, None)
    if value is not None:
        return value

    # 3. 硬编码默认值
    return default


def get_browser_config_int(settings, prefix: str, key: str, default: int = 0) -> int:
    """get_browser_config 的 int 类型安全变体"""
    value = get_browser_config(settings, prefix, key, default)
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def get_browser_config_bool(settings, prefix: str, key: str, default: bool = False) -> bool:
    """get_browser_config 的 bool 类型安全变体（兼容 '0'/'1'/'true'/'false' 字符串）"""
    value = get_browser_config(settings, prefix, key, default)
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.lower().strip() in ('1', 'true')
    return bool(value)


def get_browser_config_list(settings, prefix: str, key: str, default: list = None) -> list:
    """get_browser_config 的 list 类型安全变体（兼容逗号分隔字符串）"""
    value = get_browser_config(settings, prefix, key, default)
    if value is None:
        return default or []
    if isinstance(value, str):
        return [v.strip() for v in value.split(',') if v.strip()]
    try:
        return list(value)
    except TypeError:
        return [value]


class ConfigUtils:
    """通用配置工具类"""

    @staticmethod
    def get_config_value(
        config_sources: List[Union[Dict, Any]],
        key: str,
        default: Any = None,
        value_type: type = str
    ) -> Any:
        """
        从多个配置源中获取配置值

        Args:
            config_sources: 配置源列表，按优先级排序
            key: 配置键名
            default: 默认值
            value_type: 值类型

        Returns:
            配置值或默认值
        """
        for config_source in config_sources:
            if not config_source:
                continue

            value = None
            if hasattr(config_source, 'get'):
                value = config_source.get(key)
            elif hasattr(config_source, key):
                value = getattr(config_source, key)
            else:
                continue

            if value is not None:
                try:
                    if value_type == bool:
                        if isinstance(value, str):
                            return value.lower() in ('1', 'true', 'yes', 'on')
                        return bool(value)
                    elif value_type == int:
                        return int(value)
                    elif value_type == float:
                        return float(value)
                    else:
                        return value_type(value)
                except (ValueError, TypeError):
                    continue

        return default

    @staticmethod
    def has_config_prefix(config_source: Union[Dict, Any], prefix: str) -> bool:
        """
        检查配置源是否包含指定前缀的配置项

        Args:
            config_source: 配置源
            prefix: 前缀

        Returns:
            是否包含指定前缀的配置项
        """
        if not config_source:
            return False

        if hasattr(config_source, 'keys'):
            return any(key.startswith(prefix) for key in config_source.keys())
        else:
            return any(key.startswith(prefix) for key in dir(config_source))

    @staticmethod
    def merge_config_sources(config_sources: List[Union[Dict, Any]]) -> Dict[str, Any]:
        """
        合并多个配置源，后面的配置源优先级更高

        Args:
            config_sources: 配置源列表

        Returns:
            合并后的配置字典
        """
        merged_config = {}

        for config_source in config_sources:
            if not config_source:
                continue

            if hasattr(config_source, 'keys'):
                for key, value in config_source.items():
                    if key.isupper():
                        merged_config[key] = value
            elif hasattr(config_source, '__dict__'):
                for key, value in config_source.__dict__.items():
                    if key.isupper():
                        merged_config[key] = value
            else:
                for key in dir(config_source):
                    if key.isupper():
                        merged_config[key] = getattr(config_source, key)

        return merged_config