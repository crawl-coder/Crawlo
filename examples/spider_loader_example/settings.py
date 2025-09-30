# -*- coding: utf-8 -*-

# 项目名称
PROJECT_NAME = 'spider_loader_example'

# 并发数
CONCURRENCY = 4

# 爬虫模块配置
SPIDER_MODULES = [
    'spider_loader_example.spiders',
    # 可以添加多个爬虫模块目录
    # 'spider_loader_example.more_spiders',
]

# 是否在爬虫加载出错时只警告而不报错
SPIDER_LOADER_WARN_ONLY = True

# 日志级别
LOG_LEVEL = 'INFO'

# 下载延迟
DOWNLOAD_DELAY = 1.0

# 是否启用随机延迟
RANDOMNESS = True

# 请求头
DEFAULT_REQUEST_HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en',
}

# 中间件
MIDDLEWARES = [
    'crawlo.middleware.download_delay.DownloadDelayMiddleware',
    'crawlo.middleware.default_header.DefaultHeaderMiddleware',
]

# 管道
PIPELINES = [
    'crawlo.pipelines.console_pipeline.ConsolePipeline',
]