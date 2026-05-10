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
    from crawlo.scheduling.daemon import SchedulerDaemon
    from crawlo.utils.time_format import format_datetime, format_duration
    
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
    
    # get_settings 已在上面导入
    settings = get_settings()
    
    if not settings.get_bool('SCHEDULER_ENABLED', False):
        logger.info("定时任务未启用，如需启用请在配置中设置 SCHEDULER_ENABLED = True")
        return
    
    # 初始化调度器（加载任务配置）
    daemon = SchedulerDaemon(settings)
    
    # 打印启动概览
    logger.info(f"调度器启动 - 时间: {datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')}, 任务数: {len(daemon.jobs)}")
    
    try:
        asyncio.run(daemon.start())
    except KeyboardInterrupt:
        logger.info("接收到中断信号，正在停止调度器...")
    except Exception as e:
        logger.error(f"调度器运行出错: {e}")
        import traceback
        logger.debug(f"详细错误信息:\n{traceback.format_exc()}")
