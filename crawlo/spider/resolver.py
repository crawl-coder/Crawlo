#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
爬虫解析相关的工具函数
用于解析爬虫类和名称
"""

from typing import Union, TYPE_CHECKING, Type, cast, List

if TYPE_CHECKING:
    from crawlo.spider import Spider


class SpiderResolver:
    """爬虫解析工具类"""
    
    @staticmethod
    def resolve_spider_class(spider_cls_or_name: Union[Type['Spider'], str], spider_modules=None) -> Type['Spider']:
        """
        解析Spider类
        
        Args:
            spider_cls_or_name: 爬虫类或名称
            spider_modules: 爬虫模块列表
            
        Returns:
            Type[Spider]: 爬虫类
            
        Raises:
            ValueError: 无法解析爬虫类（附带导入失败的原始错误）
        """
        import_failures: List[str] = []
        _seen_failures: set = set()
        
        def _add_failure(msg: str) -> None:
            """添加导入失败记录，自动去重"""
            if msg not in _seen_failures:
                _seen_failures.add(msg)
                import_failures.append(msg)
        
        def _fail(msg: str) -> ValueError:
            """构建异常：优先报告导入失败，其次报告未找到"""
            if import_failures:
                details = "; ".join(import_failures)
                return ValueError(f"Failed to import spider modules: {details}")
            return ValueError(msg)
        
        if isinstance(spider_cls_or_name, str):
            try:
                from crawlo.spider import get_global_spider_registry, Spider
                registry = get_global_spider_registry()
                if spider_cls_or_name in registry:
                    return registry[spider_cls_or_name]
                
                # 尝试通过spider_modules导入所有模块来触发注册
                if spider_modules:
                    for module_path in spider_modules:
                        try:
                            __import__(module_path)
                        except Exception as e:
                            _add_failure(f"{module_path}: {type(e).__name__}: {e}")
                    
                    if spider_cls_or_name in registry:
                        return registry[spider_cls_or_name]
                
                # 尝试自动发现模式（跳过已扫描过的模块）
                if spider_modules:
                    from crawlo.spider import SpiderDiscoveryState
                    from crawlo.utils.process_utils import SpiderDiscoveryUtils
                    from crawlo.logging import get_logger
                    undiscovered_modules = [
                        m for m in spider_modules
                        if not SpiderDiscoveryState.is_discovered(m)
                    ]
                    if undiscovered_modules:
                        SpiderDiscoveryUtils.auto_discover_spider_modules(undiscovered_modules, get_logger('crawlo.framework'))
                    if spider_cls_or_name in registry:
                        return registry[spider_cls_or_name]
                
                # 尝试直接导入模块
                try:
                    if '.' in spider_cls_or_name:
                        pkg_path, class_name = spider_cls_or_name.rsplit('.', 1)
                        module = __import__(pkg_path, fromlist=[class_name])
                        spider_class = getattr(module, class_name)
                        if not (isinstance(spider_class, type) and issubclass(spider_class, Spider)):
                            raise ValueError(f"'{spider_cls_or_name}' is not a Spider subclass")
                        registry[spider_class.name] = spider_class
                        return spider_class
                    else:
                        if spider_modules:
                            for module_path in spider_modules:
                                try:
                                    full_module_path = f"{module_path}.{spider_cls_or_name}"
                                    module = __import__(full_module_path, fromlist=[spider_cls_or_name])
                                    for attr_name in dir(module):
                                        attr_value = getattr(module, attr_name)
                                        if (isinstance(attr_value, type) and
                                                issubclass(attr_value, Spider) and
                                                attr_value.name == spider_cls_or_name):
                                            registry[spider_cls_or_name] = attr_value
                                            return attr_value
                                except Exception as e:
                                    _add_failure(f"{module_path}.{spider_cls_or_name}: {type(e).__name__}: {e}")
                                    continue
                except Exception as e:
                    _add_failure(f"{spider_cls_or_name}: {type(e).__name__}: {e}")
                
                raise _fail(f"Spider '{spider_cls_or_name}' not found in registry")
            except ImportError:
                raise ValueError(f"Cannot resolve spider name '{spider_cls_or_name}'")
        else:
            return cast(Type['Spider'], spider_cls_or_name)
