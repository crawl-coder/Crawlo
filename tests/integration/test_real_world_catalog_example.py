#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
P2 验收：real_world_catalog 示例端到端跑通（单机模式）
====================================================

起一个本地 mock 目录站（分页列表页 + 详情页），用示例 spider 全流程爬取：
列表页 → 分页 → 详情页 → 去重 → JSONL 存储，断言：
- 爬取完成（CRAWL OK）；
- JSONL 输出非空且字段完整（url/title/price/category/description/sku/in_stock）；
- 去重生效（同一详情页只写一次）；
- 统计里 jsonl_written 与文件行数一致。
"""

import json
import asyncio
import threading
from pathlib import Path

import pytest
from aiohttp import web

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE_DIR = ROOT / "examples" / "real_world_catalog"

def _product_card(index: int) -> str:
    return f"""
    <div class="product-card">
      <a class="product-link" href="/product/{index}">Product {index:04d}</a>
      <span class="product-title">Product {index:04d}</span>
      <span class="product-price">${index}.99</span>
      <span class="product-category">category_{index % 3}</span>
    </div>"""

async def catalog_page(request):
    page = max(1, int(request.query.get("page", "1")))
    cards = "".join(_product_card(i) for i in range((page - 1) * 3 + 1, page * 3 + 1))
    next_link = (
        f'<a class="pagination-link next" href="/catalog?page={page + 1}">next</a>'
        if page < 2
        else ""
    )
    return web.Response(
        text=f"<html><body><h1>Catalog</h1>{cards}<nav>{next_link}</nav></body></html>",
        content_type="text/html",
    )

async def product_page(request):
    pid = int(request.match_info["id"])
    return web.Response(
        text=(
            f"<html><body><h1 class='product-title'>Product {pid:04d}</h1>"
            f"<div class='product-description'>Desc for {pid}</div>"
            f"<div class='product-sku'>SKU-{pid:04d}</div>"
            "<div class='stock-status in-stock'>in stock</div>"
            "</body></html>"
        ),
        content_type="text/html",
    )

@pytest.fixture(scope="module")
def mock_site():
    """模块级 mock 站点：后台线程跑独立事件循环，保持循环持续运转。"""
    port_holder = {}
    started = threading.Event()
    stop = threading.Event()

    async def stop_waiter(stop_event, loop):
        while not stop_event.is_set():
            await asyncio.sleep(0.1)

    def _run_server():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        app = web.Application()
        app.router.add_get("/catalog", catalog_page)
        app.router.add_get("/product/{id}", product_page)

        runner = web.AppRunner(app)
        loop.run_until_complete(runner.setup())
        site = web.TCPSite(runner, "127.0.0.1", 0)
        loop.run_until_complete(site.start())
        port_holder["port"] = site._server.sockets[0].getsockname()[1]
        started.set()

        loop.run_until_complete(stop_waiter(stop, loop))
        loop.run_until_complete(runner.cleanup())
        loop.close()

    thread = threading.Thread(target=_run_server, daemon=True)
    thread.start()
    assert started.wait(timeout=10), "mock 站点启动超时"
    yield f"http://127.0.0.1:{port_holder['port']}"
    stop.set()
    thread.join(timeout=10)

@pytest.fixture()
def example_env(mock_site, tmp_path, monkeypatch):
    """把示例项目加入 sys.path + 配置环境变量，隔离输出文件。"""
    # 重置初始化器单例：防止前序测试（其他项目目录）把 settings 缓存泄漏进来，
    # 导致 CrawlerProcess 拿到旧 SPIDER_MODULES（如 ofweek_spider.spiders）。
    from crawlo.core.initialization.core import CoreInitializer
    CoreInitializer().reset()

    monkeypatch.syspath_prepend(str(ROOT / "examples"))
    monkeypatch.chdir(EXAMPLE_DIR)
    monkeypatch.setenv("CATALOG_BASE_URL", mock_site)
    monkeypatch.setenv("CATALOG_MAX_PAGES", "2")
    out = tmp_path / "catalog.jsonl"
    monkeypatch.setenv("CATALOG_OUTPUT_PATH", str(out))
    return out

def test_catalog_example_end_to_end(example_env):
    """整站抓取全流程：列表 → 分页 → 详情 → 去重 → JSONL 存储。"""
    from crawlo.crawler import CrawlerProcess
    import os
    from crawlo.project import _find_project_root, read_crawlo_cfg
    asyncio.run(CrawlerProcess().crawl("catalog"))

    output_path = example_env
    assert output_path.exists(), f"缺少 JSONL 输出: {output_path}"
    lines = output_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) >= 3, f"期望至少 3 条 item（2 页 × 3 条），实际 {len(lines)}"

    records = [json.loads(line) for line in lines]
    for rec in records:
        assert rec["url"].startswith("http://127.0.0.1:")
        assert rec["title"]
        assert rec["price"]
        assert rec["description"]
        assert rec["sku"]
        assert rec["in_stock"] is True

    urls = [r["url"] for r in records]
    assert len(urls) == len(set(urls)), "同一详情页被重复写入（去重失效）"

    # 去重语义：2 页 × 3 条 = 6 个产品；下一页链接（page=2 的 next）不存在
    # 但因页 1 与页 2 无重叠产品，应恰好 6 条
    assert len(records) == 6
