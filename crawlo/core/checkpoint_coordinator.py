#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
CheckpointCoordinator — Phase 3 抽出的检查点协调组件

职责：封装 Engine 中检查点恢复/保存/清除三段逻辑，用组合替代 mixin。
Engine 持有 ``self._checkpoint = CheckpointCoordinator(settings, logger)``，
不再直接管理 CheckpointManager 的实例化与编排。

注意：本组件只负责检查点的编排（是否启用、何时保存/清除、恢复到调度器），
底层序列化/存储仍由 ``crawlo.checkpoint.CheckpointManager`` 完成。
"""
from typing import Any, Optional

from crawlo.checkpoint import CheckpointManager
from crawlo.logging import get_logger


class CheckpointCoordinator:
    """检查点协调器：封装恢复/保存/清除三段流程。

    Phase 3 从 Engine 抽出，用组合方式注入 Engine，避免 Engine 承担过多职责。

    Args:
        settings: 配置对象
        logger: 可选日志器，未提供时创建独立实例
    """

    def __init__(self, settings: Any, logger: Optional[Any] = None):
        self._settings = settings
        self._logger = logger or get_logger('CheckpointCoordinator')

    async def resume_from_checkpoint(self, spider: Any, scheduler: Any) -> bool:
        """尝试从检查点恢复爬取状态。

        恢复成功时调用方应跳过 start_requests（由调用方设置 ``_start_requests_source = None``）。

        Args:
            spider: 爬虫实例（用于恢复 callback）
            scheduler: 调度器实例（用于重新入队请求与恢复指纹）

        Returns:
            bool: 是否成功从检查点恢复
        """
        try:
            checkpoint_mgr = CheckpointManager(spider.name, self._settings)
            if not checkpoint_mgr.enabled or not await checkpoint_mgr.has_checkpoint():
                return False

            checkpoint = await checkpoint_mgr.load()
            if checkpoint is None:
                return False

            # 恢复请求到调度器
            requests_data = checkpoint.get('requests', [])
            restored_count = 0
            for req_data in requests_data:
                try:
                    request = checkpoint_mgr.restore_request(req_data, spider)
                    if request and scheduler is not None:
                        # 设置 dont_filter=True 避免被过滤器拦截
                        request.dont_filter = True
                        await scheduler.enqueue_request(request)
                        restored_count += 1
                except Exception as e:
                    self._logger.debug(f"Failed to restore request: {e}")

            # 恢复去重指纹
            fingerprints = checkpoint.get('fingerprints', set())
            if fingerprints and scheduler is not None:
                checkpoint_mgr.restore_fingerprints(fingerprints, scheduler)

            # 关键修复：只有当真的恢复了请求 OR 恢复了指纹时才算恢复成功
            # 否则（空 checkpoint：0 请求、0 指纹）应返回 False，让 start_requests 正常执行
            if restored_count == 0 and not fingerprints:
                self._logger.info(
                    "Checkpoint file exists but no requests/fingerprints to restore, "
                    "treating as no-resume so start_requests will execute normally"
                )
                return False

            self._logger.info(
                f"Resumed from checkpoint: {restored_count}/{len(requests_data)} requests restored, "
                f"{len(fingerprints)} fingerprints recovered"
            )
            return True

        except Exception as e:
            self._logger.warning(f"Failed to resume from checkpoint: {e}")
            return False

    async def save_checkpoint(
        self,
        scheduler: Any,
        spider: Any,
        stats: Any,
        save_on_signal: bool,
    ) -> None:
        """保存检查点（仅在 shutdown 触发时调用）。

        Args:
            scheduler: 调度器实例
            spider: 爬虫实例
            stats: 统计收集器
            save_on_signal: 是否由信号触发（``CHECKPOINT_SAVE_ON_SIGNAL``）
        """
        try:
            spider_name = spider.name if spider else 'unknown'
            checkpoint_mgr = CheckpointManager(spider_name, self._settings)

            if not checkpoint_mgr.enabled:
                return

            if not save_on_signal:
                return

            await checkpoint_mgr.save(scheduler, stats)

        except Exception as e:
            self._logger.warning(f"Failed to save checkpoint on shutdown: {e}")

    async def clear_checkpoint(self, spider: Any) -> None:
        """清除检查点（爬取正常完成后调用）。

        Args:
            spider: 爬虫实例
        """
        try:
            spider_name = spider.name if spider else 'unknown'
            checkpoint_mgr = CheckpointManager(spider_name, self._settings)

            if checkpoint_mgr.enabled:
                await checkpoint_mgr.clear()

        except Exception as e:
            self._logger.debug(f"Failed to clear checkpoint: {e}")
