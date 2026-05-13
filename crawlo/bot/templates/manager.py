# -*- coding: utf-8 -*-
"""
===================================
通知消息模板管理器
===================================

提供可配置的消息模板和变量替换功能，支持用户自定义消息格式。
"""

from typing import Dict, Any, Optional, List
import re

from crawlo.logging import get_logger

logger = get_logger(__name__)


class MessageTemplateManager:
    """消息模板管理器"""
    
    # 默认模板配置
    DEFAULT_TEMPLATES = {
        # 任务通知模板
        'task_startup': {
            'title': '🚀 {task_name} 开始执行',
            'content': '▶️ 目标：{target}\n⏱️ 预计时长：{estimated_time}'
        },
        'task_completion': {
            'title': '✅ {task_name} 执行完成',
            'content': '📊 结果：成功抓取 {success_count} 条数据\n⏱️ 耗时：{duration}'
        },
        'task_progress': {
            'title': '📊 {task_name} 执行进度',
            'content': '📈 已完成：{percentage}%\n🔢 当前数量：{current_count} 条'
        },
        
        # 异常通知模板
        'error_alert': {
            'title': '🚨 {task_name} 执行异常',
            'content': '❌ 错误：{error_message}\n⏰ 时间：{error_time}'
        },
        'performance_warning': {
            'title': '⚠️ 系统性能异常',
            'content': '📉 {metric_name}：{current_value} (阈值：{threshold})'
        },
        
        # 统计报告模板
        'daily_report': {
            'title': '📊 {date} 数据统计',
            'content': '📈 新增：{new_count} 条\n🔢 总量：{total_count} 条\n🎯 成功率：{success_rate}%'
        },
        'weekly_report': {
            'title': '📅 {period} 统计报告',
            'content': '📊 总抓取：{total_count} 条\n📈 日均：{daily_avg} 条\n✅ 成功率：{success_rate}%'
        },
        
        # 系统通知模板
        'config_update': {
            'title': '🔧 配置更新',
            'content': '📝 {config_item}：{old_value} → {new_value}\n⏰ 生效时间：{update_time}'
        },
        'system_maintenance': {
            'title': '🛠️ 系统维护通知',
            'content': '📅 维护时间：{maintenance_time}\n⚠️ 影响范围：{impact_scope}'
        },
        
        # 爬虫特定模板
        'http_error': {
            'title': '🌐 HTTP请求异常',
            'content': '❌ 状态码：{status_code}\n🔗 URL：{url}\n⏱️ 响应时间：{response_time}ms\n🔄 重试次数：{retry_count}'
        },
        'login_failed': {
            'title': '🔐 登录失败告警',
            'content': '👤 登录状态：{login_status}\n🍪 Cookie状态：{cookie_status}\n🌐 会话状态：{session_status}\n⏰ 时间：{error_time}'
        },
        'proxy_issue': {
            'title': '网络异常',
            'content': '使用网络：{proxy_used}\n📶 代理状态：{proxy_status}\n🔒 认证状态：{auth_status}\n📊 失败次数：{retry_count}'
        },
        'captcha_detected': {
            'title': '🤖 验证码拦截',
            'content': '🛡️ 验证码状态：{captcha_status}\n🔗 URL：{url}\n📱 用户代理：{user_agent}\n⚠️ 需要人工处理'
        },
        'parse_failure': {
            'title': '📄 数据解析失败',
            'content': '🔍 解析成功：{parse_success}\n📊 数据条数：{data_count}\n❌ 错误类型：{error_type}\n📄 URL：{url}'
        },
        'resource_monitor': {
            'title': '📊 资源监控告警',
            'content': '💾 内存使用：{memory_usage}%\n⚙️ CPU使用：{cpu_usage}%\n📂 磁盘使用：{disk_usage}%\n🔗 活跃连接：{active_connections}'
        },
        'db_connection_error': {
            'title': '🗄️ 数据库连接异常',
            'content': '🔌 连接状态：{db_connection}\n⏱️ 查询时间：{db_query_time}ms\n❌ 错误信息：{db_error}\n📋 表名：{table_name}'
        },
        'security_alert': {
            'title': '🔒 安全告警',
            'content': '🚨 告警类型：{security_alert}\n🛡️ 认证状态：{auth_status}\n🚫 访问拒绝：{access_denied}\n⏱️ 时间：{error_time}'
        }
    }
    
    def __init__(self, custom_templates: Optional[Dict] = None):
        """
        初始化模板管理器
        
        Args:
            custom_templates: 自定义模板配置，会与默认模板合并
        """
        self.templates = self.DEFAULT_TEMPLATES.copy()
        if custom_templates:
            self.templates.update(custom_templates)
        logger.debug(f"[TemplateManager] 已加载 {len(self.templates)} 个模板")
    
    def get_template(self, template_name: str) -> Optional[Dict[str, str]]:
        """
        获取指定名称的模板
        
        Args:
            template_name: 模板名称
            
        Returns:
            模板字典，包含title和content
        """
        return self.templates.get(template_name)
    
    def render_template(self, template_name: str, **kwargs) -> Optional[Dict[str, str]]:
        """
        渲染指定模板
        
        Args:
            template_name: 模板名称
            **kwargs: 模板变量
            
        Returns:
            渲染后的消息字典
        """
        template = self.get_template(template_name)
        if not template:
            logger.warning(f"[TemplateManager] 未找到模板: {template_name}")
            return None
        
        try:
            rendered = {
                'title': self._render_string(template['title'], kwargs),
                'content': self._render_string(template['content'], kwargs)
            }
            logger.debug(f"[TemplateManager] 成功渲染模板: {template_name}")
            return rendered
        except Exception as e:
            logger.error(f"[TemplateManager] 渲染模板失败: {template_name}, 错误: {e}")
            return None
    
    def _render_string(self, template_str: str, variables: Dict[str, Any]) -> str:
        """
        渲染字符串模板
        
        Args:
            template_str: 模板字符串
            variables: 变量字典
            
        Returns:
            渲染后的字符串
        """
        # re 已在顶部导入
        
        # 支持 {变量名} 和 {{变量名}} 两种格式
        pattern = r'\{(\w+)\}|\{\{(\w+)\}\}'
        
        def replace_var(match):
            var_name = match.group(1) or match.group(2)
            value = variables.get(var_name)
            if value is None:
                # 如果变量不存在，保持原样
                return match.group(0)
            return str(value)
        
        return re.sub(pattern, replace_var, template_str)
    
    def list_templates(self) -> Dict[str, str]:
        """
        列出所有可用模板
        
        Returns:
            模板名称和简要描述的字典
        """
        descriptions = {
            'task_startup': '任务启动通知',
            'task_completion': '任务完成通知',
            'task_progress': '任务进度通知',
            'error_alert': '错误告警通知',
            'performance_warning': '性能警告通知',
            'daily_report': '日报统计',
            'weekly_report': '周报统计',
            'config_update': '配置更新通知',
            'system_maintenance': '系统维护通知',
            'http_error': 'HTTP请求异常',
            'login_failed': '登录失败告警',
            'proxy_issue': '代理网络异常',
            'captcha_detected': '验证码拦截',
            'parse_failure': '数据解析失败',
            'resource_monitor': '资源监控告警',
            'db_connection_error': '数据库连接异常',
            'security_alert': '安全告警'
        }
        
        return {name: descriptions.get(name, '未命名模板') 
                for name in self.templates.keys()}
    
    def add_template(self, name: str, title: str, content: str):
        """
        添加新模板
        
        Args:
            name: 模板名称
            title: 标题模板
            content: 内容模板
        """
        self.templates[name] = {
            'title': title,
            'content': content
        }
        logger.info(f"[TemplateManager] 添加新模板: {name}")
    
    def remove_template(self, name: str) -> bool:
        """
        删除模板
        
        Args:
            name: 模板名称
            
        Returns:
            是否删除成功
        """
        if name in self.templates and name not in self.DEFAULT_TEMPLATES:
            del self.templates[name]
            logger.info(f"[TemplateManager] 删除模板: {name}")
            return True
        logger.warning(f"[TemplateManager] 无法删除模板: {name}")
        return False
    
    def get_template_parameters(self, template_name: str) -> Optional[List[str]]:
        """获取模板所需的参数列表"""
        template = self.templates.get(template_name)
        if not template:
            return None
        
        # 从标题和内容中提取变量
        # re 已在顶部导入
        title_params = re.findall(r'\{([^}]+)\}', template['title'])
        content_params = re.findall(r'\{([^}]+)\}', template['content'])
        
        # 合并并去重，保持顺序
        all_params = []
        seen = set()
        for param in title_params + content_params:
            if param not in seen:
                all_params.append(param)
                seen.add(param)
        
        return all_params


# 全局模板管理器实例
_template_manager = None


def get_template_manager(custom_templates: Optional[Dict] = None) -> MessageTemplateManager:
    """
    获取全局模板管理器实例
    
    Args:
        custom_templates: 自定义模板配置
        
    Returns:
        MessageTemplateManager实例
    """
    global _template_manager
    if _template_manager is None:
        _template_manager = MessageTemplateManager(custom_templates)
    return _template_manager


def render_message(template_name: str, **kwargs) -> Optional[Dict[str, str]]:
    """
    便捷函数：渲染消息模板
    
    Args:
        template_name: 模板名称
        **kwargs: 模板变量
        
    Returns:
        渲染后的消息字典
    """
    manager = get_template_manager()
    return manager.render_template(template_name, **kwargs)


def list_available_templates() -> Dict[str, str]:
    """
    便捷函数：列出所有可用模板
    
    Returns:
        模板名称和描述的字典
    """
    manager = get_template_manager()
    return manager.list_templates()


# 预定义的常用模板变量
COMMON_VARIABLES = {
    # 任务相关
    'task_name': '任务名称',
    'target': '目标地址',
    'estimated_time': '预计时长',
    'success_count': '成功数量',
    'duration': '执行时长',
    'percentage': '完成百分比',
    'current_count': '当前数量',
    
    # 爬虫特定变量
    'status_code': 'HTTP状态码',
    'response_time': '响应时间',
    'url': '请求URL',
    'user_agent': '用户代理',
    'proxy_used': '使用代理',
    'retry_count': '重试次数',
    'proxy_status': '代理状态',
    'login_status': '登录状态',
    'cookie_status': 'Cookie状态',
    'session_status': '会话状态',
    'captcha_status': '验证码状态',
    'parse_success': '解析成功',
    'data_count': '数据条数',
    'error_type': '错误类型',
    'request_method': '请求方法',
    
    # 错误相关
    'error_message': '错误信息',
    'error_time': '错误时间',
    'error_detail': '错误详情',
    'stack_trace': '堆栈跟踪',
    'failed_url': '失败URL',
    'exception_type': '异常类型',
    'metric_name': '指标名称',
    'current_value': '当前值',
    'threshold': '阈值',
    
    # 统计相关
    'date': '日期',
    'new_count': '新增数量',
    'total_count': '总数量',
    'success_rate': '成功率',
    'period': '统计周期',
    'daily_avg': '日均数量',
    'avg_response_time': '平均响应时间',
    'max_response_time': '最大响应时间',
    'min_response_time': '最小响应时间',
    'throughput': '吞吐量',
    
    # 系统相关
    'config_item': '配置项',
    'old_value': '原值',
    'new_value': '新值',
    'update_time': '更新时间',
    'maintenance_time': '维护时间',
    'impact_scope': '影响范围',
    'memory_usage': '内存使用',
    'cpu_usage': 'CPU使用',
    'disk_usage': '磁盘使用',
    'network_status': '网络状态',
    
    # 数据库相关
    'db_connection': '数据库连接',
    'db_query_time': '查询时间',
    'db_error': '数据库错误',
    'table_name': '表名',
    'record_count': '记录数',
    'insert_count': '插入数',
    'update_count': '更新数',
    'delete_count': '删除数',
    
    # 资源相关
    'connection_pool': '连接池',
    'active_connections': '活跃连接',
    'idle_connections': '空闲连接',
    'queue_size': '队列大小',
    'resource_leak': '资源泄露',
    'file_handle': '文件句柄',
    'thread_count': '线程数',
    'process_count': '进程数',
    
    # 安全相关
    'security_alert': '安全告警',
    'auth_status': '认证状态',
    'permission_level': '权限级别',
    'access_denied': '访问拒绝',
    'rate_limit': '速率限制',
    'blocked_ip': '被阻止IP',
    
    # 业务相关
    'business_type': '业务类型',
    'data_source': '数据源',
    'data_quality': '数据质量',
    'completeness_rate': '完整率',
    'accuracy_rate': '准确率',
    'consistency_rate': '一致性',
    'freshness': '数据新鲜度',
    'last_update': '最后更新',
    
    # 监控相关
    'monitor_item': '监控项',
    'monitor_status': '监控状态',
    'alert_level': '告警级别',
    'recovery_time': '恢复时间',
    'downtime': '停机时间',
    'availability': '可用性',
    'sla_status': 'SLA状态'
}

def get_template_parameters(template_name: str) -> Optional[List[str]]:
    """
    便捷函数：获取模板所需的参数列表
    
    Args:
        template_name: 模板名称
        
    Returns:
        模板所需参数列表
    """
    manager = get_template_manager()
    return manager.get_template_parameters(template_name)
