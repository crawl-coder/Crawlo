# Crawlo Examples

所有示例均使用双层项目结构（与 `crawlo startproject` 生成的一致），支持 `--schedule` 定时任务模式。

## 示例索引

| 示例 | 学什么 | 运行方式 | 关键配置 |
|------|--------|---------|---------|
| **ofweek_standalone** | 工程化单机爬虫：通知/DB/自适应抓取 | `python run.py` | `settings.py` 中 `SCHEDULER_ENABLED` |
| **ofweek_distributed** | 分布式爬虫：Redis Streams + Worker 集群 | `python run.py`（多终端启动多 Worker） | `QUEUE_TYPE = redis_stream` |
| **ofweek_spider** | 最简模板项目（startproject 生成后微调） | `python run.py` | `SPIDER_MODULES` |
| **errback_examples** | errback 错误回调：基础/智能重试/async start | `python run.py basic_errback` | `RETRY_TIMES` |
| **eastmoney_fin_report_crawler** | 多 spider 并发：6 个财报爬虫同时运行 | `python run.py` | `CONCURRENCY` |
| **listed_companies_market_value_info** | 数据管道 + 股票数据采集 | `python run.py` | `SCHEDULER_ENABLED` |
| **infoq_dynamic_test** | 动态下载器：Playwright/CloakBrowser | `python run.py protocol` | `DOWNLOADER` |
| **scrapy_ofweek** | Scrapy 兼容示例（非 Crawlo 原生） | `scrapy crawl ofweek_spider` | `scrapy.cfg` |

## 通用运行方式

```bash
# 正常爬虫运行模式
cd examples/<project_name>
python run.py

# 定时任务模式
python run.py --schedule
```

> **注意**：运行示例前需将 Crawlo 安装到当前环境（`pip install -e .`），或将仓库根目录加入 `PYTHONPATH`。
