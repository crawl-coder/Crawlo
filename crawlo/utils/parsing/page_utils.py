#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
通用页面操作处理器
==================
为 Playwright 和 DrissionPage 提供统一的页面操作接口。

功能特性:
- 统一的操作配置格式（dynamic_actions）
- 自动检测并转换 XPath/CSS 选择器
- 支持两种下载器的操作执行
- 智能选择器类型识别
"""
import re
from typing import List, Dict, Any, Optional, Tuple


class SelectorConverter:
    """选择器转换器 - 自动识别和转换 XPath/CSS 选择器"""
    
    @staticmethod
    def detect_selector_type(selector: str) -> str:
        """
        检测选择器类型
        
        Returns:
            "xpath" - XPath 选择器
            "css" - CSS 选择器
        """
        if not selector:
            return "css"
        
        # XPath 特征：以 // 或 / 开头，或包含 xpath: 前缀
        selector = selector.strip()
        if selector.startswith('//') or selector.startswith('/'):
            return "xpath"
        if selector.startswith('xpath='):
            return "xpath"
        if selector.startswith('css='):
            return "css"
            
        # 包含 XPath 特征语法
        xpath_patterns = [
            r'\[contains\(',
            r'\[text\(\)\s*=',
            r'\[@\w+\s*=',
            r'//\w+',
            r'/\w+',
        ]
        
        for pattern in xpath_patterns:
            if re.search(pattern, selector):
                return "xpath"
        
        return "css"
    
    @staticmethod
    def normalize_selector(selector: str) -> Tuple[str, str]:
        """
        标准化选择器，返回 (类型, 纯净选择器)
        
        Examples:
            '//div[@class="test"]' -> ('xpath', '//div[@class="test"]')
            'xpath=//div' -> ('xpath', '//div')
            '.test' -> ('css', '.test')
            'css=.test' -> ('css', '.test')
        """
        if not selector:
            return ("css", selector)
        
        selector = selector.strip()
        
        # 处理前缀
        if selector.startswith('xpath='):
            return ("xpath", selector[6:].strip())
        if selector.startswith('css='):
            return ("css", selector[4:].strip())
        
        # 自动检测
        selector_type = SelectorConverter.detect_selector_type(selector)
        return (selector_type, selector)
    
    @staticmethod
    def xpath_to_css(xpath: str) -> str:
        """
        将简单的 XPath 转换为 CSS 选择器（有限支持）
        
        注意：复杂的 XPath 无法完全转换为 CSS，这种情况下应该使用原生 XPath
        
        Examples:
            '//div[@class="test"]' -> 'div.test'
            '//div[@id="main"]' -> 'div#main'
        """
        # 简单的属性选择器转换
        # //tag[@class="value"] -> tag.value
        match = re.match(r'//(\w+)\[@class="([^"]+)"\]', xpath)
        if match:
            tag, class_name = match.groups()
            return f"{tag}.{class_name}"
        
        # //tag[@id="value"] -> tag#value
        match = re.match(r'//(\w+)\[@id="([^"]+)"\]', xpath)
        if match:
            tag, id_value = match.groups()
            return f"{tag}#{id_value}"
        
        # //tag[@attr="value"] -> tag[attr="value"]
        match = re.match(r'//(\w+)\[@(\w+)="([^"]+)"\]', xpath)
        if match:
            tag, attr, value = match.groups()
            return f'{tag}[{attr}="{value}"]'
        
        # contains 转换
        match = re.match(r'//(\w+)\[contains\(@class,\s*"([^"]+)"\)\]', xpath)
        if match:
            tag, class_name = match.groups()
            return f"{tag}.{class_name}"
        
        # 无法转换，返回原 XPath
        return xpath


class PageActionHandler:
    """通用页面操作处理器"""
    
    @staticmethod
    def get_actions_from_request(request) -> List[Dict[str, Any]]:
        """
        从请求中获取操作列表（兼容多种键名）
        
        优先级：
        1. dynamic_actions（推荐，通用）
        2. playwright_actions（向后兼容）
        3. drissionpage_actions（向后兼容）
        """
        actions = (
            request.meta.get('dynamic_actions') or
            request.meta.get('playwright_actions') or
            request.meta.get('drissionpage_actions') or
            []
        )
        return actions if isinstance(actions, list) else []
    
    @staticmethod
    def extract_selector(action: Dict[str, Any]) -> Optional[str]:
        """从操作中安全地提取选择器"""
        params = action.get('params', {})
        if not isinstance(params, dict):
            return None
        return params.get('selector')
    
    @staticmethod
    def update_selector(action: Dict[str, Any], new_selector: str) -> Dict[str, Any]:
        """更新操作中的选择器"""
        if 'params' not in action:
            action['params'] = {}
        action['params']['selector'] = new_selector
        return action
