# -*- coding: UTF-8 -*-
"""最小配置：只做两件事——找爬虫、输出日志。"""

SPIDER_MODULES = ["simple_quickstart.spiders"]
PIPELINES = {"simple_quickstart.pipelines.JsonlPipeline": 300}
LOG_LEVEL = "INFO"
