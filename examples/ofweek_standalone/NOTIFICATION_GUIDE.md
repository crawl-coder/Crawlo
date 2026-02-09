# ofweek_standalone 通知系统使用指南

## 🎯 概述

本文档介绍如何在 `ofweek_standalone` 项目中使用 Crawlo 通知系统，特别是钉钉通知功能。

## 📋 配置说明

### 1. 通知系统基础配置

在 `settings.py` 中已配置好通知系统：

```python
# 启用通知系统
NOTIFICATION_ENABLED = True
NOTIFICATION_CHANNELS = ['dingtalk']

# 钉钉通知配置
DINGTALK_WEBHOOK = "https://oapi.dingtalk.com/robot/send?access_token=YOUR_TOKEN"
DINGTALK_SECRET = "YOUR_SECRET"
DINGTALK_KEYWORDS = ["爬虫"]
DINGTALK_AT_MOBILES = ["15361276730"]
DINGTALK_IS_AT_ALL = False
```

### 2. 通知类型说明

系统支持三种主要通知类型：

- **状态通知** (`send_crawler_status`) - 用于一般状态更新
- **进度通知** (`send_crawler_progress`) - 用于任务进度汇报  
- **告警通知** (`send_crawler_alert`) - 用于异常和错误提醒

## 🚀 实际使用示例

### 1. 基础通知使用

```python
from crawlo.bot.handlers import send_crawler_status, send_crawler_alert, send_crawler_progress
from crawlo.bot.models import ChannelType

# 发送状态通知
await send_crawler_status(
    title="【状态】爬虫启动",
    content="爬虫任务已启动，开始抓取数据...",
    channel=ChannelType.DINGTALK
)

# 发送进度通知
await send_crawler_progress(
    title="【进度】数据抓取",
    content="已完成 50% 的数据抓取任务",
    channel=ChannelType.DINGTALK
)

# 发送告警通知
await send_crawler_alert(
    title="【告警】网络异常",
    content="检测到网络连接不稳定，部分请求失败",
    channel=ChannelType.DINGTALK
)
```

### 2. 在爬虫中的集成使用

参考 `of_week_with_notifications.py` 文件中的完整示例：

```python
class OfWeekSpiderWithNotifications(Spider):
    async def start_requests(self):
        # 爬虫启动时发送通知
        await send_crawler_status(
            title="【启动】爬虫开始运行",
            content="爬虫任务已启动...",
            channel=ChannelType.DINGTALK
        )
        
        # 原有逻辑...
    
    async def parse(self, response):
        # 处理过程中发送进度通知
        if self.stats['processed_pages'] % 100 == 0:
            await send_crawler_progress(
                title="【进度】处理进度",
                content=f"已处理 {self.stats['processed_pages']} 个页面",
                channel=ChannelType.DINGTALK
            )
        
        # 异常时发送告警
        if response.status_code != 200:
            await send_crawler_alert(
                title="【告警】页面访问失败",
                content=f"URL: {response.url}, 状态码: {response.status_code}",
                channel=ChannelType.DINGTALK
            )
```

## 📊 通知时机建议

### 推荐的通知节点：

1. **爬虫启动时** - 发送状态通知告知任务开始
2. **关键里程碑** - 每处理一定数量页面时发送进度通知
3. **异常情况** - 出现错误时立即发送告警通知
4. **任务完成时** - 发送总结通知汇报最终结果
5. **定期汇报** - 可设置定时任务发送日报/周报

### 通知频率控制：

```python
# 建议的发送频率
if self.processed_items % 100 == 0:  # 每100条数据发送一次进度通知
    await send_progress_notification()

if error_count > threshold:  # 错误超过阈值时发送告警
    await send_alert_notification()
```

## 🔧 高级功能

### 1. @ 功能使用

```python
# @ 特定手机号
DINGTALK_AT_MOBILES = ["15361276730"]

# @ 所有人
DINGTALK_IS_AT_ALL = True

# @ 特定用户ID
DINGTALK_AT_USERIDS = ["user123"]
```

### 2. 重试机制

```python
# 通知发送失败时自动重试
NOTIFICATION_RETRY_ENABLED = True
NOTIFICATION_RETRY_TIMES = 3
NOTIFICATION_RETRY_DELAY = 5  # 秒
```

## 📝 最佳实践

### 1. 通知内容设计

- **标题**：简洁明了，包含状态标识 `[状态][进度][告警]`
- **内容**：结构化信息，包含关键数据和建议措施
- **时机**：选择合适的发送时机，避免过度打扰

### 2. 错误处理

```python
try:
    # 爬虫逻辑
    pass
except Exception as e:
    # 发送详细错误信息
    await send_crawler_alert(
        title="【紧急告警】系统异常",
        content=f"错误详情：{str(e)}\n发生时间：{datetime.now()}",
        channel=ChannelType.DINGTALK
    )
```

### 3. 性能考虑

- 避免过于频繁的通知发送
- 使用异步方式发送通知
- 合理设置超时时间

## 🎯 运行演示

执行以下命令查看通知功能演示：

```bash
cd examples/ofweek_standalone
python ofweek_standalone/notification_demo.py
```

这将演示各种通知类型的使用方法和效果。

## 💡 注意事项

1. 确保钉钉机器人配置正确（Webhook URL 和密钥）
2. 钉钉机器人需要设置关键词验证（如："爬虫"）
3. 网络连接稳定，确保通知能够成功发送
4. 合理控制通知频率，避免信息过载
5. 生产环境中建议开启重试机制

## 🆘 故障排除

### 常见问题：

1. **通知发送失败**：检查网络连接和配置参数
2. **@ 功能不生效**：确认手机号或用户ID正确
3. **关键词验证失败**：检查消息内容是否包含指定关键词
4. **签名验证失败**：确认密钥配置正确

### 调试建议：

```python
# 查看详细响应信息
response = await send_crawler_status(...)
print(f"发送结果: {response.success}")
print(f"错误信息: {response.error}")
```

通过以上配置和使用方法，您就可以在 ofweek_standalone 项目中有效地使用 Crawlo 通知系统了！