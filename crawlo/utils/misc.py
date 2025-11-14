import importlib
import pkgutil
from typing import Iterator, Any, Type, Union, Dict

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
    except (TypeError, ValueError, AttributeError, Exception):
        return default