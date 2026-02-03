# -*- coding: UTF-8 -*-
"""
listed_companies_market_value_info 项目配置文件
=============================
基于 Crawlo 框架的爬虫项目配置。

此配置使用 CrawloConfig.auto() 工厂方法创建自动检测模式配置，
框架会自动检测Redis可用性，可用则使用分布式模式，否则使用单机模式。
"""

import os
from crawlo.config import CrawloConfig

# 获取示例项目的根目录（上一级目录，即run.py所在的位置）
# 当前文件路径: .../examples/listed_companies_market_value_info/listed_companies_market_value_info/settings.py
# 项目根目录: .../examples/listed_companies_market_value_info/
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 使用自动检测模式配置工厂创建配置
config = CrawloConfig.standalone(
    project_name='listed_companies_market_value_info',
    concurrency=8,
    download_delay=1.0
)

# 将配置转换为当前模块的全局变量
locals().update(config.to_dict())

# =================================== 爬虫配置 ===================================

# 爬虫模块配置
SPIDER_MODULES = ['listed_companies_market_value_info.spiders']

# 默认请求头
# DEFAULT_REQUEST_HEADERS = {}

# 允许的域名
# ALLOWED_DOMAINS = []

# 数据管道
# 如需添加自定义管道，请取消注释并添加
# PIPELINES = [
#     'crawlo.pipelines.mysql_pipeline.AsyncmyMySQLPipeline',  # MySQL 存储（使用asyncmy异步库）
#     # 'listed_companies_market_value_info.pipelines.CustomPipeline',  # 用户自定义管道示例
# ]

# =================================== 系统配置 ===================================
# 扩展组件
# 如需添加自定义扩展，请取消注释并添加
# EXTENSIONS = [
#     # 'listed_companies_market_value_info.extensions.CustomExtension',  # 用户自定义扩展示例
# ]

# 中间件
# 如需添加自定义中间件，请取消注释并添加
MIDDLEWARES = {
    'listed_companies_market_value_info.middlewares.ProxyMiddleware': 50,
}

# 日志配置
LOG_LEVEL = 'INFO'#'DEBUG'
LOG_FILE = os.path.join(_PROJECT_ROOT, 'logs', 'listed_companies_market_value_info.log')
LOG_ENCODING = 'utf-8'  # 明确指定日志文件编码
LOG_MAX_BYTES = 0  # 日志轮转功能已取消，文件会持续增長
LOG_BACKUP_COUNT = 0  # 日志轮转功能已取消



# =================================== 数据库配置 ===================================

# Redis配置
REDIS_HOST = '127.0.0.1'
REDIS_PORT = 6379
REDIS_PASSWORD = ''
REDIS_DB = 0

# MySQL配置
MYSQL_HOST = '127.0.0.1'
MYSQL_PORT = 3306
MYSQL_USER = 'root'
MYSQL_PASSWORD = 'oscar&0503'
MYSQL_DB = 'crawlo_db'
MYSQL_TABLE = 'listed_companies_market_value_info'

# MySQL 冲突处理策略（三者互斥，按优先级生效）
MYSQL_UPDATE_COLUMNS = ()      # 优先级最高：主键冲突时更新指定列，使用 ON DUPLICATE KEY UPDATE
MYSQL_AUTO_UPDATE = False      # 优先级中等：是否使用 REPLACE INTO（完全覆盖已存在记录）
MYSQL_INSERT_IGNORE = True    # 优先级最低：是否使用 INSERT IGNORE（忽略重复数据）
MYSQL_PREFER_ALIAS_SYNTAX = True      # 是否优先使用 AS `alias` 语法，False 则使用 VALUES() 语法
MYSQL_BATCH_SIZE = 100
MYSQL_USE_BATCH = False  # 是否启用批量插入

# MongoDB配置
# MONGO_URI = 'mongodb://localhost:27017'
# MONGO_DATABASE = 'listed_companies_market_value_info_db'
# MONGO_COLLECTION = 'listed_companies_market_value_info_items'
# MONGO_MAX_POOL_SIZE = 200
# MONGO_MIN_POOL_SIZE = 20
# MONGO_BATCH_SIZE = 100  # 批量插入条数
# MONGO_USE_BATCH = False  # 是否启用批量插入

# =================================== 定时任务配置 ===================================

# 启用定时任务 - 默认关闭
SCHEDULER_ENABLED = False

# 定时任务配置
SCHEDULER_JOBS = [
    {
        'spider': 'a_market_value',  # 爬虫名称（对应spider的name属性）
        'cron': '1 15 * * *',       # 每2分钟执行一次
        'enabled': True,              # 任务启用状态
        'priority': 10,               # 任务优先级
        'max_retries': 3,             # 最大重试次数
        'retry_delay': 60,            # 重试延迟（秒）
        'args': {},                  # 传递给爬虫的参数
        'kwargs': {}                  # 传递给爬虫的额外参数
    },
    {
        'spider': 'a_market_value',  # 爬虫名称
        'cron': '0 17 * * *',         # 每天凌晨2点执行
        'enabled': True,              # 任务启用状态
        'priority': 20,               # 任务优先级
        'max_retries': 2,             # 最大重试次数
        'retry_delay': 120,           # 重试延迟（秒）
        'args': {'daily': True},      # 传递给爬虫的参数
        'kwargs': {}                  # 传递给爬虫的额外参数
    }
]

# 关键配置参数（用户可能需要调整）
SCHEDULER_CHECK_INTERVAL = 1           # 调度器检查间隔（秒）
SCHEDULER_MAX_CONCURRENT = 3           # 最大并发任务数
SCHEDULER_JOB_TIMEOUT = 3600           # 单个任务超时时间（秒）
SCHEDULER_RESOURCE_MONITOR_ENABLED = True  # 是否启用资源监控
SCHEDULER_RESOURCE_CHECK_INTERVAL = 300    # 资源检查间隔（秒）
SCHEDULER_RESOURCE_LEAK_THRESHOLD = 3600   # 资源泄露检测阈值（秒）

# =================================== 资源监控配置 ===================================

# 内存监控配置
# MEMORY_MONITOR_ENABLED = False  # 是否启用内存监控
# MEMORY_MONITOR_INTERVAL = 60  # 内存监控检查间隔（秒）
# MEMORY_WARNING_THRESHOLD = 80.0  # 内存使用率警告阈值（百分比）
# MEMORY_CRITICAL_THRESHOLD = 90.0  # 内存使用率严重阈值（百分比）

# MySQL监控配置
# MYSQL_MONITOR_ENABLED = False  # 是否启用MySQL监控
# MYSQL_MONITOR_INTERVAL = 120  # MySQL监控检查间隔（秒）

# Redis监控配置
# REDIS_MONITOR_ENABLED = False  # 是否启用Redis监控
# REDIS_MONITOR_INTERVAL = 120  # Redis监控检查间隔（秒）

# 输出配置
OUTPUT_DIR = 'output'

# =================================== 代理配置 ===================================

# 简单代理（SimpleProxyMiddleware）
# 配置代理列表后中间件自动启用
# PROXY_LIST = ["http://proxy1:8080", "http://proxy2:8080"]

# 动态代理（ProxyMiddleware）
# 配置代理API URL后中间件自动启用
PROXY_API_URL = 'http://123.56.42.142:5000/proxy/getitem/'

STOCKS = [
'000001.SZ-平安银行',
'000002.SZ-万  科Ａ',
'000004.SZ-*ST国华',
'000006.SZ-深振业Ａ',
'000007.SZ-全新好',
'000008.SZ-神州高铁',
'000009.SZ-中国宝安',
'000010.SZ-美丽生态',
'000011.SZ-深物业A',
'000012.SZ-南  玻Ａ',
'000014.SZ-沙河股份',
'000016.SZ-深康佳Ａ',
'000017.SZ-深中华A',
'000019.SZ-深粮控股',
'000020.SZ-深华发Ａ',
'000021.SZ-深科技',
'000025.SZ-特  力Ａ',
'000026.SZ-飞亚达',
'000027.SZ-深圳能源',
'000028.SZ-国药一致',
'000029.SZ-深深房Ａ',
'000030.SZ-富奥股份',
'000031.SZ-大悦城',
'000032.SZ-深桑达Ａ',
'000034.SZ-神州数码',
'000035.SZ-中国天楹',
'000036.SZ-华联控股',
'000037.SZ-深南电A',
'000039.SZ-中集集团',
'000040.SZ-ST旭蓝',
'000042.SZ-中洲控股',
'000045.SZ-深纺织Ａ',
'000048.SZ-京基智农',
'000049.SZ-德赛电池',
'000050.SZ-深天马Ａ',
'000055.SZ-方大集团',
'000056.SZ-皇庭国际',
'000058.SZ-深 赛 格',
'000059.SZ-华锦股份',
'000060.SZ-中金岭南',
'000061.SZ-农 产 品',
'000062.SZ-深圳华强',
'000063.SZ-中兴通讯',
'000065.SZ-北方国际',
'000066.SZ-中国长城',
'000068.SZ-华控赛格',
'000069.SZ-华侨城Ａ',
'000070.SZ-特发信息',
'000078.SZ-海王生物',
'000088.SZ-盐 田 港',
'000089.SZ-深圳机场',
'000090.SZ-天健集团',
'000096.SZ-广聚能源',
'000099.SZ-中信海直',
'000100.SZ-TCL科技',
'000151.SZ-中成股份',
'000153.SZ-丰原药业',
'000155.SZ-川能动力',
'000156.SZ-华数传媒',
'000157.SZ-中联重科',
'000158.SZ-常山北明',
'000159.SZ-国际实业',
'000166.SZ-申万宏源',
'000301.SZ-东方盛虹',
'000333.SZ-美的集团',
'000338.SZ-潍柴动力',
'000400.SZ-许继电气',
'000401.SZ-金隅冀东',
'000402.SZ-金 融 街',
'000403.SZ-派林生物',
'000404.SZ-长虹华意',
'000407.SZ-胜利股份',
'000408.SZ-藏格矿业',
'000409.SZ-云鼎科技',
'000410.SZ-沈阳机床',
'000411.SZ-英特集团',
'000415.SZ-渤海租赁',
'000417.SZ-合百集团',
'000419.SZ-通程控股',
'000420.SZ-吉林化纤',
'000421.SZ-南京公用',
'000422.SZ-湖北宜化',
'000423.SZ-东阿阿胶',
'000425.SZ-徐工机械',
'000426.SZ-兴业银锡',
'000428.SZ-华天酒店',
'000429.SZ-粤高速Ａ',
'000430.SZ-*ST张股',
'000488.SZ-ST晨鸣',
'000498.SZ-山东路桥',
'000501.SZ-武商集团',
'000503.SZ-国新健康',
'000504.SZ-*ST生物',
'000505.SZ-京粮控股',
'000506.SZ-招金黄金',
'000507.SZ-珠海港',
'000509.SZ-华塑控股',
'000510.SZ-新金路',
'000513.SZ-丽珠集团',
'000514.SZ-渝 开 发',
'000516.SZ-国际医学',
'000517.SZ-荣安地产',
'000518.SZ-*ST四环',
'000519.SZ-中兵红箭',
'000520.SZ-凤凰航运',
'000521.SZ-长虹美菱',
'000523.SZ-红棉股份',
'000524.SZ-岭南控股',
'000525.SZ-红太阳',
'000526.SZ-学大教育',
'000528.SZ-柳    工',
'000529.SZ-广弘控股',
'000530.SZ-冰山冷热',
'000531.SZ-穗恒运Ａ',
'000532.SZ-华金资本',
'000533.SZ-顺钠股份',
'000534.SZ-万泽股份',
'000536.SZ-华映科技',
'000537.SZ-绿发电力',
'000538.SZ-云南白药',
'000539.SZ-粤电力Ａ',
'000541.SZ-佛山照明',
'000543.SZ-皖能电力',
'000544.SZ-中原环保',
'000545.SZ-金浦钛业',
'000546.SZ-金圆股份',
'000547.SZ-航天发展',
'000548.SZ-湖南投资',
'000550.SZ-江铃汽车',
'000551.SZ-创元科技',
'000552.SZ-甘肃能化',
'000553.SZ-安道麦A',
'000554.SZ-泰山石油',
'000555.SZ-神州信息',
'000557.SZ-西部创业',
'000558.SZ-天府文旅',
'000559.SZ-万向钱潮',
'000560.SZ-我爱我家',
'000561.SZ-烽火电子',
'000563.SZ-陕国投Ａ',
'000564.SZ-供销大集',
'000565.SZ-渝三峡Ａ',
'000566.SZ-海南海药',
'000567.SZ-海德股份',
'000568.SZ-泸州老窖',
'000570.SZ-苏常柴Ａ',
'000571.SZ-新大洲A',
'000572.SZ-海马汽车',
'000573.SZ-粤宏远Ａ',
'000576.SZ-甘化科工',
'000581.SZ-威孚高科',
'000582.SZ-北部湾港',
'000584.SZ-*ST工智',
'000586.SZ-汇源通信',
'000589.SZ-贵州轮胎',
'000590.SZ-古汉医药',
'000591.SZ-太阳能',
'000592.SZ-平潭发展',
'000593.SZ-德龙汇能',
'000595.SZ-*ST宝实',
'000596.SZ-古井贡酒',
'000597.SZ-东北制药',
'000598.SZ-兴蓉环境',
'000599.SZ-青岛双星',
'000600.SZ-建投能源',
'000601.SZ-韶能股份',
'000603.SZ-盛达资源',
'000605.SZ-渤海股份',
'000607.SZ-华媒控股',
'000608.SZ-*ST阳光',
'000609.SZ-ST中迪',
'000610.SZ-西安旅游',
'000612.SZ-焦作万方',
'000615.SZ-*ST美谷',
'000617.SZ-中油资本',
'000619.SZ-海螺新材',
'000620.SZ-盈新发展',
'000622.SZ-*ST恒立',
'000623.SZ-吉林敖东',
'000625.SZ-长安汽车',
'000626.SZ-远大控股',
'000627.SZ-*ST天茂',
]
