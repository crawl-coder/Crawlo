#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
反检测脚本模块
===============

提供多种反检测脚本，用于隐藏浏览器自动化特征：
- navigator：隐藏 webdriver 标识
- chrome_runtime：Chrome Runtime API 伪装
- webgl：WebGL 指纹伪造
- canvas：Canvas 指纹噪声
- drissionpage：DrissionPage 专用反检测脚本

脚本来源与更新：
- 主要参考: puppeteer-extra-plugin-stealth (https://github.com/berstend/puppeteer-extra)
- 部分参考: scrapling-stealth (https://github.com/ixpeeta/scrapling-stealth)
- DrissionPage 脚本: 来自 DrissionPage 内置反检测模块

注意: 反检测脚本需要持续更新以应对网站不断变化的检测技术。
建议定期检查上游仓库的更新，并同步更新本模块中的脚本。
"""

from .navigator import NAVIGATOR_STEALTH_SCRIPT
from .chrome_runtime import CHROME_RUNTIME_SCRIPT
from .webgl import WEBGL_STEALTH_SCRIPT
from .canvas import CANVAS_STEALTH_SCRIPT
from .drissionpage import DRISSIONPAGE_STEALTH_SCRIPT, DRISSIONPAGE_ADVANCED_SCRIPT, get_drissionpage_stealth_script

__all__ = [
    'NAVIGATOR_STEALTH_SCRIPT',
    'CHROME_RUNTIME_SCRIPT',
    'WEBGL_STEALTH_SCRIPT',
    'CANVAS_STEALTH_SCRIPT',
    'DRISSIONPAGE_STEALTH_SCRIPT',
    'DRISSIONPAGE_ADVANCED_SCRIPT',
    'get_drissionpage_stealth_script',
    'get_stealth_scripts',
]


def get_stealth_scripts(level: str = 'basic') -> str:
    """
    根据反检测级别获取脚本组合（Playwright 专用）
    
    Args:
        level: 'none' | 'basic' | 'advanced'
        
    Returns:
        组合后的脚本字符串
    """
    if level == 'none':
        return ''
    
    scripts = [NAVIGATOR_STEALTH_SCRIPT]
    
    if level == 'advanced':
        scripts.extend([
            CHROME_RUNTIME_SCRIPT,
            WEBGL_STEALTH_SCRIPT,
            CANVAS_STEALTH_SCRIPT,
        ])
    
    return '\n\n'.join(scripts)
