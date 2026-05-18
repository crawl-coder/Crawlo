# -*- coding: utf-8 -*-
"""
===================================
资源监控通知模板
===================================

提供 MySQL、Redis、MongoDB 资源监控和资源泄露检测的通知模板。
"""

from enum import Enum
from typing import Dict, List, Optional
from crawlo.bot.templates.manager import MessageTemplateManager, get_template_manager
from crawlo.bot.core.models import NotificationType


class ResourceMonitorTemplateManager:
    """
    资源监控模板管理器
    
    专门管理数据库和缓存资源监控相关的通知模板。
    """
    
    # 预定义的资源监控模板
    RESOURCE_TEMPLATES = {
        # MySQL 相关模板
        'mysql_connection_pool_monitor': {
            'title': '📊 MySQL 连接池监控',
            'content': '🔌 连接池状态：{pool_status}\n📈 活跃连接：{active_connections}\n🔄 空闲连接：{idle_connections}\n⚡ 最大连接：{max_connections}\n⏳ 等待连接：{waiting_connections}\n⏰ 监控时间：{timestamp}'
        },
        'mysql_resource_leak_alert': {
            'title': '🚨 MySQL 资源泄露告警',
            'content': '💥 检测到资源泄露！\n📊 连接数：{current_connections}/{max_connections}\n🔍 泄露类型：{leak_type}\n🏷️ 泄露标签：{leak_tag}\n⏰ 发现时间：{discovery_time}\n⚠️ 影响范围：{impact_scope}'
        },
        'mysql_slow_query_alert': {
            'title': '🐌 MySQL 慢查询告警',
            'content': '⏱️ 慢查询告警！\n🔍 SQL语句：{sql_statement}\n⏰ 执行时间：{execution_time}s\n📊 影响行数：{affected_rows}\n🎯 目标表：{target_table}\n📍 查询来源：{query_source}'
        },
        'mysql_deadlock_alert': {
            'title': '💀 MySQL 死锁告警',
            'content': '💥 检测到死锁！\n🔗 事务ID：{transaction_id}\n⏰ 等待时间：{wait_time}s\n👥 参与事务：{involved_transactions}\n📝 锁类型：{lock_type}\n🎯 受影响表：{affected_table}'
        },
        
        # Redis 相关模板
        'redis_memory_monitor': {
            'title': '💾 Redis 内存监控',
            'content': '📊 内存使用：{used_memory}/{max_memory}\n📈 内存使用率：{memory_usage_percent}%\n🔄 内存碎片率：{memory_fragmentation_ratio}\n⚡ 命中率：{hit_rate}%\n⏰ 监控时间：{timestamp}'
        },
        'redis_connection_monitor': {
            'title': '🔗 Redis 连接监控',
            'content': '🔌 连接状态：{connection_status}\n👥 客户端连接数：{connected_clients}\n🔄 最大客户端数：{max_clients}\n⚡ 输入流量：{input_kbps}/s\n📤 输出流量：{output_kbps}/s\n⏰ 监控时间：{timestamp}'
        },
        'redis_resource_leak_alert': {
            'title': '🚨 Redis 资源泄露告警',
            'content': '💥 检测到资源泄露！\n📊 当前连接数：{current_connections}\n📈 内存使用：{current_memory_mb}MB\n🔍 泄露趋势：{leak_trend}\n🏷️ 泄露标识：{leak_identifier}\n⏰ 发现时间：{discovery_time}\n⚠️ 影响范围：{impact_scope}'
        },
        'redis_key_ttl_monitor': {
            'title': '🔑 Redis Key 过期监控',
            'content': '⏰ TTL 过期告警！\n🔑 Key：{key_name}\n⏱️ 剩余TTL：{ttl_seconds}s\n🎯 业务类型：{business_type}\n📊 Key大小：{key_size_bytes}bytes\n📍 存储位置：{storage_location}'
        },
        
        # MongoDB 相关模板
        'mongodb_connection_monitor': {
            'title': '🔗 MongoDB 连接监控',
            'content': '🔌 连接池状态：{pool_status}\n📊 当前连接：{current_connections}\n🔄 可用连接：{available_connections}\n⚡ 等待连接：{pending_requests}\n⏰ 监控时间：{timestamp}'
        },
        'mongodb_resource_leak_alert': {
            'title': '🚨 MongoDB 资源泄露告警',
            'content': '💥 检测到资源泄露！\n📊 连接数：{current_connections}\n📈 内存使用：{memory_usage_mb}MB\n🔍 泄露类型：{leak_type}\n🏷️ 泄露标签：{leak_tag}\n⏰ 发现时间：{discovery_time}\n⚠️ 影响范围：{impact_scope}'
        },
        'mongodb_slow_operation_alert': {
            'title': '🐢 MongoDB 慢操作告警',
            'content': '⏱️ 慢操作告警！\n🔍 操作类型：{operation_type}\n⏰ 执行时间：{execution_time}s\n🎯 集合名称：{collection_name}\n📊 影响文档：{documents_affected}\n📍 操作来源：{operation_source}'
        },
        'mongodb_index_miss_alert': {
            'title': '🔍 MongoDB 索引缺失告警',
            'content': '❌ 索引缺失告警！\n🎯 集合：{collection_name}\n📊 查询条件：{query_condition}\n🔍 扫描文档：{scanned_documents}\n📈 返回文档：{returned_documents}\n⚠️ 建议索引：{recommended_index}'
        },
        
        # 通用资源监控模板
        'general_resource_monitor': {
            'title': '📈 通用资源监控',
            'content': '📊 资源类型：{resource_type}\n📈 当前值：{current_value}\n⚡ 阈值：{threshold_value}\n📊 使用率：{usage_percentage}%\n🎯 目标服务：{target_service}\n📍 监控时间：{timestamp}'
        },
        'general_resource_leak_alert': {
            'title': '🚨 通用资源泄露告警',
            'content': '💥 资源泄露检测！\n📊 资源类型：{resource_type}\n🔍 泄露详情：{leak_details}\n📈 增长趋势：{growth_trend}\n⚠️ 泄露严重度：{severity_level}\n⏰ 发现时间：{discovery_time}\n🎯 影响服务：{affected_service}'
        }
    }
    
    def __init__(self):
        self.manager = get_template_manager()  # 使用全局模板管理器（与 send_template_notification 共享）
        # 添加资源监控模板到全局模板管理器
        for name, template in self.RESOURCE_TEMPLATES.items():
            self.manager.add_template(name, template['title'], template['content'])
    
    def get_template(self, template_name: str) -> Optional[Dict[str, str]]:
        """获取资源监控模板"""
        return self.manager.render_template(template_name)
    
    def render_resource_template(self, template_name: str, **kwargs) -> Optional[Dict[str, str]]:
        """渲染资源监控模板"""
        return self.manager.render_template(template_name, **kwargs)
    
    def list_resource_templates(self) -> Dict[str, str]:
        """列出所有资源监控模板"""
        descriptions = {
            # MySQL 模板描述
            'mysql_connection_pool_monitor': 'MySQL 连接池监控',
            'mysql_resource_leak_alert': 'MySQL 资源泄露告警',
            'mysql_slow_query_alert': 'MySQL 慢查询告警',
            'mysql_deadlock_alert': 'MySQL 死锁告警',
            
            # Redis 模板描述
            'redis_memory_monitor': 'Redis 内存监控',
            'redis_connection_monitor': 'Redis 连接监控',
            'redis_resource_leak_alert': 'Redis 资源泄露告警',
            'redis_key_ttl_monitor': 'Redis Key 过期监控',
            
            # MongoDB 模板描述
            'mongodb_connection_monitor': 'MongoDB 连接监控',
            'mongodb_resource_leak_alert': 'MongoDB 资源泄露告警',
            'mongodb_slow_operation_alert': 'MongoDB 慢操作告警',
            'mongodb_index_miss_alert': 'MongoDB 索引缺失告警',
            
            # 通用模板描述
            'general_resource_monitor': '通用资源监控',
            'general_resource_leak_alert': '通用资源泄露告警'
        }
        
        return {name: descriptions.get(name, '未命名模板') for name in self.RESOURCE_TEMPLATES.keys()}
    
    def get_mysql_templates(self) -> Dict[str, str]:
        """获取所有 MySQL 相关模板"""
        return {k: v for k, v in self.list_resource_templates().items() if k.startswith('mysql')}
    
    def get_redis_templates(self) -> Dict[str, str]:
        """获取所有 Redis 相关模板"""
        return {k: v for k, v in self.list_resource_templates().items() if k.startswith('redis')}
    
    def get_mongodb_templates(self) -> Dict[str, str]:
        """获取所有 MongoDB 相关模板"""
        return {k: v for k, v in self.list_resource_templates().items() if k.startswith('mongodb')}
    
    def get_resource_leak_templates(self) -> Dict[str, str]:
        """获取所有资源泄露相关的模板"""
        return {k: v for k, v in self.list_resource_templates().items() if 'leak' in k}


def get_resource_monitor_manager() -> ResourceMonitorTemplateManager:
    """获取全局资源监控模板管理器实例（存储于 ApplicationContext）"""
    from crawlo.core.application import get_global_context
    ctx = get_global_context()
    if ctx.resource_monitor_manager is None:
        ctx.resource_monitor_manager = ResourceMonitorTemplateManager()
    return ctx.resource_monitor_manager


def render_resource_monitor_template(template_name: str, **kwargs) -> Optional[Dict[str, str]]:
    """
    渲染资源监控模板的便捷函数
    
    Args:
        template_name: 模板名称
        **kwargs: 模板变量
        
    Returns:
        渲染后的消息字典
    """
    manager = get_resource_monitor_manager()
    return manager.render_resource_template(template_name, **kwargs)


def list_resource_monitor_templates() -> Dict[str, str]:
    """
    列出所有资源监控模板
    
    Returns:
        模板名称和描述的字典
    """
    manager = get_resource_monitor_manager()
    return manager.list_resource_templates()


def get_mysql_monitor_templates() -> Dict[str, str]:
    """
    获取 MySQL 监控模板列表
    
    Returns:
        MySQL 模板名称和描述的字典
    """
    manager = get_resource_monitor_manager()
    return manager.get_mysql_templates()


def get_redis_monitor_templates() -> Dict[str, str]:
    """
    获取 Redis 监控模板列表
    
    Returns:
        Redis 模板名称和描述的字典
    """
    manager = get_resource_monitor_manager()
    return manager.get_redis_templates()


def get_mongodb_monitor_templates() -> Dict[str, str]:
    """
    获取 MongoDB 监控模板列表
    
    Returns:
        MongoDB 模板名称和描述的字典
    """
    manager = get_resource_monitor_manager()
    return manager.get_mongodb_templates()


def get_resource_leak_monitor_templates() -> Dict[str, str]:
    """
    获取资源泄露监控模板列表
    
    Returns:
        资源泄露模板名称和描述的字典
    """
    manager = get_resource_monitor_manager()
    return manager.get_resource_leak_templates()