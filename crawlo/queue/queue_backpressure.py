#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
队列背压配置 Mixin

提供 QueueManager 的背压控制相关方法。
"""


class QueueBackpressureMixin:
    """队列背压配置混入类"""

    def _apply_redis_backpressure_config(self):
        """应用Redis队列的背压配置（用于AUTO模式）"""
        from crawlo.utils.misc import safe_get_config

        settings = self.config.settings if hasattr(self.config, 'settings') and self.config.settings else {}  # type: ignore

        # 更新QueueConfig的背压参数为Redis配置
        self.config.max_queue_size = safe_get_config(  # type: ignore
            settings, 'REDIS_SCHEDULER_MAX_QUEUE_SIZE',
            safe_get_config(settings, 'SCHEDULER_MAX_QUEUE_SIZE', 50000), int
        )
        self.config.backpressure_ratio = safe_get_config(  # type: ignore
            settings, 'REDIS_BACKPRESSURE_RATIO',
            safe_get_config(settings, 'BACKPRESSURE_RATIO', 0.6)
        )
        self.config.backpressure_delay_base = safe_get_config(  # type: ignore
            settings, 'REDIS_BACKPRESSURE_DELAY_BASE',
            safe_get_config(settings, 'BACKPRESSURE_DELAY_BASE', 0.5)
        )
        self.config.backpressure_delay_max = safe_get_config(  # type: ignore
            settings, 'REDIS_BACKPRESSURE_DELAY_MAX',
            safe_get_config(settings, 'BACKPRESSURE_DELAY_MAX', 5.0)
        )

        # 更新extra_config中的阈值
        if hasattr(self.config, 'extra_config') and self.config.extra_config:  # type: ignore
            self.config.extra_config['backpressure_warning_threshold'] = safe_get_config(  # type: ignore
                settings, 'REDIS_BACKPRESSURE_WARNING_THRESHOLD',
                safe_get_config(settings, 'BACKPRESSURE_WARNING_THRESHOLD', 0.6)
            )
            self.config.extra_config['backpressure_critical_threshold'] = safe_get_config(  # type: ignore
                settings, 'REDIS_BACKPRESSURE_CRITICAL_THRESHOLD',
                safe_get_config(settings, 'BACKPRESSURE_CRITICAL_THRESHOLD', 0.85)
            )

        self.logger.debug(  # type: ignore
            f"Applied Redis backpressure config: "
            f"max_size={self.config.max_queue_size}, "  # type: ignore
            f"ratio={self.config.backpressure_ratio}, "  # type: ignore
            f"delay_base={self.config.backpressure_delay_base}s, "  # type: ignore
            f"delay_max={self.config.backpressure_delay_max}s"  # type: ignore
        )

        # 重要：重新创建背压控制器以应用新配置
        self._recreate_backpressure_controller()

    def _apply_memory_backpressure_config(self):
        """应用内存队列的背压配置（用于AUTO模式或降级场景）"""
        from crawlo.utils.misc import safe_get_config

        settings = self.config.settings if hasattr(self.config, 'settings') and self.config.settings else {}  # type: ignore

        # 更新QueueConfig的背压参数为Memory配置
        self.config.max_queue_size = safe_get_config(  # type: ignore
            settings, 'MEMORY_SCHEDULER_MAX_QUEUE_SIZE',
            safe_get_config(settings, 'SCHEDULER_MAX_QUEUE_SIZE', 10000), int
        )
        self.config.backpressure_ratio = safe_get_config(
            settings, 'MEMORY_BACKPRESSURE_RATIO',
            safe_get_config(settings, 'BACKPRESSURE_RATIO', 0.8)
        )
        self.config.backpressure_delay_base = safe_get_config(
            settings, 'MEMORY_BACKPRESSURE_DELAY_BASE',
            safe_get_config(settings, 'BACKPRESSURE_DELAY_BASE', 0.1)
        )
        self.config.backpressure_delay_max = safe_get_config(
            settings, 'MEMORY_BACKPRESSURE_DELAY_MAX',
            safe_get_config(settings, 'BACKPRESSURE_DELAY_MAX', 1.0)
        )

        # 更新extra_config中的阈值
        if hasattr(self.config, 'extra_config') and self.config.extra_config:  # type: ignore
            self.config.extra_config['backpressure_warning_threshold'] = safe_get_config(  # type: ignore
                settings, 'MEMORY_BACKPRESSURE_WARNING_THRESHOLD',
                safe_get_config(settings, 'BACKPRESSURE_WARNING_THRESHOLD', 0.8)
            )
            self.config.extra_config['backpressure_critical_threshold'] = safe_get_config(  # type: ignore
                settings, 'MEMORY_BACKPRESSURE_CRITICAL_THRESHOLD',
                safe_get_config(settings, 'BACKPRESSURE_CRITICAL_THRESHOLD', 0.95)
            )

        self.logger.debug(  # type: ignore
            f"Applied Memory backpressure config: "
            f"max_size={self.config.max_queue_size}, "  # type: ignore
            f"ratio={self.config.backpressure_ratio}, "  # type: ignore
            f"delay_base={self.config.backpressure_delay_base}s, "  # type: ignore
            f"delay_max={self.config.backpressure_delay_max}s"  # type: ignore
        )

        # 重要：重新创建背压控制器以应用新配置
        self._recreate_backpressure_controller()

    def _recreate_backpressure_controller(self):
        """
        重新创建背压控制器以应用更新后的配置

        当AUTO模式检测到Redis可用或不可用时，会更新self.config的背压参数，
        需要重新创建背压控制器才能使新配置生效。
        """
        from crawlo.backpressure import (
            BackpressureController,
            QueueSizeStrategy,
            BackpressureStrategyConfig
        )
        from crawlo.utils.misc import safe_get_config

        # 获取背压策略类型配置
        strategy_type = safe_get_config(
            self.config.settings,  # type: ignore
            'BACKPRESSURE_STRATEGY',
            'queue_size'
        )

        # 使用更新后的配置创建新的策略配置
        bp_config = BackpressureStrategyConfig(
            threshold=self.config.backpressure_ratio,  # type: ignore
            base_delay=self.config.backpressure_delay_base,  # type: ignore
            max_delay=self.config.backpressure_delay_max,  # type: ignore
        )

        # 根据配置创建对应策略
        if strategy_type == 'adaptive':
            from crawlo.backpressure import AdaptiveStrategy
            strategy = AdaptiveStrategy(config=bp_config)
        elif strategy_type == 'composite':
            from crawlo.backpressure import CompositeStrategy
            strategy = CompositeStrategy([
                QueueSizeStrategy(config=bp_config)
            ])
        else:  # 默认使用queue_size策略
            strategy = QueueSizeStrategy(config=bp_config)

        # 创建新的背压控制器
        self._backpressure_controller = BackpressureController(  # type: ignore
            strategy=strategy,
            enabled=True
        )

        self._backpressure_strategy_type = strategy_type  # type: ignore

        self.logger.info(  # type: ignore
            f"Backpressure controller recreated with strategy: {strategy_type} "
            f"(threshold: {bp_config.threshold:.0%}, "
            f"base_delay: {bp_config.base_delay}s, "
            f"max_delay: {bp_config.max_delay}s)"
        )
