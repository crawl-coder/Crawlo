#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
长期运行的定时爬虫测试
=====================

基于真实项目的逻辑，使用安全的事件循环管理，每5分钟运行一次爬虫，测试长期运行的稳定性
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
import sys
import os
# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from crawlo.crawler import CrawlerProcess
import signal
import sys


class LongRunningSpiderTester:
    """长期运行的爬虫测试器，避免事件循环问题"""
    
    def __init__(self):
        self.running = True
        self.logger = logging.getLogger(__name__)
        
        # 注册信号处理器以优雅关闭
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """信号处理器，用于优雅关闭"""
        self.logger.info(f"收到信号 {signum}，正在停止爬虫测试器...")
        self.running = False
    
    async def run_single_crawl(self, spider_name: str):
        """运行单次爬虫任务"""
        try:
            print(f"🚀 开始运行爬虫 {spider_name}... (时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")
            
            # 使用现有的CrawlerProcess实例来运行爬虫
            # 这样可以避免多次创建和销毁事件循环
            process = CrawlerProcess()
            await process.crawl(spider_name)
            
            print(f"✅ 爬虫 {spider_name} 执行完成 (时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")
        except Exception as e:
            print(f"❌ 爬虫 {spider_name} 执行失败: {e}")
            import traceback
            traceback.print_exc()
    
    async def run_continuous_scheduler(self, spider_name: str, interval_minutes: int = 5):
        """运行连续调度器，每指定分钟数运行一次爬虫"""
        print(f"⏰ 爬虫测试器启动")
        print(f"📊 爬虫名称: {spider_name}")
        print(f"⏱️  运行间隔: {interval_minutes} 分钟")
        print(f"🔄 程序将持续运行，按 Ctrl+C 停止")
        
        run_count = 0
        
        while self.running:
            try:
                run_count += 1
                print(f"\n--- 第 {run_count} 次运行 ---")
                print(f"🕐 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                
                # 运行爬虫任务
                await self.run_single_crawl(spider_name)
                
                print(f"🏁 结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                
                # 等待指定的时间间隔，但要定期检查是否需要停止
                total_wait_time = interval_minutes * 60  # 转换为秒
                elapsed = 0
                
                while elapsed < total_wait_time and self.running:
                    # 每次最多睡眠10秒，以便及时响应停止信号
                    sleep_time = min(10, total_wait_time - elapsed)
                    await asyncio.sleep(sleep_time)
                    elapsed += sleep_time
                    
                    # 显示剩余时间
                    remaining = total_wait_time - elapsed
                    if remaining % 60 == 0 and remaining > 0:
                        minutes_left = remaining // 60
                        print(f"⏳ 距离下次运行还有 {minutes_left} 分钟")
                    elif remaining <= 30 and remaining > 0:
                        print(f"⏳ 距离下次运行还有 {remaining} 秒")
                
                if not self.running:
                    break
                
                print(f"✅ 准备进行第 {run_count + 1} 次运行...")
                
            except KeyboardInterrupt:
                print("\n🏃 收到键盘中断信号")
                break
            except Exception as e:
                print(f"❌ 调度器运行出错: {e}")
                import traceback
                traceback.print_exc()
                # 出错后等待一段时间再继续
                await asyncio.sleep(60)
        
        print("⏹️  爬虫测试器已停止")

    async def run_with_statistics(self, spider_name: str, interval_minutes: int = 5):
        """运行带有统计信息的测试"""
        print(f"📈 启动长期运行测试，爬虫: {spider_name}，间隔: {interval_minutes}分钟")
        
        start_time = datetime.now()
        run_count = 0
        successful_runs = 0
        failed_runs = 0
        
        while self.running:
            try:
                run_count += 1
                print(f"\n{'='*60}")
                print(f"运行 #{run_count} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"累计运行时间: {datetime.now() - start_time}")
                print(f"成功: {successful_runs}, 失败: {failed_runs}")
                print(f"成功率: {(successful_runs/max(1, run_count)*100):.1f}%")
                print(f"{'='*60}")
                
                # 记录开始时间
                run_start_time = time.time()
                
                # 运行爬虫任务
                process = CrawlerProcess()
                await process.crawl(spider_name)
                
                # 计算运行时间
                run_duration = time.time() - run_start_time
                successful_runs += 1
                
                print(f"✅ 第 {run_count} 次运行成功，耗时: {run_duration:.2f}秒")
                
                # 等待指定的时间间隔
                total_wait_time = interval_minutes * 60  # 转换为秒
                elapsed = 0
                
                while elapsed < total_wait_time and self.running:
                    sleep_time = min(30, total_wait_time - elapsed)  # 每30秒检查一次
                    await asyncio.sleep(sleep_time)
                    elapsed += sleep_time
                    
                    # 每分钟显示一次剩余时间
                    remaining = total_wait_time - elapsed
                    if remaining > 0 and remaining % 60 == 0:
                        minutes_left = remaining // 60
                        print(f"⏳ 距离下次运行还有 {minutes_left} 分钟")
                        
            except Exception as e:
                failed_runs += 1
                print(f"❌ 第 {run_count} 次运行失败: {e}")
                import traceback
                traceback.print_exc()
                
                # 发生错误后仍然等待完整的时间间隔再进行下次运行
                total_wait_time = interval_minutes * 60
                elapsed = 0
                while elapsed < total_wait_time and self.running:
                    sleep_time = min(30, total_wait_time - elapsed)
                    await asyncio.sleep(sleep_time)
                    elapsed += sleep_time
            
            if not self.running:
                break
        
        # 输出最终统计
        total_runtime = datetime.now() - start_time
        print(f"\n{'='*60}")
        print("📊 长期运行测试完成统计")
        print(f"总运行时间: {total_runtime}")
        print(f"计划运行次数: {run_count}")
        print(f"成功运行次数: {successful_runs}")
        print(f"失败运行次数: {failed_runs}")
        print(f"成功率: {(successful_runs/max(1, run_count)*100):.1f}%")
        print(f"平均运行时间: {total_runtime.total_seconds()/max(1, successful_runs):.2f}秒/次")
        print(f"{'='*60}")


def main():
    """主函数"""
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 创建测试器实例
    tester = LongRunningSpiderTester()
    
    # 设置要运行的爬虫名称（使用真实的ofweek爬虫）
    spider_name = 'of_week'
    
    # 设置运行间隔（5分钟）
    interval_minutes = 5
    
    print("="*60)
    print("長期運行穩定性測試")
    print("="*60)
    print(f"爬虫名称: {spider_name}")
    print(f"运行间隔: {interval_minutes} 分钟")
    print(f"预计每小时运行: {60 // interval_minutes} 次")
    print(f"按 Ctrl+C 停止程序")
    print("="*60)
    
    try:
        # 使用单个事件循环运行测试器
        asyncio.run(tester.run_with_statistics(spider_name, interval_minutes))
    except KeyboardInterrupt:
        print("\n⏹️  程序已手动停止")
    except Exception as e:
        print(f"❌ 程序运行出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()