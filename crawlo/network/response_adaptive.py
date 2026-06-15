#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Response 自适应选择器 Mixin
==========================
将自适应选择器相关功能从 Response 中提取为独立 Mixin，
保持与 ClusterMixin 一致的设计模式。

包含：
- 类级别存储/匹配器缓存
- _is_adaptive_enabled / _cleanup_adaptive / configure_adaptive
- find_similar / _save / _retrieve / _relocate
"""
import atexit
from typing import Dict, Any, List, Optional

from lxml.html import HtmlElement
from parsel import Selector, SelectorList

from crawlo.logging import get_logger


class ResponseAdaptiveMixin:
    """Response 自适应选择器功能 Mixin"""

    # 类级别缓存（按配置 key 隔离不同 crawler 的存储/匹配器）
    _adaptive_storage = None
    _adaptive_matcher = None
    _adaptive_config_key = None
    _adaptive_enabled_global = None
    _adaptive_initialized = False
    _cleanup_registered = False

    # ========================================================================
    # 初始化 / 配置 / 清理
    # ========================================================================

    @classmethod
    def _is_adaptive_enabled(cls, settings=None) -> bool:
        """检查自适应选择器是否可用（延迟初始化，支持按 settings 隔离不同 crawler 配置）

        第一次调用时从 settings 或默认配置读取并初始化存储/匹配器。
        不同配置的 crawler 会重新初始化各自的存储实例。

        Args:
            settings: 可选 settings 对象（dict 或 Settings 实例）
        """
        def _get(key, default):
            if settings is None:
                return default
            if hasattr(settings, 'get'):
                return settings.get(key, default)
            return settings.get(key, default) if isinstance(settings, dict) else default

        backend = _get('ADAPTIVE_STORAGE_BACKEND', 'sqlite')
        sqlite_path = _get('ADAPTIVE_SQLITE_PATH', 'adaptive_fingerprints.db')
        threshold = float(_get('ADAPTIVE_SIMILARITY_THRESHOLD', 0))
        redis_host = _get('REDIS_HOST', 'localhost')
        redis_port = int(_get('REDIS_PORT', 6379))
        redis_password = _get('REDIS_PASSWORD', '')
        redis_db = int(_get('REDIS_DB', 0))

        config_key = (backend, sqlite_path, threshold)
        if cls._adaptive_config_key == config_key and cls._adaptive_storage is not None:
            return True

        try:
            from crawlo.helpers.adaptive_selector import FingerprintStorage, SimilarityMatcher
            cls._adaptive_storage = FingerprintStorage(
                backend=backend, storage_file=sqlite_path,
                redis_host=redis_host, redis_port=redis_port,
                redis_password=redis_password, redis_db=redis_db,
            )
            cls._adaptive_matcher = SimilarityMatcher(threshold=threshold)
            cls._adaptive_config_key = config_key
            cls._adaptive_enabled_global = True
            cls._adaptive_initialized = True

            if not cls._cleanup_registered:
                atexit.register(cls._cleanup_adaptive)
                cls._cleanup_registered = True

            return True
        except Exception:
            cls._adaptive_enabled_global = False
            cls._adaptive_initialized = True
            return False

    @classmethod
    def _cleanup_adaptive(cls):
        """清理自适应选择器资源（防止内存泄漏）"""
        try:
            if cls._adaptive_storage:
                if hasattr(cls._adaptive_storage, 'close'):
                    cls._adaptive_storage.close()
                cls._adaptive_storage = None

            cls._adaptive_matcher = None
            cls._adaptive_config_key = None
            cls._adaptive_enabled_global = None
            cls._adaptive_initialized = False

            get_logger('Response').debug("Adaptive selector resources cleaned up")
        except Exception as e:
            get_logger('Response').warning(f"Failed to cleanup adaptive selector: {e}")

    @classmethod
    def cleanup_adaptive(cls):
        """公开方法：手动清理自适应选择器资源（供爬虫关闭时调用）"""
        cls._cleanup_adaptive()

    @classmethod
    def configure_adaptive(cls, backend: str = 'sqlite',
                           storage_file: str = 'adaptive_fingerprints.db',
                           threshold: float = 0.0, **kwargs) -> None:
        """手动配置自适应选择器（不依赖 settings，方便独立使用）

        Args:
            backend: 存储后端 'sqlite' 或 'redis'
            storage_file: SQLite 文件路径
            threshold: 最低相似度阈值
        """
        from crawlo.helpers.adaptive_selector import FingerprintStorage, SimilarityMatcher
        cls._adaptive_enabled_global = True
        cls._adaptive_storage = FingerprintStorage(
            backend=backend, storage_file=storage_file, **kwargs
        )
        cls._adaptive_matcher = SimilarityMatcher(threshold=threshold)

    # ========================================================================
    # 指纹保存 / 检索 / 重定位
    # ========================================================================

    def _save_element_fingerprint(self, selector_item, identifier: str) -> None:
        """保存元素的指纹到存储（仅首次保存，已有指纹不覆盖）

        设计意图：保留首次抓取时的"原始"指纹作为恢复基准。
        网站渐进改版时（class→tag→结构），始终用原始指纹匹配，
        避免被中间状态的指纹污染。

        Args:
            selector_item: parsel Selector 对象
            identifier: 指纹标识符
        """
        if self.__class__._adaptive_storage is None:
            return

        try:
            existing = self.__class__._adaptive_storage.retrieve(self.url, identifier)
            if existing is not None:
                return

            root = selector_item.root if hasattr(selector_item, 'root') else selector_item
            if isinstance(root, HtmlElement):
                from crawlo.helpers.adaptive_selector import ElementFingerprint
                fp = ElementFingerprint.from_element(root)
                self.__class__._adaptive_storage.save(self.url, identifier, fp)
        except Exception as e:
            get_logger('Response').debug(f"Failed to save fingerprint: {e}")

    def _retrieve_element_fingerprint(self, identifier: str):
        """从存储加载元素指纹

        Args:
            identifier: 指纹标识符

        Returns:
            指纹字典或 None
        """
        if self.__class__._adaptive_storage is None:
            return None

        try:
            return self.__class__._adaptive_storage.retrieve(self.url, identifier)
        except Exception:
            return None

    def _adaptive_relocate(self, element_data, percentage: float = 0.0):
        """自适应重新定位元素：遍历页面元素，找到最匹配的

        Args:
            element_data: 保存的元素指纹字典
            percentage: 最低匹配百分比

        Returns:
            List[lxml.html.HtmlElement]: 匹配的元素列表
        """
        if self.__class__._adaptive_matcher is None:
            return []

        try:
            from crawlo.helpers.adaptive_selector import ElementFingerprint
            target_fp = ElementFingerprint.from_dict(element_data)
            root = self._selector.root
            if not isinstance(root, HtmlElement):
                return []

            return self.__class__._adaptive_matcher.find_best_matches(
                target_fp, root, percentage=percentage
            )
        except Exception as e:
            get_logger('Response').debug(f"Adaptive relocate failed: {e}")
            return []

    # ========================================================================
    # 自适应选择器执行流程（xpath/css 中调用）
    # ========================================================================

    def _handle_adaptive_result(self, result: SelectorList, query: str,
                                 adaptive: bool, identifier: str,
                                 percentage: float) -> SelectorList:
        """统一处理 xpath/css 的自适应结果（保存 or 恢复）

        Args:
            result: xpath/css 查询结果
            query: 原始查询字符串
            adaptive: 是否启用自适应
            identifier: 指纹标识符
            percentage: 最低匹配百分比

        Returns:
            SelectorList: 处理后的结果
        """
        if result:
            if adaptive and self._is_adaptive_enabled():
                base_id = identifier or query
                for i, elem in enumerate(result[:10]):
                    idx_id = f'{base_id}_{i}' if len(result) > 1 else base_id
                    self._save_element_fingerprint(elem, idx_id)
            return result

        if adaptive and self._is_adaptive_enabled():
            base_id = identifier or query
            saved_elements = []
            for i in range(10):
                idx_id = f'{base_id}_{i}' if i > 0 else base_id
                element_data = self._retrieve_element_fingerprint(idx_id)
                if not element_data:
                    if i == 0:
                        continue
                    else:
                        break
                matched = self._adaptive_relocate(element_data, percentage)
                if matched:
                    saved_elements.extend(matched)
            if saved_elements:
                get_logger('Response').info(
                    f"Adaptive matched {len(saved_elements)} element(s) "
                    f"for selector '{query}'"
                )
                return SelectorList([
                    Selector(root=el, type='html') for el in saved_elements
                ])
        elif adaptive:
            get_logger('Response').warning(
                "Adaptive selector argument ignored because "
                "ADAPTIVE_SELECTOR_ENABLED is not set to True in settings"
            )

        return result

    def find_similar(
        self,
        identifier: str,
        threshold: float = 50.0,
        ignore_attributes: Optional[Any] = None,
    ) -> SelectorList:
        """Find structurally similar elements based on a saved fingerprint.

        After locating a reference element with adaptive=True, this method finds
        all structurally similar sibling elements (e.g., other products in the same
        list). Uses DOM hierarchy (same parent/grandparent + depth) + attribute/text
        similarity for matching.

        Example:
            response.css('.product-item', adaptive=True, identifier='product')
            all_products = response.find_similar('product', threshold=60)

        Args:
            identifier: Fingerprint identifier (same as used in xpath/css adaptive call)
            threshold: Minimum similarity percentage (0-100, default 50)
            ignore_attributes: Attribute names to skip in comparison (e.g., {'href', 'src'})

        Returns:
            SelectorList of similar elements (excluding the reference element itself)
        """
        if not self._is_adaptive_enabled() or self.__class__._adaptive_storage is None:
            return SelectorList([])

        element_data = self._retrieve_element_fingerprint(identifier)
        if not element_data:
            get_logger('Response').warning(
                f"find_similar: no fingerprint found for identifier '{identifier}'"
            )
            return SelectorList([])

        from crawlo.helpers.adaptive_selector import ElementFingerprint, SimilarityMatcher

        target_fp = ElementFingerprint.from_dict(element_data)
        matcher = SimilarityMatcher(
            threshold=threshold,
            ignore_attributes=ignore_attributes or set(),
        )

        page_root = self.selector._root if hasattr(self.selector, '_root') else self.selector.root
        results = matcher.find_similar_elements(target_fp, page_root, threshold)

        if results:
            get_logger('Response').debug(
                f"find_similar: found {len(results)} similar elements for '{identifier}'"
            )

        return SelectorList([Selector(root=el, type='html') for el in results])
