#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
工具函数集合
"""
from decimal import Decimal, ROUND_HALF_UP


def round_if_numeric(value, decimal_places=4):
    """
    如果 value 是数值（int/float/Decimal），则保留指定小数位；
    否则原样返回（用于字符串、日期等）。
    """
    if value is None:
        return None

    # 排除布尔值
    if isinstance(value, bool):
        return value

    if isinstance(value, (int, float, Decimal)):
        try:
            # 转为 Decimal 并四舍五入，然后转为 float
            d = Decimal(str(value))
            quantize_exp = Decimal('0.1') ** decimal_places
            rounded = d.quantize(quantize_exp, rounding=ROUND_HALF_UP)
            return float(rounded)  # 转换为 float
        except Exception:
            return float(value) if isinstance(value, (int, float, Decimal)) else value
    else:
        return value
