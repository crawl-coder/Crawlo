#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
场景适配器
=========
根据不同的动态加载场景，自动配置和优化下载器选择策略。

支持的场景:
1. 列表页、详情页都要动态加载
2. 列表页使用协议请求、详情页使用动态加载
3. 列表页使用动态加载，详情页使用协议请求

使用示例:
    # 场景1: 全动态加载
    adapter = DynamicLoadingScenarioAdapter(scenario="all_dynamic")
    
    # 场景2: 列表页协议，详情页动态
    adapter = DynamicLoadingScenarioAdapter(scenario="list_protocol_detail_dynamic")
    
    # 场景3: 列表页动态，详情页协议
    adapter = DynamicLoadingScenarioAdapter(scenario="list_dynamic_detail_protocol")
"""
import re
from typing import Dict, Any
from urllib.parse import urlparse

from crawlo.logging import get_logger


class DynamicLoadingScenarioAdapter:
    """
    动态加载场景适配器
    根据不同的业务场景自动配置下载器选择策略
    """
    
    SCENARIOS = {
        "all_dynamic": "列表页、详情页都要动态加载",
        "list_protocol_detail_dynamic": "列表页使用协议请求、详情页使用动态加载",
        "list_dynamic_detail_protocol": "列表页使用动态加载，详情页使用协议请求"
    }
    
    def __init__(self, scenario: str = "list_protocol_detail_dynamic", **kwargs):
        """
        初始化场景适配器
        
        :param scenario: 场景类型
        :param kwargs: 其他配置参数
        """
        self.scenario = scenario
        self.logger = get_logger(self.__class__.__name__)
        
        # 验证场景类型
        if scenario not in self.SCENARIOS:
            raise ValueError(f"Unsupported scenario: {scenario}. Supported: {list(self.SCENARIOS.keys())}")
            
        self.logger.info(f"Initializing DynamicLoadingScenarioAdapter for scenario: {scenario}")
        
        # 配置参数
        self.list_page_patterns = kwargs.get("list_page_patterns", [
            r"/list", r"/search", r"/category", r"/page/\d+", r"\?page=", r"\?p=\d+"
        ])
        
        self.detail_page_patterns = kwargs.get("detail_page_patterns", [
            r"/detail", r"/item", r"/product", r"/article", r"/post", r"/view", r"/\d+"
        ])
        
        self.list_domains = set(kwargs.get("list_domains", []))
        self.detail_domains = set(kwargs.get("detail_domains", []))
        
        # 构建配置
        self.config = self._build_config()
        
    def _build_config(self) -> Dict[str, Any]:
        """根据场景构建配置"""
        config = {
            "HYBRID_DYNAMIC_URL_PATTERNS": [],
            "HYBRID_PROTOCOL_URL_PATTERNS": [],
            "HYBRID_DYNAMIC_DOMAINS": [],
            "HYBRID_PROTOCOL_DOMAINS": []
        }
        
        if self.scenario == "all_dynamic":
            # 所有页面都使用动态加载
            config["HYBRID_DYNAMIC_URL_PATTERNS"].extend(self.list_page_patterns)
            config["HYBRID_DYNAMIC_URL_PATTERNS"].extend(self.detail_page_patterns)
            
        elif self.scenario == "list_protocol_detail_dynamic":
            # 列表页使用协议请求，详情页使用动态加载
            config["HYBRID_PROTOCOL_URL_PATTERNS"].extend(self.list_page_patterns)
            config["HYBRID_DYNAMIC_URL_PATTERNS"].extend(self.detail_page_patterns)
            
            # 域名配置
            config["HYBRID_PROTOCOL_DOMAINS"].extend(self.list_domains)
            config["HYBRID_DYNAMIC_DOMAINS"].extend(self.detail_domains)
            
        elif self.scenario == "list_dynamic_detail_protocol":
            # 列表页使用动态加载，详情页使用协议请求
            config["HYBRID_DYNAMIC_URL_PATTERNS"].extend(self.list_page_patterns)
            config["HYBRID_PROTOCOL_URL_PATTERNS"].extend(self.detail_page_patterns)
            
            # 域名配置
            config["HYBRID_DYNAMIC_DOMAINS"].extend(self.list_domains)
            config["HYBRID_PROTOCOL_DOMAINS"].extend(self.detail_domains)
            
        return config
    
    def get_settings(self) -> Dict[str, Any]:
        """获取场景配置设置"""
        return self.config
    
    def should_use_dynamic_loader(self, url: str) -> bool:
        """
        判断给定URL是否应该使用动态加载器
        
        :param url: 要判断的URL
        :return: 是否使用动态加载器
        """
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.lower()
        path = parsed_url.path.lower()
        query = parsed_url.query.lower()
        full_path = path + ("?" + query if query else "")
        
        # 检查域名
        if domain in self.config["HYBRID_DYNAMIC_DOMAINS"]:
            return True
        if domain in self.config["HYBRID_PROTOCOL_DOMAINS"]:
            return False
            
        # 检查URL模式
        # 检查动态模式
        for pattern in self.config["HYBRID_DYNAMIC_URL_PATTERNS"]:
            if re.search(pattern, full_path):
                return True
                
        # 检查协议模式
        for pattern in self.config["HYBRID_PROTOCOL_URL_PATTERNS"]:
            if re.search(pattern, full_path):
                return False
                
        # 默认策略
        if self.scenario == "all_dynamic":
            return True
        elif self.scenario == "list_protocol_detail_dynamic":
            # 默认详情页使用动态加载
            return True
        elif self.scenario == "list_dynamic_detail_protocol":
            # 默认详情页使用协议加载
            return False
            
        # 默认返回False（使用协议加载器）
        return False
    
    def get_loader_options(self, url: str) -> Dict[str, Any]:
        """
        获取特定URL的加载器选项
        
        :param url: URL
        :return: 加载器选项
        """
        options = {}
        
        # 可以根据URL添加特定的加载器选项
        # 例如，对于某些页面可能需要等待特定元素加载完成
        if "product" in url:
            options["wait_for_element"] = ".product-detail"
        elif "article" in url:
            options["wait_for_element"] = ".article-content"
            
        return options
    
    def adapt_request(self, request) -> None:
        """
        适配请求对象，根据场景自动设置加载器
        
        :param request: 请求对象
        """
        use_dynamic = self.should_use_dynamic_loader(request.url)
        
        if use_dynamic:
            request.set_dynamic_loader(True, self.get_loader_options(request.url))
            self.logger.debug(f"Adapted request {request.url} to use dynamic loader")
        else:
            request.set_protocol_loader()
            self.logger.debug(f"Adapted request {request.url} to use protocol loader")


# 便利函数
def create_scenario_adapter(scenario: str = "list_protocol_detail_dynamic", **kwargs):
    """
    创建场景适配器的便利函数
    
    :param scenario: 场景类型
    :param kwargs: 其他配置参数
    :return: 场景适配器实例
    """
    return DynamicLoadingScenarioAdapter(scenario, **kwargs)


def get_scenario_settings(scenario: str = "list_protocol_detail_dynamic", **kwargs) -> Dict[str, Any]:
    """
    获取场景配置设置的便利函数
    
    :param scenario: 场景类型
    :param kwargs: 其他配置参数
    :return: 配置设置字典
    """
    adapter = DynamicLoadingScenarioAdapter(scenario, **kwargs)
    return adapter.get_settings()


# 预定义场景配置
SCENARIO_CONFIGS = {
    "电商网站": {
        "scenario": "list_protocol_detail_dynamic",
        "list_page_patterns": [r"/list", r"/search", r"/category", r"/page/\d+"],
        "detail_page_patterns": [r"/product", r"/item", r"/detail/\d+"],
        "list_domains": [],
        "detail_domains": []
    },
    
    "新闻网站": {
        "scenario": "list_protocol_detail_dynamic",
        "list_page_patterns": [r"/list", r"/category", r"/page/\d+"],
        "detail_page_patterns": [r"/article", r"/post", r"/news/\d+"],
        "list_domains": [],
        "detail_domains": []
    },
    
    "社交平台": {
        "scenario": "all_dynamic",
        "list_page_patterns": [r"/feed", r"/timeline", r"/explore"],
        "detail_page_patterns": [r"/post", r"/status", r"/photo"],
        "list_domains": [],
        "detail_domains": []
    },
    
    "博客平台": {
        "scenario": "list_dynamic_detail_protocol",
        "list_page_patterns": [r"/blog", r"/posts", r"/archive"],
        "detail_page_patterns": [r"/\d{4}/\d{2}/\d{2}/"],
        "list_domains": [],
        "detail_domains": []
    }
}


def create_adapter_for_platform(platform: str, **custom_kwargs) -> DynamicLoadingScenarioAdapter:
    """
    为特定平台创建场景适配器
    
    :param platform: 平台名称
    :param custom_kwargs: 自定义配置参数
    :return: 场景适配器实例
    """
    if platform not in SCENARIO_CONFIGS:
        raise ValueError(f"Unsupported platform: {platform}. Supported: {list(SCENARIO_CONFIGS.keys())}")
    
    config = SCENARIO_CONFIGS[platform].copy()
    config.update(custom_kwargs)
    scenario = config.pop("scenario")
    
    return DynamicLoadingScenarioAdapter(scenario, **config)