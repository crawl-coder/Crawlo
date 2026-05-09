#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
DefaultHeaderMiddleware
=======================
Adds default headers to all requests, supports User-Agent rotation.

Configuration:
    USER_AGENT = "Mozilla/5.0 ..."           # Fixed User-Agent (priority highest)
    USER_AGENT_ROTATION = True               # Enable random User-Agent rotation
    USER_AGENT_TYPE = "desktop"              # Device type: desktop/mobile/all
    DEFAULT_REQUEST_HEADERS = {              # Additional default headers
        'Accept': 'text/html,application/xhtml+xml',
        'Accept-Language': 'zh-CN,zh;q=0.9',
    }
"""

import random
from crawlo.logging import get_logger
from crawlo.exceptions import NotConfiguredError
from crawlo.middleware.user_agents import get_user_agents


class DefaultHeaderMiddleware(object):
    """
    DefaultHeaderMiddleware - Simple and practical header management
    
    Priority:
    1. Fixed USER_AGENT (if set)
    2. Rotating User-Agent (if USER_AGENT_ROTATION=True)
    3. Built-in default headers
    """

    def __init__(self, settings):
        """Initialize middleware with simplified configuration"""
        self.logger = get_logger(self.__class__.__name__)

        # Fixed User-Agent (highest priority)
        self.user_agent = settings.get('USER_AGENT')
        
        # User-Agent rotation settings
        self.rotation_enabled = settings.get_bool('USER_AGENT_ROTATION', False)
        self.rotation_type = settings.get('USER_AGENT_TYPE', 'desktop')
        
        # Additional default headers
        self.default_headers = settings.get_dict('DEFAULT_REQUEST_HEADERS', {})
        
        # Build final headers
        self.headers = {}
        
        # Add fixed User-Agent if configured
        if self.user_agent:
            self.headers['User-Agent'] = self.user_agent
        
        # Add default headers (without overriding User-Agent)
        for key, value in self.default_headers.items():
            if key not in self.headers:
                self.headers[key] = value
        
        # Validate: at least one header or rotation must be configured
        if not self.headers and not self.rotation_enabled:
            raise NotConfiguredError(
                "DefaultHeaderMiddleware: Configure USER_AGENT, USER_AGENT_ROTATION, or DEFAULT_REQUEST_HEADERS"
            )
        
        # Load User-Agent list if rotation enabled
        self.user_agents = []
        if self.rotation_enabled and not self.user_agent:
            self.user_agents = get_user_agents(self.rotation_type)
        
        self.logger.debug(
            f"DefaultHeaderMiddleware enabled [fixed_ua={'yes' if self.user_agent else 'no'}, "
            f"rotation={'yes' if self.rotation_enabled else 'no'}, "
            f"type={self.rotation_type}, headers={len(self.headers)}]"
        )

    @classmethod
    def create_instance(cls, crawler):
        """Create middleware instance"""
        return cls(crawler.settings)

    def _get_rotated_user_agent(self):
        """Get a random User-Agent from the rotation list"""
        if self.user_agents:
            return random.choice(self.user_agents)
        return None

    def process_request(self, request, _spider):
        """
        Process request, add headers following priority:
        1. Fixed USER_AGENT (if configured)
        2. Rotating User-Agent (if rotation enabled and no fixed UA)
        3. Default headers
        """
        # Add fixed headers first
        if self.headers:
            added = []
            for key, value in self.headers.items():
                if key not in request.headers:
                    request.headers[key] = value
                    added.append(key)
            
            if added:
                self.logger.debug(f"Added headers to {request.url}: {added}")
        
        # Apply rotating User-Agent if enabled and no fixed UA
        if self.rotation_enabled and not self.user_agent and 'User-Agent' not in request.headers:
            ua = self._get_rotated_user_agent()
            if ua:
                request.headers['User-Agent'] = ua
                self.logger.debug(f"Set rotating User-Agent for {request.url}: {ua[:50]}...")
        
        return None
