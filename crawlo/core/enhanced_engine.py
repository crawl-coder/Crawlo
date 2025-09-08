#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强的引擎实现
解决大规模请求生成时的并发控制和背压问题
"""
import asyncio

from crawlo.core.engine import Engine as BaseEngine
from crawlo.utils.log import get_logger


class EnhancedEngine(BaseEngine):
    """
    增强的引擎实现
    
    主要改进：
    1. 智能的请求生成控制
    2. 背压感知的调度
    3. 动态并发调整
    """
    
    def __init__(self, crawler):
        super().__init__(crawler)
        
        # 增强控制参数
        self.max_queue_size = self.settings.get_int('SCHEDULER_MAX_QUEUE_SIZE', 200)
        self.generation_batch_size = 10
        self.generation_interval = 0.05
        self.backpressure_ratio = 0.8  # 队列达到80%时启动背压
        
        # 状态跟踪
        self._generation_paused = False
        self._last_generation_time = 0
        self._generation_stats = {
            'total_generated': 0,
            'backpressure_events': 0
        }
        
        self.logger = get_logger(self.__class__.__name__)
    
    async def crawl(self):
        """
        增强的爬取循环
        支持智能请求生成和背压控制
        """
        generation_task = None
        
        try:
            # 启动请求生成任务
            if self.start_requests:
                generation_task = asyncio.create_task(
                    self._controlled_request_generation()
                )
            
            # 主爬取循环
            while self.running:
                # 获取并处理请求
                if request := await self._get_next_request():
                    await self._crawl(request)
                
                # 检查退出条件
                if await self._should_exit():
                    break
                
                # 短暂休息避免忙等
                await asyncio.sleep(0.001)
        
        finally:
            # 清理生成任务
            if generation_task and not generation_task.done():
                generation_task.cancel()
                try:
                    await generation_task
                except asyncio.CancelledError:
                    pass
            
            await self.close_spider()
    
    async def _controlled_request_generation(self):
        """受控的请求生成"""
        self.logger.info("🎛️ 启动受控请求生成")
        
        batch = []
        total_generated = 0
        
        try:
            for request in self.start_requests:
                batch.append(request)
                
                # 批量处理
                if len(batch) >= self.generation_batch_size:
                    generated = await self._process_generation_batch(batch)
                    total_generated += generated
                    batch = []
                
                # 背压检查
                if await self._should_pause_generation():
                    await self._wait_for_capacity()
            
            # 处理剩余请求
            if batch:
                generated = await self._process_generation_batch(batch)
                total_generated += generated
        
        except Exception as e:
            self.logger.error(f"❌ 请求生成失败: {e}")
        
        finally:
            self.start_requests = None
            self.logger.info(f"🎉 请求生成完成，总计: {total_generated}")
    
    async def _process_generation_batch(self, batch) -> int:
        """处理一批请求"""
        generated = 0
        
        for request in batch:
            if not self.running:
                break
            
            # 等待队列有空间
            while await self._is_queue_full() and self.running:
                await asyncio.sleep(0.1)
            
            if self.running:
                await self.enqueue_request(request)
                generated += 1
                self._generation_stats['total_generated'] += 1
            
            # 控制生成速度
            if self.generation_interval > 0:
                await asyncio.sleep(self.generation_interval)
        
        return generated
    
    async def _should_pause_generation(self) -> bool:
        """判断是否应该暂停生成"""
        # 检查队列大小
        if await self._is_queue_full():
            return True
        
        # 检查任务管理器负载
        if self.task_manager:
            current_tasks = len(self.task_manager.current_task)
            if hasattr(self.task_manager, 'semaphore'):
                max_concurrency = getattr(self.task_manager.semaphore, '_initial_value', 8)
                if current_tasks >= max_concurrency * self.backpressure_ratio:
                    return True
        
        return False
    
    async def _is_queue_full(self) -> bool:
        """检查队列是否已满"""
        if not self.scheduler:
            return False
        
        queue_size = len(self.scheduler)
        return queue_size >= self.max_queue_size * self.backpressure_ratio
    
    async def _wait_for_capacity(self):
        """等待系统有足够容量"""
        self._generation_stats['backpressure_events'] += 1
        self.logger.debug("⏸️ 触发背压，暂停请求生成")
        
        wait_time = 0.1
        max_wait = 2.0
        
        while await self._should_pause_generation() and self.running:
            await asyncio.sleep(wait_time)
            wait_time = min(wait_time * 1.1, max_wait)
    
    async def _should_exit(self) -> bool:
        """检查是否应该退出"""
        # 没有启动请求，且所有队列都空闲
        if (self.start_requests is None and 
            self.scheduler.idle() and 
            self.downloader.idle() and 
            self.task_manager.all_done() and 
            self.processor.idle()):
            return True
        
        return False
    
    def get_generation_stats(self) -> dict:
        """获取生成统计"""
        return {
            **self._generation_stats,
            'queue_size': len(self.scheduler) if self.scheduler else 0,
            'active_tasks': len(self.task_manager.current_task) if self.task_manager else 0
        }