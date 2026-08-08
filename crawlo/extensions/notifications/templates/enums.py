# -*- coding: utf-8 -*-
"""
===================================
模板变量枚举定义
===================================

提供预定义的模板变量枚举，方便用户在IDE中查看和选择变量。
"""

from enum import Enum
from typing import Dict, List


class TemplateVariable(Enum):
    """模板变量枚举"""
    
    # 任务相关变量
    TASK_NAME = "task_name"
    TARGET = "target"
    ESTIMATED_TIME = "estimated_time"
    SUCCESS_COUNT = "success_count"
    DURATION = "duration"
    PERCENTAGE = "percentage"
    CURRENT_COUNT = "current_count"
    
    # 爬虫特定变量
    STATUS_CODE = "status_code"
    RESPONSE_TIME = "response_time"
    URL = "url"
    USER_AGENT = "user_agent"
    PROXY_USED = "proxy_used"
    RETRY_COUNT = "retry_count"
    PROXY_STATUS = "proxy_status"
    LOGIN_STATUS = "login_status"
    COOKIE_STATUS = "cookie_status"
    SESSION_STATUS = "session_status"
    CAPTCHA_STATUS = "captcha_status"
    PARSE_SUCCESS = "parse_success"
    DATA_COUNT = "data_count"
    ERROR_TYPE = "error_type"
    REQUEST_METHOD = "request_method"
    
    # 错误相关变量
    ERROR_MESSAGE = "error_message"
    ERROR_TIME = "error_time"
    ERROR_DETAIL = "error_detail"
    STACK_TRACE = "stack_trace"
    FAILED_URL = "failed_url"
    EXCEPTION_TYPE = "exception_type"
    METRIC_NAME = "metric_name"
    CURRENT_VALUE = "current_value"
    THRESHOLD = "threshold"
    
    # 统计相关变量
    DATE = "date"
    NEW_COUNT = "new_count"
    TOTAL_COUNT = "total_count"
    SUCCESS_RATE = "success_rate"
    PERIOD = "period"
    DAILY_AVG = "daily_avg"
    AVG_RESPONSE_TIME = "avg_response_time"
    MAX_RESPONSE_TIME = "max_response_time"
    MIN_RESPONSE_TIME = "min_response_time"
    THROUGHPUT = "throughput"
    
    # 系统相关变量
    CONFIG_ITEM = "config_item"
    OLD_VALUE = "old_value"
    NEW_VALUE = "new_value"
    UPDATE_TIME = "update_time"
    MAINTENANCE_TIME = "maintenance_time"
    IMPACT_SCOPE = "impact_scope"
    MEMORY_USAGE = "memory_usage"
    CPU_USAGE = "cpu_usage"
    DISK_USAGE = "disk_usage"
    NETWORK_STATUS = "network_status"
    
    # 数据库相关变量
    DB_CONNECTION = "db_connection"
    DB_QUERY_TIME = "db_query_time"
    DB_ERROR = "db_error"
    TABLE_NAME = "table_name"
    RECORD_COUNT = "record_count"
    INSERT_COUNT = "insert_count"
    UPDATE_COUNT = "update_count"
    DELETE_COUNT = "delete_count"
    
    # 资源相关变量
    CONNECTION_POOL = "connection_pool"
    ACTIVE_CONNECTIONS = "active_connections"
    IDLE_CONNECTIONS = "idle_connections"
    QUEUE_SIZE = "queue_size"
    RESOURCE_LEAK = "resource_leak"
    FILE_HANDLE = "file_handle"
    THREAD_COUNT = "thread_count"
    PROCESS_COUNT = "process_count"
    
    # 安全相关变量
    SECURITY_ALERT = "security_alert"
    AUTH_STATUS = "auth_status"
    PERMISSION_LEVEL = "permission_level"
    ACCESS_DENIED = "access_denied"
    RATE_LIMIT = "rate_limit"
    BLOCKED_IP = "blocked_ip"
    
    # 业务相关变量
    BUSINESS_TYPE = "business_type"
    DATA_SOURCE = "data_source"
    DATA_QUALITY = "data_quality"
    COMPLETENESS_RATE = "completeness_rate"
    ACCURACY_RATE = "accuracy_rate"
    CONSISTENCY_RATE = "consistency_rate"
    FRESHNESS = "freshness"
    LAST_UPDATE = "last_update"
    
    # 监控相关变量
    MONITOR_ITEM = "monitor_item"
    MONITOR_STATUS = "monitor_status"
    ALERT_LEVEL = "alert_level"
    RECOVERY_TIME = "recovery_time"
    DOWNTIME = "downtime"
    AVAILABILITY = "availability"
    SLA_STATUS = "sla_status"
    
    @classmethod
    def get_variable_info(cls) -> Dict[str, str]:
        """获取所有变量的详细信息"""
        return {
            cls.TASK_NAME.value: "任务名称",
            cls.TARGET.value: "目标地址",
            cls.ESTIMATED_TIME.value: "预计时长",
            cls.SUCCESS_COUNT.value: "成功数量",
            cls.DURATION.value: "执行时长",
            cls.PERCENTAGE.value: "完成百分比",
            cls.CURRENT_COUNT.value: "当前数量",
            
            cls.STATUS_CODE.value: "HTTP状态码",
            cls.RESPONSE_TIME.value: "响应时间(ms)",
            cls.URL.value: "请求URL",
            cls.USER_AGENT.value: "用户代理",
            cls.PROXY_USED.value: "是否使用代理",
            cls.RETRY_COUNT.value: "重试次数",
            cls.PROXY_STATUS.value: "代理状态",
            cls.LOGIN_STATUS.value: "登录状态",
            cls.COOKIE_STATUS.value: "Cookie状态",
            cls.SESSION_STATUS.value: "会话状态",
            cls.CAPTCHA_STATUS.value: "验证码状态",
            cls.PARSE_SUCCESS.value: "解析是否成功",
            cls.DATA_COUNT.value: "数据条数",
            cls.ERROR_TYPE.value: "错误类型",
            cls.REQUEST_METHOD.value: "请求方法",
            
            cls.ERROR_MESSAGE.value: "错误信息",
            cls.ERROR_TIME.value: "错误时间",
            cls.ERROR_DETAIL.value: "错误详情",
            cls.STACK_TRACE.value: "堆栈跟踪",
            cls.FAILED_URL.value: "失败URL",
            cls.EXCEPTION_TYPE.value: "异常类型",
            cls.METRIC_NAME.value: "指标名称",
            cls.CURRENT_VALUE.value: "当前值",
            cls.THRESHOLD.value: "阈值",
            
            cls.DATE.value: "日期",
            cls.NEW_COUNT.value: "新增数量",
            cls.TOTAL_COUNT.value: "总数量",
            cls.SUCCESS_RATE.value: "成功率",
            cls.PERIOD.value: "统计周期",
            cls.DAILY_AVG.value: "日均数量",
            cls.AVG_RESPONSE_TIME.value: "平均响应时间",
            cls.MAX_RESPONSE_TIME.value: "最大响应时间",
            cls.MIN_RESPONSE_TIME.value: "最小响应时间",
            cls.THROUGHPUT.value: "吞吐量",
            
            cls.CONFIG_ITEM.value: "配置项",
            cls.OLD_VALUE.value: "原值",
            cls.NEW_VALUE.value: "新值",
            cls.UPDATE_TIME.value: "更新时间",
            cls.MAINTENANCE_TIME.value: "维护时间",
            cls.IMPACT_SCOPE.value: "影响范围",
            cls.MEMORY_USAGE.value: "内存使用",
            cls.CPU_USAGE.value: "CPU使用",
            cls.DISK_USAGE.value: "磁盘使用",
            cls.NETWORK_STATUS.value: "网络状态",
            
            cls.DB_CONNECTION.value: "数据库连接",
            cls.DB_QUERY_TIME.value: "查询时间",
            cls.DB_ERROR.value: "数据库错误",
            cls.TABLE_NAME.value: "表名",
            cls.RECORD_COUNT.value: "记录数",
            cls.INSERT_COUNT.value: "插入数",
            cls.UPDATE_COUNT.value: "更新数",
            cls.DELETE_COUNT.value: "删除数",
            
            cls.CONNECTION_POOL.value: "连接池",
            cls.ACTIVE_CONNECTIONS.value: "活跃连接",
            cls.IDLE_CONNECTIONS.value: "空闲连接",
            cls.QUEUE_SIZE.value: "队列大小",
            cls.RESOURCE_LEAK.value: "资源泄露",
            cls.FILE_HANDLE.value: "文件句柄",
            cls.THREAD_COUNT.value: "线程数",
            cls.PROCESS_COUNT.value: "进程数",
            
            cls.SECURITY_ALERT.value: "安全告警",
            cls.AUTH_STATUS.value: "认证状态",
            cls.PERMISSION_LEVEL.value: "权限级别",
            cls.ACCESS_DENIED.value: "访问拒绝",
            cls.RATE_LIMIT.value: "速率限制",
            cls.BLOCKED_IP.value: "被阻止IP",
            
            cls.BUSINESS_TYPE.value: "业务类型",
            cls.DATA_SOURCE.value: "数据源",
            cls.DATA_QUALITY.value: "数据质量",
            cls.COMPLETENESS_RATE.value: "完整率",
            cls.ACCURACY_RATE.value: "准确率",
            cls.CONSISTENCY_RATE.value: "一致性",
            cls.FRESHNESS.value: "数据新鲜度",
            cls.LAST_UPDATE.value: "最后更新",
            
            cls.MONITOR_ITEM.value: "监控项",
            cls.MONITOR_STATUS.value: "监控状态",
            cls.ALERT_LEVEL.value: "告警级别",
            cls.RECOVERY_TIME.value: "恢复时间",
            cls.DOWNTIME.value: "停机时间",
            cls.AVAILABILITY.value: "可用性",
            cls.SLA_STATUS.value: "SLA状态"
        }
    
    @classmethod
    def get_category_variables(cls, category: str) -> List['TemplateVariable']:
        """根据类别获取变量列表"""
        categories = {
            'task': [cls.TASK_NAME, cls.TARGET, cls.ESTIMATED_TIME, cls.SUCCESS_COUNT, 
                    cls.DURATION, cls.PERCENTAGE, cls.CURRENT_COUNT],
            'spider': [cls.STATUS_CODE, cls.RESPONSE_TIME, cls.URL, cls.USER_AGENT,
                      cls.PROXY_USED, cls.RETRY_COUNT, cls.PROXY_STATUS, cls.LOGIN_STATUS,
                      cls.COOKIE_STATUS, cls.SESSION_STATUS, cls.CAPTCHA_STATUS,
                      cls.PARSE_SUCCESS, cls.DATA_COUNT, cls.ERROR_TYPE, cls.REQUEST_METHOD],
            'error': [cls.ERROR_MESSAGE, cls.ERROR_TIME, cls.ERROR_DETAIL, cls.STACK_TRACE,
                     cls.FAILED_URL, cls.EXCEPTION_TYPE, cls.METRIC_NAME, cls.CURRENT_VALUE,
                     cls.THRESHOLD],
            'stats': [cls.DATE, cls.NEW_COUNT, cls.TOTAL_COUNT, cls.SUCCESS_RATE, cls.PERIOD,
                     cls.DAILY_AVG, cls.AVG_RESPONSE_TIME, cls.MAX_RESPONSE_TIME,
                     cls.MIN_RESPONSE_TIME, cls.THROUGHPUT],
            'system': [cls.CONFIG_ITEM, cls.OLD_VALUE, cls.NEW_VALUE, cls.UPDATE_TIME,
                      cls.MAINTENANCE_TIME, cls.IMPACT_SCOPE, cls.MEMORY_USAGE, cls.CPU_USAGE,
                      cls.DISK_USAGE, cls.NETWORK_STATUS],
            'database': [cls.DB_CONNECTION, cls.DB_QUERY_TIME, cls.DB_ERROR, cls.TABLE_NAME,
                        cls.RECORD_COUNT, cls.INSERT_COUNT, cls.UPDATE_COUNT, cls.DELETE_COUNT],
            'resource': [cls.CONNECTION_POOL, cls.ACTIVE_CONNECTIONS, cls.IDLE_CONNECTIONS,
                        cls.QUEUE_SIZE, cls.RESOURCE_LEAK, cls.FILE_HANDLE, cls.THREAD_COUNT,
                        cls.PROCESS_COUNT],
            'security': [cls.SECURITY_ALERT, cls.AUTH_STATUS, cls.PERMISSION_LEVEL,
                        cls.ACCESS_DENIED, cls.RATE_LIMIT, cls.BLOCKED_IP],
            'business': [cls.BUSINESS_TYPE, cls.DATA_SOURCE, cls.DATA_QUALITY,
                        cls.COMPLETENESS_RATE, cls.ACCURACY_RATE, cls.CONSISTENCY_RATE,
                        cls.FRESHNESS, cls.LAST_UPDATE],
            'monitor': [cls.MONITOR_ITEM, cls.MONITOR_STATUS, cls.ALERT_LEVEL,
                       cls.RECOVERY_TIME, cls.DOWNTIME, cls.AVAILABILITY, cls.SLA_STATUS]
        }
        
        return categories.get(category, [])
    
    @classmethod
    def search_variables(cls, keyword: str) -> List['TemplateVariable']:
        """根据关键字搜索变量"""
        keyword = keyword.lower()
        results = []
        info = cls.get_variable_info()
        
        for var in cls:
            if keyword in var.value.lower() or keyword in info[var.value].lower():
                results.append(var)
        
        return results


# 便捷的变量访问方式
class TemplateVar:
    """模板变量便捷访问类"""
    
    # 直接提供常用变量的便捷访问
    task_name = TemplateVariable.TASK_NAME
    target = TemplateVariable.TARGET
    estimated_time = TemplateVariable.ESTIMATED_TIME
    success_count = TemplateVariable.SUCCESS_COUNT
    duration = TemplateVariable.DURATION
    percentage = TemplateVariable.PERCENTAGE
    current_count = TemplateVariable.CURRENT_COUNT
    
    # 爬虫相关变量
    status_code = TemplateVariable.STATUS_CODE
    response_time = TemplateVariable.RESPONSE_TIME
    url = TemplateVariable.URL
    user_agent = TemplateVariable.USER_AGENT
    proxy_used = TemplateVariable.PROXY_USED
    retry_count = TemplateVariable.RETRY_COUNT
    proxy_status = TemplateVariable.PROXY_STATUS
    login_status = TemplateVariable.LOGIN_STATUS
    cookie_status = TemplateVariable.COOKIE_STATUS
    session_status = TemplateVariable.SESSION_STATUS
    captcha_status = TemplateVariable.CAPTCHA_STATUS
    parse_success = TemplateVariable.PARSE_SUCCESS
    data_count = TemplateVariable.DATA_COUNT
    error_type = TemplateVariable.ERROR_TYPE
    request_method = TemplateVariable.REQUEST_METHOD
    
    # 错误相关变量
    error_message = TemplateVariable.ERROR_MESSAGE
    error_time = TemplateVariable.ERROR_TIME
    error_detail = TemplateVariable.ERROR_DETAIL
    stack_trace = TemplateVariable.STACK_TRACE
    failed_url = TemplateVariable.FAILED_URL
    exception_type = TemplateVariable.EXCEPTION_TYPE
    metric_name = TemplateVariable.METRIC_NAME
    current_value = TemplateVariable.CURRENT_VALUE
    threshold = TemplateVariable.THRESHOLD


# 预定义模板名称枚举
class TemplateName(Enum):
    """预定义模板名称枚举"""
    
    # 任务相关模板
    TASK_STARTUP = "task_startup"
    TASK_COMPLETION = "task_completion"
    TASK_PROGRESS = "task_progress"
    
    # 错误告警模板
    ERROR_ALERT = "error_alert"
    PERFORMANCE_WARNING = "performance_warning"
    
    # 统计报告模板
    DAILY_REPORT = "daily_report"
    WEEKLY_REPORT = "weekly_report"
    
    # 系统通知模板
    CONFIG_UPDATE = "config_update"
    SYSTEM_MAINTENANCE = "system_maintenance"
    
    # 爬虫特定模板
    HTTP_ERROR = "http_error"
    LOGIN_FAILED = "login_failed"
    PROXY_ISSUE = "proxy_issue"
    CAPTCHA_DETECTED = "captcha_detected"
    PARSE_FAILURE = "parse_failure"
    RESOURCE_MONITOR = "resource_monitor"
    DB_CONNECTION_ERROR = "db_connection_error"
    SECURITY_ALERT = "security_alert"
    
    @classmethod
    def get_template_descriptions(cls) -> Dict[str, str]:
        """获取模板描述信息"""
        return {
            cls.TASK_STARTUP.value: "任务启动通知",
            cls.TASK_COMPLETION.value: "任务完成通知",
            cls.TASK_PROGRESS.value: "任务进度通知",
            cls.ERROR_ALERT.value: "错误告警通知",
            cls.PERFORMANCE_WARNING.value: "性能警告通知",
            cls.DAILY_REPORT.value: "日报统计",
            cls.WEEKLY_REPORT.value: "周报统计",
            cls.CONFIG_UPDATE.value: "配置更新通知",
            cls.SYSTEM_MAINTENANCE.value: "系统维护通知",
            cls.HTTP_ERROR.value: "HTTP请求异常",
            cls.LOGIN_FAILED.value: "登录失败告警",
            cls.PROXY_ISSUE.value: "代理网络异常",
            cls.CAPTCHA_DETECTED.value: "验证码拦截",
            cls.PARSE_FAILURE.value: "数据解析失败",
            cls.RESOURCE_MONITOR.value: "资源监控告警",
            cls.DB_CONNECTION_ERROR.value: "数据库连接异常",
            cls.SECURITY_ALERT.value: "安全告警"
        }


# 便捷的模板名称访问方式
class Template:
    """模板名称便捷访问类"""
    
    # 任务相关模板
    task_startup = TemplateName.TASK_STARTUP.value
    task_completion = TemplateName.TASK_COMPLETION.value
    task_progress = TemplateName.TASK_PROGRESS.value
    
    # 错误告警模板
    error_alert = TemplateName.ERROR_ALERT.value
    performance_warning = TemplateName.PERFORMANCE_WARNING.value
    
    # 统计报告模板
    daily_report = TemplateName.DAILY_REPORT.value
    weekly_report = TemplateName.WEEKLY_REPORT.value
    
    # 系统通知模板
    config_update = TemplateName.CONFIG_UPDATE.value
    system_maintenance = TemplateName.SYSTEM_MAINTENANCE.value
    
    # 爬虫特定模板
    http_error = TemplateName.HTTP_ERROR.value
    login_failed = TemplateName.LOGIN_FAILED.value
    proxy_issue = TemplateName.PROXY_ISSUE.value
    captcha_detected = TemplateName.CAPTCHA_DETECTED.value
    parse_failure = TemplateName.PARSE_FAILURE.value
    resource_monitor = TemplateName.RESOURCE_MONITOR.value
    db_connection_error = TemplateName.DB_CONNECTION_ERROR.value
    security_alert = TemplateName.SECURITY_ALERT.value


# 导出主要类
__all__ = [
    'TemplateVariable',
    'TemplateVar',
    'TemplateName',
    'Template'
]