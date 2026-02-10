"""
定时任务命令行扩展
"""

import sys
from crawlo.settings.setting_manager import SettingManager as Settings


def main(args):
    """运行定时任务命令"""
    # 加载配置
    settings = Settings()
    
    if not settings.get_bool('SCHEDULER_ENABLED', False):
        print("定时任务未启用，如需启用请在配置中设置 SCHEDULER_ENABLED = True")
        return 1
    
    # 启动定时任务调度器
    try:
        from crawlo.scheduling import start_scheduler
        start_scheduler()
    except KeyboardInterrupt:
        print("\n接收到中断信号，正在停止调度器...")
    except Exception as e:
        print(f"调度器运行出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    return 0