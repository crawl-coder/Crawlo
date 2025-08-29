import importlib
import inspect
from pathlib import Path
from typing import List, Type, Optional, Dict

from crawlo.spider import Spider
from crawlo.utils.log import get_logger

logger = get_logger(__name__)


class SpiderLoader:
    """爬虫加载器，负责发现和加载爬虫"""

    def __init__(self, project_package: str):
        self.project_package = project_package
        self._spiders: Dict[str, Type[Spider]] = {}
        self._load_spiders()

    def _load_spiders(self):
        """加载所有爬虫"""
        spiders_dir = Path.cwd() / self.project_package / 'spiders'
        if not spiders_dir.exists():
            logger.warning(f"Spiders directory not found: {spiders_dir}")
            return

        for py_file in spiders_dir.glob("*.py"):
            if py_file.name.startswith('_'):
                continue

            module_name = py_file.stem
            spider_module_path = f"{self.project_package}.spiders.{module_name}"

            try:
                module = importlib.import_module(spider_module_path)
            except ImportError as e:
                logger.debug(f"Skip module {module_name}: {e}")
                continue

            # 查找所有 Spider 子类
            for attr_name in dir(module):
                attr_value = getattr(module, attr_name)
                if (isinstance(attr_value, type) and
                        issubclass(attr_value, Spider) and
                        attr_value != Spider and
                        hasattr(attr_value, 'name')):

                    spider_name = getattr(attr_value, 'name')
                    if spider_name in self._spiders:
                        logger.warning(f"Duplicate spider name '{spider_name}' found")
                    self._spiders[spider_name] = attr_value

    def load(self, spider_name: str) -> Optional[Type[Spider]]:
        """通过 name 加载爬虫"""
        return self._spiders.get(spider_name)

    def list(self) -> List[str]:
        """列出所有可用的爬虫名称"""
        return list(self._spiders.keys())

    def get_all(self) -> Dict[str, Type[Spider]]:
        """获取所有爬虫"""
        return self._spiders.copy()