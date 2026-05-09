#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
OffsiteMiddleware
Filters out requests that are outside the allowed domains
"""
import re
from urllib.parse import urlparse

from crawlo.logging import get_logger
from crawlo.exceptions import IgnoreRequestError


class OffsiteMiddleware:
    """
    OffsiteMiddleware
    Filters out requests outside the allowed domains to prevent crawling unrelated sites
    """

    def __init__(self, stats, allowed_domains=None):
        self.logger = get_logger(self.__class__.__name__)
        self.stats = stats
        self.allowed_domains = allowed_domains or []

    @classmethod
    def create_instance(cls, crawler):
        """
        Create middleware instance
        Retrieves allowed domains list from crawler settings
        """
        # Priority: Spider's allowed_domains > Global ALLOWED_DOMAINS setting
        allowed_domains = []
        
        # Check if spider instance has allowed_domains attribute
        if hasattr(crawler, 'spider') and crawler.spider and hasattr(crawler.spider, 'allowed_domains'):
            allowed_domains = getattr(crawler.spider, 'allowed_domains', [])
        
        # Fallback to global settings if spider doesn't have allowed_domains
        if not allowed_domains:
            allowed_domains = crawler.settings.get_list('ALLOWED_DOMAINS')
        
        # Disable middleware if no allowed domains configured
        if not allowed_domains:
            from crawlo.exceptions import NotConfiguredError
            raise NotConfiguredError("ALLOWED_DOMAINS not configured, OffsiteMiddleware disabled")
            
        o = cls(
            stats=crawler.stats,
            allowed_domains=allowed_domains
        )
        
        # Compile domain regex patterns for better performance
        o._compile_domains()
        
        # Use middleware's own logger instead of crawler.logger
        o.logger.debug(f"OffsiteMiddleware enabled, allowed domains: {allowed_domains}")
        return o

    def _compile_domains(self):
        """
        Compile domain regex patterns for efficient matching
        """
        self._domain_regexes = []
        for domain in self.allowed_domains:
            # Escape special characters in domain
            escaped_domain = re.escape(domain)
            # Create regex pattern matching domain and subdomains
            regex = re.compile(r'(^|.*\.)' + escaped_domain + '$', re.IGNORECASE)
            self._domain_regexes.append(regex)

    def _is_offsite_request(self, request):
        """
        Check if request is offsite (outside allowed domains)
        """
        try:
            parsed_url = urlparse(request.url)
            hostname = parsed_url.hostname
            
            if not hostname:
                return True  # Invalid URL
                
            # Check if hostname matches any allowed domain
            for regex in self._domain_regexes:
                if regex.match(hostname):
                    return False  # Matches allowed domain
                    
            return True  # No match found
        except Exception:
            # URL parsing failed, treat as offsite
            return True

    async def process_request(self, request, spider):
        """
        Process request, filter offsite requests
        """
        if self._is_offsite_request(request):
            # Record filtered request
            self.stats.inc_value('offsite_request_count')
            
            # Record filtered domain
            try:
                parsed_url = urlparse(request.url)
                hostname = parsed_url.hostname or "unknown"
                self.stats.inc_value(f'offsite_request_count/{hostname}')
            except:
                self.stats.inc_value('offsite_request_count/invalid_url')
            
            self.logger.info(f"Filtered offsite request: {request.url}")
            
            # Raise exception to ignore this request
            # Optimization: only include reason to avoid generating separate stats per URL
            raise IgnoreRequestError("Offsite request filtered")
            
        return None

    def process_exception(self, request, exception, spider):
        """
        Handle exception
        """
        # If this is IgnoreRequestError that we raised, handle it
        if isinstance(exception, IgnoreRequestError) and "Offsite request filtered" in str(exception):
            self.logger.debug(f"Filtered offsite request: {request.url}")
            return None  # Exception has been handled
        return None