# -*- coding: utf-8 -*-
"""
MySQL Pipeline 工具类

包含错误分类、性能统计等工具类
"""
import re
from typing import Optional
from dataclasses import dataclass


@dataclass
class ErrorConfig:
    """错误配置"""
    code: int
    description: str
    skipable: bool = False
    retryable: bool = False


@dataclass
class PerformanceStats:
    """性能统计"""
    insert_count: int = 0
    insert_time: float = 0.0
    batch_count: int = 0
    batch_time: float = 0.0
    fallback_count: int = 0
    retry_count: int = 0
    
    def get_avg_insert_time(self) -> float:
        return self.insert_time / self.insert_count if self.insert_count > 0 else 0.0
    
    def get_avg_batch_time(self) -> float:
        return self.batch_time / self.batch_count if self.batch_count > 0 else 0.0


class ErrorClassifier:
    """MySQL 错误分类器"""
    
    ERROR_CONFIGS = {
        # 数据完整性错误（可跳过）
        1062: ErrorConfig(1062, '重复数据', skipable=True),
        1048: ErrorConfig(1048, '字段不能为空', skipable=True),
        1364: ErrorConfig(1364, '字段缺少默认值', skipable=True),
        
        # 锁相关错误（可跳过+可重试）
        1205: ErrorConfig(1205, '锁等待超时', skipable=True, retryable=True),
        1213: ErrorConfig(1213, '死锁', skipable=True, retryable=True),
        1206: ErrorConfig(1206, '锁文件已满', skipable=True, retryable=True),
        
        # 连接错误（可重试）
        2002: ErrorConfig(2002, '无法连接MySQL服务器', retryable=True),
        2003: ErrorConfig(2003, '连接被拒绝', retryable=True),
        2006: ErrorConfig(2006, 'MySQL服务器断开', retryable=True),
        2013: ErrorConfig(2013, '连接丢失', retryable=True),
        2014: ErrorConfig(2014, '脏连接', retryable=True),
        2026: ErrorConfig(2026, 'SSL连接错误', retryable=True),
        
        # 认证/权限错误（不可恢复）
        1044: ErrorConfig(1044, '权限不足'),
        1045: ErrorConfig(1045, '访问被拒绝'),
        1698: ErrorConfig(1698, '密码过期'),
        
        # 数据库/表结构错误
        1049: ErrorConfig(1049, '数据库不存在'),
        1054: ErrorConfig(1054, '字段不存在'),
        1146: ErrorConfig(1146, '表不存在'),
        1304: ErrorConfig(1304, '存储过程不存在'),
        
        # SQL语法错误
        1064: ErrorConfig(1064, 'SQL语法错误'),
        1149: ErrorConfig(1149, 'SQL语句错误'),
        1176: ErrorConfig(1176, '键不存在'),
        
        # 数据类型错误
        1264: ErrorConfig(1264, '数据类型溢出'),
        1292: ErrorConfig(1292, '日期时间格式错误'),
        1366: ErrorConfig(1366, '数据格式错误'),
        
        # 其他常见错误
        1153: ErrorConfig(1153, '数据包过大', skipable=True),
        1189: ErrorConfig(1189, '网络错误', retryable=True),
        1836: ErrorConfig(1836, '外键约束失败', skipable=True),
    }
    
    @classmethod
    def extract_error_code(cls, error: Exception) -> Optional[int]:
        """从异常中提取 MySQL 错误码"""
        if not error:
            return None
        
        if hasattr(error, 'args') and error.args:
            first_arg = error.args[0]
            if isinstance(first_arg, int):
                return first_arg
            if isinstance(first_arg, tuple) and len(first_arg) > 0:
                code = first_arg[0]
                if isinstance(code, int):
                    return code
        
        err_str = str(error)
        match = re.search(r'\((\d+),', err_str)
        if match:
            return int(match.group(1))
        
        return None
    
    @classmethod
    def get_error_config(cls, error: Exception) -> Optional[ErrorConfig]:
        """获取错误配置"""
        code = cls.extract_error_code(error)
        return cls.ERROR_CONFIGS.get(code)
    
    @classmethod
    def is_skipable(cls, error: Exception) -> bool:
        """判断是否为可跳过的错误"""
        config = cls.get_error_config(error)
        return config.skipable if config else False
    
    @classmethod
    def is_retryable(cls, error: Exception) -> bool:
        """判断是否为可重试的错误"""
        config = cls.get_error_config(error)
        return config.retryable if config else False
    
    @classmethod
    def get_error_description(cls, error: Exception) -> str:
        """获取错误描述"""
        config = cls.get_error_config(error)
        if config:
            return f"{config.description} (Error {config.code})"
        return str(error)
