# 通知系统 (Notification)

> 5 渠道 × 30+ 模板 × 异步投递 — 爬虫运行状态尽在掌握。

## 概述

Crawlo 内置多渠道通知系统，支持将爬虫的运行状态、异常告警、进度更新推送到企业通讯工具。

### 支持渠道

| 渠道 | 配置前缀 | 说明 |
|------|---------|------|
| 钉钉 | `DINGTALK_` | Webhook 机器人 |
| 飞书 | `FEISHU_` | 自定义机器人 |
| 企业微信 | `WECOM_` | 群机器人 |
| 邮件 | `EMAIL_` | SMTP 发送 |
| 短信 | `SMS_` | 短信网关 |

## 快速开始

```python
# settings.py
NOTIFICATION_ENABLED = True
NOTIFICATION_CHANNELS = ['dingtalk', 'feishu']  # 启用钉钉 + 飞书

# 钉钉
DINGTALK_WEBHOOK = "https://oapi.dingtalk.com/robot/send?access_token=YOUR_TOKEN"
DINGTALK_SECRET = "YOUR_SECRET"

# 飞书
FEISHU_WEBHOOK = "https://open.feishu.cn/open-apis/bot/v2/hook/YOUR_HOOK_ID"
FEISHU_SECRET = "YOUR_SECRET"
```

## 渠道配置

### 钉钉

```python
DINGTALK_WEBHOOK = "https://oapi.dingtalk.com/robot/send?access_token=xxx"
DINGTALK_SECRET = "your_secret"          # 签名密钥（可选）
DINGTALK_KEYWORDS = ["爬虫", "告警"]     # 自定义关键词（可选）
```

### 飞书

```python
FEISHU_WEBHOOK = "https://open.feishu.cn/open-apis/bot/v2/hook/xxx"
FEISHU_SECRET = "your_secret"            # 签名校验（可选）
```

### 企业微信

```python
WECOM_WEBHOOK = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx"
WECOM_MENTIONED_LIST = ["@all"]          # @指定成员
```

### 邮件

```python
EMAIL_HOST = "smtp.example.com"
EMAIL_PORT = 587
EMAIL_USER = "crawler@example.com"
EMAIL_PASSWORD = "your_password"
EMAIL_RECIPIENTS = ["admin@example.com"]
EMAIL_USE_TLS = True
```

### 短信

```python
SMS_API_URL = "https://sms-provider.com/api/send"
SMS_API_KEY = "your_key"
SMS_RECIPIENTS = ["+8613800138000"]
SMS_SIGNATURE = "【爬虫监控】"
```

## 消息模板

Crawlo 内置 30+ 消息模板，覆盖爬虫全生命周期。

### 任务生命周期

| 模板 | 触发时机 | 包含信息 |
|------|---------|---------|
| `spider_started` | 爬虫启动 | 爬虫名、启动时间、并发数、队列类型 |
| `spider_finished` | 爬虫结束 | 爬虫名、耗时、抓取量、成功率、退出原因 |
| `spider_paused` | 爬虫暂停 | 爬虫名、暂停时间 |
| `spider_resumed` | 爬虫恢复 | 爬虫名、恢复时间 |
| `spider_error` | 爬虫异常退出 | 爬虫名、异常类型、堆栈摘要 |

### 异常告警

| 模板 | 触发时机 | 包含信息 |
|------|---------|---------|
| `download_error` | 下载异常 | URL、异常类型、重试次数 |
| `memory_warning` | 内存告警 | 当前用量、阈值、进程 PID |
| `queue_full` | 队列溢出 | 队列类型、当前大小、上限 |
| `dead_letter` | 死信产生 | 消息 ID、重试次数、失败原因 |
| `worker_crash` | Worker 崩溃 | Worker ID、最后心跳时间 |
| `proxy_exhausted` | 代理耗尽 | 代理池大小、耗时 |
| `cloudflare_detected` | 触发 CF 挑战 | URL、绕过状态 |

### 进度更新

| 模板 | 触发时机 | 包含信息 |
|------|---------|---------|
| `progress_milestone` | 抓取量达标 | 当前量、目标、速率、进度百分比 |
| `hourly_summary` | 每小时汇总 | 请求数、成功率、队列状态 |
| `daily_report` | 每日报告 | 总抓取量、错误率、Top 错误类型 |

### 数据库监控

| 模板 | 说明 |
|------|------|
| `mysql_pool_status` | MySQL 连接池状态 |
| `redis_status` | Redis 去重集合大小、内存使用 |
| `mongo_pool_status` | MongoDB 连接池状态 |

## 自定义模板

```python
NOTIFICATION_TEMPLATES_CUSTOM = {
    'price_alert': {
        'title': '价格异常告警',
        'content': '商品 {product_name} 价格从 {old_price} 变为 {new_price}',
        'channels': ['dingtalk', 'feishu'],
    }
}
```

在爬虫中手动触发：

```python
from crawlo.bot import get_notifier

notifier = get_notifier()
await notifier.send('price_alert', {
    'product_name': 'iPhone 15',
    'old_price': '¥6999',
    'new_price': '¥5999',
})
```

## 防刷机制

```python
# 同一消息类型的最小间隔（秒），防止消息风暴
NOTIFICATION_DEDUP_WINDOW = 300     # 5 分钟内同类型只发一次
NOTIFICATION_RATE_LIMIT = 10         # 每分钟最大消息数
```

## 配置总览

```python
# settings.py
NOTIFICATION_ENABLED = True
NOTIFICATION_CHANNELS = ['dingtalk', 'feishu', 'wecom', 'email', 'sms']

# 通用
NOTIFICATION_DEDUP_WINDOW = 300
NOTIFICATION_RATE_LIMIT = 10

# 钉钉
DINGTALK_WEBHOOK = "https://oapi.dingtalk.com/robot/send?access_token=xxx"
DINGTALK_SECRET = "your_secret"

# 飞书
FEISHU_WEBHOOK = "https://open.feishu.cn/open-apis/bot/v2/hook/xxx"

# 企业微信
WECOM_WEBHOOK = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx"

# 邮件
EMAIL_HOST = "smtp.example.com"
EMAIL_PORT = 587
EMAIL_USER = "user@example.com"
EMAIL_RECIPIENTS = ["admin@example.com"]

# 短信
SMS_API_URL = "https://sms-provider.com/api/send"
SMS_RECIPIENTS = ["+8613800138000"]
```
