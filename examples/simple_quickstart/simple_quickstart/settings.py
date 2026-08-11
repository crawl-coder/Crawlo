# -*- coding: UTF-8 -*-
"""最小配置：只做两件事——找爬虫、输出日志。"""

SPIDER_MODULES = ["simple_quickstart.spiders"]
PIPELINES = {"simple_quickstart.pipelines.JsonlPipeline": 300}
LOG_LEVEL = "INFO"

# 日志文件走框架默认：logs/simple_quickstart.log（固定文件名，按天轮转，
# 保留 7 份，UTF-8）。如需自定义，按 crawlo 模板在下方添加：
# LOG_FILE = 'logs/simple_quickstart.log'
# LOG_FILE_WHEN = 'midnight'        # 轮转周期：每天 0 点（可改 S/M/H/D）
# LOG_FILE_BACKUP_COUNT = 7         # 保留 7 份轮转文件
