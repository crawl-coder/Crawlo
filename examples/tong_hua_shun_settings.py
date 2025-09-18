# 同花顺爬虫配置示例
# ==================

# 项目基本信息
PROJECT_NAME = 'tong_hua_shun_crawler'

# 并发数
CONCURRENCY = 1

# 日志配置
LOG_LEVEL = 'INFO'
LOG_FILE = 'logs/tong_hua_shun.log'

# 下载延迟配置
DOWNLOAD_DELAY = 2
RANDOMNESS = True

# 请求头配置
DEFAULT_REQUEST_HEADERS = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
    "cache-control": "no-cache",
    "pragma": "no-cache",
    "priority": "u=0, i",
    "sec-ch-ua": '"Chromium";v="140", "Not=A?Brand";v="24", "Google Chrome";v="140"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "document",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "none",
    "sec-fetch-user": "?1",
    "upgrade-insecure-requests": "1",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
}

# 代理配置
PROXY_ENABLED = True
PROXY_API_URL = 'http://test.proxy.api:8080/proxy/getitem/'
PROXY_EXTRACTOR = 'proxy'
PROXY_REFRESH_INTERVAL = 60
PROXY_API_TIMEOUT = 10
PROXY_POOL_SIZE = 3
PROXY_HEALTH_CHECK_THRESHOLD = 0.5

# 中间件配置
MIDDLEWARES = [
    'crawlo.middleware.request_ignore.RequestIgnoreMiddleware',
    'crawlo.middleware.download_delay.DownloadDelayMiddleware',
    'crawlo.middleware.default_header.DefaultHeaderMiddleware',
    'crawlo.middleware.proxy.ProxyMiddleware',
    'crawlo.middleware.retry.RetryMiddleware',
    'crawlo.middleware.response_code.ResponseCodeMiddleware',
    'crawlo.middleware.response_filter.ResponseFilterMiddleware',
]

# 管道配置
PIPELINES = [
    'crawlo.pipelines.console_pipeline.ConsolePipeline',
]

# 其他配置
DOWNLOAD_TIMEOUT = 30