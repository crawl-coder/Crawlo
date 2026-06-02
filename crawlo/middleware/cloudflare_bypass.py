#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Cloudflare Bypass Middleware
=============================
Automatically detect and bypass Cloudflare challenge pages.

Features:
- Detect Cloudflare challenge pages (403/503 + signatures)
- Progressive downloader chain (camoufox → cloakbrowser auto-escalation)
- CF cookie persistence (cf_clearance cache per domain)
- Smart retry mechanism

Usage:
# settings.py
# Middleware is already registered in framework, no manual configuration needed
# Only configure the downloader chain for bypass
CLOUDFLARE_BYPASS_DOWNLOADER_CHAIN = ['camoufox', 'cloakbrowser']
CLOUDFLARE_BYPASS_COOKIE_CACHE_ENABLED = True
"""

import re
import time
from typing import Optional, Union, Dict, List
from urllib.parse import urlparse

from crawlo.network.request import Request
from crawlo.network.response import Response
from crawlo.logging import get_logger


class CloudflareBypassMiddleware:
    """
    Cloudflare bypass middleware
    
    Automatically detect Cloudflare challenge pages and retry with stealth browser.
    
    Detection logic:
    1. HTTP status code is 403, 503, 520, 521, 522, 523, 524
    2. Response content contains Cloudflare signatures
    3. Support Turnstile challenge type detection
    
    Bypass strategy:
    1. Use progressive downloader chain (default: camoufox → cloakbrowser)
    2. Cache cf_clearance cookies for reuse
    3. Support request-level configuration for different browsers
    """
    
    # 类级别：是否已输出过初始化日志（避免重复）
    _init_logged: bool = False

    # Cloudflare challenge status codes
    CHALLENGE_STATUS_CODES = {403, 503, 520, 521, 522, 523, 524}
    
    # Cloudflare Turnstile challenge types
    CHALLENGE_TYPES = (
        "non-interactive",
        "managed",
        "interactive",
    )
    
    # Cloudflare response signatures (will be compiled in __init__)
    CLOUDFLARE_SIGNATURE_PATTERNS = [
        r'cloudflare',
        r'cf-ray',
        r'cf-browser-verify',
        r'cf_chl_opt',
        r'challenge-platform',
        r'ray id:',
        r'Checking your browser',
        r'Just a moment',
        r'DDoS protection by Cloudflare',
        r'Please Wait\.\.\. \| Cloudflare',
        r'<title>Access denied</title>',
        r'<title>Attention Required!</title>',
        r'enable JavaScript',
        r'cf_clearance',
        r'__cf_bm',
        r'cf-mitigated',
        r'cType:',  # Turnstile challenge type identifier
    ]
    
    # Cloudflare challenge platform URL pattern
    CF_CHALLENGE_PATTERN = re.compile(r"^https?://challenges\.cloudflare\.com/cdn-cgi/challenge-platform/.*")
    
    def __init__(self, crawler):
        self.crawler = crawler
        self.logger = get_logger(self.__class__.__name__)
        
        # Configuration
        self.max_retries = crawler.settings.get_int("CLOUDFLARE_BYPASS_MAX_RETRIES", 2)
        self.default_downloader = crawler.settings.get("CLOUDFLARE_BYPASS_DOWNLOADER", "cloakbrowser")
        
        # Progressive downloader chain
        raw_chain = crawler.settings.get("CLOUDFLARE_BYPASS_DOWNLOADER_CHAIN", None)
        if raw_chain:
            self._downloader_chain = list(raw_chain)
        else:
            self._downloader_chain = ['cloakbrowser']
        
        # Cookie cache
        self._cookie_cache_enabled = crawler.settings.get_bool(
            "CLOUDFLARE_BYPASS_COOKIE_CACHE_ENABLED", True
        )
        # domain -> {cookies: dict, expires_at: float}
        self._cf_cookie_cache: Dict[str, Dict] = {}
        # CF cookies to capture after successful bypass
        self._cf_cookie_names = {'cf_clearance', '__cf_bm', '__cflb', 'cf_chl_rc_m'}
        
        # Cache known Cloudflare domains
        self._cloudflare_domains = set()
        
        # Downloader instance cache (lazy initialization)
        self._bypass_downloader = None
        
        # Pre-compile regex patterns for performance
        self._compiled_signatures = [
            re.compile(pattern, re.IGNORECASE) 
            for pattern in self.CLOUDFLARE_SIGNATURE_PATTERNS
        ]
        
        # 首次实例化输出 INFO，后续仅 debug 避免重复
        if not CloudflareBypassMiddleware._init_logged:
            CloudflareBypassMiddleware._init_logged = True
            self.logger.info(
                f"CloudflareBypassMiddleware initialized "
                f"(chain={self._downloader_chain}, "
                f"cookie_cache={'enabled' if self._cookie_cache_enabled else 'disabled'})"
            )
        else:
            self.logger.debug(
                f"CloudflareBypassMiddleware initialized "
                f"(chain={self._downloader_chain}, "
                f"cookie_cache={'enabled' if self._cookie_cache_enabled else 'disabled'})"
            )

    @classmethod
    def create_instance(cls, crawler):
        """Create middleware instance"""
        return cls(crawler)

    async def process_request(self, request: Request, spider) -> Optional[Request]:
        """Pre-process request"""
        # Skip if request already marked as using stealth browser
        if request.meta.get('cloudflare_bypass_attempted'):
            return None
        
        # If domain is known to need Cloudflare bypass, use stealth browser directly
        if self._is_known_cloudflare_domain(request.url):
            self.logger.debug(f"Known Cloudflare domain, using stealth browser for {request.url}")
            request.meta['use_dynamic_loader'] = True
            request.meta['dynamic_downloader_type'] = request.meta.get(
                'cloudflare_bypass_downloader', 
                self._downloader_chain[0]
            )
        
        # Inject cached CF cookies for known domains
        if self._cookie_cache_enabled:
            self._inject_cf_cookies(request)
        
        return None

    async def process_response(self, request: Request, response: Response, spider) -> Union[Request, Response]:
        """Post-process response"""
        # If this request used a stealth browser and succeeded, cache cookies
        if response.status < 400 and request.meta.get('cloudflare_bypass_attempted'):
            if self._cookie_cache_enabled:
                self._capture_cf_cookies(request.url, response)
            # Check if the stealth browser itself got a CF challenge (escalation needed)
            if self._is_cloudflare_challenge(response):
                return self._handle_escalation(request, response)
            return response
        
        # Check if this is a Cloudflare challenge page
        if not self._is_cloudflare_challenge(response):
            return response
        
        return self._handle_bypass_retry(request)

    async def process_exception(self, request: Request, exception: Exception, spider) -> Optional[Request]:
        """Handle exception"""
        # Some exceptions may also be caused by Cloudflare
        exception_str = str(exception).lower()
        cloudflare_error_indicators = [
            'cloudflare',
            'cf-ray',
            '403',
            'forbidden',
            'access denied',
        ]
        
        if any(indicator in exception_str for indicator in cloudflare_error_indicators):
            return self._handle_bypass_retry(request)
        
        return None

    # ── Private: Detection ──

    def _is_cloudflare_challenge(self, response: Response) -> bool:
        """Detect if this is a Cloudflare challenge page"""
        # Check status code
        if response.status not in self.CHALLENGE_STATUS_CODES:
            return False
        
        # Check response headers
        headers_lower = {k.lower(): v for k, v in response.headers.items()}
        if 'cf-ray' in headers_lower or 'cf-cache-status' in headers_lower:
            return True
        
        # Check response content
        body = response.body
        if not body:
            return False
        
        # Ensure body is string for regex matching (response.body may be bytes)
        if isinstance(body, bytes):
            try:
                body = body.decode('utf-8', errors='ignore')
            except Exception:
                return False
        
        # Check Cloudflare signatures using pre-compiled patterns
        for pattern in self._compiled_signatures:
            if pattern.search(body):
                return True
        
        return False
    
    def _detect_cloudflare_type(self, page_content: str) -> Optional[str]:
        """Detect Cloudflare Turnstile challenge type"""
        try:
            content = page_content if isinstance(page_content, str) else page_content.decode('utf-8', errors='ignore')
            
            for ctype in self.CHALLENGE_TYPES:
                if f"cType: '{ctype}'" in content:
                    return ctype
            
            if 'challenges.cloudflare.com/turnstile' in content:
                return "embedded"
            
            return None
        except Exception:
            return None

    # ── Private: Bypass & Escalation ──

    def _handle_bypass_retry(self, request: Request) -> Optional[Request]:
        """Create bypass retry request with progressive downloader chain"""
        bypass_count = request.meta.get('cloudflare_bypass_count', 0)
        
        # Determine which downloader to use based on chain index
        chain_index = min(bypass_count, len(self._downloader_chain) - 1)
        downloader = self._downloader_chain[chain_index]
        
        # Check if we've exhausted all downloaders
        if chain_index >= len(self._downloader_chain) - 1 and bypass_count >= self.max_retries:
            self.logger.warning(
                f"All {len(self._downloader_chain)} downloaders exhausted for {request.url}"
            )
            return None
        
        # Mark domain as Cloudflare-protected
        self._mark_cloudflare_domain(request.url)
        
        self.logger.info(
            f"Cloudflare challenge detected for {request.url}, "
            f"attempting bypass with {downloader} "
            f"(attempt {bypass_count + 1}/{self.max_retries}, "
            f"chain[{chain_index}/{len(self._downloader_chain) - 1}])"
        )
        
        return self._create_bypass_request(request, bypass_count, downloader)

    def _handle_escalation(self, request: Request, response: Response) -> Optional[Request]:
        """Handle case where current stealth browser also hit CF challenge — escalate to next"""
        chain_index = request.meta.get('cloudflare_bypass_chain_index', 0)
        bypass_count = request.meta.get('cloudflare_bypass_count', 0)
        
        next_index = chain_index + 1
        
        if next_index >= len(self._downloader_chain):
            self.logger.warning(
                f"All downloaders in chain exhausted for {request.url}, "
                f"last tried: {self._downloader_chain[chain_index]}"
            )
            return None
        
        next_downloader = self._downloader_chain[next_index]
        self.logger.info(
            f"Escalating Cloudflare bypass for {request.url}: "
            f"{self._downloader_chain[chain_index]} → {next_downloader}"
        )
        
        return self._create_bypass_request(request, bypass_count, next_downloader, chain_index=next_index)

    def _create_bypass_request(
        self, 
        original_request: Request, 
        bypass_count: int, 
        downloader: str,
        chain_index: int = None
    ) -> Request:
        """Create bypass request"""
        retry_request = original_request.copy()
        
        if chain_index is None:
            chain_index = min(bypass_count, len(self._downloader_chain) - 1)
        
        retry_request.meta['cloudflare_bypass_count'] = bypass_count + 1
        retry_request.meta['cloudflare_bypass_attempted'] = True
        retry_request.meta['cloudflare_bypass_chain_index'] = chain_index
        retry_request.meta['use_dynamic_loader'] = True
        retry_request.meta['dynamic_downloader_type'] = downloader
            
        self.logger.debug(
            f"Created bypass request (attempt {bypass_count + 1}), "
            f"downloader={downloader}, chain_index={chain_index}"
        )
            
        return retry_request

    # ── Private: Cookie Management ──

    def _capture_cf_cookies(self, url: str, response: Response):
        """Capture Cloudflare cookies from successful response"""
        try:
            domain = urlparse(url).netloc.lower()
            cookies = {}
            
            # Extract from response headers
            set_cookie_headers = response.headers.get('Set-Cookie', '')
            if isinstance(set_cookie_headers, list):
                cookie_strs = set_cookie_headers
            else:
                cookie_strs = [set_cookie_headers] if set_cookie_headers else []
            
            for cookie_str in cookie_strs:
                for part in cookie_str.split(';'):
                    part = part.strip()
                    if '=' in part:
                        key, _, value = part.partition('=')
                        key = key.strip()
                        if key in self._cf_cookie_names:
                            cookies[key] = value
            
            if cookies:
                # Cache with 24h expiry
                self._cf_cookie_cache[domain] = {
                    'cookies': cookies,
                    'expires_at': time.time() + 86400,
                }
                self.logger.info(
                    f"Cached CF cookies for {domain}: "
                    f"{', '.join(cookies.keys())}"
                )
        except Exception as e:
            self.logger.debug(f"Failed to capture CF cookies: {e}")

    def _inject_cf_cookies(self, request: Request):
        """Inject cached CF cookies into request"""
        try:
            domain = urlparse(request.url).netloc.lower()
            cached = self._cf_cookie_cache.get(domain)
            
            if not cached:
                return
            
            # Check expiry
            if time.time() > cached['expires_at']:
                del self._cf_cookie_cache[domain]
                return
            
            # Inject cookies
            existing_cookies = request.cookies or {}
            for key, value in cached['cookies'].items():
                if key not in existing_cookies:
                    existing_cookies[key] = value
            
            if existing_cookies != request.cookies:
                request.cookies = existing_cookies
                self.logger.debug(f"Injected CF cookies for {domain}")
        except Exception:
            pass

    # ── Private: Domain Cache ──

    def _is_known_cloudflare_domain(self, url: str) -> bool:
        """Check if this is a known Cloudflare domain"""
        try:
            domain = urlparse(url).netloc.lower()
            return domain in self._cloudflare_domains
        except Exception:
            return False

    def _mark_cloudflare_domain(self, url: str):
        """Mark domain as needing Cloudflare bypass"""
        try:
            domain = urlparse(url).netloc.lower()
            self._cloudflare_domains.add(domain)
            self.logger.debug(f"Marked {domain} as Cloudflare-protected domain")
        except Exception:
            pass
