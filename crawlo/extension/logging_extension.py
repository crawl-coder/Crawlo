#!/usr/bin/python
# -*- coding:UTF-8 -*-
from typing import Any
from crawlo.exceptions import NotConfigured
from crawlo.logging import get_logger

# Get logger instance
_logger = get_logger(__name__)


class CustomLoggerExtension:
    """
    Logging System Initialization Extension
    Follows the same interface specification as ExtensionManager: uses create_instance
    """

    def __init__(self, settings: Any):
        self.settings = settings
        # Use new logging system with simplified config passing
        try:
            from crawlo.logging import configure_logging
            # Pass settings object directly, let logging system handle it
            configure_logging(settings)
        except Exception as e:
            # If logging system configuration fails, should not prevent extension loading
            # Use basic logging to output error message
            import logging
            logging.getLogger(__name__).warning(f"Failed to configure logging system: {e}")
            # Don't raise exception, let extension continue loading

    @classmethod
    def create_instance(cls, crawler: Any, *args: Any, **kwargs: Any) -> 'CustomLoggerExtension':
        """
        Factory method: compatible with ExtensionManager's creation method
        Called by ExtensionManager
        """
        # Can control whether to enable via settings
        log_file = crawler.settings.get('LOG_FILE')
        log_enable_custom = crawler.settings.get('LOG_ENABLE_CUSTOM', False)
        
        # Only disable when no log file configured and custom logging not enabled
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
            # Even if logging initialization info cannot be printed, should not affect program execution
            pass