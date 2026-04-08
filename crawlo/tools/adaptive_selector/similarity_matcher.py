#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
# @Time    : 2026-04-07
# @Author  : crawl-coder
# @Desc    : 相似度匹配算法

使用多维等权平均相似度算法，在候选元素中找到与原始指纹最接近的匹配。

核心算法：
- 遍历页面所有元素，逐一计算与目标指纹的相似度
- 每个维度独立计算分数，最终取平均值（等权平均策略）
- 使用 SequenceMatcher 进行模糊文本比较
- 返回得分最高的元素

优化特性：
- 阈值过滤：避免低分误匹配
- 同标签预过滤：提升匹配性能
- 详细匹配日志：便于调试和监控
"""
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Tuple

from lxml.html import HtmlElement
from lxml.etree import _ElementUnicodeResult

from crawlo.logging import get_logger
from .element_fingerprint import ElementFingerprint


class SimilarityMatcher:
    """多维相似度匹配器

    算法：等权平均 + SequenceMatcher
    各维度独立评分，最终 score / checks 得到百分比
    """

    def __init__(self, threshold: float = 0.0):
        """初始化匹配器

        Args:
            threshold: 最低相似度阈值（0-100百分比），低于此分数的匹配结果将被丢弃
        """
        self.threshold = threshold
        self.logger = get_logger(self.__class__.__name__)

    def calculate_similarity(self, original: ElementFingerprint, candidate: ElementFingerprint) -> float:
        """计算两个指纹的相似度百分比

        算法逻辑：
        - 每个维度独立计分
        - 使用 SequenceMatcher 进行模糊文本比较
        - 最终 score / checks * 100 得到百分比

        Args:
            original: 原始指纹（保存的）
            candidate: 候选指纹（当前页面的元素）

        Returns:
            float: 相似度百分比 (0.0 ~ 100.0)
        """
        score: float = 0
        checks: int = 0

        # 1. 标签名精确匹配（权重等同于其他维度，因为最终取平均值）
        score += 1 if original.tag == candidate.tag else 0
        checks += 1

        # 2. 文本内容相似度（SequenceMatcher 模糊匹配）
        if original.text:
            score += SequenceMatcher(
                None, original.text, candidate.text or ""
            ).ratio()
            checks += 1

        # 3. 属性字典相似度（keys 和 values 分别比较）
        score += self._calculate_dict_diff(original.attributes, candidate.attributes)
        checks += 1

        # 4. 重要属性单独比较（class, id, href, src）
        #    这一步对全结构变更的场景非常有帮助
        for attrib in ('class', 'id', 'href', 'src'):
            if original.attributes.get(attrib):
                score += SequenceMatcher(
                    None,
                    original.attributes[attrib],
                    candidate.attributes.get(attrib) or "",
                ).ratio()
                checks += 1

        # 5. DOM 路径相似度
        score += SequenceMatcher(None, original.path, candidate.path).ratio()
        checks += 1

        # 6. 父节点信息
        if original.parent_name:
            if candidate.parent_name:
                # 父标签名
                score += SequenceMatcher(
                    None, original.parent_name, candidate.parent_name or ""
                ).ratio()
                checks += 1

                # 父属性
                score += self._calculate_dict_diff(
                    original.parent_attribs, candidate.parent_attribs or {}
                )
                checks += 1

                # 父文本
                if original.parent_text:
                    score += SequenceMatcher(
                        None,
                        original.parent_text,
                        candidate.parent_text or "",
                    ).ratio()
                    checks += 1

        # 7. 兄弟节点相似度
        if original.siblings:
            score += SequenceMatcher(
                None, original.siblings, candidate.siblings or ()
            ).ratio()
            checks += 1

        # 计算百分比
        return round((score / checks) * 100, 2) if checks > 0 else 0.0

    def find_best_matches(
        self,
        target_fp: ElementFingerprint,
        root_element: HtmlElement,
        percentage: float = 0.0,
    ) -> List[HtmlElement]:
        """在页面中查找与目标指纹最匹配的元素

        遍历所有元素并计算相似度，返回得分最高的一组。

        Args:
            target_fp: 目标元素指纹
            root_element: 页面根元素
            percentage: 最低匹配百分比阈值

        Returns:
            List[HtmlElement]: 匹配的元素列表（得分最高的一组）
        """
        score_table: Dict[float, List[HtmlElement]] = {}

        # 遍历所有元素
        all_elements = root_element.xpath('.//*')
        for node in all_elements:
            if not isinstance(node, HtmlElement):
                continue
            # 只对同标签的元素计算相似度（性能优化）
            if node.tag != target_fp.tag:
                continue

            candidate_fp = ElementFingerprint.from_element(node)
            score = self.calculate_similarity(target_fp, candidate_fp)
            score_table.setdefault(score, []).append(node)

        if not score_table:
            return []

        # 找到最高分
        highest_score = max(score_table.keys())

        # 检查阈值
        effective_threshold = max(self.threshold, percentage)
        if highest_score < effective_threshold:
            self.logger.debug(
                f"Best match score {highest_score}% below threshold {effective_threshold}%"
            )
            return []

        self.logger.debug(
            f"Best match score: {highest_score}% "
            f"({len(score_table[highest_score])} element(s))"
        )

        # 调试日志：输出 Top 5 匹配分数
        if self.logger.isEnabledFor(10):  # DEBUG level
            top_scores = sorted(score_table.keys(), reverse=True)[:5]
            for s in top_scores:
                self.logger.debug(f"  {s}% -> {len(score_table[s])} element(s)")

        return score_table[highest_score]

    @staticmethod
    def _calculate_dict_diff(dict1: Dict, dict2: Dict) -> float:
        """计算两个字典的相似度

        keys 和 values 分别用 SequenceMatcher 比较，各占 50% 权重

        Args:
            dict1: 第一个字典
            dict2: 第二个字典

        Returns:
            float: 相似度 (0.0 ~ 1.0)
        """
        score = SequenceMatcher(
            None, tuple(dict1.keys()), tuple(dict2.keys())
        ).ratio() * 0.5
        score += SequenceMatcher(
            None, tuple(dict1.values()), tuple(dict2.values())
        ).ratio() * 0.5
        return score
