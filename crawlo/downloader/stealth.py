#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Playwright Anti-Detection Mixin

Extracted from PlaywrightDownloader, contains anti-detection script injection logic.
"""
from typing import TYPE_CHECKING
from crawlo.downloader.stealth_scripts import get_stealth_scripts

if TYPE_CHECKING:
    from playwright.async_api import Page


class StealthMixin:
    """Anti-detection script injection Mixin"""

    async def _inject_stealth_scripts(self, page: 'Page'):
        """
        Inject anti-detection scripts
        
        Inject different levels of anti-detection scripts based on stealth_level:
        - none: No scripts injected
        - basic: Only hide webdriver identifier
        - advanced: Full-chain fingerprint forgery (Canvas, WebGL, AudioContext, etc.)
        """
        try:
            # If stealth_level is none, do not inject scripts
            if self.stealth_level == 'none':
                self.logger.debug("Stealth level is 'none', skipping anti-detection scripts")
                return
            
            # Get request-level stealth_level (higher priority than global config)
            request_stealth_level = page.request.meta.get('playwright_stealth_level', self.stealth_level) if hasattr(page, 'request') and page.request else self.stealth_level
            
            # Get scripts from stealth_scripts module
            stealth_script = get_stealth_scripts(request_stealth_level)
            
            if stealth_script:
                await page.add_init_script(stealth_script)
                self.logger.debug(f"Injected stealth scripts (level: {request_stealth_level})")
            else:
                self.logger.debug("No stealth scripts to inject (level: none)")
                
        except Exception as e:
            self.logger.warning(f"Failed to inject stealth scripts: {e}")
