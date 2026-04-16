#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
DefaultHeaderMiddleware
Adds default headers to all requests, supports random User-Agent rotation
"""

import random
from crawlo.logging import get_logger
from crawlo.exceptions import NotConfiguredError
# Import User-Agent data
from crawlo.data.user_agents import get_user_agents


class DefaultHeaderMiddleware(object):
    """
    DefaultHeaderMiddleware
    Adds default headers to all requests including User-Agent, supports random rotation
    """

    def __init__(self, settings):
        """
        Initialize middleware
        """
        self.logger = get_logger(self.__class__.__name__)

        # Get default headers configuration
        self.headers = settings.get_dict('DEFAULT_REQUEST_HEADERS', {})

        # Get User-Agent configuration
        self.user_agent = settings.get('USER_AGENT')

        # Get random User-Agent list
        self.user_agents = settings.get_list('USER_AGENTS', [])

        # Get random headers configuration
        self.random_headers = settings.get_dict('RANDOM_HEADERS', {})

        # Get randomness configuration
        self.randomness = settings.get_bool("RANDOMNESS", False)

        # Check if random User-Agent is enabled
        self.random_user_agent_enabled = settings.get_bool("RANDOM_USER_AGENT_ENABLED", False)

        # Get User-Agent device type
        self.user_agent_device_type = settings.get("USER_AGENT_DEVICE_TYPE", "all")

        # Disable middleware if no headers, User-Agent or random configuration is set
        if not self.headers and not self.user_agent and not self.user_agents and not self.random_headers:
            raise NotConfiguredError(
                "DEFAULT_REQUEST_HEADERS, USER_AGENT or random headers not configured, DefaultHeaderMiddleware disabled")

        # If User-Agent is configured, add it to default headers
        if self.user_agent:
            self.headers.setdefault('User-Agent', self.user_agent)

        # If random User-Agent is enabled but no list provided, use built-in list
        if self.random_user_agent_enabled and not self.user_agents:
            self.user_agents = get_user_agents(self.user_agent_device_type)

        self.logger.debug(f"DefaultHeaderMiddleware enabled [default_headers={len(self.headers)}, "
                          f"user_agents={len(self.user_agents)}, "
                          f"random_headers={len(self.random_headers)}, "
                          f"randomness={'enabled' if self.randomness else 'disabled'}]")

    @classmethod
    def create_instance(cls, crawler):
        """Create middleware instance"""
        return cls(crawler.settings)

    def _get_random_user_agent(self):
        """
        Get random User-Agent
        """
        if self.user_agents:
            return random.choice(self.user_agents)
        return None

    def _apply_random_headers(self, request):
        """
        Apply random headers
        """
        if not self.random_headers:
            return

        for header_name, header_values in self.random_headers.items():
            # If header_values is a list, randomly select one
            if isinstance(header_values, (list, tuple)):
                header_value = random.choice(header_values)
            else:
                header_value = header_values

            # Only add if header doesn't exist in request
            if header_name not in request.headers:
                request.headers[header_name] = header_value
                self.logger.debug(f"Added random header to {request.url}: {header_name}={header_value[:50]}...")

    async def process_request(self, request, _spider):
        """
        Process request, add default headers
        """
        # Add default headers
        if self.headers:
            added_headers = []
            for key, value in self.headers.items():
                # Only add if header doesn't exist in request
                if key not in request.headers:
                    request.headers[key] = value
                    added_headers.append(key)

            # Log added headers (only in debug mode)
            if added_headers and self.logger.isEnabledFor(10):  # DEBUG level
                self.logger.debug(f"Added {len(added_headers)} default headers to {request.url}: {added_headers}")

        # Handle random User-Agent
        if self.random_user_agent_enabled and 'User-Agent' not in request.headers:
            random_ua = self._get_random_user_agent()
            if random_ua:
                request.headers['User-Agent'] = random_ua
                self.logger.debug(f"Set random User-Agent for {request.url}: {random_ua[:50]}...")

        # Handle random headers
        if self.randomness:
            self._apply_random_headers(request)

        return None
