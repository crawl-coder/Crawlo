from typing import Any
from crawlo.exceptions import NotConfigured
from crawlo.utils.log import get_logger
from crawlo.utils.log import LoggerManager


class CustomLoggerExtension:
    """
    日志系统初始化扩展
    遵循与 ExtensionManager 一致的接口规范：使用 create_instance
    """

    def __init__(self, settings: Any):
        self.settings = settings
        # 初始化全局日志配置
        LoggerManager.configure(settings)

    @classmethod
    def create_instance(cls, crawler: Any, *args: Any, **kwargs: Any) -> 'CustomLoggerExtension':
        """
        工厂方法：兼容 ExtensionManager 的创建方式
        被 ExtensionManager 调用
        """
        # 可以通过 settings 控制是否启用
        log_file = crawler.settings.get('LOG_FILE')
        log_enable_custom = crawler.settings.get('LOG_ENABLE_CUSTOM', False)
        
        # 只有当没有配置日志文件且未启用自定义日志时才禁用
        if not log_file and not log_enable_custom:
            raise NotConfigured("CustomLoggerExtension: LOG_FILE not set and LOG_ENABLE_CUSTOM=False")

        return cls(crawler.settings)

    def spider_opened(self, spider: Any) -> None:
        logger = get_logger(__name__)
        try:
            logger.info(
                f"CustomLoggerExtension: Logging initialized. "
                f"LOG_FILE={self.settings.get('LOG_FILE')}, "
                f"LOG_LEVEL={self.settings.get('LOG_LEVEL')}"
            )
        except Exception as e:
            # 即使日志初始化信息无法打印，也不应该影响程序运行
            pass