#!/usr/bin/python
# -*- coding:UTF-8 -*-

VERSION = 1.0

# 并发数
CONCURRENCY = 8

# 下载超时时长
DOWNLOAD_TIMEOUT = 60

INTERVAL = 5

# --------------------------------------------------- delay ------------------------------------------------------------
# 下载延迟，默认关闭
DOWNLOAD_DELAY = 0
# 下载延迟范围
RANDOM_RANGE = (0.75, 1.25)
# 是否需要随机
RANDOMNESS = True

# --------------------------------------------------- retry ------------------------------------------------------------
MAX_RETRY_TIMES = 2
IGNORE_HTTP_CODES = [403, 404]
RETRY_HTTP_CODES = [408, 429, 500, 502, 503, 504, 522, 524]
# 允许通过的状态码
ALLOWED_CODES = []

STATS_DUMP = True
# ssl 验证
VERIFY_SSL = True
# 是否使用同一个session
USE_SESSION = True
# 日志级别
LOG_LEVEL = 'DEBUG'
# 选择下载器
DOWNLOADER = "crawlo.downloader.aiohttp_downloader.AioHttpDownloader"  # HttpXDownloader

EXTENSIONS = []
