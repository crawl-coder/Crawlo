from crawlo.exceptions import NotConfigured
from crawlo.utils.log import get_logger
from crawlo.utils.log import LoggerManager


class CustomLoggerExtension:
    """
    日志系统初始化扩展
    遵循与 ExtensionManager 一致的接口规范：使用 create_instance
    """

    def __init__(self, settings):
        self.settings = settings
        # 初始化全局日志配置
        LoggerManager.configure(settings)

    @classmethod
    def create_instance(cls, crawler, *args, **kwargs):
        """
        工厂方法：兼容 ExtensionManager 的创建方式
        被 ExtensionManager 调用
        """
        # 可以通过 settings 控制是否启用
        if not crawler.settings.get('LOG_FILE') and not crawler.settings.get('LOG_ENABLE_CUSTOM'):
            raise NotConfigured("CustomLoggerExtension: LOG_FILE not set and LOG_ENABLE_CUSTOM=False")

        return cls(crawler.settings)

    def spider_opened(self, spider):
        logger = get_logger(__name__)
        logger.info(
            f"CustomLoggerExtension: Logging initialized. "
            f"LOG_FILE={self.settings.get('LOG_FILE')}, "
            f"LOG_LEVEL={self.settings.get('LOG_LEVEL')}"
        )