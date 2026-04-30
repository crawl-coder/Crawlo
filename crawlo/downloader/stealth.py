#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Playwright 反检测 Mixin

提取自 PlaywrightDownloader，包含反检测脚本注入逻辑。
"""
from crawlo.downloader.stealth_scripts import get_stealth_scripts


class StealthMixin:
    """反检测脚本注入 Mixin"""

    async def _inject_stealth_scripts(self, page):
        """
        注入反检测脚本
        
        根据 stealth_level 注入不同级别的反检测脚本：
        - none: 不注入任何脚本
        - basic: 仅隐藏 webdriver 标识
        - advanced: 全链路指纹伪造（Canvas、WebGL、AudioContext 等）
        """
        try:
            # 如果 stealth_level 为 none，则不注入脚本
            if self.stealth_level == 'none':
                self.logger.debug("Stealth level is 'none', skipping anti-detection scripts")
                return
            
            # 获取请求级别的 stealth_level（优先级高于全局配置）
            request_stealth_level = page.request.meta.get('playwright_stealth_level', self.stealth_level) if hasattr(page, 'request') and page.request else self.stealth_level
            
            # 从 stealth_scripts 模块获取脚本
            stealth_script = get_stealth_scripts(request_stealth_level)
            
            if stealth_script:
                await page.add_init_script(stealth_script)
                self.logger.debug(f"Injected stealth scripts (level: {request_stealth_level})")
            else:
                self.logger.debug("No stealth scripts to inject (level: none)")
                
        except Exception as e:
            self.logger.warning(f"Failed to inject stealth scripts: {e}")
