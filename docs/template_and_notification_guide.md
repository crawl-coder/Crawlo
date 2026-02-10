# Crawlo 模板和通知系统综合指南

## 📋 概述

Crawlo 框架提供了强大的消息模板和通知系统，包括：

- **通用消息模板**：支持预定义和自定义模板
- **资源监控模板**：专门针对 MySQL、Redis、MongoDB 的监控模板
- **消息去重功能**：防止重复发送相同内容的通知
- **枚举支持**：提供枚举类型支持，便于 IDE 自动补全

## 🚀 快速开始

### 1. 基本使用

```python
from crawlo.bot import send_template_notification, ChannelType, Template

# 使用预定义模板发送通知
response = send_template_notification(
    Template.task_startup,  # 使用枚举
    task_name='新闻爬虫',
    target='OFweek电子工程网', 
    estimated_time='5-10分钟',
    channel=ChannelType.DINGTALK
)
```

### 2. 查看可用模板

```python
from crawlo.bot import list_notification_templates

templates = list_notification_templates()
for name, description in templates.items():
    print(f"{name}: {description}")
```

## 🎯 使用枚举获得更好的开发体验

为了提升开发体验，Crawlo提供了枚举类来访问模板变量和模板名称：

### 模板名称枚举
```python
from crawlo.bot import Template

# 使用枚举访问模板名称
Template.task_startup      # 'task_startup'
Template.http_error        # 'http_error'
Template.login_failed      # 'login_failed'
Template.resource_monitor  # 'resource_monitor'
```

### 模板变量枚举
```python
from crawlo.bot import TemplateVar

# 使用枚举访问变量名称
TemplateVar.task_name      # TemplateVariable.TASK_NAME
TemplateVar.status_code    # TemplateVariable.STATUS_CODE
TemplateVar.error_message  # TemplateVariable.ERROR_MESSAGE
```

### IDE友好的使用方式
```python
from crawlo.bot import send_template_notification, Template, TemplateVar, ChannelType

# 发送HTTP错误通知 - 使用枚举
send_template_notification(
    Template.http_error,
    **{
        TemplateVar.status_code.value: 403,
        TemplateVar.url.value: 'https://example.com',
        TemplateVar.response_time.value: 1500,
        TemplateVar.retry_count.value: 3
    },
    channel=ChannelType.DINGTALK
)
```

## 📋 查询模板参数

你可以使用 `get_template_parameters()` 函数来查询特定模板需要哪些参数：

```python
from crawlo.bot import get_template_parameters, Template

# 查询启动模板的参数
params = get_template_parameters(Template.task_startup)
print(params)  # ['task_name', 'target', 'estimated_time']

# 查询进度模板的参数
progress_params = get_template_parameters(Template.task_progress)
print(progress_params)  # ['task_name', 'percentage', 'current_count']

# 查询HTTP错误模板的参数
error_params = get_template_parameters(Template.http_error)
print(error_params)  # ['status_code', 'url', 'response_time', 'retry_count']
```

这个功能可以帮助你在使用模板时知道需要提供哪些参数，避免遗漏或错误。

## 📋 预定义模板

### 任务通知模板
- `task_startup`: 任务启动通知
- `task_completion`: 任务完成通知  
- `task_progress`: 任务进度通知

### 异常通知模板
- `error_alert`: 错误告警通知
- `performance_warning`: 性能警告通知

### 统计报告模板
- `daily_report`: 日报统计
- `weekly_report`: 周报统计

### 爬虫场景模板
- `http_error`: HTTP请求异常
- `login_failed`: 登录失败告警
- `proxy_issue`: 代理网络异常
- `captcha_detected`: 验证码拦截
- `parse_failure`: 数据解析失败
- `resource_monitor`: 资源监控告警
- `db_connection_error`: 数据库连接异常
- `security_alert`: 安全告警

## 🛠️ 模板变量说明

### 任务相关变量
| 变量名 | 说明 | 示例 |
|--------|------|------|
| `task_name` | 任务名称 | 新闻爬虫 |
| `target` | 目标地址 | OFweek电子工程网 |
| `estimated_time` | 预计时长 | 5-10分钟 |
| `success_count` | 成功数量 | 156 |
| `duration` | 执行时长 | 8分23秒 |
| `percentage` | 完成百分比 | 65.5 |
| `current_count` | 当前数量 | 102 |

### 爬虫特定变量
| 变量名 | 说明 | 示例 |
|--------|------|------|
| `status_code` | HTTP状态码 | 403 |
| `response_time` | 响应时间(ms) | 1500 |
| `url` | 请求URL | https://example.com |
| `user_agent` | 用户代理 | Chrome/91.0 |
| `proxy_used` | 是否使用代理 | 是/否 |
| `retry_count` | 重试次数 | 3 |
| `proxy_status` | 代理状态 | 连接超时 |
| `login_status` | 登录状态 | 成功/失败 |
| `cookie_status` | Cookie状态 | 有效/无效 |
| `session_status` | 会话状态 | 正常/过期 |
| `captcha_status` | 验证码状态 | 检测到/未检测 |
| `parse_success` | 解析是否成功 | 是/否 |
| `data_count` | 数据条数 | 156 |
| `error_type` | 错误类型 | ParseError |
| `request_method` | 请求方法 | GET/POST |

### 统计相关变量
| 变量名 | 说明 | 示例 |
|--------|------|------|
| `date` | 日期 | 2024-01-15 |
| `new_count` | 新增数量 | 156 |
| `total_count` | 总数量 | 1250 |
| `success_rate` | 成功率 | 98.5 |
| `period` | 统计周期 | 2024-01-01至2024-01-15 |
| `daily_avg` | 日均数量 | 83 |

### 系统相关变量
| 变量名 | 说明 | 示例 |
|--------|------|------|
| `config_item` | 配置项 | DATABASE_URL |
| `old_value` | 原值 | old_value |
| `new_value` | 新值 | new_value |
| `update_time` | 更新时间 | 2024-01-15 14:30 |
| `maintenance_time` | 维护时间 | 2024-01-15 23:00 |
| `impact_scope` | 影响范围 | 数据抓取服务 |

## 🚨 资源监控模板

Crawlo 还提供了专门用于监控 MySQL、Redis、MongoDB 资源使用情况的模板：

```python
from crawlo.bot import (
    render_resource_monitor_template,
    ResourceTemplate,
    ResourceMonitorVariable
)

# MySQL 连接池监控
result = render_resource_monitor_template(
    ResourceTemplate.MYSQL_CONNECTION_POOL_MONITOR.value,
    pool_status="正常",
    active_connections=15,
    idle_connections=5,
    max_connections=50,
    waiting_connections=0,
    timestamp="2026-02-10 11:30:00"
)

# Redis 内存监控
result = render_resource_monitor_template(
    ResourceTemplate.REDIS_MEMORY_MONITOR.value,
    used_memory="2.5GB",
    max_memory="4GB",
    memory_usage_percent=62.5,
    memory_fragmentation_ratio=1.2,
    hit_rate=98.5,
    timestamp="2026-02-10 11:30:00"
)
```

### 资源监控枚举

使用 `ResourceTemplate` 枚举访问资源监控模板，使用 `ResourceMonitorVariable` 枚举访问模板变量。

### 资源泄露检测

特别提供资源泄露检测模板，用于监控和告警数据库连接泄露、内存泄露等问题：

```python
# MySQL 资源泄露告警
result = render_resource_monitor_template(
    ResourceTemplate.MYSQL_RESOURCE_LEAK_ALERT.value,
    current_connections=45,
    max_connections=50,
    leak_type="连接泄露",
    leak_tag="POOL_OVERFLOW",
    discovery_time="2026-02-10 11:30:00",
    impact_scope="用户服务模块"
)
```

### 资源监控模板使用方式

#### 1. 基本使用

```python
from crawlo.bot import (
    render_resource_monitor_template,
    ResourceTemplate,
    ResourceMonitorVariable
)

# 使用 MySQL 连接池监控模板
result = render_resource_monitor_template(
    ResourceTemplate.MYSQL_CONNECTION_POOL_MONITOR.value,
    pool_status="正常",
    active_connections=15,
    idle_connections=5,
    max_connections=50,
    waiting_connections=0,
    timestamp="2026-02-10 11:30:00"
)
```

#### 2. MySQL 监控模板

##### 连接池监控
```python
# MySQL 连接池状态监控
render_resource_monitor_template(
    ResourceTemplate.MYSQL_CONNECTION_POOL_MONITOR.value,
    pool_status="正常",
    active_connections=15,
    idle_connections=5,
    max_connections=50,
    waiting_connections=0,
    timestamp="2026-02-10 11:30:00"
)
```

##### 资源泄露告警
```python
# MySQL 资源泄露告警
render_resource_monitor_template(
    ResourceTemplate.MYSQL_RESOURCE_LEAK_ALERT.value,
    current_connections=45,
    max_connections=50,
    leak_type="连接泄露",
    leak_tag="POOL_OVERFLOW",
    discovery_time="2026-02-10 11:30:00",
    impact_scope="用户服务模块"
)
```

##### 慢查询告警
```python
# MySQL 慢查询告警
render_resource_monitor_template(
    ResourceTemplate.MYSQL_SLOW_QUERY_ALERT.value,
    sql_statement="SELECT * FROM users WHERE email LIKE '%@example.com'",
    execution_time=5.2,
    affected_rows=10000,
    target_table="users",
    query_source="user_service"
)
```

#### 3. Redis 监控模板

##### 内存监控
```python
# Redis 内存使用监控
render_resource_monitor_template(
    ResourceTemplate.REDIS_MEMORY_MONITOR.value,
    used_memory="2.5GB",
    max_memory="4GB",
    memory_usage_percent=62.5,
    memory_fragmentation_ratio=1.2,
    hit_rate=98.5,
    timestamp="2026-02-10 11:30:00"
)
```

##### 连接监控
```python
# Redis 连接监控
render_resource_monitor_template(
    ResourceTemplate.REDIS_CONNECTION_MONITOR.value,
    connection_status="健康",
    connected_clients=120,
    max_clients=1000,
    input_kbps=1024,
    output_kbps=2048,
    timestamp="2026-02-10 11:30:00"
)
```

#### 4. MongoDB 监控模板

##### 连接监控
```python
# MongoDB 连接监控
render_resource_monitor_template(
    ResourceTemplate.MONGODB_CONNECTION_MONITOR.value,
    pool_status="健康",
    current_connections=8,
    available_connections=12,
    pending_requests=0,
    timestamp="2026-02-10 11:30:00"
)
```

##### 慢操作告警
```python
# MongoDB 慢操作告警
render_resource_monitor_template(
    ResourceTemplate.MONGODB_SLOW_OPERATION_ALERT.value,
    operation_type="find",
    execution_time=3.5,
    collection_name="products",
    documents_affected=5000,
    operation_source="product_service"
)
```

### 资源监控模板列表

#### MySQL 模板
1. `mysql_connection_pool_monitor` - 连接池监控
2. `mysql_resource_leak_alert` - 资源泄露告警
3. `mysql_slow_query_alert` - 慢查询告警
4. `mysql_deadlock_alert` - 死锁告警

#### Redis 模板
1. `redis_memory_monitor` - 内存监控
2. `redis_connection_monitor` - 连接监控
3. `redis_resource_leak_alert` - 资源泄露告警
4. `redis_key_ttl_monitor` - Key 过期监控

#### MongoDB 模板
1. `mongodb_connection_monitor` - 连接监控
2. `mongodb_resource_leak_alert` - 资源泄露告警
3. `mongodb_slow_operation_alert` - 慢操作告警
4. `mongodb_index_miss_alert` - 索引缺失告警

#### 通用模板
1. `general_resource_monitor` - 通用资源监控
2. `general_resource_leak_alert` - 通用资源泄露告警

### 资源监控应用场景

#### 1. 定期资源监控
```python
# 定期发送资源监控报告
def send_periodic_resource_report():
    # 获取 MySQL 状态
    mysql_stats = get_mysql_stats()
    
    # 发送监控通知
    render_resource_monitor_template(
        ResourceTemplate.MYSQL_CONNECTION_POOL_MONITOR.value,
        pool_status=mysql_stats['status'],
        active_connections=mysql_stats['active'],
        idle_connections=mysql_stats['idle'],
        max_connections=mysql_stats['max'],
        waiting_connections=mysql_stats['waiting'],
        timestamp=mysql_stats['timestamp']
    )
```

#### 2. 资源泄露检测告警
```python
# 检测到资源泄露时发送告警
def alert_resource_leak(resource_type, leak_details):
    if resource_type == 'mysql':
        template = ResourceTemplate.MYSQL_RESOURCE_LEAK_ALERT.value
    elif resource_type == 'redis':
        template = ResourceTemplate.REDIS_RESOURCE_LEAK_ALERT.value
    elif resource_type == 'mongodb':
        template = ResourceTemplate.MONGODB_RESOURCE_LEAK_ALERT.value
    else:
        template = ResourceTemplate.GENERAL_RESOURCE_LEAK_ALERT.value
    
    render_resource_monitor_template(
        template,
        resource_type=resource_type,
        leak_details=leak_details,
        growth_trend=get_growth_trend(leak_details),
        severity_level=get_severity_level(leak_details),
        discovery_time=datetime.now(),
        affected_service=get_affected_service(leak_details)
    )
```

## 🔁 消息去重功能

Crawlo 框架现在支持消息去重功能，可以自动检测和过滤重复的消息，防止在短时间内重复发送相同内容的通知。

### 功能特点

- **自动检测重复消息**：基于标题、内容和渠道的组合判断
- **时间窗口控制**：默认5分钟内相同消息视为重复
- **跨渠道独立**：不同渠道的消息独立判断
- **线程安全**：支持并发环境下的安全使用
- **低性能影响**：使用高效的哈希算法

### 使用方式

#### 1. 基本使用

```python
from crawlo.bot import send_template_notification, Template, ChannelType

# 第一次发送 - 会成功发送
send_template_notification(
    Template.task_startup,
    task_name='爬虫任务',
    target='目标网站',
    estimated_time='5分钟',
    channel=ChannelType.DINGTALK
)

# 第二次发送相同内容 - 会被去重机制拦截
send_template_notification(
    Template.task_startup,
    task_name='爬虫任务',
    target='目标网站',
    estimated_time='5分钟',
    channel=ChannelType.DINGTALK
)
```

#### 2. 不同消息不会被去重

```python
# 不同标题 - 会被发送
send_template_notification(
    Template.task_startup,
    task_name='爬虫任务A',
    target='目标网站',
    estimated_time='5分钟',
    channel=ChannelType.DINGTALK
)

send_template_notification(
    Template.task_startup,
    task_name='爬虫任务B',  # 不同标题
    target='目标网站',
    estimated_time='5分钟',
    channel=ChannelType.DINGTALK
)

# 不同内容 - 会被发送
send_template_notification(
    Template.task_startup,
    task_name='爬虫任务',
    target='目标网站A',  # 不同内容
    estimated_time='5分钟',
    channel=ChannelType.DINGTALK
)

send_template_notification(
    Template.task_startup,
    task_name='爬虫任务',
    target='目标网站B',  # 不同内容
    estimated_time='5分钟',
    channel=ChannelType.DINGTALK
)

# 不同渠道 - 会被发送
send_template_notification(
    Template.task_startup,
    task_name='爬虫任务',
    target='目标网站',
    estimated_time='5分钟',
    channel=ChannelType.DINGTALK
)

send_template_notification(
    Template.task_startup,
    task_name='爬虫任务',
    target='目标网站',
    estimated_time='5分钟',
    channel=ChannelType.FEISHU  # 不同渠道
)
```

### 配置选项

#### 时间窗口配置

可以通过修改时间窗口来调整去重敏感度：

```python
from crawlo.bot.duplicate_manager import get_deduplicator

# 获取去重器实例，设置10分钟时间窗口
deduplicator = get_deduplicator(time_window=600)  # 10分钟
```

### API 接口

#### MessageDeduplicator 类

```python
class MessageDeduplicator:
    def __init__(self, time_window: int = 300):
        """初始化去重器，time_window 为时间窗口（秒）"""
    
    def is_duplicate(self, title: str, content: str, channel: str) -> bool:
        """检查消息是否为重复，如果是则返回 True"""
    
    def add_message(self, title: str, content: str, channel: str) -> None:
        """手动添加消息到去重记录"""
    
    def clear_history(self) -> None:
        """清空所有历史记录"""
```

#### 全局实例

```python
from crawlo.bot import get_deduplicator

# 获取全局去重器实例
deduplicator = get_deduplicator()
```

### 技术原理

消息去重基于以下要素的组合：
- 消息标题
- 消息内容  
- 发送渠道
- 时间窗口（默认300秒）

系统使用 SHA256 哈希算法生成消息的唯一标识，并在内存中维护一个时间窗口内的消息记录。

### 工作流程

1. **消息生成**：当发送通知时，系统生成消息的哈希值
2. **重复检查**：检查哈希值是否在时间窗口内存在
3. **去重决策**：如果存在则跳过发送，否则发送并记录
4. **过期清理**：定期清理过期的消息记录

### 性能影响

- **内存占用**：少量内存存储哈希值和时间戳
- **CPU 开销**：每次发送消息时进行一次哈希计算
- **并发安全**：使用线程锁保证并发环境下的安全性

## 💡 实际应用示例

### 1. 爬虫启动通知
```python
def start_requests(self):
    send_template_notification(
        Template.task_startup,
        task_name=self.name,
        target='新闻网站',
        estimated_time='8-12分钟'
    )
    # 爬虫逻辑...
```

### 2. 进度通知
```python
def parse(self, response):
    self.stats['items_count'] += 1
    
    # 每100条发送进度通知
    if self.stats['items_count'] % 100 == 0:
        percentage = (self.stats['items_count'] / 1000) * 100
        send_template_notification(
            Template.task_progress,
            task_name=self.name,
            percentage=f"{percentage:.1f}",
            current_count=self.stats['items_count']
        )
```

### 3. 完成通知
```python
def closed(self, reason):
    duration = self.calculate_duration()
    send_template_notification(
        Template.task_completion,
        task_name=self.name,
        success_count=self.stats['items_count'],
        duration=duration
    )
```

### 5. HTTP错误处理
```python
def handle_http_error(self, response):
    if response.status_code != 200:
        send_template_notification(
            Template.http_error,
            status_code=response.status_code,
            url=response.url,
            response_time=response.meta.get('download_latency', 0) * 1000,
            retry_count=response.meta.get('retry_times', 0)
        )
```

### 6. 登录状态监控
```python
def check_login_status(self, login_result):
    if not login_result['success']:
        send_template_notification(
            Template.login_failed,
            login_status='失败' if not login_result['logged_in'] else '成功',
            cookie_status='有效' if login_result['cookie_valid'] else '无效',
            session_status='正常' if login_result['session_active'] else '过期',
            error_time=self.get_current_time()
        )
```

### 7. 资源监控
```python
def monitor_resources(self):
    stats = self.get_system_stats()
    if stats['memory_usage'] > 80:
        send_template_notification(
            Template.resource_monitor,
            memory_usage=stats['memory_usage'],
            cpu_usage=stats['cpu_usage'],
            disk_usage=stats['disk_usage'],
            active_connections=stats['active_connections']
        )
```

## 🎨 自定义模板

### 1. 添加自定义模板
```python
from crawlo.bot import add_custom_notification_template

# 添加业务特定模板
add_custom_notification_template(
    'stock_alert',
    '📈 {stock_name} 价格预警',
    '⚠️ 当前价格：{current_price}\n📊 涨跌幅：{change_percent}%'
)
```

### 2. 使用自定义模板
```python
send_template_notification(
    'stock_alert',
    stock_name='腾讯控股',
    current_price='325.80',
    change_percent='-2.3'
)
```

### 3. 批量添加模板
```python
custom_templates = {
    'api_monitor': {
        'title': '🌐 API监控告警',
        'content': '❌ {api_name} 接口异常\n📊 响应时间：{response_time}ms\n⏰ 发生时间：{alert_time}'
    },
    'data_quality': {
        'title': '🔍 数据质量报告',
        'content': '✅ 有效数据：{valid_count} 条\n❌ 异常数据：{invalid_count} 条\n📊 完整率：{completeness_rate}%'
    }
}

for name, template in custom_templates.items():
    add_custom_notification_template(
        name, 
        template['title'], 
        template['content']
    )
```

## 🔧 高级用法

### 1. 直接使用模板管理器
```python
from crawlo.bot import get_template_manager

manager = get_template_manager()
message = manager.render_template(
    'task_completion',
    task_name='新闻爬虫',
    success_count=156,
    duration='8分23秒'
)

if message:
    print(f"标题: {message['title']}")
    print(f"内容: {message['content']}")
```

### 2. 条件性通知
```python
def send_conditional_notification(self):
    if self.stats['error_count'] > 10:
        template = Template.error_alert
        variables = {
            'task_name': self.name,
            'error_message': f'错误数量过多: {self.stats["error_count"]}',
            'error_time': self.get_current_time()
        }
    elif self.stats['success_rate'] < 95:
        template = Template.performance_warning
        variables = {
            'metric_name': '成功率',
            'current_value': f"{self.stats['success_rate']}%",
            'threshold': '95%'
        }
    else:
        template = Template.task_completion
        variables = {
            'task_name': self.name,
            'success_count': self.stats['success_count'],
            'duration': self.get_duration()
        }
    
    send_template_notification(template, **variables)
```

## 📊 最佳实践

### 1. 模板设计原则
- **简洁明了**：突出核心信息
- **结构统一**：保持一致的格式风格
- **变量清晰**：使用有意义的变量名
- **适度emoji**：增强可读性但不过度使用

### 2. 性能优化
```python
# 缓存常用模板渲染结果
class NotificationCache:
    def __init__(self):
        self.cache = {}
    
    def get_cached_message(self, template_name, **kwargs):
        cache_key = f"{template_name}_{hash(frozenset(kwargs.items()))}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        message = render_message(template_name, **kwargs)
        self.cache[cache_key] = message
        return message

# 使用缓存
cache = NotificationCache()
message = cache.get_cached_message('task_progress', **variables)
```

### 3. 错误处理
```python
def safe_send_notification(template_name, **kwargs):
    try:
        response = send_template_notification(template_name, **kwargs)
        if not response.success:
            logger.warning(f"通知发送失败: {response.message}")
    except Exception as e:
        logger.error(f"发送通知时发生异常: {e}")
```

## 🚨 注意事项

1. **变量完整性**：使用模板时确保提供所有必需的变量
2. **性能影响**：频繁的资源监控可能影响性能，建议合理设置监控频率
3. **阈值设置**：根据实际业务情况设置合理的监控阈值
4. **告警降噪**：对于周期性的资源使用高峰，应适当调整告警策略
5. **时间窗口**：合理设置时间窗口，过短可能导致误判，过长占用过多内存
6. **内存清理**：系统会自动清理过期记录，无需手动干预
7. **渠道独立**：不同渠道的消息独立判断，不会相互影响
8. **故障处理**：即使去重功能异常也不会影响消息发送
9. **变量完整性**：确保传递所有必需的模板变量
10. **模板存在性**：使用前检查模板是否存在
11. **渠道配置**：确保通知渠道已正确配置
12. **性能考虑**：避免在高频循环中频繁发送通知
13. **错误处理**：合理处理模板渲染和发送失败的情况

## ✅ 最佳实践总结

1. **合理使用**：在可能产生重复消息的场景下充分利用去重功能
2. **差异化内容**：尽可能使消息内容有所区别，提高消息价值
3. **监控去重率**：关注去重功能的效果，适时调整参数
4. **错误处理**：确保去重功能异常时不影响核心消息发送逻辑
5. **分层监控**：建立不同级别的监控（正常、警告、告警）
6. **趋势分析**：不仅关注当前值，还要分析资源使用的趋势
7. **关联分析**：将资源监控与业务指标关联分析
8. **自动化处理**：结合自动化脚本实现告警的自动处理

## 📞 支持渠道

模板系统支持所有Crawlo框架支持的通知渠道：
- 钉钉 (DingTalk)  
- 飞书 (Feishu)  
- 企业微信 (WeCom)
- 邮件 (Email)
- 短信 (SMS)

通过统一的模板接口，可以轻松切换不同的通知渠道。

## 🎯 通知格式优化

从版本 1.5.9 开始，Crawlo 通知系统进行了格式优化，简化了消息前缀，使通知更加简洁明了：

### 优化内容
1. **移除冗余前缀**：移除了 "Crawlo-Status"、"Crawlo-Alert" 等冗长前缀
2. **避免图标重复**：确保每个通知只包含一个图标，避免渠道处理器和模板同时添加图标导致重复
3. **保持图标标识**：保留了适当的 emoji 图标以增强可读性
4. **统一格式风格**：各渠道采用一致的简洁格式
5. **提升可读性**：消息内容更加直观清晰

### 格式对比

**优化前**：
- 钉钉：`🚀 Crawlo-Status | 任务名称 开始执行`
- 飞书：`📊 Crawlo-Progress | 任务进度通知`
- 企业微信：`🚨 Crawlo-Alert | 错误告警信息`

**优化后**：
- 钉钉：`🚀 任务名称 开始执行`
- 飞书：`📊 任务进度通知` 
- 企业微信：`🚨 错误告警信息`

通过这种优化，通知消息变得更加简洁，同时保留了必要的标识和可读性。
