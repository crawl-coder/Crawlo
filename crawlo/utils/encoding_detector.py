#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
编码检测工具模块
==============

提供智能编码检测功能，支持：
- BOM 字节顺序标记检测
- HTTP Content-Type 头部编码检测
- HTML meta 标签编码检测
- 内容自动检测（chardet 优先，内置 fallback）

设计原则：
1. 纯函数设计，无状态，便于测试
2. 支持 w3lib 和内置 fallback 两种实现
3. 优先级明确，可配置
"""

import re
from typing import Optional, Dict, Any

try:
    import chardet
    CHARDET_AVAILABLE = True
except ImportError:
    CHARDET_AVAILABLE = False

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
        # UTF 别名: normalize to hyphenated form
        'utf8': 'utf-8',
        'utf16': 'utf-16',
        'utf32': 'utf-32',
        # ASCII
        'us-ascii': 'ascii',
        # Latin-1 别名
        'latin1': 'latin-1',
        'iso-8859-1': 'latin-1',
        'iso8859-1': 'latin-1',
        'cp819': 'latin-1',
        # Windows 代码页
        'windows-1252': 'cp1252',
        'windows-1251': 'cp1251',
        # 中文编码别名
        'big5-tw': 'big5',
        'big5-hkscs': 'big5',
        # 日文编码别名
        'shift-jis': 'shift_jis',
        'sjis': 'shift_jis',
        'euc-jp': 'euc_jp',
        'eucjp': 'euc_jp',
        'iso-2022-jp': 'iso2022_jp',
        # 韩文编码别名
        'euckr': 'euc_kr',
        # 西里尔编码别名
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
    
    # 西欧编码
    WESTERN_ENCODINGS = ('latin-1', 'cp1252')
    
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
        return encoding
    
    @classmethod
    def _detect_fallback(
        cls,
        body: bytes,
        headers: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        内置编码检测逻辑（w3lib 不可用时使用）
        
        检测优先级（参考 Scrapy）：
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
    
    # ---------- 内容自动检测 ----------
        """
        基于内容自动检测编码（chardet 优先，内置常见编码试探作为 fallback）

        Args:
            body: 响应体字节内容

        Returns:
            Optional[str]: 检测到的编码或 None
        """
        # 1. chardet 统计检测（精度高）
        if CHARDET_AVAILABLE and body:
            result = chardet.detect(body[:4096])
            enc = result.get('encoding')
            confidence = result.get('confidence', 0)
            if enc and confidence > 0.5:
                return resolve_encoding(enc)

        # 2. 无 chardet 或置信度不足，用常见编码试探
        return cls._try_common_encodings(body)

    @classmethod
    def _try_common_encodings(cls, body: bytes) -> Optional[str]:
        """常见编码试探（chardet 不可用或置信度不足时使用，中文优先）"""
        encodings = [
            'ascii', 'utf-8',
            'gbk', 'gb2312', 'gb18030', 'big5',          # 中文
            'cp1252', 'cp1251', 'latin-1',                # 西欧/西里尔
        ]
        for enc in encodings:
            try:
                body.decode(enc)
                return resolve_encoding(enc)
            except UnicodeError:
                continue
        return None

    @classmethod
    def _auto_detect_callback(cls, text: bytes) -> Optional[str]:
        """
        自动检测编码的回调函数（供 w3lib 使用）
        委托给 _try_common_encodings。
        """
        return cls._try_common_encodings(text)
    
    @classmethod
    def _chardet_cross_check(cls, body: bytes, declared_encoding: str) -> Optional[str]:
        """用 chardet 对全 body 做交叉验证，检测声明编码与内容是否一致"""
        if not CHARDET_AVAILABLE or not body or len(body) < 64:
            return None
        # 取 body 多段采样（开头 + 中间 + 结尾），避免前部全是 ASCII 漏检
        samples = [body[:4096]]
        if len(body) > 8192:
            samples.append(body[len(body)//2:len(body)//2+4096])
        if len(body) > 12288:
            samples.append(body[-4096:])
        for s in samples:
            result = chardet.detect(s)
            enc = result.get('encoding')
            conf = result.get('confidence', 0)
            if enc and conf > 0.8 and resolve_encoding(enc).lower() != declared_encoding.lower():
                return resolve_encoding(enc)
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

        先用 strict 模式验证声明编码（取前 4KB 采样），
        再用 chardet 交叉验证（采样开头/中间/结尾多点），
        如果声明编码与内容不一致（如页面声明 utf-8 但实际是 gbk），
        自动回退到内容检测。

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

        # 步骤 1: 取前 4KB 采样验证声明编码是否可解码
        sample = body[:4096]
        strict_ok = True
        try:
            sample.decode(encoding, errors='strict')
        except UnicodeDecodeError:
            strict_ok = False
        except (LookupError, UnicodeError):
            strict_ok = False

        if not strict_ok:
            # 声明编码明显不可用，直接回退内容检测
            sample_enc = cls._detect_from_content(sample)
            if sample_enc:
                encoding = sample_enc
        else:
            # 步骤 2: 采样验证通过，再用 chardet 交叉验证
            # （前 4KB 可能是纯 ASCII 标签，GBK 中文在后面）
            chardet_enc = cls._chardet_cross_check(body, encoding)
            if chardet_enc:
                encoding = chardet_enc

        return body.decode(encoding, errors='replace')


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
