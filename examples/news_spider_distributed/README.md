# 分布式新闻爬虫示例

这个示例演示了Crawlo框架的分布式功能和高级特性。

## 功能特点

- **Redis分布式队列**: 多节点共享任务队列
- **分布式去重**: Redis实现的全局去重机制
- **多节点协同**: 支持水平扩展，多机器并行处理
- **智能调节**: 自动调节并发数和下载延迟
- **容错机制**: 节点故障自动恢复
- **实时监控**: 统计数据和性能指标
- **数据持久化**: MySQL数据库存储

## 环境要求

- Python 3.10+
- Redis服务器
- MySQL数据库 (可选)

## 快速启动

### 1. 启动Redis服务
```bash
redis-server
```

### 2. 创建数据库 (如果使用MySQL)
```sql
CREATE DATABASE crawlo_news;
USE crawlo_news;

CREATE TABLE news_items (
    id VARCHAR(32) PRIMARY KEY,
    title TEXT,
    url TEXT,
    content LONGTEXT,
    author VARCHAR(255),
    publish_time VARCHAR(100),
    category VARCHAR(100),
    source VARCHAR(100),
    crawl_time DATETIME
);
```

### 3. 单节点运行
```bash
cd /Users/oscar/projects/crawlo/examples/news_spider_distributed
python run.py
```

### 4. 多节点集群运行
```bash
# 启动3个节点的集群
chmod +x start_cluster.sh stop_cluster.sh
./start_cluster.sh 3

# 停止集群
./stop_cluster.sh
```

### 5. 手动部署节点
```bash
# 节点1 (高并发)
python deploy.py news-node-1 --concurrent 25 --daemon

# 节点2 (中等并发)
python deploy.py news-node-2 --concurrent 20 --daemon

# 节点3 (低并发)
python deploy.py news-node-3 --concurrent 15 --daemon
```

## 配置说明

### Redis配置
- URL: `redis://localhost:6379/0`
- 队列: `crawlo:requests`
- 去重: `crawlo:dupefilter`
- 统计: `crawlo:stats`

### 性能配置
- 并发请求数: 15-30 (根据节点调整)
- 下载延迟: 0.5秒
- 自动调节: 启用
- 重试次数: 5次
- 超时时间: 60秒

### 数据管道
- 控制台输出: 实时显示
- JSON文件: 追加模式保存
- MySQL数据库: 结构化存储

## 监控和调试

### 查看运行状态
```bash
# 查看运行中的进程
ps aux | grep python

# 查看Redis队列状态
redis-cli -u redis://localhost:6379/0
> LLEN crawlo:requests
> SCARD crawlo:dupefilter
```

### 日志查看
```bash
# 查看实时日志
tail -f logs/*.log

# 查看错误日志
grep ERROR logs/*.log
```

### 性能监控
```bash
# Redis内存使用
redis-cli info memory

# 队列长度监控
watch -n 5 'redis-cli LLEN crawlo:requests'
```

## 扩展使用

### 自定义配置
修改 `run.py` 中的配置:
```python
config = (CrawloConfig.distributed()
          .set_redis_url('redis://your-redis-server:6379/0')
          .set_concurrent_requests(50)  # 调整并发数
          .set_download_delay(0.2)      # 调整延迟
          # ... 其他配置
         )
```

### 添加中间件
```python
config.add_middleware('proxy', proxy_list=['proxy1:8080', 'proxy2:8080'])
config.add_middleware('user_agent', rotate=True)
```

### 自定义数据管道
```python
config.add_pipeline('elasticsearch', 
                   hosts=['localhost:9200'],
                   index='news_items')
```

## 最佳实践

1. **合理设置并发数**: 根据目标网站负载能力调整
2. **监控队列状态**: 防止队列积压
3. **定期清理Redis**: 避免内存占用过高
4. **使用代理轮换**: 大规模爬取时推荐
5. **数据验证**: 确保爬取质量
6. **容错处理**: 设置合理的重试策略

## 故障排除

### Redis连接失败
- 检查Redis服务是否启动
- 验证连接URL是否正确
- 检查网络防火墙设置

### 数据库连接问题
- 确认MySQL服务运行
- 验证数据库连接参数
- 检查表结构是否创建

### 性能问题
- 调整并发数和延迟设置
- 监控Redis内存使用
- 检查网络带宽限制