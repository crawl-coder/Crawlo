"""
定时任务启动器
"""

import os
import sys
import time
from datetime import datetime


def start_scheduler(project_root: str = None):
    """启动定时任务调度器的便捷函数"""
    import asyncio
    
    # 先配置日志系统
    from crawlo.project import get_settings
    from crawlo.logging import configure_logging, get_logger
    
    try:
        temp_settings = get_settings()
        configure_logging(temp_settings)
    except Exception:
        configure_logging()
    
    logger = get_logger("SchedulerStarter")
    
    # 如果指定了项目根目录
    if project_root:
        project_root = os.path.abspath(project_root)
        if os.path.isdir(project_root):
            os.chdir(project_root)
            sys.path.insert(0, project_root)
            logger.info(f"切换到项目目录: {project_root}")
        else:
            raise RuntimeError(f"项目目录不存在: {project_root}")
    
    from crawlo.project import get_settings
    from crawlo.scheduling.daemon import SchedulerDaemon
    from crawlo.utils.time_utils import format_datetime, format_duration
    
    settings = temp_settings
    
    if not settings.get_bool('SCHEDULER_ENABLED', False):
        logger.info("定时任务未启用，如需启用请在配置中设置 SCHEDULER_ENABLED = True")
        return
    
    daemon = SchedulerDaemon(settings)
    
    # 记录任务信息
    logger.info("=" * 80)
    logger.info("定时任务调度器")
    logger.info("=" * 80)
    logger.info(f"当前时间: {datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"任务数量: {len(daemon.jobs)}")
    
    if len(daemon.jobs) == 0:
        logger.info("未配置任何定时任务")
    else:
        for job in daemon.jobs:
            next_time = datetime.fromtimestamp(job.next_execution_time).strftime('%Y-%m-%d %H:%M:%S')
            time_diff = job.next_execution_time - time.time()
            if time_diff > 0:
                time_str = format_duration(time_diff)
                logger.info(f"任务: {job.spider_name}")
                logger.info(f"  Cron表达式: {job.cron or job.interval}")
                logger.info(f"  下次运行时间: {next_time}")
                logger.info(f"  距离下次运行: {time_str}")
            else:
                logger.info(f"任务: {job.spider_name}")
                logger.info(f"  Cron表达式: {job.cron or job.interval}")
                logger.info(f"  下次运行时间: {next_time}")
                logger.info(f"  状态: 立即执行")
    
    logger.info("=" * 80)
    logger.info("调度器主循环启动，等待任务执行...")
    logger.info("=" * 80)
    
    try:
        asyncio.run(daemon.start())
    except KeyboardInterrupt:
        logger.info("接收到中断信号，正在停止调度器...")
    except Exception as e:
        logger.error(f"调度器运行出错: {e}")
        import traceback
        logger.debug(f"详细错误信息:\n{traceback.format_exc()}")
