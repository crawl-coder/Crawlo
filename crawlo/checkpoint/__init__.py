#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Crawlo 检查点模块
基于检查点的爬取持久化，支持 Ctrl+C 优雅关闭后从断点续爬。
"""
from crawlo.checkpoint.manager import CheckpointManager

__all__ = ['CheckpointManager']
