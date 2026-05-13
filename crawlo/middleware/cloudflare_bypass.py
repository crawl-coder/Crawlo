#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Cloudflare Bypass Middleware
=============================
Automatically detect and bypass Cloudflare challenge pages.

Features:
- Detect Cloudflare challenge pages (403/503 + signatures)
- Auto fallback to stealth browser for retry
- Support multiple stealth browsers (camoufox, playwright, drissionpage)
- Smart retry mechanism

Usage:
# settings.py
# Middleware is already registered in framework, no manual configuration needed
# Only configure the downloader type for bypass
CLOUDFLARE_BYPASS_DOWNLOADER = 'camoufox'  # or 'playwright', 'drissionpage'
"""

import re
from typing import Optional, Union
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
    1. Use stealth browser (camoufox recommended) to retry
    2. Support request-level configuration for different browsers
    """
    
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
        self.default_downloader = crawler.settings.get("CLOUDFLARE_BYPASS_DOWNLOADER", "camoufox")
        
        # Cache known Cloudflare domains
        self._cloudflare_domains = set()
        
        # Downloader instance cache (lazy initialization)
        self._bypass_downloader = None
        
        # Pre-compile regex patterns for performance
        self._compiled_signatures = [
            re.compile(pattern, re.IGNORECASE) 
            for pattern in self.CLOUDFLARE_SIGNATURE_PATTERNS
        ]
        
        self.logger.debug(f"CloudflareBypassMiddleware initialized (downloader={self.default_downloader})")

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
                self.default_downloader
            )
        
        return None

    async def process_response(self, request: Request, response: Response, spider) -> Union[Request, Response]:
        """Post-process response"""
        # Check if this is a Cloudflare challenge page
        if not self._is_cloudflare_challenge(response):
            return response
        
        # Check if max retries reached
        bypass_count = request.meta.get('cloudflare_bypass_count', 0)
        if bypass_count >= self.max_retries:
            self.logger.warning(f"Max Cloudflare bypass retries reached for {request.url}")
            return response
        
        # Mark as Cloudflare domain
        self._mark_cloudflare_domain(request.url)
        
        # Create new request with stealth browser
        self.logger.info(f"Cloudflare challenge detected for {request.url}, attempting bypass with {self.default_downloader}")
        
        # Create retry request
        retry_request = self._create_bypass_request(request, bypass_count)
        
        return retry_request

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
            bypass_count = request.meta.get('cloudflare_bypass_count', 0)
            if bypass_count < self.max_retries:
                self.logger.info(f"Cloudflare-related exception for {request.url}, attempting bypass")
                return self._create_bypass_request(request, bypass_count)
        
        return None

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
        """
        Detect Cloudflare Turnstile challenge type
        
        Args:
            page_content: Page content
            
        Returns:
            Challenge type: 'non-interactive', 'managed', 'interactive', 'embedded' or None
        """
        try:
            content = page_content if isinstance(page_content, str) else page_content.decode('utf-8', errors='ignore')
            
            # Check Turnstile type
            for ctype in self.CHALLENGE_TYPES:
                if f"cType: '{ctype}'" in content:
                    return ctype
            
            # Check if embedded Turnstile
            if 'challenges.cloudflare.com/turnstile' in content:
                return "embedded"
            
            return None
        except Exception:
            return None

    def _create_bypass_request(self, original_request: Request, bypass_count: int) -> Request:
        """Create bypass request"""
        # Copy original request
        retry_request = original_request.copy()
            
        # Update meta
        retry_request.meta['cloudflare_bypass_count'] = bypass_count + 1
        retry_request.meta['cloudflare_bypass_attempted'] = True
        retry_request.meta['use_dynamic_loader'] = True
        retry_request.meta['dynamic_downloader_type'] = retry_request.meta.get(
            'cloudflare_bypass_downloader', 
            self.default_downloader
        )
            
        self.logger.debug(
            f"Created bypass request (attempt {bypass_count + 1}/{self.max_retries}) "
            f"using {retry_request.meta['dynamic_downloader_type']}"
        )
            
        return retry_request

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
