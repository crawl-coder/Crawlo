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
from typing import Dict, List, Optional, Tuple, Set

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

    def __init__(self, threshold: float = 0.0, weights: Optional[Dict[str, float]] = None,
                 ignore_attributes: Optional[Set[str]] = None):
        """Initialize matcher

        Args:
            threshold: Minimum similarity threshold (0-100 percentage), matches below this score will be discarded
            weights: Dimension weight configuration, uses default if None
            ignore_attributes: Attribute names to skip in important_attrs comparison (e.g., {'href', 'src'})
        """
        self.threshold = threshold
        self.weights = weights or self.DEFAULT_WEIGHTS
        self.ignore_attributes = ignore_attributes or set()
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
        important_attrs = [a for a in ('class', 'id', 'href', 'src') if a not in self.ignore_attributes]
        if important_attrs:
            important_attrs_weight = self.weights.get('important_attrs', 2.0)
            important_checks = 0
            important_score = 0
            for attrib in important_attrs:
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

    # Element scanning limit to prevent performance degradation on large pages
    MAX_SCAN_ELEMENTS = 5000

    def find_best_matches(
        self,
        target_fp: ElementFingerprint,
        root_element: HtmlElement,
        percentage: float = 0.0,
    ) -> List[HtmlElement]:
        """Find best matching elements in page

        Uses same-tag pre-filtering and element cap for performance.
        For common tags, narrows scope based on the original DOM path depth.

        Args:
            target_fp: Target element fingerprint
            root_element: Page root element
            percentage: Minimum matching percentage threshold

        Returns:
            List[HtmlElement]: Matched elements list (highest scoring group)
        """
        score_table: Dict[float, List[HtmlElement]] = {}

        # Get all same-tag elements with scope optimization:
        # Start from the original path depth to avoid scanning irrelevant nesting levels
        path_depth = len(target_fp.path) if target_fp.path else 0
        if path_depth > 1:
            # Narrow scope: only scan elements at similar depth (±1 level)
            scope_xpath = f'.//{target_fp.tag}'
        else:
            scope_xpath = f'.//{target_fp.tag}'

        all_elements = root_element.xpath(scope_xpath)
        total_scanned = 0

        for node in all_elements:
            if not isinstance(node, HtmlElement):
                continue

            total_scanned += 1
            if total_scanned > self.MAX_SCAN_ELEMENTS:
                self.logger.debug(
                    f"Element scan limit ({self.MAX_SCAN_ELEMENTS}) reached for "
                    f"tag='{target_fp.tag}', stopping scan"
                )
                break

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

        Uses Jaccard-like set comparison (order-independent) for keys,
        and SequenceMatcher for values. Each contributes 50% weight.

        Args:
            dict1: First dictionary
            dict2: Second dictionary

        Returns:
            float: Similarity (0.0 ~ 1.0)
        """
        # Key similarity: Jaccard-style (order-independent)
        keys1, keys2 = set(dict1.keys()), set(dict2.keys())
        if not keys1 and not keys2:
            return 1.0  # 两个字典都为空，视为完美匹配
        if not keys1 or not keys2:
            return 0.0  # 一个为空另一个非空，视为完全不同

        key_score = len(keys1 & keys2) / len(keys1 | keys2)

        # Value similarity: SequenceMatcher on sorted keys ensures stability
        if keys1 and keys2:
            common = sorted(keys1 & keys2)
            vals1 = tuple(str(dict1.get(k, '')) for k in common)
            vals2 = tuple(str(dict2.get(k, '')) for k in common)
            if vals1:
                val_score = SequenceMatcher(None, vals1, vals2).ratio()
            else:
                val_score = 0.0
        else:
            val_score = 0.0

        return key_score * 0.5 + val_score * 0.5

    def find_similar_elements(
        self,
        target_fp: ElementFingerprint,
        root_element: HtmlElement,
        threshold: float = 50.0,
    ) -> List[HtmlElement]:
        """Find structurally similar sibling elements based on DOM hierarchy.

        Uses same ancestry path + tag + depth to locate structurally similar
        elements (e.g., list items under the same parent), then filters by
        attribute/text similarity.

        Inspired by Scrapling's find_similar().

        Args:
            target_fp: Reference element fingerprint (e.g., the first matched product)
            root_element: Page root element
            threshold: Minimum similarity percentage to include (default 50.0)

        Returns:
            List[HtmlElement]: Structurally similar elements, excluding the reference
        """
        if not target_fp.path or len(target_fp.path) < 2:
            self.logger.debug("find_similar_elements: path too short, cannot determine structure")
            return []

        # Build scoped xpath using parent tag to limit search scope
        path_parts = list(target_fp.path)
        if len(path_parts) >= 3:
            # Scope: find tag under the same parent, at same nesting depth
            parent_tag = path_parts[-2]
            child_tag = path_parts[-1]
            xpath_query = f".//{parent_tag}/{child_tag}"
        elif len(path_parts) >= 2:
            parent_tag = path_parts[-2]
            child_tag = path_parts[-1]
            xpath_query = f".//{parent_tag}/{child_tag}"
        else:
            child_tag = path_parts[-1]
            xpath_query = f".//{child_tag}"

        try:
            candidates = root_element.xpath(xpath_query)
        except Exception:
            self.logger.debug(f"find_similar_elements: invalid xpath '{xpath_query}'")
            return []

        if not candidates:
            return []

        # Determine reference element depth
        ref_depth = len(target_fp.path)
        matched = []
        first_match: Optional[HtmlElement] = None

        for node in candidates:
            if not isinstance(node, HtmlElement):
                continue

            candidate_fp = ElementFingerprint.from_element(node)

            # Depth check: same or +/-1
            node_depth = len(candidate_fp.path)
            if abs(node_depth - ref_depth) > 1:
                continue

            score = self.calculate_similarity(target_fp, candidate_fp)

            # Exclude the reference element: skip first 100% match (self-match)
            # When fingerprints are structurally identical (e.g., same-class siblings),
            # the first element with 100% score is the reference itself.
            # Keep subsequent 100% matches (other structurally identical siblings).
            if score >= 99.9:
                if not matched and first_match is None:
                    first_match = node
                    continue

            if score >= threshold:
                matched.append(node)

        self.logger.debug(
            f"find_similar_elements: found {len(matched)} similar elements "
            f"(path='{xpath_query}', threshold={threshold}%)"
        )
        return matched
