#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
P3 验收：simple_quickstart 端到端跑通（同一网站 ee.ofweek.com 结构）
=================================================================

用 ofweek 结构 mock 站验证：列表页 → 详情页 → Item 输出。
断言：3 条 News 均被 ConsolePipeline 处理（通过统计验证）。
"""

import asyncio
import threading
from pathlib import Path

import pytest
from aiohttp import web

ROOT = Path(__file__).resolve().parents[2]
QUICKSTART_DIR = ROOT / "examples" / "simple_quickstart"


def _list_page() -> str:
    rows = ""
    for i in range(1, 4):
        rows += (
            f'<div class="model_right model_right2">'
            f'<h3><a href="/news/{i}">News {i:03d}</a></h3></div>'
        )
    return f'<html><body><div class="main_left"><div class="list_model">{rows}</div></div></body></html>'


def _detail_page(i: int) -> str:
    return (
        f'<html><body><div class="title"><h1>News {i:03d}</h1></div>'
        f'<div class="TRS_Editor"><p>content {i}</p></div></body></html>'
    )


async def list_handler(request):
    return web.Response(text=_list_page(), content_type="text/html")


async def detail_handler(request):
    return web.Response(text=_detail_page(int(request.match_info["id"])), content_type="text/html")


@pytest.fixture(scope="module")
def mock_site():
    """ofweek 结构 mock 站（后台线程 + 独立事件循环）。"""
    port_holder = {}
    started = threading.Event()
    stop = threading.Event()

    async def _waiter():
        while not stop.is_set():
            await asyncio.sleep(0.1)

    def _run():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        app = web.Application()
        app.router.add_get("/CATList-2800-8100-ee-1.html", list_handler)
        app.router.add_get("/news/{id}", detail_handler)
        runner = web.AppRunner(app)
        loop.run_until_complete(runner.setup())
        site = web.TCPSite(runner, "127.0.0.1", 0)
        loop.run_until_complete(site.start())
        port_holder["port"] = site._server.sockets[0].getsockname()[1]
        started.set()
        loop.run_until_complete(_waiter())
        loop.run_until_complete(runner.cleanup())
        loop.close()

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    assert started.wait(timeout=10), "mock 站启动超时"
    yield f"http://127.0.0.1:{port_holder['port']}"
    stop.set()
    thread.join(timeout=10)


def test_simple_quickstart_runs(mock_site, monkeypatch):
    """23 行爬虫在 ofweek 结构站点上跑通并产出 3 条 item。"""
    from crawlo.core.initialization.core import CoreInitializer
    CoreInitializer().reset()

    monkeypatch.syspath_prepend(str(ROOT / "examples" / "simple_quickstart"))
    monkeypatch.chdir(QUICKSTART_DIR)
    monkeypatch.setenv("OFWEEK_BASE_URL", mock_site)

    out = QUICKSTART_DIR / "output" / "items.jsonl"
    monkeypatch.chdir(QUICKSTART_DIR)
    if out.exists():
        out.unlink()

    from crawlo.crawler import CrawlerProcess

    asyncio.run(CrawlerProcess().crawl("simple_ofweek"))

    assert out.exists(), f"缺少 JSONL 输出: {out}"
    lines = out.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 3, f"期望 3 条 item，实际 {len(lines)}"
    import json as _json
    first = _json.loads(lines[0])
    assert first["title"] and first["url"].startswith("http://127.0.0.1:")
