#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Generic Proxy Middleware
Supports static proxy list and dynamic proxy API modes

Features:
1. Static proxy mode: randomly select from configured proxy list
2. Dynamic proxy mode: fetch proxy from external API
3. Automatic proxy health tracking and failure detection
4. Immediate downgrade to direct connection when proxy fails
5. Failed proxy recovery on successful requests
"""
import json
import random
import aiohttp
from typing import Optional, List

from crawlo.logging import get_logger
from crawlo.network import Request, Response


class ProxyMiddleware:
    """Generic proxy middleware for managing proxy assignment and health tracking"""

    def __init__(self, settings):
        self.logger = get_logger(self.__class__.__name__)

        # Get proxy list and API URL
        self.proxies: List[str] = settings.get("PROXY_LIST", [])
        self.api_url = settings.get("PROXY_API_URL")  # 代理 API URL（可选）
        # Get proxy extraction configuration
        self.proxy_extractor = settings.get("PROXY_EXTRACTOR", "proxy")  # Default extract from "proxy" field
        
        # Record failed proxies to avoid reuse
        self.failed_proxies = set()
        # Max failure attempts, proxy will be marked as failed after this threshold
        self.max_failed_attempts = settings.get("PROXY_MAX_FAILED_ATTEMPTS", 3)
        # Failure tracking for proxies
        self.proxy_failure_count = {}
        
        # Determine which mode to enable based on configuration
        if self.proxies:
            self.mode = "static"  # Static proxy mode
            self.enabled = True
            self.logger.info(f"ProxyMiddleware enabled (static mode) with {len(self.proxies)} proxies")
        elif self.api_url:
            self.mode = "dynamic"  # Dynamic proxy mode
            self.enabled = True
            self.logger.info(f"ProxyMiddleware enabled (dynamic mode) | API: {self.api_url}")
        else:
            self.mode = None
            self.enabled = False
            self.logger.info("ProxyMiddleware disabled (no proxy configuration)")

    @classmethod
    def create_instance(cls, crawler):
        return cls(settings=crawler.settings)

    async def _fetch_proxy_from_api(self) -> Optional[str]:
        """Fetch proxy from API"""
        try:
            # Create connector with proper configuration to avoid version compatibility issues
            connector = aiohttp.TCPConnector(limit=10, limit_per_host=5, force_close=True)
            timeout = aiohttp.ClientTimeout(total=10)
            
            async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                async with session.get(self.api_url) as resp:
                    if resp.status == 200:
                        # Check content type
                        content_type = resp.headers.get('content-type', '')
                        if 'application/json' in content_type:
                            data = await resp.json()
                        else:
                            # If not JSON, try to parse as text
                            text = await resp.text()
                            data = json.loads(text)
                        
                        # Support multiple proxy extraction methods
                        proxy = self._extract_proxy_from_data(data)
                        if proxy and isinstance(proxy, str) and (proxy.startswith("http://") or proxy.startswith("https://")):
                            return proxy
                    else:
                        self.logger.warning(f"Proxy API returned status {resp.status}")
        except ImportError as e:
            self.logger.error(f"aiohttp not installed: {repr(e)}")
        except json.JSONDecodeError as e:
            self.logger.warning(f"Proxy API response JSON parse error: {e}")
        except UnicodeDecodeError as e:
            self.logger.warning(f"Proxy API response encoding error: {e}")
        except Exception as e:
            self.logger.warning(f"Failed to fetch proxy from API: {repr(e)}")
        return None

    def _extract_proxy_from_data(self, data) -> Optional[str]:
        """
        Extract proxy from API response data
        
        Supports simple field extraction methods:
        1. String: Used directly as field name
        """
        if isinstance(self.proxy_extractor, str):
            # Simple field name extraction (backward compatible)
            if self.proxy_extractor in data:
                proxy_value = data[self.proxy_extractor]
                return str(proxy_value) if proxy_value is not None else None
        
        # Default extraction method (backward compatible)
        if "proxy" in data:
            proxy_value = data["proxy"]
            return str(proxy_value) if proxy_value is not None else None
        
        return None

    async def process_request(self, request: Request, spider) -> Optional[Request]:
        """Assign proxy to request"""
        if not self.enabled:
            return None

        if request.proxy:
            # Request already has proxy, don't override
            return None

        proxy = None
        if self.mode == "static" and self.proxies:
            # Static mode: randomly select a proxy, excluding known failed ones
            available_proxies = [p for p in self.proxies if p not in self.failed_proxies]
            if available_proxies:
                proxy = random.choice(available_proxies)
            else:
                self.logger.warning("All static proxies failed, will use direct connection")
        elif self.mode == "dynamic" and self.api_url:
            # Dynamic mode: fetch proxy from API
            proxy = await self._fetch_proxy_from_api()

        if proxy:
            # Check if proxy is in failed list
            if proxy in self.failed_proxies:
                self.logger.warning(f"Attempting to use known failed proxy: {proxy}, but will try anyway")
            
            request.proxy = proxy
            self.logger.info(f"Assigned proxy {proxy} to {request.url}")
        else:
            self.logger.warning(f"No proxy available, request connecting directly: {request.url}")

        return None

    async def process_response(self, request: Request, response: Response, spider) -> Response:
        """Handle successful response"""
        if request.proxy:
            self.logger.debug(f"Proxy request successful: {request.proxy} | {request.url}")
            # Remove from failed list if present
            self.failed_proxies.discard(request.proxy)
            # Reset failure count
            if request.proxy in self.proxy_failure_count:
                del self.proxy_failure_count[request.proxy]
        return response

    async def process_exception(self, request: Request, exception: Exception, spider) -> Optional[Request]:
        """Handle proxy failure and downgrade to direct connection"""
        if not request.proxy:
            return None
            
        proxy = request.proxy
        error_msg = f"Proxy request failed: {proxy} | {request.url} | {repr(exception)}"
        self.logger.warning(error_msg)
        
        # Record failure count
        if proxy not in self.proxy_failure_count:
            self.proxy_failure_count[proxy] = 0
        self.proxy_failure_count[proxy] += 1
        
        # Mark proxy as failed if threshold reached
        if self.proxy_failure_count[proxy] >= self.max_failed_attempts:
            self.failed_proxies.add(proxy)
            self.logger.warning(f"Proxy {proxy} failed {self.max_failed_attempts} times, marked as failed")
            
            # Downgrade to direct connection immediately
            self.logger.info(f"Downgrading request to direct connection: {request.url}")
            request_copy = request.copy()
            request_copy.proxy = None
            request_copy.meta['proxy_downgraded'] = True
            return request_copy
        
        return None
