#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
带认证代理工具
=============
支持带用户名密码认证的代理和非认证代理的统一处理工具

功能特性:
- 支持HTTP/HTTPS/SOCKS代理
- 支持带认证和不带认证的代理
- 统一的代理格式处理
- 代理有效性检测
"""

from typing import Dict, Any, Optional, Union
from urllib.parse import urlparse, urlunparse


class AuthenticatedProxy:
    """带认证代理处理类"""

    def __init__(self, proxy_url: str):
        """
        初始化代理对象
        
        Args:
            proxy_url (str): 代理URL，支持带认证信息的格式
                - 带认证: http://username:password@proxy.example.com:8080
                - 无认证: http://proxy.example.com:8080
        """
        self.proxy_url = proxy_url
        self.parsed = urlparse(proxy_url)
        
        # 提取认证信息
        self.username = self.parsed.username
        self.password = self.parsed.password
        
        # 构造不带认证信息的URL
        self.clean_url = urlunparse((
            self.parsed.scheme,
            f"{self.parsed.hostname}:{self.parsed.port}" if self.parsed.port else self.parsed.hostname,
            self.parsed.path,
            self.parsed.params,
            self.parsed.query,
            self.parsed.fragment
        ))
        
        # 构造下载器兼容的代理字典
        self.proxy_dict = {
            "http": self.clean_url,
            "https": self.clean_url
        }
        
        # 如果有认证信息，构造认证字符串
        if self.username and self.password:
            self.auth_string = f"{self.username}:{self.password}"
        else:
            self.auth_string = None

    def get_proxy_for_downloader(self) -> Union[str, Dict[str, str]]:
        """
        获取适用于下载器的代理配置
        
        Returns:
            Union[str, Dict[str, str]]: 代理配置
                - 对于AioHttp/CurlCffi: 返回字典格式 {"http": "...", "https": "..."}
                - 对于HttpX: 可以直接使用字符串或字典格式
        """
        return self.proxy_dict

    def get_auth_credentials(self) -> Optional[Dict[str, str]]:
        """
        获取认证凭据
        
        Returns:
            Optional[Dict[str, str]]: 认证凭据 {"username": "...", "password": "..."}
        """
        if self.username and self.password:
            return {
                "username": self.username,
                "password": self.password
            }
        return None

    def get_auth_header(self) -> Optional[str]:
        """
        获取Basic Auth认证头
        
        Returns:
            Optional[str]: Basic Auth头信息
        """
        if self.username and self.password:
            import base64
            credentials = f"{self.username}:{self.password}"
            encoded = base64.b64encode(credentials.encode()).decode()
            return f"Basic {encoded}"
        return None

    def is_valid(self) -> bool:
        """
        检查代理URL是否有效
        
        Returns:
            bool: 代理URL是否有效
        """
        # 检查协议
        if self.parsed.scheme not in ["http", "https", "socks4", "socks5"]:
            return False
            
        # 检查主机名
        if not self.parsed.hostname:
            return False
            
        # 检查端口（如果指定）
        if self.parsed.port and (self.parsed.port < 1 or self.parsed.port > 65535):
            return False
            
        return True

    def __str__(self) -> str:
        return self.proxy_url

    def __repr__(self) -> str:
        return f"AuthenticatedProxy(url='{self.proxy_url}', username={self.username is not None})"


def create_proxy_config(proxy_url: str) -> Dict[str, Any]:
    """
    创建代理配置，兼容各种下载器
    
    Args:
        proxy_url (str): 代理URL
        
    Returns:
        Dict[str, Any]: 代理配置字典
    """
    proxy = AuthenticatedProxy(proxy_url)
    
    if not proxy.is_valid():
        raise ValueError(f"Invalid proxy URL: {proxy_url}")
    
    config = {
        "url": proxy.clean_url,
        "proxy_dict": proxy.proxy_dict,
        "has_auth": proxy.auth_string is not None
    }
    
    if proxy.auth_string:
        config["auth"] = proxy.get_auth_credentials()
        config["auth_header"] = proxy.get_auth_header()
        
    return config


def format_proxy_for_request(proxy_config: Dict[str, Any], downloader_type: str = "aiohttp") -> Dict[str, Any]:
    """
    格式化代理配置以适配特定下载器
    
    Args:
        proxy_config (Dict[str, Any]): 代理配置
        downloader_type (str): 下载器类型 (aiohttp, httpx, curl_cffi)
        
    Returns:
        Dict[str, Any]: 适配下载器的代理配置
    """
    formatted = {}
    
    if downloader_type.lower() == "aiohttp":
        # AioHttp使用proxy和proxy_auth参数
        formatted["proxy"] = proxy_config["url"]
        if proxy_config.get("has_auth") and proxy_config.get("auth"):
            from aiohttp import BasicAuth
            auth = proxy_config["auth"]
            formatted["proxy_auth"] = BasicAuth(auth["username"], auth["password"])
            
    elif downloader_type.lower() == "httpx":
        # HttpX可以直接使用代理URL字符串或字典
        formatted["proxy"] = proxy_config["url"]
        
    elif downloader_type.lower() == "curl_cffi":
        # CurlCffi使用proxies字典
        formatted["proxies"] = proxy_config["proxy_dict"]
        # 认证信息包含在URL中或通过headers传递
        if proxy_config.get("auth_header"):
            formatted["headers"] = {"Proxy-Authorization": proxy_config["auth_header"]}
            
    return formatted


# 便捷函数
def parse_proxy_url(proxy_url: str) -> Dict[str, Any]:
    """
    解析代理URL并返回详细信息
    
    Args:
        proxy_url (str): 代理URL
        
    Returns:
        Dict[str, Any]: 代理详细信息
    """
    return create_proxy_config(proxy_url)


def validate_proxy_url(proxy_url: str) -> bool:
    """
    验证代理URL是否有效
    
    Args:
        proxy_url (str): 代理URL
        
    Returns:
        bool: 是否有效
    """
    try:
        proxy = AuthenticatedProxy(proxy_url)
        return proxy.is_valid()
    except:
        return False


def get_proxy_info(proxy_url: str) -> Dict[str, Any]:
    """
    获取代理详细信息
    
    Args:
        proxy_url (str): 代理URL
        
    Returns:
        Dict[str, Any]: 代理详细信息
    """
    proxy = AuthenticatedProxy(proxy_url)
    return {
        "original_url": proxy.proxy_url,
        "clean_url": proxy.clean_url,
        "scheme": proxy.parsed.scheme,
        "hostname": proxy.parsed.hostname,
        "port": proxy.parsed.port,
        "has_auth": proxy.auth_string is not None,
        "username": proxy.username,
        "is_valid": proxy.is_valid()
    }