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
            raise ValueError(f"Invalid cron expression: {cron}, expected 5 or 6 fields")
        
        # 如果是5位表达式，添加秒位（默认为0）
        if len(parts) == 5:
            parts = ['0'] + parts  # 在前面添加秒位
        
        # 校验每个字段的格式
        field_names = ['second', 'minute', 'hour', 'day', 'month', 'weekday']
        for i, part in enumerate(parts):
            self._validate_cron_field(part, field_names[i])
        
        self._cron_parts = parts  # 现在是 [秒, 分钟, 小时, 日, 月, 星期]

    CRON_FIELD_RE = re.compile(r'^(\d+(-\d+)?(/\d+)?|\*(/\d+)?)$')

    @classmethod
    def _validate_cron_field(cls, field: str, name: str):
        """校验单个 cron 字段的格式是否合法"""
        # 允许 comma-separated 的复合格式
        for sub_field in field.split(','):
            if not cls.CRON_FIELD_RE.match(sub_field):
                raise ValueError(
                    f"Invalid cron field '{name}': '{field}' - "
                    f"sub-field '{sub_field}' is not a valid pattern. "
                    f"Expected formats: *, */N, N, N-M, N-M/N, or comma-separated combinations"
                )
    
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
        """计算基于cron表达式的下次执行时间 — 字段级跳进，避免逐秒扫描"""
        if not self._cron_parts:
            return float('inf')
        
        parts = self._cron_parts  # [second, minute, hour, day, month, weekday]
        dt = datetime.fromtimestamp(current_time)
        dt = dt.replace(microsecond=0)
        dt += timedelta(seconds=1)
        
        import calendar
        
        for day_offset in range(367):  # 最多扫描 367 天
            target_date = dt.replace(hour=0, minute=0, second=0) + timedelta(days=day_offset)
            
            # 检查月份
            if not self._match_cron_field(parts[4], target_date.month, 1, 12):
                continue
            # 检查日期
            if not self._match_cron_field(parts[3], target_date.day, 1, 31):
                continue
            # 检查星期 (0=周日, 1=周一, ..., 6=周六)
            weekday = (target_date.weekday() + 1) % 7
            if not self._match_cron_field(parts[5], weekday, 0, 6):
                continue
            
            # 找到匹配的日期，在当天内查找匹配的时分秒
            start_hour = dt.hour if day_offset == 0 else 0
            h = start_hour
            while h < 24:
                if not self._match_cron_field(parts[2], h, 0, 23):
                    h += 1
                    continue
                
                start_min = dt.minute if day_offset == 0 and h == dt.hour else 0
                m = start_min
                while m < 60:
                    if not self._match_cron_field(parts[1], m, 0, 59):
                        m += 1
                        continue
                    
                    start_sec = dt.second if day_offset == 0 and h == dt.hour and m == dt.minute else 0
                    s = start_sec
                    while s < 60:
                        if self._match_cron_field(parts[0], s, 0, 59):
                            result = target_date.replace(hour=h, minute=m, second=s)
                            return result.timestamp()
                        s += 1
                    m += 1
                h += 1
        
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