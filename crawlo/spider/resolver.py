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
        
        # 如果是字符串，需要解析
        if not isinstance(spider_cls_or_name, str):
            return cast(Type['Spider'], spider_cls_or_name)
        
        # 导入必要的模块
        try:
            from crawlo.spider import get_global_spider_registry, Spider
        except ImportError:
            raise ValueError(f"Cannot resolve spider name '{spider_cls_or_name}'")
        
        registry = get_global_spider_registry()
        spider_name = spider_cls_or_name
        
        # 1. 尝试从注册表获取
        if spider_name in registry:
            return registry[spider_name]
        
        # 2. 尝试通过spider_modules导入所有模块来触发注册
        if spider_modules:
            SpiderResolver._import_modules(spider_modules, _add_failure)
            if spider_name in registry:
                return registry[spider_name]
        
        # 3. 尝试自动发现模式
        if spider_modules:
            SpiderResolver._auto_discover_spiders(spider_modules, registry)
            if spider_name in registry:
                return registry[spider_name]
        
        # 4. 尝试直接导入模块
        SpiderResolver._try_direct_import(spider_name, registry, _add_failure)
        if spider_name in registry:
            return registry[spider_name]
        
        # 5. 所有方法都失败
        raise _fail(f"Spider '{spider_name}' not found in registry")
    
    @staticmethod
    def _import_modules(modules: List[str], add_failure) -> None:
        """导入模块列表"""
        for module_path in modules:
            try:
                __import__(module_path)
            except Exception as e:
                add_failure(f"{module_path}: {type(e).__name__}: {e}")
    
    @staticmethod
    def _auto_discover_spiders(modules: List[str], registry: dict) -> None:
        """自动发现爬虫"""
        from crawlo.spider import SpiderDiscoveryState
        from crawlo.utils.process_utils import SpiderDiscoveryUtils
        from crawlo.logging import get_logger
        
        undiscovered_modules = [
            m for m in modules
            if not SpiderDiscoveryState.is_discovered(m)
        ]
        
        if undiscovered_modules:
            SpiderDiscoveryUtils.auto_discover_spider_modules(
                undiscovered_modules, 
                get_logger('crawlo.framework')
            )
    
    @staticmethod
    def _try_direct_import(spider_name: str, registry: dict, add_failure) -> None:
        """尝试直接导入模块"""
        from crawlo.spider import Spider
        
        try:
            # 格式：module.ClassName
            if '.' in spider_name:
                pkg_path, class_name = spider_name.rsplit('.', 1)
                module = __import__(pkg_path, fromlist=[class_name])
                spider_class = getattr(module, class_name)
                
                if isinstance(spider_class, type) and issubclass(spider_class, Spider):
                    registry[spider_class.name] = spider_class
                return
            
            # 格式：ClassName（在spider_modules中搜索）
            # 注：此逻辑已在 auto_discover_spiders 中处理
            
        except Exception as e:
            add_failure(f"{spider_name}: {type(e).__name__}: {e}")
