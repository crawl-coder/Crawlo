"""
时间触发器
"""

import time
import re
from typing import Dict, Optional, Union
from datetime import datetime, timedelta


class TimeTrigger:
    """时间触发器，处理 cron 表达式和时间间隔"""
    
    def __init__(self, cron: Optional[str] = None, interval: Optional[Dict[str, int]] = None):
        self.cron = cron
        self.interval = interval
        self._cron_parts = None
        
        if cron:
            self._parse_cron(cron)
    
    def _parse_cron(self, cron: str):
        """解析 cron 表达式"""
        # 支持扩展的6位cron表达式：秒 分钟 小时 日 月 星期（前向兼容5位标准表达式）
        parts = cron.strip().split()
        if len(parts) != 5 and len(parts) != 6:
            raise ValueError(f"无效的cron表达式: {cron}，应为5位或6位表达式")
        
        # 如果是5位表达式，添加秒位（默认为0）
        if len(parts) == 5:
            parts = ['0'] + parts  # 在前面添加秒位
        
        self._cron_parts = parts  # 现在是 [秒, 分钟, 小时, 日, 月, 星期]
    
    def _match_cron(self, dt: datetime) -> bool:
        """检查时间是否匹配cron表达式"""
        if not self._cron_parts:
            return False
        
        second, minute, hour, day, month, weekday = self._cron_parts
        
        # 检查秒
        if not self._match_cron_field(second, dt.second, 0, 59):
            return False
        
        # 检查分钟
        if not self._match_cron_field(minute, dt.minute, 0, 59):
            return False
        
        # 检查小时
        if not self._match_cron_field(hour, dt.hour, 0, 23):
            return False
        
        # 检查日期
        if not self._match_cron_field(day, dt.day, 1, 31):
            return False
        
        # 检查月份
        if not self._match_cron_field(month, dt.month, 1, 12):
            return False
        
        # 检查星期 (0=周日, 6=周六)
        weekday_num = dt.weekday() + 1  # Python中周一为0，周日为6，cron中周日为0
        if weekday_num == 7:
            weekday_num = 0
        if not self._match_cron_field(weekday, weekday_num, 0, 6):
            return False
        
        return True
    
    def _match_cron_field(self, cron_field: str, actual_value: int, min_val: int, max_val: int) -> bool:
        """检查单个cron字段是否匹配"""
        if cron_field == '*':
            return True
        
        # 处理范围，如 1-5
        if '-' in cron_field:
            range_match = re.match(r'(\d+)-(\d+)', cron_field)
            if range_match:
                start, end = map(int, range_match.groups())
                if min_val <= start <= max_val and min_val <= end <= max_val:
                    return start <= actual_value <= end
        
        # 处理步长，如 */2
        if '*/' in cron_field:
            step_match = re.match(r'\*/(\d+)', cron_field)
            if step_match:
                step = int(step_match.group(1))
                return actual_value % step == 0
        
        # 处理单个数字
        try:
            value = int(cron_field)
            if min_val <= value <= max_val:
                return actual_value == value
        except ValueError:
            pass
        
        # 处理多个值，如 1,2,3
        if ',' in cron_field:
            values = cron_field.split(',')
            for val in values:
                try:
                    if int(val) == actual_value:
                        return True
                except ValueError:
                    continue
        
        return False
    
    def _calculate_next_interval_time(self, current_time: float) -> float:
        """计算基于时间间隔的下次执行时间"""
        if not self.interval:
            return float('inf')
        
        # 将间隔转换为秒
        total_seconds = 0
        if 'seconds' in self.interval:
            total_seconds += self.interval['seconds']
        if 'minutes' in self.interval:
            total_seconds += self.interval['minutes'] * 60
        if 'hours' in self.interval:
            total_seconds += self.interval['hours'] * 3600
        if 'days' in self.interval:
            total_seconds += self.interval['days'] * 86400
        
        if total_seconds <= 0:
            return float('inf')
        
        # 返回当前时间加上间隔
        return current_time + total_seconds
    
    def _calculate_next_cron_time(self, current_time: float) -> float:
        """计算基于cron表达式的下次执行时间"""
        if not self._cron_parts:
            return float('inf')
        
        # 从当前时间开始，逐秒检查直到找到匹配的时间
        current_dt = datetime.fromtimestamp(current_time)
        # 重置到秒的开始
        current_dt = current_dt.replace(microsecond=0)
        
        # 最多检查一周，避免无限循环
        max_check_time = current_dt + timedelta(days=7)
        
        while current_dt < max_check_time:
            if self._match_cron(current_dt):
                # 如果匹配的时间是当前时间之后，则返回
                if current_dt.timestamp() > current_time:
                    return current_dt.timestamp()
            
            # 增加一秒
            current_dt += timedelta(seconds=1)
        
        # 如果一周内都没找到匹配时间，返回无穷大
        return float('inf')
    
    def get_next_time(self, current_time: float) -> float:
        """获取下次执行时间"""
        if self.cron:
            return self._calculate_next_cron_time(current_time)
        elif self.interval:
            return self._calculate_next_interval_time(current_time)
        else:
            # 如果既没有cron也没有interval，则永不执行
            return float('inf')
    
    def __repr__(self):
        if self.cron:
            return f"TimeTrigger(cron={self.cron})"
        elif self.interval:
            return f"TimeTrigger(interval={self.interval})"
        else:
            return "TimeTrigger(inactive)"