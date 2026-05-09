#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
# @Time    : 2026-04-07
# @Author  : crawl-coder
# @Desc    : Similarity Matching Algorithms

Uses multi-dimensional weighted average similarity algorithm to find
the closest match to the original fingerprint among candidate elements.

Core Algorithm:
- Iterate through all elements on the page, calculate similarity with target fingerprint
- Each dimension scores independently, final score is weighted average
- Uses SequenceMatcher for fuzzy text comparison
- Returns element with highest score

Optimizations:
- Threshold filtering: Avoid low-score false matches
- Same-tag pre-filtering: Improve matching performance
- Detailed match logging: Facilitate debugging and monitoring
"""
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Tuple

from lxml.html import HtmlElement

from crawlo.logging import get_logger
from .element_fingerprint import ElementFingerprint


class SimilarityMatcher:
    """Multi-dimensional similarity matcher

    Algorithm: Weighted average + SequenceMatcher
    Each dimension scores independently, final score is weighted average.
    """

    # Default weight configuration (can be dynamically adjusted per scenario)
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
        """Initialize matcher

        Args:
            threshold: Minimum similarity threshold (0-100 percentage), matches below this score will be discarded
            weights: Dimension weight configuration, uses default if None
        """
        self.threshold = threshold
        self.weights = weights or self.DEFAULT_WEIGHTS
        self.logger = get_logger(self.__class__.__name__)

    def calculate_similarity(self, original: ElementFingerprint, candidate: ElementFingerprint) -> float:
        """Calculate similarity percentage between two fingerprints

        Algorithm logic:
        - Each dimension scores independently
        - Weighted score calculation
        - Final (weighted total / total weight) * 100 for percentage

        Args:
            original: Original fingerprint (saved)
            candidate: Candidate fingerprint (current page element)

        Returns:
            float: Similarity percentage (0.0 ~ 100.0)
        """
        total_score: float = 0
        total_weight: float = 0

        # 1. Tag name exact match
        tag_weight = self.weights.get('tag', 1.0)
        total_score += (1 if original.tag == candidate.tag else 0) * tag_weight
        total_weight += tag_weight

        # 2. Text content similarity (SequenceMatcher fuzzy matching)
        if original.text:
            text_weight = self.weights.get('text', 2.0)
            total_score += SequenceMatcher(
                None, original.text, candidate.text or ""
            ).ratio() * text_weight
            total_weight += text_weight

        # 3. Attributes dictionary similarity
        attr_weight = self.weights.get('attributes', 1.5)
        total_score += self._calculate_dict_diff(original.attributes, candidate.attributes) * attr_weight
        total_weight += attr_weight

        # 4. Important attributes comparison (class, id, href, src)
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

        # 5. DOM path similarity
        path_weight = self.weights.get('path', 1.0)
        total_score += SequenceMatcher(None, original.path, candidate.path).ratio() * path_weight
        total_weight += path_weight

        # 6. Parent node information
        if original.parent_name:
            parent_weight = self.weights.get('parent', 1.0)
            p_score = 0
            p_checks = 0
            
            if candidate.parent_name:
                # Parent tag name
                p_score += SequenceMatcher(
                    None, original.parent_name, candidate.parent_name or ""
                ).ratio()
                p_checks += 1

                # Parent attributes
                p_score += self._calculate_dict_diff(
                    original.parent_attribs, candidate.parent_attribs or {}
                )
                p_checks += 1

                # Parent text
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

        # 7. Sibling nodes similarity
        if original.siblings:
            siblings_weight = self.weights.get('siblings', 0.5)
            total_score += SequenceMatcher(
                None, original.siblings, candidate.siblings or ()
            ).ratio() * siblings_weight
            total_weight += siblings_weight

        # Calculate percentage
        return round((total_score / total_weight) * 100, 2) if total_weight > 0 else 0.0

    def find_best_matches(
        self,
        target_fp: ElementFingerprint,
        root_element: HtmlElement,
        percentage: float = 0.0,
    ) -> List[HtmlElement]:
        """Find best matching elements in page

        Iterates through all elements and calculates similarity,
        returns group with highest score.

        Args:
            target_fp: Target element fingerprint
            root_element: Page root element
            percentage: Minimum matching percentage threshold

        Returns:
            List[HtmlElement]: Matched elements list (highest scoring group)
        """
        score_table: Dict[float, List[HtmlElement]] = {}

        # Iterate through all elements
        all_elements = root_element.xpath('.//*')
        for node in all_elements:
            if not isinstance(node, HtmlElement):
                continue
            # Only calculate similarity for same-tag elements (performance optimization)
            if node.tag != target_fp.tag:
                continue

            candidate_fp = ElementFingerprint.from_element(node)
            score = self.calculate_similarity(target_fp, candidate_fp)
            score_table.setdefault(score, []).append(node)

        if not score_table:
            return []

        # Find highest score
        highest_score = max(score_table.keys())

        # Check threshold
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

        # Debug log: Output Top 5 match scores
        if self.logger.isEnabledFor(10):  # DEBUG level
            top_scores = sorted(score_table.keys(), reverse=True)[:5]
            for s in top_scores:
                self.logger.debug(f"  {s}% -> {len(score_table[s])} element(s)")

        return score_table[highest_score]

    @staticmethod
    def _calculate_dict_diff(dict1: Dict, dict2: Dict) -> float:
        """Calculate similarity between two dictionaries

        Keys and values compared separately using SequenceMatcher, 50% weight each

        Args:
            dict1: First dictionary
            dict2: Second dictionary

        Returns:
            float: Similarity (0.0 ~ 1.0)
        """
        score = SequenceMatcher(
            None, tuple(dict1.keys()), tuple(dict2.keys())
        ).ratio() * 0.5
        score += SequenceMatcher(
            None, tuple(dict1.values()), tuple(dict2.values())
        ).ratio() * 0.5
        return score
