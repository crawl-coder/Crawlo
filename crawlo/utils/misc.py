import importlib
import pkgutil
from typing import Iterator, Any, Type

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