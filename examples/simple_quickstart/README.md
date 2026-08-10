# simple_quickstart — 30 行跑通第一个爬虫

最小的 Crawlo 爬虫：抓取 **ee.ofweek.com**（与 ofweek_standalone /
ofweek_distributed 同一个网站），列表页 → 详情页 → 打印标题。

## 运行

```bash
cd examples/simple_quickstart
python run.py
```

默认抓取真实站点（`https://ee.ofweek.com/`）。本地/CI 无网环境可用
`demo_server.py` 起的 mock 站（与真实站点同结构同选择器）：

```bash
python demo_server.py --port 9100     # 终端 1
OFWEEK_BASE_URL=http://127.0.0.1:9100 python run.py   # 终端 2
```

## 代码只有 23 行

见 [simple_spider.py](simple_quickstart/spiders/simple_spider.py)（23 行）：
`Spider` 子类 + 列表解析 + 详情解析。输出落到 `output/items.jsonl`
（由 12 行的 [pipelines.py](simple_quickstart/pipelines.py) 负责）。

从它开始学，再到
[real_world_catalog](../real_world_catalog/README.md)（工程化）和
[ofweek_distributed](../ofweek_distributed/run.py)（分布式）。
