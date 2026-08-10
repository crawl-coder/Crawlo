# real_world_catalog — 整站抓取 Cookbook

一个可直接运行的"真实项目级"示例：列表页 → 分页 → 详情页 → 去重 →
存储 → 监控 → 分布式。完整讲解见
[docs/tutorials/real-world-catalog.md](../../docs/tutorials/real-world-catalog.md)。

## 快速开始（单机）

```bash
cd examples/real_world_catalog
python demo_server.py --port 9000     # 终端 1：本地 mock 目录站
python run.py                         # 终端 2：跑爬虫（JSONL 输出）
```

## 分布式

```bash
docker compose up -d redis
python run.py --distributed           # 终端 1（Leader，生成种子）
python run.py --distributed           # 终端 2+（Worker）
```

## MySQL 存储（可选）

```bash
docker compose up -d mysql
CRAWLO_MYSQL_ENABLED=1 python run.py
```
