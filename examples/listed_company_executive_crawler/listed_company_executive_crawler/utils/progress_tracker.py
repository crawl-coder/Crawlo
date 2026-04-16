#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
进度追踪器
用于跟踪和输出爬虫进度
"""


class ProgressTracker:
    """进度追踪器"""
    
    def __init__(self, total, step=100, logger=None):
        """
        初始化进度追踪器
        
        Args:
            total: 总数量
            step: 每隔多少步输出一次进度，默认100
            logger: 日志记录器
        """
        self.total = total
        self.step = step
        self.logger = logger
        self.current = 0
    
    def update(self, current, item_name=None):
        """
        更新进度
        
        Args:
            current: 当前进度
            item_name: 当前处理的项目名称（可选）
        """
        self.current = current
        
        # 每 step 步输出一次进度
        if current % self.step == 0 and self.logger:
            progress = (current / self.total * 100) if self.total > 0 else 0
            self.logger.info(
                f"📊 进度：{current}/{self.total} ({progress:.1f}%)"
            )
        
        # 输出当前处理项
        if item_name and self.logger:
            self.logger.info(
                f"➡️ 处理：{item_name} ({current + 1}/{self.total})"
            )
    
    def finish(self, failed_count=0):
        """
        标记完成
        
        Args:
            failed_count: 失败数量
        """
        if self.logger:
            self.logger.info(f"✅ 所有 {self.total} 项处理完毕！")
            if failed_count > 0:
                self.logger.warning(f"失败数量: {failed_count}")
