# -*- coding: UTF-8 -*-
"""
高级日志功能使用示例
展示如何在Crawlo项目中使用高级日志功能
"""

# 示例1: 基本使用
def basic_usage_example():
    """基本使用示例"""
    from crawlo.utils.advanced_log import get_logger
    
    # 获取日志记录器
    logger = get_logger('example.spider')
    
    # 记录不同级别的日志
    logger.debug("这是调试信息")
    logger.info("这是普通信息")
    logger.warning("这是警告信息")
    logger.error("这是错误信息")
    logger.critical("这是严重错误信息")


# 示例2: 结构化日志
def structured_logging_example():
    """结构化日志示例"""
    from crawlo.utils.advanced_log import get_structured_logger
    
    # 获取结构化日志记录器
    logger = get_structured_logger('example.spider')
    
    # 记录带有结构化数据的日志
    logger.info("爬取页面完成", 
                url="https://example.com", 
                status_code=200, 
                response_time=0.5)
    
    logger.error("页面爬取失败", 
                 url="https://example.com/error", 
                 status_code=404, 
                 retry_count=3)


# 示例3: 配置高级日志
def advanced_logging_configuration():
    """高级日志配置示例"""
    from crawlo.utils.advanced_log import AdvancedLoggerManager
    
    # 配置日志管理器
    AdvancedLoggerManager.configure(
        log_file='logs/advanced_example.log',
        log_level='DEBUG',
        log_format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        max_bytes=5 * 1024 * 1024,  # 5MB
        backup_count=3,
        json_logging=True  # 启用JSON格式日志
    )
    
    # 获取配置好的日志记录器
    logger = AdvancedLoggerManager.get_logger('advanced.example')
    logger.info("高级日志配置完成")


# 示例4: 在爬虫中使用
class ExampleSpider:
    """示例爬虫类"""
    
    def __init__(self):
        from crawlo.utils.advanced_log import get_logger, get_structured_logger
        self.logger = get_logger(f"{self.__class__.__name__}")
        self.structured_logger = get_structured_logger(f"{self.__class__.__name__}.structured")
    
    def parse(self, response):
        """解析响应"""
        # 使用普通日志
        self.logger.info(f"正在解析页面: {response.url}")
        
        # 使用结构化日志
        self.structured_logger.info("页面解析完成",
                                   url=response.url,
                                   status_code=response.status,
                                   parsed_items=5,
                                   parse_time=0.1)
        
        # 错误处理
        try:
            # 模拟处理逻辑
            pass
        except Exception as e:
            self.logger.error(f"解析页面时出错: {e}", exc_info=True)


# 示例5: 项目配置文件示例
def project_settings_example():
    """
    项目配置文件示例 (settings.py)
    
    # 启用高级日志功能
    ADVANCED_LOGGING_ENABLED = True
    
    # 日志文件配置
    LOG_FILE = 'logs/spider.log'
    LOG_LEVEL = 'INFO'
    LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT = 5
    LOG_JSON_FORMAT = False  # 设置为True启用JSON格式
    
    # 启用日志监控
    LOG_MONITOR_ENABLED = True
    LOG_MONITOR_INTERVAL = 30
    LOG_MONITOR_DETAILED_STATS = True
    
    # 添加扩展
    EXTENSIONS = [
        'crawlo.extension.log_interval.LogIntervalExtension',
        'crawlo.extension.log_stats.LogStats',
        'crawlo.extension.advanced_logging_extension.AdvancedLoggingExtension',
        'crawlo.extension.log_monitor.LogMonitorExtension',
    ]
    """
    pass


if __name__ == '__main__':
    # 运行示例
    basic_usage_example()
    structured_logging_example()
    advanced_logging_configuration()
    
    # 创建示例爬虫
    spider = ExampleSpider()
    print("高级日志功能示例运行完成")