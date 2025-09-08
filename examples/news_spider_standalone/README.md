# 单机版新闻爬虫示例

这个示例演示了Crawlo框架的单机版使用方法。

## 功能特点

- **零配置启动**: 无需复杂配置，开箱即用
- **智能解析**: 多重选择器确保数据提取成功率
- **多格式输出**: 同时输出JSON、CSV和控制台格式
- **错误处理**: 内置重试机制和异常处理
- **性能优化**: 自动调节和下载延迟控制

## 运行方法

```bash
cd /Users/oscar/projects/crawlo/examples/news_spider_standalone
python run.py
```

## 输出文件

- `news_data.json`: JSON格式的新闻数据
- `news_data.csv`: CSV格式的新闻数据
- 控制台实时输出

## 配置说明

在 `run.py` 中可以调整以下配置:
- 并发请求数
- 下载延迟
- 重试次数
- 超时时间
- 下载器类型
- 数据管道