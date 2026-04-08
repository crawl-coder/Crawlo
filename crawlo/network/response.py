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
import ujson
from typing import Dict, Any, List, Optional, Union, Pattern, Match, TYPE_CHECKING
from urllib.parse import urljoin as _urljoin
from parsel import Selector, SelectorList
from lxml.html import HtmlElement

if TYPE_CHECKING:
    from crawlo.network.request import Request

# 尝试导入 w3lib 编码检测函数
try:
    from w3lib.encoding import (
        html_body_declared_encoding,
        html_to_unicode,
        http_content_type_encoding,
        read_bom,
        resolve_encoding,
    )
    W3LIB_AVAILABLE = True
except ImportError:
    W3LIB_AVAILABLE = False
    # 当 w3lib 不可用时，从 utils 导入替代函数
    from crawlo.utils import (
        html_body_declared_encoding,
        html_to_unicode,
        http_content_type_encoding,
        read_bom,
        resolve_encoding,
    )

from crawlo.exceptions import DecodeError
from crawlo.logging import get_logger
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
from crawlo.tools.adaptive_selector import (
    FingerprintStorage,
    SimilarityMatcher,
    ElementFingerprint,
)


def memoize_method_noargs(func):
    """
    装饰器，用于缓存无参数方法的结果
    
    Args:
        func: 要装饰的函数
        
    Returns:
        function: 装饰后的函数
    """
    cache_attr = f'_cache_{func.__name__}'
    
    def wrapper(self):
        if not hasattr(self, cache_attr):
            setattr(self, cache_attr, func(self))
        return getattr(self, cache_attr)
    
    return wrapper


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

    def __init__(
            self,
            url: str,
            *,
            headers: Optional[Dict[str, Any]] = None,
            body: bytes = b"",
            method: str = 'GET',
            request: Optional['Request'] = None,  # 使用字符串注解避免循环导入
            status_code: int = 200,
    ) -> None:
        """
        初始化响应对象
        
        Args:
            url: 响应URL
            headers: 响应头
            body: 响应体
            method: 请求方法
            request: 对应的请求对象
            status_code: 状态码
        """
        # 基本属性
        self.url: str = url
        self.headers: Dict[str, Any] = headers or {}
        self.body: bytes = body
        self.method: str = method.upper()
        self.request: Optional['Request'] = request
        self.status_code: int = status_code

        # 编码处理
        self.encoding: str = self._determine_encoding()

        # 缓存属性
        self._text_cache: Optional[str] = None
        self._json_cache: Optional[Any] = None
        self._selector_instance: Optional[Selector] = None

        # 状态标记
        self._is_success: bool = 200 <= status_code < 300
        self._is_redirect: bool = 300 <= status_code < 400
        self._is_client_error: bool = 400 <= status_code < 500
        self._is_server_error: bool = status_code >= 500

    # ==================== 编码检测相关方法 ====================
    
    def _determine_encoding(self) -> str:
        """
        智能检测响应编码
        
        编码检测优先级：
        1. Request 中指定的编码
        2. BOM 字节顺序标记
        3. HTTP Content-Type 头部
        4. HTML meta 标签声明
        5. 内容自动检测
        6. 默认编码 (utf-8)
        
        Returns:
            str: 检测到的编码
        """
        # 1. 优先使用声明的编码
        declared_encoding = self._declared_encoding()
        if declared_encoding:
            return declared_encoding
            
        # 2. 使用 w3lib 进行编码检测（如果可用）
        if W3LIB_AVAILABLE:
            return self._body_inferred_encoding()
        else:
            # 如果 w3lib 不可用，使用原有的检测逻辑
            # 从 Content-Type 头中检测
            content_type = self.headers.get("content-type", "") or self.headers.get("Content-Type", "")
            if content_type:
                charset_match = re.search(r"charset=([\w-]+)", content_type, re.I)
                if charset_match:
                    return charset_match.group(1).lower()

            # 从 HTML meta 标签中检测(仅对HTML内容)
            if b'<html' in self.body[:1024].lower():
                # 查找 <meta charset="xxx"> 或 <meta http-equiv="Content-Type" content="...charset=xxx">
                html_start = self.body[:4096]  # 只检查前4KB
                try:
                    html_text = html_start.decode('ascii', errors='ignore')
                    # <meta charset="utf-8">
                    charset_match = re.search(r'<meta[^>]+charset=["\']?([\w-]+)', html_text, re.I)
                    if charset_match:
                        return charset_match.group(1).lower()

                    # <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
                    content_match = re.search(r'<meta[^>]+content=["\'][^"\'>]*charset=([\w-]+)', html_text, re.I)
                    if content_match:
                        return content_match.group(1).lower()
                except Exception:
                    pass

        # 3. 默认使用 utf-8
        return 'utf-8'

    def _declared_encoding(self) -> Optional[str]:
        """
        获取声明的编码
        优先级：Request编码 > BOM > HTTP头部 > HTML meta标签
        
        Returns:
            Optional[str]: 声明的编码
        """
        # 1. Request 中指定的编码
        if self.request and getattr(self.request, 'encoding', None):
            return self.request.encoding
            
        # 2. BOM 字节顺序标记
        bom_encoding = self._bom_encoding()
        if bom_encoding:
            return bom_encoding
            
        # 3. HTTP Content-Type 头部
        headers_encoding = self._headers_encoding()
        if headers_encoding:
            return headers_encoding
            
        # 4. HTML meta 标签声明编码
        body_declared_encoding = self._body_declared_encoding()
        if body_declared_encoding:
            return body_declared_encoding
            
        return None

    @memoize_method_noargs
    def _bom_encoding(self) -> Optional[str]:
        """
        BOM 字节顺序标记编码检测
        
        Returns:
            Optional[str]: BOM编码
        """
        if not W3LIB_AVAILABLE:
            # 使用替代函数
            encoding, _ = read_bom(self.body)
            return encoding
        return read_bom(self.body)[0]

    @memoize_method_noargs
    def _headers_encoding(self) -> Optional[str]:
        """
        HTTP Content-Type 头部编码检测
        
        Returns:
            Optional[str]: 头部编码
        """
        if not W3LIB_AVAILABLE:
            # 使用替代函数
            content_type = self.headers.get("content-type", "") or self.headers.get("Content-Type", "")
            return http_content_type_encoding(content_type)
        content_type = self.headers.get("Content-Type", b"") or self.headers.get("content-type", b"")
        if isinstance(content_type, bytes):
            content_type = content_type.decode('latin-1')
        return http_content_type_encoding(content_type)

    @memoize_method_noargs
    def _body_declared_encoding(self) -> Optional[str]:
        """
        HTML meta 标签声明编码检测
        
        Returns:
            Optional[str]: HTML声明编码
        """
        if not W3LIB_AVAILABLE:
            # 使用替代函数
            return html_body_declared_encoding(self.body)
        return html_body_declared_encoding(self.body)

    @memoize_method_noargs
    def _body_inferred_encoding(self) -> str:
        """
        内容自动检测编码
        
        Returns:
            str: 推断的编码
        """
        if not W3LIB_AVAILABLE:
            # 使用替代函数
            content_type = self.headers.get("content-type", "") or self.headers.get("Content-Type", "")
            # 使用 html_to_unicode 函数进行编码检测
            encoding, _ = html_to_unicode(
                content_type,
                self.body,
                auto_detect_fun=self._auto_detect_fun,
                default_encoding=self._DEFAULT_ENCODING,
            )
            return encoding

        content_type = self.headers.get("Content-Type", b"") or self.headers.get("content-type", b"")
        if isinstance(content_type, bytes):
            content_type = content_type.decode('latin-1')
        
        # 使用 w3lib 的 html_to_unicode 函数进行编码检测
        benc, _ = html_to_unicode(
            content_type,
            self.body,
            auto_detect_fun=self._auto_detect_fun,
            default_encoding=self._DEFAULT_ENCODING,
        )
        return benc

    def _auto_detect_fun(self, text: bytes) -> Optional[str]:
        """
        自动检测编码的回调函数
        
        Args:
            text: 要检测的字节文本
            
        Returns:
            Optional[str]: 检测到的编码
        """
        if not W3LIB_AVAILABLE:
            # 使用替代函数
            for enc in (self._DEFAULT_ENCODING, "utf-8", "cp1252"):
                try:
                    text.decode(enc)
                except UnicodeError:
                    continue
                return resolve_encoding(enc)
            return None
        for enc in (self._DEFAULT_ENCODING, "utf-8", "cp1252"):
            try:
                text.decode(enc)
            except UnicodeError:
                continue
            return resolve_encoding(enc)
        return None

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

        # 如果可用，使用 w3lib 进行更准确的解码
        if W3LIB_AVAILABLE:
            try:
                content_type = self.headers.get("Content-Type", b"") or self.headers.get("content-type", b"")
                if isinstance(content_type, bytes):
                    content_type = content_type.decode('latin-1')
                
                # 使用 w3lib 的 html_to_unicode 函数
                _, self._text_cache = html_to_unicode(
                    content_type,
                    self.body,
                    default_encoding=self.encoding
                )
                return self._text_cache
            except Exception:
                # 如果 w3lib 解码失败，回退到原有方法
                pass
        else:
            # 使用替代函数
            try:
                content_type = self.headers.get("content-type", "") or self.headers.get("Content-Type", "")
                # 使用 html_to_unicode 函数
                _, self._text_cache = html_to_unicode(
                    content_type,
                    self.body,
                    default_encoding=self.encoding
                )
                return self._text_cache
            except Exception:
                # 如果解码失败，回退到原有方法
                pass

        # 尝试多种编码
        encodings_to_try = [self.encoding]
        if self.encoding != 'utf-8':
            encodings_to_try.append('utf-8')
        if 'gbk' not in encodings_to_try:
            encodings_to_try.append('gbk')
        if 'gb2312' not in encodings_to_try:
            encodings_to_try.append('gb2312')
        encodings_to_try.append('latin1')  # 最后的回退选项

        for encoding in encodings_to_try:
            if not encoding:
                continue
            try:
                self._text_cache = self.body.decode(encoding)
                return self._text_cache
            except (UnicodeDecodeError, LookupError):
                continue

        # 所有编码都失败，使用容错解码
        try:
            self._text_cache = self.body.decode('utf-8', errors='replace')
            return self._text_cache
        except Exception as e:
            raise DecodeError(f"Failed to decode response from {self.url}: {e}")

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
            self._json_cache = ujson.loads(self.text)
            return self._json_cache
        except (ujson.JSONDecodeError, ValueError) as e:
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

        # 延迟初始化：从 settings 读取配置
        try:
            cls._adaptive_storage = FingerprintStorage(
                backend=ADAPTIVE_STORAGE_BACKEND,
                storage_file=ADAPTIVE_SQLITE_PATH,
                redis_host=REDIS_HOST,
                redis_port=REDIS_PORT,
                redis_password=REDIS_PASSWORD,
                redis_db=REDIS_DB,
            )
            cls._adaptive_matcher = SimilarityMatcher(threshold=ADAPTIVE_SIMILARITY_THRESHOLD)
            cls._adaptive_enabled_global = True
            return True
        except Exception:
            cls._adaptive_enabled_global = False
            return False

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

    def get(self, xpath_or_css: str, default: Optional[str] = None) -> Optional[str]:
        """
        获取第一个匹配元素的文本。
        
        等同于 response.css(query).get() 或 response.xpath(query).get()
        
        Args:
            xpath_or_css: XPath 或 CSS 选择器
            default: 未找到时的默认值
            
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
        except Exception:
            return default

    def getall(self, xpath_or_css: str) -> List[str]:
        """
        获取所有匹配元素的文本列表。
        
        等同于 response.css(query).getall() 或 response.xpath(query).getall()
        
        Args:
            xpath_or_css: XPath 或 CSS 选择器
            
        Returns:
            List[str]: 所有匹配元素的文本列表
            
        示例:
            items = response.getall('.item')
            links = response.getall('a::text')
        """
        try:
            elements = self._get_elements(xpath_or_css)
            return self._extract_text(elements, first_only=False)
        except Exception:
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
        return f"<{self.status_code} {self.url}>"