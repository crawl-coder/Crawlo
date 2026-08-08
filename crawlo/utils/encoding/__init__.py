#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
编码检测工具子包
================
提供智能编码检测功能（BOM / Content-Type / HTML meta / 内容自动检测）。
"""
from .encoding_detector import (
    EncodingDetector,
    detect_encoding,
    decode_body,
)

__all__ = [
    'EncodingDetector',
    'detect_encoding',
    'decode_body',
]
