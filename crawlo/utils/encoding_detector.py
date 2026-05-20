#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
编码检测工具模块
==============

提供智能编码检测功能，支持：
- BOM 字节顺序标记检测
- HTTP Content-Type 头部编码检测
- HTML meta 标签编码检测
- 内容自动检测

设计原则：
1. 纯函数设计，无状态，便于测试
2. 支持 w3lib 和内置 fallback 两种实现
3. 优先级明确，可配置
"""

import re
from typing import Optional, Dict, Any

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
    # Define fallback function references
    # Actual implementations are defined below
    html_body_declared_encoding = None
    html_to_unicode = None
    http_content_type_encoding = None
    read_bom = None
    resolve_encoding = None


# ============================================================================
# Fallback implementations when w3lib is not available
# ============================================================================

def _read_bom(data: bytes) -> tuple:
    """Read the byte order mark from the data, if present."""
    if data.startswith(b'\xef\xbb\xbf'):
        return ('utf-8', 3)
    elif data.startswith(b'\xff\xfe\x00\x00'):
        return ('utf-32-le', 4)
    elif data.startswith(b'\x00\x00\xfe\xff'):
        return ('utf-32-be', 4)
    elif data.startswith(b'\xff\xfe'):
        return ('utf-16-le', 2)
    elif data.startswith(b'\xfe\xff'):
        return ('utf-16-be', 2)
    return (None, 0)


def _http_content_type_encoding(content_type: str) -> Optional[str]:
    """Extract encoding from HTTP Content-Type header."""
    if not content_type:
        return None
    # Match charset in Content-Type: text/html; charset=utf-8
    match = re.search(r'charset=([\w-]+)', content_type, re.IGNORECASE)
    if match:
        return match.group(1).lower()
    return None


def _html_body_declared_encoding(body: bytes) -> Optional[str]:
    """Extract encoding from HTML meta tags or XML declaration.

    Similar to w3lib.html_body_declared_encoding but as fallback.
    """
    if not body:
        return None

    # Check first 4KB for performance
    chunk = body[:4096]

    # Try ASCII first (fast path)
    try:
        text = chunk.decode('ascii', errors='ignore')
    except Exception:
        return None

    # XML declaration: <?xml version="1.0" encoding="UTF-8"?>
    xml_match = re.search(
        r'<\?xml[^>]+encoding=["\']([\w-]+)["\']',
        text,
        re.IGNORECASE
    )
    if xml_match:
        return xml_match.group(1).lower()

    # HTML5: <meta charset="utf-8">
    meta_charset = re.search(
        r'<meta\s+charset=["\']?([\w-]+)',
        text,
        re.IGNORECASE
    )
    if meta_charset:
        return meta_charset.group(1).lower()

    # HTML4: <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
    meta_http = re.search(
        r'<meta[^>]+http-equiv=["\']?content-type["\']?[^>]*>',
        text,
        re.IGNORECASE
    )
    if meta_http:
        content_match = re.search(
            r'charset=([\w-]+)',
            meta_http.group(0),
            re.IGNORECASE
        )
        if content_match:
            return content_match.group(1).lower()

    return None


def _resolve_encoding(encoding_alias: str) -> str:
    """Resolve encoding alias to canonical name.

    Reference: https://docs.python.org/3/library/codecs.html#standard-encodings
    """
    if not encoding_alias:
        return 'utf-8'

    encoding_map = {
        # Unicode
        'utf8': 'utf-8',
        'utf-8': 'utf-8',
        'utf16': 'utf-16',
        'utf-16': 'utf-16',
        'utf32': 'utf-32',
        'utf-32': 'utf-32',
        # ASCII
        'ascii': 'ascii',
        'us-ascii': 'ascii',
        # Latin-1
        'latin1': 'latin-1',
        'latin-1': 'latin-1',
        'iso-8859-1': 'latin-1',
        'iso8859-1': 'latin-1',
        'cp819': 'latin-1',
        # Windows
        'cp1252': 'cp1252',
        'windows-1252': 'cp1252',
        'cp1251': 'cp1251',
        'windows-1251': 'cp1251',
        # Chinese
        'gbk': 'gbk',
        'gb2312': 'gb2312',
        'gb18030': 'gb18030',
        'big5': 'big5',
        'big5-tw': 'big5',
        'big5-hkscs': 'big5',
        # Japanese
        'shift_jis': 'shift_jis',
        'shift-jis': 'shift_jis',
        'sjis': 'shift_jis',
        'euc-jp': 'euc_jp',
        'eucjp': 'euc_jp',
        'iso-2022-jp': 'iso2022_jp',
        # Korean
        'euc-kr': 'euc_kr',
        'euckr': 'euc_kr',
        # Other
        'koi8-r': 'koi8_r',
        'koi8r': 'koi8_r',
    }

    normalized = encoding_alias.lower().replace('_', '-')
    return encoding_map.get(normalized, encoding_alias)


# Assign fallback implementations if w3lib is not available
if not W3LIB_AVAILABLE:
    read_bom = _read_bom
    http_content_type_encoding = _http_content_type_encoding
    html_body_declared_encoding = _html_body_declared_encoding
    resolve_encoding = _resolve_encoding


class EncodingDetector:
    """
    编码检测器

    提供统一的编码检测接口，支持多种检测策略。
    """

    # 默认编码
    DEFAULT_ENCODING = "utf-8"

    # 常见中文编码（按优先级排序）
    CHINESE_ENCODINGS = ('utf-8', 'gbk', 'gb2312', 'gb18030', 'big5')

    # 东亚编码（中/日/韩，chardet 不可用时的兜底顺序）
    # 中文编码在先（更常见），再日韩编码
    # gb18030 放最后（范围太广需 CJK 验证）
    EAST_ASIAN_ENCODINGS = (
        'gbk', 'gb2312', 'big5',            # 中文
        'euc_kr', 'shift_jis', 'euc_jp',    # 韩/日/日
        'gb18030',                           # 中文超集（最后，需验证）
    )

    @classmethod
    def _has_cjk_chars(cls, text: str, sample_size: int = 500) -> bool:
        """检查文本是否包含中日韩字符"""
        for ch in text[:sample_size]:
            cp = ord(ch)
            if 0x4e00 <= cp <= 0x9fff:   # CJK Unified
                return True
            if 0x3040 <= cp <= 0x30ff:   # Hiragana + Katakana
                return True
            if 0xac00 <= cp <= 0xd7af:   # Hangul
                return True
        return False

    # 西欧及西里尔编码
    WESTERN_ENCODINGS = ('latin-1', 'cp1252', 'cp1251')

    @classmethod
    def detect(
            cls,
            body: bytes,
            headers: Optional[Dict[str, Any]] = None,
            declared_encoding: Optional[str] = None,
            use_w3lib: bool = True,
    ) -> str:
        """
        智能检测编码

        检测优先级：
        1. 显式声明的编码（最高优先级）
        2. BOM 字节顺序标记
        3. HTTP Content-Type 头部
        4. HTML meta 标签声明
        5. 内容自动检测
        6. 默认编码 (utf-8)

        Args:
            body: 响应体字节内容
            headers: HTTP 响应头
            declared_encoding: 显式声明的编码（如 Request.encoding）
            use_w3lib: 是否优先使用 w3lib 进行检测

        Returns:
            str: 检测到的编码
        """
        # 1. 优先使用显式声明的编码
        if declared_encoding:
            return declared_encoding

        # 2. 使用 w3lib 进行完整检测（如果可用且启用）
        if use_w3lib and W3LIB_AVAILABLE:
            return cls._detect_with_w3lib(body, headers)

        # 3. 使用内置检测逻辑
        return cls._detect_fallback(body, headers)

    @classmethod
    def _detect_with_w3lib(
            cls,
            body: bytes,
            headers: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        使用 w3lib 进行编码检测

        w3lib 的 html_to_unicode 包含完整的检测逻辑：
        - BOM 检测
        - HTTP Content-Type 检测
        - HTML meta 标签检测
        - 内容自动检测

        Args:
            body: 响应体字节内容
            headers: HTTP 响应头

        Returns:
            str: 检测到的编码
        """
        headers = headers or {}
        content_type = headers.get('Content-Type', '') or headers.get('content-type', '')

        # 统一处理 bytes 类型的 content_type
        if isinstance(content_type, bytes):
            content_type = content_type.decode('latin-1')

        encoding, _ = html_to_unicode(
            content_type,
            body,
            auto_detect_fun=cls._auto_detect_callback,
            default_encoding=cls.DEFAULT_ENCODING,
        )
        # w3lib 可能返回 gb18030 但内容实际是韩文/日文 → 回退到内置检测
        if encoding in ('gb18030', 'gbk', 'gb2312') and len(body) > 64:
            try:
                decoded = body.decode(encoding, errors='replace')
                if not cls._has_cjk_chars(decoded):
                    return cls._detect_fallback(body, headers)
            except (UnicodeError, LookupError):
                pass
        return encoding

    @classmethod
    def _detect_fallback(
            cls,
            body: bytes,
            headers: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        内置编码检测逻辑（w3lib 不可用时使用）

        检测优先级：
        1. BOM 字节顺序标记
        2. HTTP Content-Type 头部
        3. HTML/XML body 中声明的编码
        4. 内容自动检测
        5. 默认编码

        Args:
            body: 响应体字节内容
            headers: HTTP 响应头

        Returns:
            str: 检测到的编码
        """
        headers = headers or {}

        # 1. BOM 检测
        encoding = cls._detect_bom(body)
        if encoding:
            return encoding

        # 2. HTTP Content-Type 头部检测
        encoding = cls._detect_from_headers(headers)
        if encoding:
            return encoding

        # 3. HTML/XML body 中声明的编码（meta 标签或 XML 声明）
        encoding = html_body_declared_encoding(body)
        if encoding:
            return resolve_encoding(encoding)

        # 4. 内容自动检测
        encoding = cls._detect_from_content(body)
        if encoding:
            return encoding

        # 5. 默认编码
        return cls.DEFAULT_ENCODING

    @classmethod
    def _detect_bom(cls, body: bytes) -> Optional[str]:
        """
        BOM 字节顺序标记编码检测

        Args:
            body: 响应体字节内容

        Returns:
            Optional[str]: BOM 编码或 None
        """
        encoding, _ = read_bom(body)
        return encoding

    @classmethod
    def _detect_from_headers(cls, headers: Dict[str, Any]) -> Optional[str]:
        """
        从 HTTP Content-Type 头部检测编码

        Args:
            headers: HTTP 响应头

        Returns:
            Optional[str]: 检测到的编码或 None
        """
        content_type = headers.get('content-type', '') or headers.get('Content-Type', '')
        if not content_type:
            return None

        # 如果是 bytes，先解码
        if isinstance(content_type, bytes):
            content_type = content_type.decode('latin-1')

        return http_content_type_encoding(content_type)

    @classmethod
    def _detect_from_html_meta(cls, body: bytes) -> Optional[str]:
        """
        从 HTML meta 标签或 XML 声明中检测编码

        这是 html_body_declared_encoding 的包装方法，
        用于保持向后兼容性。

        Args:
            body: 响应体字节内容

        Returns:
            Optional[str]: 检测到的编码或 None
        """
        encoding = html_body_declared_encoding(body)
        if encoding:
            return resolve_encoding(encoding)
        return None

    @classmethod
    def _detect_from_content(cls, body: bytes) -> Optional[str]:
        """基于内容自动检测编码（多语言通用）

        策略：UTF-8 → chardet 统计检测 → 东亚编码覆盖兜底 → 西欧编码

        设计说明：
        - UTF-8 优先（全球占比最高，2026 年 >95%）
        - chardet 能正确区分中/日/韩编码（区别于逐字节解码的假阳性问题）
        - chardet 存在将 GBK 中文误判为 latin-1 的已知缺陷 → CJK 安全阀兜底
        - 东亚编码兜底确保即使 chardet 不可用，中/日/韩仍能正确检测
        """
        # 1. UTF-8 优先（全球最常用）
        try:
            body.decode('utf-8')
            return 'utf-8'
        except UnicodeError:
            pass

        # 2. chardet 统计检测（能正确区分中/日/韩/俄/阿拉伯等语言）
        try:
            import chardet
            result = chardet.detect(body)
            enc = result.get('encoding')
            confidence = result.get('confidence', 0)
            if enc and confidence > 0.6:
                resolved = resolve_encoding(enc)
                # 安全阀：chardet 将 GBK 中文误判为 latin-1 时自动纠正
                # 取 body 中间段采样（前部可能全是 ASCII 标签），尝试 GB18030 交叉验证
                mid = body[len(body)//2:len(body)//2 + 4096] if len(body) > 4096 else body
                try:
                    decoded = mid.decode('gb18030')
                    if cls._has_cjk_chars(decoded):
                        return 'gb18030'
                except UnicodeError:
                    pass
                return resolved
        except ImportError:
            pass

        # 3. 东亚编码覆盖（chardet 不可用或置信度不足时的兜底）
        for enc in cls.EAST_ASIAN_ENCODINGS:
            try:
                decoded = body.decode(enc)
                if enc == 'gb18030' and not cls._has_cjk_chars(decoded):
                    continue
                return enc
            except UnicodeError:
                continue

        # 4. 西欧编码（最后手段）
        for enc in cls.WESTERN_ENCODINGS:
            try:
                body.decode(enc)
                return enc
            except UnicodeError:
                continue

        return None

    @classmethod
    def _auto_detect_callback(cls, text: bytes) -> Optional[str]:
        """自动检测编码的回调函数（供 w3lib 使用）

        策略与 _detect_from_content 一致：
        ASCII/UTF-8 → chardet 统计检测 → 东亚编码兜底 → 西欧编码
        """
        # 1. ASCII / UTF-8
        for enc in ('ascii', 'utf-8'):
            try:
                text.decode(enc)
                return resolve_encoding(enc)
            except UnicodeError:
                continue

        # 2. chardet 统计检测
        try:
            import chardet
            result = chardet.detect(text)
            enc = result.get('encoding')
            confidence = result.get('confidence', 0)
            if enc and confidence > 0.6:
                resolved = resolve_encoding(enc)
                # 安全阀：单字节编码结果再做 GB18030 交叉验证
                mid = text[len(text)//2:len(text)//2 + 4096] if len(text) > 4096 else text
                try:
                    decoded = mid.decode('gb18030')
                    if cls._has_cjk_chars(decoded):
                        return 'gb18030'
                except (UnicodeError, LookupError):
                    pass
                return resolved
        except ImportError:
            pass

        # 3. 东亚编码兜底
        for enc in cls.EAST_ASIAN_ENCODINGS:
            try:
                decoded = text.decode(enc)
                if enc == 'gb18030' and not cls._has_cjk_chars(decoded):
                    continue
                return resolve_encoding(enc)
            except UnicodeError:
                continue

        # 4. 西欧编码（最后手段）
        for enc in ('latin-1', 'cp1252', 'cp1251'):
            try:
                text.decode(enc)
                return resolve_encoding(enc)
            except UnicodeError:
                continue

        return None

    @classmethod
    def decode_body(
            cls,
            body: bytes,
            encoding: Optional[str] = None,
            headers: Optional[Dict[str, Any]] = None,
            declared_encoding: Optional[str] = None,
    ) -> str:
        """
        解码响应体为字符串

        如果未提供编码，会自动检测

        Args:
            body: 响应体字节内容
            encoding: 指定编码（可选）
            headers: HTTP 响应头
            declared_encoding: 显式声明的编码

        Returns:
            str: 解码后的字符串
        """
        if not encoding:
            encoding = cls.detect(body, headers, declared_encoding)

        try:
            return body.decode(encoding, errors='replace')
        except (UnicodeError, LookupError):
            # 如果指定编码失败，使用默认编码
            return body.decode(cls.DEFAULT_ENCODING, errors='replace')


# 便捷函数接口
def detect_encoding(
        body: bytes,
        headers: Optional[Dict[str, Any]] = None,
        declared_encoding: Optional[str] = None,
        use_w3lib: bool = True,
) -> str:
    """
    便捷函数：智能检测编码

    Args:
        body: 响应体字节内容
        headers: HTTP 响应头
        declared_encoding: 显式声明的编码
        use_w3lib: 是否优先使用 w3lib

    Returns:
        str: 检测到的编码
    """
    return EncodingDetector.detect(body, headers, declared_encoding, use_w3lib)


def decode_body(
        body: bytes,
        encoding: Optional[str] = None,
        headers: Optional[Dict[str, Any]] = None,
        declared_encoding: Optional[str] = None,
) -> str:
    """
    便捷函数：解码响应体

    Args:
        body: 响应体字节内容
        encoding: 指定编码（可选）
        headers: HTTP 响应头
        declared_encoding: 显式声明的编码

    Returns:
        str: 解码后的字符串
    """
    return EncodingDetector.decode_body(body, encoding, headers, declared_encoding)