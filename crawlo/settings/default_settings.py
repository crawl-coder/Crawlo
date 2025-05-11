#!/usr/bin/python
# -*- coding:UTF-8 -*-
# 并发数
CONCURRENCY = 8
# 下载超时时长
DOWNLOAD_TIMEOUT = 60
# ssl 验证
VERIFY_SSL = True
# 是否使用同一个session
USE_SESSION = True
# 日志级别
LOG_LEVEL = 'DEBUG'
# 选择下载器
DOWNLOADER = "crawlo.downloader.aiohttp_downloader.AioHttpDownloader"  # HttpXDownloader
