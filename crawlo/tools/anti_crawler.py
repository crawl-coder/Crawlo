#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
# @Time    : 2025-09-10 22:00
# @Author  : crawl-coder
# @Desc    : 反爬虫应对工具
"""

import asyncio
import random
import time
from typing import Dict, Any, Optional, List, Callable


class ProxyPoolManager:
    """代理池管理器类"""

    def __init__(self, proxies: Optional[List[Dict[str, str]]] = None):
        """
        初始化代理池管理器
        
        Args:
            proxies (Optional[List[Dict[str, str]]]): 代理列表
        """
        self.proxies = proxies or [
            {"http": "http://proxy1.example.com:8080", "https": "https://proxy1.example.com:8080"},
            {"http": "http://proxy2.example.com:8080", "https": "https://proxy2.example.com:8080"},
            {"http": "http://proxy3.example.com:8080", "https": "https://proxy3.example.com:8080"}
        ]
        self.proxy_status = {id(proxy): {"last_used": 0, "success_count": 0, "fail_count": 0} 
                           for proxy in self.proxies}

    def get_random_proxy(self) -> Dict[str, str]:
        """
        获取随机代理
        
        Returns:
            Dict[str, str]: 代理配置
        """
        return random.choice(self.proxies)

    def get_best_proxy(self) -> Dict[str, str]:
        """
        根据成功率获取最佳代理
        
        Returns:
            Dict[str, str]: 代理配置
        """
        if not self.proxy_status:
            return self.get_random_proxy()
            
        # 计算每个代理的成功率
        proxy_scores = []
        for proxy in self.proxies:
            proxy_id = id(proxy)
            status = self.proxy_status.get(proxy_id, {"success_count": 0, "fail_count": 0})
            total = status["success_count"] + status["fail_count"]
            
            if total == 0:
                score = 0.5  # 默认成功率
            else:
                score = status["success_count"] / total
                
            proxy_scores.append((proxy, score))
            
        # 按成功率排序，返回成功率最高的代理
        proxy_scores.sort(key=lambda x: x[1], reverse=True)
        return proxy_scores[0][0]

    def report_proxy_result(self, proxy: Dict[str, str], success: bool) -> None:
        """
        报告代理使用结果
        
        Args:
            proxy (Dict[str, str]): 代理配置
            success (bool): 是否成功
        """
        proxy_id = id(proxy)
        if proxy_id not in self.proxy_status:
            self.proxy_status[proxy_id] = {"last_used": 0, "success_count": 0, "fail_count": 0}
            
        status = self.proxy_status[proxy_id]
        status["last_used"] = time.time()
        
        if success:
            status["success_count"] += 1
        else:
            status["fail_count"] += 1

    def remove_invalid_proxy(self, proxy: Dict[str, str]) -> None:
        """
        移除无效代理
        
        Args:
            proxy (Dict[str, str]): 代理配置
        """
        if proxy in self.proxies:
            self.proxies.remove(proxy)
            proxy_id = id(proxy)
            if proxy_id in self.proxy_status:
                del self.proxy_status[proxy_id]


class CaptchaHandler:
    """验证码处理器类"""

    def __init__(self, captcha_service: Optional[Callable] = None):
        """
        初始化验证码处理器
        
        Args:
            captcha_service (Optional[Callable]): 验证码识别服务
        """
        self.captcha_service = captcha_service

    async def recognize_captcha(self, image_data: bytes, 
                               captcha_type: str = "image") -> Optional[str]:
        """
        识别验证码
        
        Args:
            image_data (bytes): 验证码图片数据
            captcha_type (str): 验证码类型
            
        Returns:
            Optional[str]: 识别结果
        """
        if self.captcha_service:
            try:
                return await self.captcha_service(image_data, captcha_type)
            except Exception:
                return None
        else:
            # 如果没有配置验证码服务，返回None
            return None

    async def handle_manual_captcha(self, prompt: str = "请输入验证码: ") -> str:
        """
        处理手动验证码输入
        
        Args:
            prompt (str): 提示信息
            
        Returns:
            str: 用户输入的验证码
        """
        # 在实际应用中，这里可能需要与用户界面交互
        # 为了演示目的，我们模拟用户输入
        print(prompt)
        return input() if not asyncio.get_event_loop().is_running() else ""


class AntiCrawler:
    """反爬虫应对工具类"""

    def __init__(self, proxies: Optional[List[Dict[str, str]]] = None,
                 captcha_service: Optional[Callable] = None):
        """
        初始化反爬虫应对工具
        
        Args:
            proxies (Optional[List[Dict[str, str]]]): 代理列表
            captcha_service (Optional[Callable]): 验证码识别服务
        """
        self.proxy_manager = ProxyPoolManager(proxies)
        self.captcha_handler = CaptchaHandler(captcha_service)

    def get_random_user_agent(self) -> str:
        """
        获取随机User-Agent
        
        Returns:
            str: 随机User-Agent
        """
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/91.0.864.59",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (Linux; Android 11; Pixel 5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Mobile Safari/537.36"
        ]
        return random.choice(user_agents)

    def rotate_proxy(self) -> Dict[str, str]:
        """
        轮换代理
        
        Returns:
            Dict[str, str]: 代理配置
        """
        return self.proxy_manager.get_best_proxy()

    def handle_captcha(self, response_text: str) -> bool:
        """
        检测是否遇到验证码
        
        Args:
            response_text (str): 响应文本
            
        Returns:
            bool: 是否遇到验证码
        """
        captcha_keywords = ["captcha", "verify", "验证", "验证码", "human verification"]
        return any(keyword in response_text.lower() for keyword in captcha_keywords)

    def detect_rate_limiting(self, status_code: int, response_headers: Dict[str, Any]) -> bool:
        """
        检测是否遇到频率限制
        
        Args:
            status_code (int): HTTP状态码
            response_headers (Dict[str, Any]): 响应头
            
        Returns:
            bool: 是否遇到频率限制
        """
        # 检查状态码
        if status_code in [429, 503]:
            return True
            
        # 检查响应头
        rate_limit_headers = ["x-ratelimit-remaining", "retry-after", "x-ratelimit-reset"]
        return any(header.lower() in [k.lower() for k in response_headers.keys()] 
                  for header in rate_limit_headers)

    def random_delay(self, min_delay: float = 1.0, max_delay: float = 3.0) -> None:
        """
        随机延迟，避免请求过于频繁
        
        Args:
            min_delay (float): 最小延迟时间（秒）
            max_delay (float): 最大延迟时间（秒）
        """
        delay = random.uniform(min_delay, max_delay)
        time.sleep(delay)

    async def async_random_delay(self, min_delay: float = 1.0, max_delay: float = 3.0) -> None:
        """
        异步随机延迟，避免请求过于频繁
        
        Args:
            min_delay (float): 最小延迟时间（秒）
            max_delay (float): 最大延迟时间（秒）
        """
        delay = random.uniform(min_delay, max_delay)
        await asyncio.sleep(delay)


# 便捷函数
def get_random_user_agent() -> str:
    """获取随机User-Agent"""
    return AntiCrawler().get_random_user_agent()


def rotate_proxy(proxies: Optional[List[Dict[str, str]]] = None) -> Dict[str, str]:
    """轮换代理"""
    return AntiCrawler(proxies).rotate_proxy()


def handle_captcha(response_text: str) -> bool:
    """检测是否遇到验证码"""
    return AntiCrawler().handle_captcha(response_text)


def detect_rate_limiting(status_code: int, response_headers: Dict[str, Any]) -> bool:
    """检测是否遇到频率限制"""
    return AntiCrawler().detect_rate_limiting(status_code, response_headers)