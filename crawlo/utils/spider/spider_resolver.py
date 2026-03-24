#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
爬虫解析相关的工具函数
用于解析爬虫类和名称
"""

from typing import Union, TYPE_CHECKING, Type, cast

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
            ValueError: 无法解析爬虫类
        """
        if isinstance(spider_cls_or_name, str):
            # 从注册表中查找
            try:
                from crawlo.spider import get_global_spider_registry
                registry = get_global_spider_registry()
                if spider_cls_or_name in registry:
                    return registry[spider_cls_or_name]
                else:
                    # 如果在注册表中找不到，尝试通过spider_modules导入所有模块来触发注册
                    # 然后再次检查注册表
                    if spider_modules:
                        for module_path in spider_modules:
                            try:
                                # 导入模块来触发爬虫注册
                                __import__(module_path)
                            except ImportError:
                                pass  # 忽略导入错误
                        
                        # 再次检查注册表
                        if spider_cls_or_name in registry:
                            return registry[spider_cls_or_name]
                    
                    # 如果仍然找不到，尝试自动发现模式
                    if spider_modules:
                        from crawlo.utils.process_utils import SpiderDiscoveryUtils
                        from crawlo.logging import get_logger
                        SpiderDiscoveryUtils.auto_discover_spider_modules(spider_modules, get_logger('crawlo.framework'))
                        if spider_cls_or_name in registry:
                            return registry[spider_cls_or_name]
                    
                    # 如果仍然找不到，尝试直接导入模块
                    try:
                        # 假设格式为 module.SpiderClass
                        if '.' in spider_cls_or_name:
                            module_path, class_name = spider_cls_or_name.rsplit('.', 1)
                            module = __import__(module_path, fromlist=[class_name])
                            spider_class = getattr(module, class_name)
                            # 注册到全局注册表
                            registry[spider_class.name] = spider_class
                            return spider_class
                        else:
                            # 尝试在spider_modules中查找
                            if spider_modules:
                                for module_path in spider_modules:
                                    try:
                                        # 构造完整的模块路径
                                        full_module_path = f"{module_path}.{spider_cls_or_name}"
                                        module = __import__(full_module_path, fromlist=[spider_cls_or_name])
                                        # 获取模块中的Spider子类
                                        for attr_name in dir(module):
                                            attr_value = getattr(module, attr_name)
                                            # 检查是否是Spider的子类
                                            if (isinstance(attr_value, type) and
                                                    hasattr(attr_value, '__bases__') and
                                                    hasattr(attr_value, 'name') and
                                                    attr_value.name == spider_cls_or_name):
                                                # 注册到全局注册表
                                                registry[spider_cls_or_name] = attr_value
                                                return attr_value
                                    except ImportError:
                                        continue
                            raise ValueError(f"Spider '{spider_cls_or_name}' not found in registry")
                    except (ImportError, AttributeError):
                        raise ValueError(f"Spider '{spider_cls_or_name}' not found in registry")
            except ImportError:
                raise ValueError(f"Cannot resolve spider name '{spider_cls_or_name}'")
        else:
            return cast(Type['Spider'], spider_cls_or_name)