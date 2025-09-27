# Ofweek 爬虫项目（单机版）

这是一个基于 Crawlo 框架的单机版爬虫项目，用于从 [OFweek 电子工程网](https://ee.ofweek.com/) 抓取新闻数据。

## 项目结构

```
ofweek_standalone/
├── crawlo.cfg              # 项目配置文件
├── run.py                  # 运行脚本
├── logs/                   # 日志目录
├── output/                 # 输出目录
└── ofweek_standalone/      # 项目源代码
    ├── __init__.py
    ├── settings.py         # 项目配置
    ├── items.py            # 数据结构定义
    └── spiders/            # 爬虫目录
        ├── __init__.py
        └── OfweekSpider.py # OFweek 网站爬虫
```

## 运行方式

```bash
# 激活 Conda 环境
conda activate crawl_o

# 运行爬虫
python run.py
```

## 配置说明

- **运行模式**: 单机模式 (standalone)
- **并发数**: 4
- **下载延迟**: 1.0 秒
- **队列类型**: 内存队列
- **去重方式**: 内存去重

## 输出格式

爬虫会将抓取的数据以 JSON 格式保存到 `output/` 目录中。