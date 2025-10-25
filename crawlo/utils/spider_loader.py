import importlib
import traceback
import warnings
from collections import defaultdict
from pathlib import Path
from typing import List, Type, Dict, Any

from crawlo.interfaces import ISpiderLoader
from crawlo.settings.setting_manager import SettingManager
from crawlo.spider import Spider
from crawlo.network.request import Request
from crawlo.logging import get_logger

logger = get_logger(__name__)


class SpiderLoaderProtocol:
    """Protocol for spider loader"""
    
    @classmethod
    def from_settings(cls, settings: SettingManager) -> 'SpiderLoaderProtocol':
        """Create spider loader from settings"""
        return cls(settings)
    
    def load(self, spider_name: str) -> Type[Spider]:
        """Load a spider by name"""
        raise NotImplementedError
    
    def list(self) -> List[str]:
        """List all available spider names"""
        raise NotImplementedError
    
    def find_by_request(self, request: 'Request') -> List[str]:
        """Find spider names that can handle the given request"""
        raise NotImplementedError


class SpiderLoader(ISpiderLoader):
    """爬虫加载器，负责发现和加载爬虫"""
    
    def __init__(self, settings: SettingManager = None):
        # 如果提供了settings，则从settings中获取配置
        if settings is not None:
            self.spider_modules = settings.get('SPIDER_MODULES', [])
            self.warn_only = settings.get('SPIDER_LOADER_WARN_ONLY', False)
        else:
            # 默认配置
            self.spider_modules = []
            self.warn_only = False
            
        self._spiders: Dict[str, Type[Spider]] = {}
        self._found: Dict[str, List[tuple]] = defaultdict(list)
        self._load_all_spiders()
    
    @classmethod
    def from_settings(cls, settings: SettingManager) -> 'SpiderLoader':
        """从设置创建SpiderLoader实例"""
        return cls(settings)
    
    def _check_name_duplicates(self) -> None:
        """检查重复的spider名称"""
        dupes = []
        for name, locations in self._found.items():
            if len(locations) > 1:
                dupes.extend([
                    f"  {cls} named {name!r} (in {mod})"
                    for mod, cls in locations
                ])
        
        if dupes:
            dupes_string = "\n\n".join(dupes)
            warnings.warn(
                "There are several spiders with the same name:\n\n"
                f"{dupes_string}\n\n  This can cause unexpected behavior.",
                category=UserWarning,
            )
    
    def _load_spiders(self, module) -> None:
        """加载模块中的所有spider"""
        for attr_name in dir(module):
            attr_value = getattr(module, attr_name)
            if (isinstance(attr_value, type) and
                    issubclass(attr_value, Spider) and
                    attr_value != Spider and
                    hasattr(attr_value, 'name')):
                
                spider_name = getattr(attr_value, 'name')
                self._found[spider_name].append((module.__name__, attr_value.__name__))
                self._spiders[spider_name] = attr_value
    
    def _load_spiders_from_package(self, package_name: str) -> None:
        """从包中加载spiders"""
        try:
            # 尝试导入包
            package = importlib.import_module(package_name)
            
            # 遍历包中的所有模块
            package_path = Path(package.__file__).parent
            for py_file in package_path.glob("*.py"):
                if py_file.name.startswith('_'):
                    continue
                
                module_name = py_file.stem
                spider_module_path = f"{package_name}.{module_name}"
                
                try:
                    module = importlib.import_module(spider_module_path)
                    self._load_spiders(module)
                except ImportError as e:
                    if self.warn_only:
                        logger.warning(f"Could not load spiders from module '{spider_module_path}': {e}")
                        logger.debug(traceback.format_exc())
                    else:
                        raise
        except (ImportError, SyntaxError) as e:
            if self.warn_only:
                logger.warning(f"Could not load spiders from package '{package_name}': {e}")
                logger.debug(traceback.format_exc())
            else:
                raise
    
    def _load_all_spiders(self) -> None:
        """加载所有spiders"""
        # 如果配置了SPIDER_MODULES，则从这些模块加载
        if self.spider_modules:
            for module_name in self.spider_modules:
                self._load_spiders_from_package(module_name)
        else:
            # 向后兼容：如果没有配置SPIDER_MODULES，则使用旧的方式
            # 这里假设默认的spiders目录结构
            spiders_dir = Path.cwd() / 'spiders'
            if not spiders_dir.exists():
                spiders_dir = Path.cwd() / 'spider'
                if not spiders_dir.exists():
                    logger.warning("Spiders directory not found")
                    return
            
            for py_file in spiders_dir.glob("*.py"):
                if py_file.name.startswith('_'):
                    continue
                
                module_name = py_file.stem
                module = None
                try:
                    # 尝试不同的导入路径
                    spider_module_path = None
                    for possible_package in ['spiders', 'spider']:
                        try:
                            spider_module_path = f"{possible_package}.{module_name}"
                            module = importlib.import_module(spider_module_path)
                            break
                        except ImportError:
                            continue
                    
                    if module is None:
                        raise ImportError(f"Could not import {module_name}")
                    
                    self._load_spiders(module)
                except ImportError as e:
                    logger.debug(f"Skip module {module_name}: {e}")
                    continue
        
        self._check_name_duplicates()
    
    def load(self, spider_name: str) -> Type[Spider]:
        """
        通过name加载爬虫
        
        Args:
            spider_name: 爬虫名称
            
        Returns:
            Spider类
            
        Raises:
            KeyError: 如果找不到指定名称的爬虫
        """
        if spider_name not in self._spiders:
            raise KeyError(f"Spider not found: {spider_name}")
        return self._spiders[spider_name]
    
    def list(self) -> List[str]:
        """列出所有可用的爬虫名称"""
        return list(self._spiders.keys())
    
    def find_by_request(self, request: 'Request') -> List[str]:
        """
        根据请求找到可以处理该请求的爬虫名称
        
        Args:
            request: 请求对象
            
        Returns:
            可以处理该请求的爬虫名称列表
        """
        # 这里可以实现更复杂的匹配逻辑
        # 目前只是返回所有爬虫名称
        return list(self._spiders.keys())
    
    def get_all(self) -> Dict[str, Type[Spider]]:
        """获取所有爬虫"""
        return self._spiders.copy()