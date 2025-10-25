from typing import Any
from crawlo.exceptions import NotConfigured
from crawlo.logging import get_logger

# 获取logger实例
_logger = get_logger(__name__)


class CustomLoggerExtension:
    """
    日志系统初始化扩展
    遵循与 ExtensionManager 一致的接口规范：使用 create_instance
    """

    def __init__(self, settings: Any):
        self.settings = settings
        # 使用新的日志系统，但要简化配置传递
        try:
            from crawlo.logging import configure_logging
            # 直接传递settings对象，让日志系统内部处理
            configure_logging(settings)
        except Exception as e:
            # 如果日志系统配置失败，不应该阻止扩展加载
            # 使用基本日志输出错误信息
            import logging
            logging.getLogger(__name__).warning(f"Failed to configure logging system: {e}")
            # 不抛出异常，让扩展继续加载

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
        try:
            _logger.info(
                f"CustomLoggerExtension: Logging initialized. "
                f"LOG_FILE={self.settings.get('LOG_FILE')}, "
                f"LOG_LEVEL={self.settings.get('LOG_LEVEL')}"
            )
        except Exception as e:
            # 即使日志初始化信息无法打印，也不应该影响程序运行
            pass