# Ofweek 爬虫项目（混合版）

这是一个基于 Crawlo 框架的混合版爬虫项目，用于从 [OFweek 电子工程网](https://ee.ofweek.com/) 抓取新闻数据。该项目支持单机和分布式模式的无缝切换。

## 项目结构

```
ofweek_spider/
├── crawlo.cfg              # 项目配置文件
├── run.py                  # 运行脚本
├── logs/                   # 日志目录
├── output/                 # 输出目录
└── ofweek_spider/          # 项目源代码
    ├── __init__.py
    ├── settings.py         # 项目配置（支持模式切换）
    ├── items.py            # 数据结构定义
    └── spiders/            # 爬虫目录
        ├── __init__.py
        └── OfweekSpider.py # OFweek 网站爬虫
```

## 运行方式

### 单机模式（默认）

```bash
# 激活 Conda 环境
conda activate crawl_o

# 运行爬虫（单机模式）
python run.py
```

### 分布式模式

```bash
# 激活 Conda 环境
conda activate crawl_o

# 设置环境变量切换到分布式模式
export CRAWLO_MODE=distributed

# 启动 Redis 服务（如果尚未启动）
# redis-server

# 运行爬虫
python run.py
```

## 配置说明

项目通过环境变量 `CRAWLO_MODE` 来切换运行模式：

- **单机模式** (`standalone`): 
  - 使用内存队列和去重
  - 适合开发测试和小规模数据采集
  - 无需额外依赖

- **分布式模式** (`distributed`):
  - 使用 Redis 队列和去重
  - 适合大规模数据采集和多节点部署
  - 需要 Redis 环境支持

## 输出格式

爬虫会将抓取的数据以 JSON 格式保存到 `output/` 目录中。

## 注意事项

1. **分布式模式需要 Redis**：运行分布式模式前请确保 Redis 服务已启动
2. **网络请求限制**：为了防止被目标网站封禁，请适当设置下载延迟
3. **数据量控制**：示例中只抓取前 100 页数据，可根据需要调整
4. **Cookie 有效期**：示例中的 Cookie 可能已过期，请根据实际情况更新

## 故障排除

### Redis 连接失败

```
❌ Redis 连接失败: Connection refused
💡 请确保 Redis 服务已启动并可访问
```

解决方法：
1. 启动 Redis 服务：`redis-server`
2. 检查 Redis 配置是否正确
3. 确保防火墙未阻止 Redis 端口

### 爬虫运行缓慢

解决方法：
1. 检查网络连接
2. 适当调整 `CONCURRENCY` 和 `DOWNLOAD_DELAY` 参数
3. 检查目标网站是否限制了请求频率

### 数据抓取不完整

解决方法：
1. 检查 XPath 表达式是否正确
2. 查看日志文件分析具体错误
3. 更新请求头和 Cookie 信息