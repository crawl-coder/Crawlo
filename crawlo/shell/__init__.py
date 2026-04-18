#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Crawlo Shell - 交互式终端
========================
提供类似 scrapy shell 的实时交互环境，用于调试选择器、测试动态渲染和验证逻辑。

核心功能：
- fetch(url): 快速抓取页面
- response.css() / response.xpath(): 实时测试选择器
- view(response): 在浏览器中预览页面
- 支持 IPython（await 异步代码）和原生 Console 降级

使用方式：
    crawlo shell                    # 启动空 Shell
    crawlo shell https://example.com # 启动并预抓取 URL
"""

from crawlo.shell.core import CrawloShell

__all__ = ['CrawloShell']
