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

    async def _inject_stealth_scripts(self, page: 'Page', request=None):
        """
        Inject anti-detection scripts

        Inject different levels of anti-detection scripts based on stealth_level:
        - none: No scripts injected
        - basic: Only hide webdriver identifier
        - advanced: Full-chain fingerprint forgery (Canvas, WebGL, AudioContext, etc.)

        :param page: Playwright Page 对象
        :param request: crawlo Request（可选）。meta['playwright_stealth_level']
            可按请求覆盖全局 stealth 级别。注意不要使用 ``page.request``——
            那是 Playwright 的 APIRequestContext，没有 meta 属性。
        """
        try:
            # If stealth_level is none, do not inject scripts
            if self.stealth_level == 'none':
                self.logger.debug("Stealth level is 'none', skipping anti-detection scripts")
                return

            # Get request-level stealth_level (higher priority than global config)
            request_stealth_level = self.stealth_level
            if request is not None:
                request_stealth_level = request.meta.get(
                    'playwright_stealth_level', self.stealth_level
                )

            # Get scripts from stealth_scripts module
            stealth_script = get_stealth_scripts(request_stealth_level)

            if stealth_script:
                await page.add_init_script(stealth_script)
                self.logger.debug(f"Injected stealth scripts (level: {request_stealth_level})")
            else:
                self.logger.debug("No stealth scripts to inject (level: none)")

        except Exception as e:
            self.logger.warning(f"Failed to inject stealth scripts: {e}")
