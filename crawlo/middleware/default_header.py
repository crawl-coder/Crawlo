#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
DefaultHeaderMiddleware 中间件
用于为所有请求添加默认请求头，支持随机更换User-Agent等功能
"""

import random
from crawlo.logging import get_logger
from crawlo.exceptions import NotConfiguredError
# 导入User-Agent数据
from crawlo.data.user_agents import get_user_agents


class DefaultHeaderMiddleware(object):
    """
    DefaultHeaderMiddleware 中间件
    用于为所有请求添加默认请求头，包括User-Agent等，支持随机更换功能
    """

    def __init__(self, settings):
        """
        初始化中间件
        """
        self.logger = get_logger(self.__class__.__name__)

        # 获取默认请求头配置
        self.headers = settings.get_dict('DEFAULT_REQUEST_HEADERS', {})

        # 获取User-Agent配置
        self.user_agent = settings.get('USER_AGENT')

        # 获取随机User-Agent列表
        self.user_agents = settings.get_list('USER_AGENTS', [])

        # 获取随机请求头配置
        self.random_headers = settings.get_dict('RANDOM_HEADERS', {})

        # 获取随机性配置
        self.randomness = settings.get_bool("RANDOMNESS", False)

        # 检查是否启用随机User-Agent
        self.random_user_agent_enabled = settings.get_bool("RANDOM_USER_AGENT_ENABLED", False)

        # 获取User-Agent设备类型
        self.user_agent_device_type = settings.get("USER_AGENT_DEVICE_TYPE", "all")

        # 如果没有配置默认请求头、User-Agent且没有启用随机功能，则禁用此中间件
        if not self.headers and not self.user_agent and not self.user_agents and not self.random_headers:
            raise NotConfiguredError(
                "未配置DEFAULT_REQUEST_HEADERS、USER_AGENT或随机头部配置，DefaultHeaderMiddleware已禁用")

        # 如果配置了User-Agent，将其添加到默认请求头中
        if self.user_agent:
            self.headers.setdefault('User-Agent', self.user_agent)

        # 如果启用了随机User-Agent但没有提供User-Agent列表，使用内置列表
        if self.random_user_agent_enabled and not self.user_agents:
            self.user_agents = get_user_agents(self.user_agent_device_type)

        self.logger.debug(f"DefaultHeaderMiddleware已启用 [默认请求头={len(self.headers)}, "
                          f"User-Agent列表={len(self.user_agents)}, "
                          f"随机头部={len(self.random_headers)}, "
                          f"随机功能={'启用' if self.randomness else '禁用'}]")

    @classmethod
    def create_instance(cls, crawler):
        """
        创建中间件实例
        """
        o = cls(
            settings=crawler.settings
        )
        return o

    def _get_random_user_agent(self):
        """
        获取随机User-Agent
        """
        if self.user_agents:
            return random.choice(self.user_agents)
        return None

    def _apply_random_headers(self, request):
        """
        应用随机请求头
        """
        if not self.random_headers:
            return

        for header_name, header_values in self.random_headers.items():
            # 如果header_values是列表，随机选择一个值
            if isinstance(header_values, (list, tuple)):
                header_value = random.choice(header_values)
            else:
                header_value = header_values

            # 只有当请求中没有该头部时才添加
            if header_name not in request.headers:
                request.headers[header_name] = header_value
                self.logger.debug(f"为请求 {request.url} 添加随机头部: {header_name}={header_value[:50]}...")

    async def process_request(self, request, _spider):
        """
        处理请求，添加默认请求头
        """
        # 添加默认请求头
        if self.headers:
            added_headers = []
            for key, value in self.headers.items():
                # 只有当请求中没有该头部时才添加
                if key not in request.headers:
                    request.headers[key] = value
                    added_headers.append(key)

            # 记录添加的请求头（仅在调试模式下）
            if added_headers and self.logger.isEnabledFor(10):  # DEBUG level
                self.logger.debug(f"为请求 {request.url} 添加了 {len(added_headers)} 个默认请求头: {added_headers}")

        # 处理随机User-Agent
        if self.random_user_agent_enabled and 'User-Agent' not in request.headers:
            random_ua = self._get_random_user_agent()
            if random_ua:
                request.headers['User-Agent'] = random_ua
                self.logger.debug(f"为请求 {request.url} 设置随机User-Agent: {random_ua[:50]}...")

        # 处理随机请求头
        if self.randomness:
            self._apply_random_headers(request)

        return None
