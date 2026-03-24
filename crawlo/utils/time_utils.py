"""
时间工具函数
"""

from datetime import datetime
from typing import Optional


def format_datetime(timestamp: float) -> str:
    """格式化时间戳为字符串
    
    Args:
        timestamp: Unix 时间戳
        
    Returns:
        格式化的日期时间字符串 'YYYY-MM-DD HH:MM:SS'
    """
    return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')


def format_duration(seconds: float) -> str:
    """格式化持续时间为易读字符串
    
    Args:
        seconds: 秒数
        
    Returns:
        格式化的时间字符串，如 '1 小时 30 分钟'
    """
    if seconds < 60:
        return f"{int(seconds)} 秒"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        remaining_seconds = int(seconds % 60)
        return f"{minutes} 分钟" + (f" {remaining_seconds} 秒" if remaining_seconds > 0 else "")
    elif seconds < 86400:  # 小于一天
        hours = int(seconds / 3600)
        remaining_minutes = int((seconds % 3600) / 60)
        return f"{hours} 小时" + (f" {remaining_minutes} 分钟" if remaining_minutes > 0 else "")
    else:  # 一天或以上
        days = int(seconds / 86400)
        remaining_hours = int((seconds % 86400) / 3600)
        return f"{days} 天" + (f" {remaining_hours} 小时" if remaining_hours > 0 else "")


def get_time_until_next(next_time: float, current_time: Optional[float] = None) -> tuple[str, float]:
    """获取距离下次执行的时间描述
    
    Args:
        next_time: 下次执行时间戳
        current_time: 当前时间戳，默认 None
        
    Returns:
        (格式化字符串, 时间差秒数)
    """
    import time
    if current_time is None:
        current_time = time.time()
    
    time_diff = next_time - current_time
    
    if time_diff <= 0:
        return "即将执行", time_diff
    
    return format_duration(time_diff), time_diff
