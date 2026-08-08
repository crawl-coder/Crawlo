#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
爬虫层异常定义
=============
Spider 注册、实例化、解析相关异常。
"""
from typing import List
import warnings

from crawlo.core.errors import CrawloException


# ============= 爬虫相关异常 =============
class SpiderException(CrawloException):
    """爬虫相关异常基类"""
    pass


class SpiderTypeError(SpiderException, TypeError):
    """爬虫类型错误。当爬虫类型不符合预期时抛出"""
    pass


class SpiderCreationError(SpiderException):
    """爬虫实例化失败异常。当无法创建爬虫实例时抛出"""
    pass


class AmbiguousSpiderError(SpiderException):
    """爬虫名称歧义错误。当多个爬虫类注册了相同 name 时抛出。

    Phase 1：SpiderMeta 不再在 import 阶段 raise，而是后注册覆盖先注册 + warning。
    当通过 get_spider_by_name 解析到冲突的 name 时，抛出此异常，
    错误信息列出所有候选类的完整模块路径，供用户决策。

    Attributes:
        name: 冲突的爬虫名称
        candidates: 候选类列表（完整模块路径）
    """

    def __init__(self, name: str, candidates: List[str]) -> None:
        self.name = name
        self.candidates = candidates
        candidate_list = "\n".join(f"  - {c}" for c in candidates)
        super().__init__(
            f"爬虫名称 '{name}' 存在歧义，以下类都注册了此名称：\n{candidate_list}\n"
            f"请使用 register_spider(name, cls, override=True) 显式指定要使用的爬虫类。"
        )


class SpiderNameConflictWarning(UserWarning):
    """爬虫名称冲突警告。

    当多个爬虫类注册了相同 name 时发出，提示后注册的类已覆盖先注册的类。
    用户可通过 warnings.filterwarnings('error', category=SpiderNameConflictWarning)
    将其升级为错误以在开发阶段严格检查。
    """
    pass


# ============= 导出 =============
__all__ = [
    'SpiderException',
    'SpiderTypeError',
    'SpiderCreationError',
    'AmbiguousSpiderError',
    'SpiderNameConflictWarning',
]
