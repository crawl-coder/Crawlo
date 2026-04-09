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

from crawlo.logging import get_logger
from .element_fingerprint import ElementFingerprint


class SimilarityMatcher:
    """多维相似度匹配器

    算法：加权平均 + SequenceMatcher
    各维度独立评分，最终根据权重进行加权平均计算。
    """

    # 默认权重配置（可以根据场景动态调整）
    DEFAULT_WEIGHTS = {
        'tag': 1.0,           # 标签名
        'text': 2.0,          # 文本内容（通常最稳定且唯一）
        'attributes': 1.5,     # 属性集合
        'important_attrs': 2.0, # 关键属性 (class, id, href, src)
        'path': 1.0,           # DOM 路径
        'parent': 1.0,         # 父节点信息
        'siblings': 0.5,       # 兄弟节点信息（通常变化较多，权重较低）
    }

    def __init__(self, threshold: float = 0.0, weights: Optional[Dict[str, float]] = None):
        """初始化匹配器

        Args:
            threshold: 最低相似度阈值（0-100百分比），低于此分数的匹配结果将被丢弃
            weights: 维度权重配置，如果为 None 则使用默认配置
        """
        self.threshold = threshold
        self.weights = weights or self.DEFAULT_WEIGHTS
        self.logger = get_logger(self.__class__.__name__)

    def calculate_similarity(self, original: ElementFingerprint, candidate: ElementFingerprint) -> float:
        """计算两个指纹的相似度百分比

        算法逻辑：
        - 每个维度独立计分
        - 使用权重计算加权得分
        - 最终 (加权总分 / 总权重) * 100 得到百分比

        Args:
            original: 原始指纹（保存的）
            candidate: 候选指纹（当前页面的元素）

        Returns:
            float: 相似度百分比 (0.0 ~ 100.0)
        """
        total_score: float = 0
        total_weight: float = 0

        # 1. 标签名精确匹配
        tag_weight = self.weights.get('tag', 1.0)
        total_score += (1 if original.tag == candidate.tag else 0) * tag_weight
        total_weight += tag_weight

        # 2. 文本内容相似度（SequenceMatcher 模糊匹配）
        if original.text:
            text_weight = self.weights.get('text', 2.0)
            total_score += SequenceMatcher(
                None, original.text, candidate.text or ""
            ).ratio() * text_weight
            total_weight += text_weight

        # 3. 属性字典相似度
        attr_weight = self.weights.get('attributes', 1.5)
        total_score += self._calculate_dict_diff(original.attributes, candidate.attributes) * attr_weight
        total_weight += attr_weight

        # 4. 重要属性单独比较 (class, id, href, src)
        important_attrs_weight = self.weights.get('important_attrs', 2.0)
        important_checks = 0
        important_score = 0
        for attrib in ('class', 'id', 'href', 'src'):
            if original.attributes.get(attrib):
                important_score += SequenceMatcher(
                    None,
                    original.attributes[attrib],
                    candidate.attributes.get(attrib) or "",
                ).ratio()
                important_checks += 1
        
        if important_checks > 0:
            total_score += (important_score / important_checks) * important_attrs_weight
            total_weight += important_attrs_weight

        # 5. DOM 路径相似度
        path_weight = self.weights.get('path', 1.0)
        total_score += SequenceMatcher(None, original.path, candidate.path).ratio() * path_weight
        total_weight += path_weight

        # 6. 父节点信息
        if original.parent_name:
            parent_weight = self.weights.get('parent', 1.0)
            p_score = 0
            p_checks = 0
            
            if candidate.parent_name:
                # 父标签名
                p_score += SequenceMatcher(
                    None, original.parent_name, candidate.parent_name or ""
                ).ratio()
                p_checks += 1

                # 父属性
                p_score += self._calculate_dict_diff(
                    original.parent_attribs, candidate.parent_attribs or {}
                )
                p_checks += 1

                # 父文本
                if original.parent_text:
                    p_score += SequenceMatcher(
                        None,
                        original.parent_text,
                        candidate.parent_text or "",
                    ).ratio()
                    p_checks += 1
            
            if p_checks > 0:
                total_score += (p_score / p_checks) * parent_weight
                total_weight += parent_weight

        # 7. 兄弟节点相似度
        if original.siblings:
            siblings_weight = self.weights.get('siblings', 0.5)
            total_score += SequenceMatcher(
                None, original.siblings, candidate.siblings or ()
            ).ratio() * siblings_weight
            total_weight += siblings_weight

        # 计算百分比
        return round((total_score / total_weight) * 100, 2) if total_weight > 0 else 0.0

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
