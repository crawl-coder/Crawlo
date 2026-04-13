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
from typing import Optional, Dict, Any, Callable

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
    from crawlo.utils.request.response_helper import (
        html_body_declared_encoding,
        http_content_type_encoding,
        read_bom,
        resolve_encoding,
    )


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
        
        # 3. HTML meta 标签检测
        encoding = cls._detect_from_html_meta(body)
        if encoding:
            return encoding
        
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
        从 HTML meta 标签中检测编码
        
        Args:
            body: 响应体字节内容
            
        Returns:
            Optional[str]: 检测到的编码或 None
        """
        # 只检查 HTML 内容
        if b'<html' not in body[:1024].lower():
            return None
        
        # 只检查前 4KB，避免大文件性能问题
        html_start = body[:4096]
        
        try:
            # 使用 ascii 解码，忽略不可解码字符
            html_text = html_start.decode('ascii', errors='ignore')
            
            # 匹配 <meta charset="xxx">
            charset_match = re.search(
                r'<meta[^>]+charset=["\']?([\w-]+)',
                html_text,
                re.IGNORECASE
            )
            if charset_match:
                return charset_match.group(1).lower()
            
            # 匹配 <meta http-equiv="Content-Type" content="...charset=xxx">
            content_match = re.search(
                r'<meta[^>]+content=["\'][^"\'>]*charset=([\w-]+)',
                html_text,
                re.IGNORECASE
            )
            if content_match:
                return content_match.group(1).lower()
        except Exception:
            pass
        
        return None
    
    @classmethod
    def _detect_from_content(cls, body: bytes) -> Optional[str]:
        """
        基于内容自动检测编码
        
        尝试常见编码，返回第一个成功解码的
        
        Args:
            body: 响应体字节内容
            
        Returns:
            Optional[str]: 检测到的编码或 None
        """
        # 常见中文编码优先
        for enc in cls.CHINESE_ENCODINGS:
            try:
                body.decode(enc)
                return enc
            except UnicodeError:
                continue
        
        # 其他常见编码
        for enc in cls.WESTERN_ENCODINGS:
            try:
                body.decode(enc)
                return enc
            except UnicodeError:
                continue
        
        return None
    
    @classmethod
    def _auto_detect_callback(cls, text: bytes) -> Optional[str]:
        """
        自动检测编码的回调函数（供 w3lib 使用）
        
        Args:
            text: 要检测的字节文本
            
        Returns:
            Optional[str]: 检测到的编码
        """
        for enc in (cls.DEFAULT_ENCODING, 'utf-8', 'cp1252'):
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
