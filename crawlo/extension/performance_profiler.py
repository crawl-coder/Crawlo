#!/usr/bin/python
# -*- coding:UTF-8 -*-
import io
import os
import pstats
import asyncio
import cProfile
from typing import Any, Optional

from crawlo.utils.log import get_logger
from crawlo.utils.error_handler import ErrorHandler
from crawlo.event import spider_opened, spider_closed


class PerformanceProfilerExtension:
    """
    性能分析扩展
    在爬虫运行期间进行性能分析，帮助优化爬虫性能
    """

    def __init__(self, crawler: Any):
        self.settings = crawler.settings
        self.logger = get_logger(self.__class__.__name__, crawler.settings.get('LOG_LEVEL'))
        self.error_handler = ErrorHandler(self.__class__.__name__, crawler.settings.get('LOG_LEVEL'))
        
        # 获取配置参数
        self.enabled = self.settings.get_bool('PERFORMANCE_PROFILER_ENABLED', False)
        self.output_dir = self.settings.get('PERFORMANCE_PROFILER_OUTPUT_DIR', 'profiling')
        self.interval = self.settings.get_int('PERFORMANCE_PROFILER_INTERVAL', 300)  # 默认5分钟
        
        self.profiler: Optional[cProfile.Profile] = None
        self.task: Optional[asyncio.Task] = None
        
        # 创建输出目录
        if self.enabled:
            os.makedirs(self.output_dir, exist_ok=True)

    @classmethod
    def create_instance(cls, crawler: Any) -> 'PerformanceProfilerExtension':
        # 只有当配置启用时才创建实例
        if not crawler.settings.get_bool('PERFORMANCE_PROFILER_ENABLED', False):
            from crawlo.exceptions import NotConfigured
            raise NotConfigured("PerformanceProfilerExtension: PERFORMANCE_PROFILER_ENABLED is False")
        
        o = cls(crawler)
        if o.enabled:
            crawler.subscriber.subscribe(o.spider_opened, event=spider_opened)
            crawler.subscriber.subscribe(o.spider_closed, event=spider_closed)
        return o

    async def spider_opened(self) -> None:
        """爬虫启动时开始性能分析"""
        if not self.enabled:
            return
            
        try:
            self.profiler = cProfile.Profile()
            self.profiler.enable()
            
            # 启动定期保存分析结果的任务
            self.task = asyncio.create_task(self._periodic_save())
            
            self.logger.info("Performance profiler started.")
        except Exception as e:
            self.error_handler.handle_error(
                e, 
                context="启动性能分析器失败", 
                raise_error=False
            )

    async def spider_closed(self) -> None:
        """爬虫关闭时停止性能分析并保存结果"""
        if not self.enabled or not self.profiler:
            return
            
        try:
            # 停止定期保存任务
            if self.task:
                self.task.cancel()
                try:
                    await self.task
                except asyncio.CancelledError:
                    pass
            
            # 停止分析器并保存最终结果
            self.profiler.disable()
            
            # 保存分析结果
            await self._save_profile("final")
            self.logger.info("Performance profiler stopped and results saved.")
        except Exception as e:
            self.error_handler.handle_error(
                e, 
                context="停止性能分析器失败", 
                raise_error=False
            )

    async def _periodic_save(self) -> None:
        """定期保存分析结果"""
        counter = 1
        while True:
            try:
                await asyncio.sleep(self.interval)
                if self.profiler:
                    # 临时禁用分析器以保存结果
                    self.profiler.disable()
                    await self._save_profile(f"periodic_{counter}")
                    counter += 1
                    # 重新启用分析器
                    self.profiler.enable()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in periodic profiling save: {e}")

    async def _save_profile(self, name: str) -> None:
        """保存分析结果到文件"""
        try:
            # 创建内存中的字符串流
            s = io.StringIO()
            ps = pstats.Stats(self.profiler, stream=s)
            
            # 排序并打印统计信息
            ps.sort_stats('cumulative')
            ps.print_stats()
            
            # 保存到文件
            filename = os.path.join(self.output_dir, f'profile_{name}.txt')
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(s.getvalue())
            
            self.logger.info(f"Performance profile saved to {filename}")
        except Exception as e:
            self.logger.error(f"Error saving performance profile: {e}")