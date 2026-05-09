#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
HTTP Response 封装模块
=====================
提供功能丰富的HTTP响应封装，支持:
- 智能编码检测和解码
- XPath/CSS 选择器
- JSON 解析和缓存
- 正则表达式支持
- Cookie 处理
"""
import re
from typing import Dict, Any, List, Optional, Union, Pattern, Match, TYPE_CHECKING
from urllib.parse import urljoin as _urljoin
from parsel import Selector, SelectorList
from lxml.html import HtmlElement

# 尝试使用 ujson 提升性能，失败时降级到标准库 json
try:
    import ujson as json_module
    USE_UJSON = True
except ImportError:
    import json as json_module
    USE_UJSON = False

if TYPE_CHECKING:
    from crawlo.network.request import Request

from crawlo.exceptions import DecodeError
from crawlo.logging import get_logger
from crawlo.utils.encoding_detector import EncodingDetector
from crawlo.utils.request.response_helper import (
    parse_cookies,
    regex_search,
    regex_findall,
    regex_findone,
    get_header_value
)
from crawlo.settings.default_settings import (
    ADAPTIVE_STORAGE_BACKEND,
    ADAPTIVE_SQLITE_PATH,
    ADAPTIVE_SIMILARITY_THRESHOLD,
    REDIS_HOST, REDIS_PORT, REDIS_PASSWORD, REDIS_DB,
)
from crawlo.helpers.adaptive_selector import (
    FingerprintStorage,
    SimilarityMatcher,
    ElementFingerprint,
)
from crawlo.utils.decorators import memoize_method_noargs


class Response:
    """
    HTTP响应的封装，提供数据解析的便捷方法。
    
    功能特性:
    - 智能编码检测和缓存
    - 懒加载 Selector 实例
    - JSON 解析和缓存
    - 多类型数据提取
    - 自适应元素追踪（adaptive=True 自动保存指纹+失效时自愈）
    """

    # 默认编码
    _DEFAULT_ENCODING = "ascii"

    # 自适应选择器相关缓存（类级别，跨 Response 共享存储）
    _adaptive_storage = None
    _adaptive_matcher = None
    _adaptive_enabled_global = None  # None 表示未初始化
    _adaptive_initialized = False  # 标记是否已初始化
    _cleanup_registered = False  # 标记是否已注册清理函数

    def __init__(
            self,
            url: str,
            *,
            headers: Optional[Dict[str, Any]] = None,
            body: bytes = b"",
            method: str = 'GET',
            request: Optional['Request'] = None,  # 使用字符串注解避免循环导入
            status: int = 200,
    ) -> None:
        """
        初始化响应对象
        
        Args:
            url: 响应URL
            headers: 响应头
            body: 响应体
            method: 请求方法
            request: 对应的请求对象
            status: HTTP 状态码
        """
        # 基本属性
        self.url: str = url
        self.headers: Dict[str, Any] = headers or {}
        self.body: bytes = body
        self.method: str = method.upper()
        self.request: Optional['Request'] = request
        self.status: int = status

        # 请求标记（从 Request.flags 传递，供回调函数检查）
        self.flags: list = getattr(request, 'flags', []) if request else []

        # 编码处理
        self.encoding: str = self._determine_encoding()

        # 缓存属性
        self._text_cache: Optional[str] = None
        self._json_cache: Optional[Any] = None
        self._selector_instance: Optional[Selector] = None

        # 状态标记
        self._is_success: bool = 200 <= status < 300
        self._is_redirect: bool = 300 <= status < 400
        self._is_client_error: bool = 400 <= status < 500
        self._is_server_error: bool = status >= 500

    # ==================== 编码检测相关方法 ====================
    
    def _determine_encoding(self) -> str:
        """
        智能检测响应编码
        
        编码检测优先级：
        1. Request 中指定的编码（最高优先级，用户显式指定）
        2. BOM 字节顺序标记
        3. HTTP Content-Type 头部
        4. HTML meta 标签声明
        5. 内容自动检测（基于字符频率分析）
        6. 默认编码 (utf-8)
        
        Returns:
            str: 检测到的编码
        """
        # 获取 Request 中声明的编码
        declared_encoding = None
        if self.request and getattr(self.request, 'encoding', None):
            declared_encoding = self.request.encoding
        
        # 使用 EncodingDetector 进行检测
        return EncodingDetector.detect(
            body=self.body,
            headers=self.headers,
            declared_encoding=declared_encoding,
        )

    @property
    def text(self) -> str:
        """
        将响应体(body)以正确的编码解码为字符串，并缓存结果。
        
        Returns:
            str: 解码后的文本
        """
        if self._text_cache is not None:
            return self._text_cache

        if not self.body:
            self._text_cache = ""
            return self._text_cache

        # 使用 EncodingDetector 解码
        self._text_cache = EncodingDetector.decode_body(
            body=self.body,
            encoding=self.encoding,
            headers=self.headers,
        )
        return self._text_cache

    # ==================== 状态检查相关属性 ====================
    
    @property
    def is_success(self) -> bool:
        """
        检查响应是否成功 (2xx)
        
        Returns:
            bool: 是否成功
        """
        return self._is_success

    @property
    def is_redirect(self) -> bool:
        """
        检查响应是否为重定向 (3xx)
        
        Returns:
            bool: 是否为重定向
        """
        return self._is_redirect

    @property
    def is_client_error(self) -> bool:
        """
        检查响应是否为客户端错误 (4xx)
        
        Returns:
            bool: 是否为客户端错误
        """
        return self._is_client_error

    @property
    def is_server_error(self) -> bool:
        """
        检查响应是否为服务器错误 (5xx)
        
        Returns:
            bool: 是否为服务器错误
        """
        return self._is_server_error

    # ==================== 响应头相关属性 ====================
    
    @property
    def content_type(self) -> str:
        """
        获取响应的 Content-Type
        
        Returns:
            str: Content-Type
        """
        return get_header_value(self.headers, 'content-type', '')

    @property
    def content_length(self) -> Optional[int]:
        """
        获取响应的 Content-Length
        
        Returns:
            Optional[int]: Content-Length
        """
        length = get_header_value(self.headers, 'content-length')
        return int(length) if length else None

    # ==================== JSON处理方法 ====================
    
    def json(self, default: Any = None) -> Any:
        """
        将响应文本解析为 JSON 对象。
        
        Args:
            default: 默认返回值，解析失败时返回
            
        Returns:
            Any: JSON对象
        """
        if self._json_cache is not None:
            return self._json_cache

        try:
            self._json_cache = json_module.loads(self.text)
            return self._json_cache
        except (json_module.JSONDecodeError, ValueError) as e:
            if default is not None:
                return default
            raise DecodeError(f"Failed to parse JSON from {self.url}: {e}")

    # ==================== URL处理方法 ====================
    
    def urljoin(self, url: str) -> str:
        """
        拼接 URL，自动处理相对路径。
        
        Args:
            url: 要拼接的URL
            
        Returns:
            str: 拼接后的URL
        """
        return _urljoin(self.url, url)

    # ==================== 选择器相关方法 ====================

    @property
    def _selector(self) -> Selector:
        """
        懒加载 Selector 实例
        
        Returns:
            Selector: Selector实例
        """
        if self._selector_instance is None:
            self._selector_instance = Selector(self.text)
        return self._selector_instance

    def xpath(self, query: str, adaptive: bool = False,
              identifier: str = '', percentage: float = 0.0) -> SelectorList:
        """
        使用 XPath 选择器查询文档。

        Args:
            query: XPath查询表达式
            adaptive: 启用自适应追踪（命中时保存/更新指纹，失效时自动匹配）
            identifier: 指纹标识符（默认使用 query 字符串）
            percentage: 最低匹配百分比阈值（0-100）

        Returns:
            SelectorList: 查询结果
        """
        # 先尝试原始选择器
        result = self._selector.xpath(query)

        # 自适应逻辑
        if result:
            # 选择器生效 → 如果 adaptive=True，保存/更新指纹
            if adaptive and self._is_adaptive_enabled():
                self._save_element_fingerprint(result[0], identifier or query)
            return result
        elif adaptive and self._is_adaptive_enabled():
            # 选择器失效 → 尝试自适应匹配
            element_data = self._retrieve_element_fingerprint(identifier or query)
            if element_data:
                matched = self._adaptive_relocate(element_data, percentage)
                if matched:
                    get_logger('Response').info(
                        f"Adaptive matched {len(matched)} element(s) "
                        f"for selector '{query}'"
                    )
                    return SelectorList([
                        Selector(root=el, type='html')
                        for el in matched
                    ])
        elif adaptive:
            get_logger('Response').warning(
                "Adaptive selector argument ignored because "
                "ADAPTIVE_SELECTOR_ENABLED is not set to True in settings"
            )

        return result

    def css(self, query: str, adaptive: bool = False,
            identifier: str = '', percentage: float = 0.0) -> SelectorList:
        """
        使用 CSS 选择器查询文档。

        Args:
            query: CSS选择器表达式
            adaptive: 启用自适应追踪（命中时保存/更新指纹，失效时自动匹配）
            identifier: 指纹标识符（默认使用 query 字符串）
            percentage: 最低匹配百分比阈值（0-100）

        Returns:
            SelectorList: 查询结果
        """
        # CSS 选择器转 XPath，复用 xpath 方法的自适应逻辑
        from parsel.csstranslator import HTMLTranslator
        try:
            xpath_query = HTMLTranslator().css_to_xpath(query)
        except Exception:
            xpath_query = query

        return self.xpath(
            xpath_query,
            adaptive=adaptive,
            identifier=identifier or query,
            percentage=percentage,
        )

    # ==================== 自适应选择器内部方法 ====================

    @classmethod
    def _is_adaptive_enabled(cls) -> bool:
        """检查自适应选择器是否可用

        延迟初始化，第一次调用时从 settings 读取配置并初始化存储/匹配器。
        只要用户调用 css/xpath 时传了 adaptive=True，此方法就会初始化并返回 True。
        """
        if cls._adaptive_enabled_global is not None:
            return cls._adaptive_enabled_global

        # 防止重复初始化
        if cls._adaptive_initialized:
            return False

        # 延迟初始化：尝试动态读取 settings，其次使用默认值
        try:
            # 尝试从当前 crawler 获取 settings（如果有）
            settings_backend = ADAPTIVE_STORAGE_BACKEND
            settings_sqlite_path = ADAPTIVE_SQLITE_PATH
            settings_redis_host = REDIS_HOST
            settings_redis_port = REDIS_PORT
            settings_redis_password = REDIS_PASSWORD
            settings_redis_db = REDIS_DB
            settings_threshold = ADAPTIVE_SIMILARITY_THRESHOLD
            
            cls._adaptive_storage = FingerprintStorage(
                backend=settings_backend,
                storage_file=settings_sqlite_path,
                redis_host=settings_redis_host,
                redis_port=settings_redis_port,
                redis_password=settings_redis_password,
                redis_db=settings_redis_db,
            )
            cls._adaptive_matcher = SimilarityMatcher(threshold=settings_threshold)
            cls._adaptive_enabled_global = True
            cls._adaptive_initialized = True
            
            # 注册清理函数（仅注册一次）
            if not cls._cleanup_registered:
                import atexit
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
                # 关闭存储连接
                if hasattr(cls._adaptive_storage, 'close'):
                    cls._adaptive_storage.close()
                cls._adaptive_storage = None
            
            cls._adaptive_matcher = None
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
        cls._adaptive_enabled_global = True
        cls._adaptive_storage = FingerprintStorage(
            backend=backend, storage_file=storage_file, **kwargs
        )
        cls._adaptive_matcher = SimilarityMatcher(threshold=threshold)

    def _save_element_fingerprint(self, selector_item, identifier: str) -> None:
        """保存元素的指纹到存储

        Args:
            selector_item: parsel Selector 对象
            identifier: 指纹标识符
        """
        if self.__class__._adaptive_storage is None:
            return

        try:
            # parsel Selector 的根元素
            root = selector_item.root if hasattr(selector_item, 'root') else selector_item
            if isinstance(root, HtmlElement):
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
        """自适应重新定位元素

        遍历页面元素，找到最匹配的

        Args:
            element_data: 保存的元素指纹字典
            percentage: 最低匹配百分比

        Returns:
            List[lxml.html.HtmlElement]: 匹配的元素列表
        """
        if self.__class__._adaptive_matcher is None:
            return []

        try:
            target_fp = ElementFingerprint.from_dict(element_data)
            # 获取页面的 lxml 根元素
            root = self._selector.root
            if not isinstance(root, HtmlElement):
                return []

            return self.__class__._adaptive_matcher.find_best_matches(
                target_fp, root, percentage=percentage
            )
        except Exception as e:
            get_logger('Response').debug(f"Adaptive relocate failed: {e}")
            return []

    # ==================== 通用选择器方法 ====================

    def _is_xpath(self, query: str) -> bool:
        """
        判断查询语句是否为 XPath
        """
        return query.startswith(('/', '//', './'))

    def _get_elements(self, xpath_or_css: str) -> SelectorList:
        """
        根据选择器获取元素列表
        """
        if self._is_xpath(xpath_or_css):
            return self.xpath(xpath_or_css)
        return self.css(xpath_or_css)

    def _extract_text(self, elements: SelectorList, first_only: bool = False) -> Union[Optional[str], List[str]]:
        """
        从元素中提取文本
        
        Args:
            elements: 元素列表
            first_only: 是否只返回第一个元素的文本
            
        Returns:
            如果 first_only=True 返回 str 或 None
            否则返回 List[str]
        """
        result = []
        for element in elements:
            if hasattr(element, 'xpath'):
                texts = element.xpath('.//text()').getall()
                cleaned = ' '.join(t.strip() for t in texts if t.strip())
                if cleaned:
                    result.append(cleaned)
            else:
                text = str(element).strip()
                if text:
                    result.append(text)
        
        if first_only:
            return result[0] if result else None
        return result

    def get(self, xpath_or_css: str, default: Optional[str] = None, strict: bool = False) -> Optional[str]:
        """
        获取第一个匹配元素的文本。
        
        等同于 response.css(query).get() 或 response.xpath(query).get()
        
        Args:
            xpath_or_css: XPath 或 CSS 选择器
            default: 未找到时的默认值
            strict: 严格模式，True 时抛出异常而非返回 default
            
        Returns:
            str: 第一个元素的文本，未找到返回 default
            
        示例:
            title = response.get('title')
            content = response.get('.content', '')
        """
        try:
            elements = self._get_elements(xpath_or_css)
            result = self._extract_text(elements, first_only=True)
            return result if result is not None else default
        except Exception as e:
            if strict:
                raise
            get_logger('Response').debug(f"Selector failed: {e}")
            return default

    def getall(self, xpath_or_css: str, strict: bool = False) -> List[str]:
        """
        获取所有匹配元素的文本列表。
        
        等同于 response.css(query).getall() 或 response.xpath(query).getall()
        
        Args:
            xpath_or_css: XPath 或 CSS 选择器
            strict: 严格模式，True 时抛出异常而非返回空列表
            
        Returns:
            List[str]: 所有匹配元素的文本列表
            
        示例:
            items = response.getall('.item')
            links = response.getall('a::text')
        """
        try:
            elements = self._get_elements(xpath_or_css)
            return self._extract_text(elements, first_only=False)
        except Exception as e:
            if strict:
                raise
            get_logger('Response').debug(f"Selector failed: {e}")
            return []

    def attr(self, xpath_or_css: str, name: str, default: Optional[str] = None) -> Optional[str]:
        """
        获取第一个匹配元素的指定属性值。
        
        Args:
            xpath_or_css: XPath 或 CSS 选择器
            name: 属性名称
            default: 未找到时的默认值
            
        Returns:
            Optional[str]: 属性值，未找到返回 default
            
        示例:
            href = response.attr('a', 'href')
            src = response.attr('img', 'src', '')
        """
        try:
            elements = self._get_elements(xpath_or_css)
            if not elements:
                return default
            return elements[0].attrib.get(name, default)
        except Exception:
            return default

    def attrs(self, xpath_or_css: str, name: str) -> List[str]:
        """
        获取所有匹配元素的指定属性值列表。
        
        Args:
            xpath_or_css: XPath 或 CSS 选择器
            name: 属性名称
            
        Returns:
            List[str]: 属性值列表
            
        示例:
            hrefs = response.attrs('a', 'href')
            srcs = response.attrs('img', 'src')
        """
        try:
            elements = self._get_elements(xpath_or_css)
            return [e.attrib.get(name) for e in elements if e.attrib.get(name) is not None]
        except Exception:
            return []

    def get_outer(self, xpath_or_css: str, default: Optional[str] = None) -> Optional[str]:
        """
        获取第一个匹配元素的完整 HTML（包含标签）。
        
        Args:
            xpath_or_css: XPath 或 CSS 选择器
            default: 未找到时的默认值
            
        Returns:
            str: 第一个元素的完整 HTML，未找到返回 default
            
        示例:
            content_html = response.get_outer('.content')
            # '<div class="content">...</div>'
        """
        try:
            elements = self._get_elements(xpath_or_css)
            return elements.get() or default
        except Exception:
            return default

    def getall_outer(self, xpath_or_css: str) -> List[str]:
        """
        获取所有匹配元素的完整 HTML 列表（包含标签）。
        
        Args:
            xpath_or_css: XPath 或 CSS 选择器
            
        Returns:
            List[str]: 所有元素的完整 HTML 列表
            
        示例:
            items_html = response.getall_outer('.item')
            # ['<div class="item">item1</div>', '<div class="item">item2</div>']
        """
        try:
            elements = self._get_elements(xpath_or_css)
            return elements.getall()
        except Exception:
            return []

    # ==================== 正则表达式相关方法 ====================
    
    def re_findone(self, pattern: Union[str, Pattern], flags: int = re.DOTALL, default: Optional[str] = None) -> Optional[str]:
        """
        在响应文本上执行正则表达式查找，返回第一个匹配。
        
        Args:
            pattern: 正则表达式模式
            flags: 正则表达式标志
            default: 未匹配时的默认值
            
        Returns:
            Optional[str]: 第一个匹配结果，未匹配返回 default
            
        示例:
            price = response.re_findone(r'price: (\\d+)', default='0')
        """
        pattern_str = pattern if isinstance(pattern, str) else pattern.pattern
        return regex_findone(pattern_str, self.text, flags) or default

    def re_search(self, pattern: Union[str, Pattern], flags: int = re.DOTALL) -> Optional[Match]:
        """
        在响应文本上执行正则表达式搜索。
        
        Args:
            pattern: 正则表达式模式
            flags: 正则表达式标志
            
        Returns:
            Optional[Match]: 匹配结果
        """
        pattern_str = pattern if isinstance(pattern, str) else pattern.pattern
        return regex_search(pattern_str, self.text, flags)

    def re_findall(self, pattern: Union[str, Pattern], flags: int = re.DOTALL) -> List[Any]:
        """
        在响应文本上执行正则表达式查找。
        
        Args:
            pattern: 正则表达式模式
            flags: 正则表达式标志
            
        Returns:
            List[Any]: 所有匹配结果
        """
        pattern_str = pattern if isinstance(pattern, str) else pattern.pattern
        return regex_findall(pattern_str, self.text, flags)

    def re_css(self, xpath_or_css: str, pattern: Union[str, Pattern], flags: int = re.DOTALL) -> List[str]:
        """
        从匹配选择器的元素中提取文本，再用正则提取。
        
        Args:
            xpath_or_css: XPath 或 CSS 选择器
            pattern: 正则表达式模式
            flags: 正则表达式标志
            
        Returns:
            List[str]: 所有正则匹配结果
            
        示例:
            # 从所有商品名称中提取价格数字
            prices = response.re_css('.price', r'\\d+\\.\\d+')
        """
        texts = self.getall(xpath_or_css)
        pattern_str = pattern if isinstance(pattern, str) else pattern.pattern
        result = []
        for text in texts:
            matches = regex_findall(pattern_str, text, flags)
            result.extend(matches)
        return result

    # ==================== Cookie处理方法 ====================
    
    def get_cookies(self) -> Dict[str, str]:
        """
        从响应头中解析并返回Cookies。
        
        Returns:
            Dict[str, str]: Cookies字典
        """
        cookie_header = self.headers.get("Set-Cookie", "")
        return parse_cookies(cookie_header)

    # ==================== 请求相关方法 ====================
    
    def follow(self, url: str, callback=None, **kwargs):
        """
        创建一个跟随链接的请求。
        
        Args:
            url: 要跟随的URL（可以是相对URL）
            callback: 回调函数
            **kwargs: 传递给Request的其他参数
            
        Returns:
            Request: 新的请求对象
        """
        # 延迟导入Request以避免循环导入
        from crawlo.network.request import Request
        
        # 使用urljoin处理相对URL
        absolute_url = self.urljoin(url)
        
        # 创建新的请求
        return Request(
            url=absolute_url,
            callback=callback or getattr(self.request, 'callback', None),
            **kwargs
        )

    @property
    def meta(self) -> Dict:
        """
        获取关联的 Request 对象的 meta 字典。
        
        Returns:
            Dict: meta字典
        """
        return self.request.meta if self.request else {}

    def __str__(self) -> str:
        return f"<{self.status} {self.url}>"