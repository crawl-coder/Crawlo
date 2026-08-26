#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
HybridDownloader 静态/动态路由矩阵实测（四种组合端到端）
========================================================

覆盖用户指定的四种抓取形态：
  1. 列表静态、详情动态   （s-list → d-detail/*）
  2. 列表动态、详情静态   （d-list → s-detail/*）
  3. 列表动态、详情动态   （d-list → d-detail/*）
  4. 列表静态、详情静态   （s-list → s-detail/*）

路由机制：DOWNLOADER='hybrid' + HYBRID_DYNAMIC_URL_PATTERNS=[r'/d-']。
mock 站点对动态页面返回 JS 注入内容的空壳页——若 hybrid 路由错误把动态页
交给协议下载器，title 将为空字符串，断言即失败（真正验证路由而非仅跑通）。

标记 browser：CI 跳过（-m "not browser"）；本地以 PLAYWRIGHT_REAL_CHROME=True
复用系统 Chrome，避免下载 chromium 二进制。
"""

import asyncio
import json
import threading
import uuid
from pathlib import Path

import pytest
from aiohttp import web

pytestmark = pytest.mark.browser


# ----------------------------------------------------------------------
# Mock 站点：static 服务端直出 / dynamic 仅 JS 注入（协议抓取看到空壳）
# ----------------------------------------------------------------------

def _static_list(target: str) -> str:
    links = "".join(
        f'<a class="detail-link" href="/{target}-detail/{i}">item {i}</a>'
        for i in (1, 2, 3)
    )
    return f"<html><body><h1>STATIC-LIST</h1>{links}</body></html>"


def _dynamic_list(target: str) -> str:
    links = "".join(
        f'<a class="detail-link" href="/{target}-detail/{i}">item {i}</a>'
        for i in (1, 2, 3)
    )
    # 协议客户端拿到的是空容器；只有浏览器执行脚本后链接才存在
    return (
        "<html><body><h1 id='hd'></h1><div id='items'></div>"
        "<script>"
        f"document.getElementById('items').innerHTML = `{links}`;"
        "</script></body></html>"
    )


def _detail_page(kind: str, n: int) -> str:
    if kind == "s":
        return f"<html><body><h1 class='title'>STATIC-{n}</h1></body></html>"
    return (
        "<html><body><h1 class='title'></h1>"
        "<script>"
        f"document.querySelector('h1.title').textContent = 'DYN-{n}';"
        "</script></body></html>"
    )


async def _list_handler(request):
    kind = request.match_info["kind"]
    target = request.query.get("target", kind)  # 详情页种类与列表种类解耦
    _HIT_LOGS.append(f"list {request.path}")
    body = _static_list(target) if kind == "s" else _dynamic_list(target)
    return web.Response(text=body, content_type="text/html")


async def _detail_handler(request):
    kind = request.match_info["kind"]
    n = int(request.match_info["n"])
    _HIT_LOGS.append(f"detail {request.path}")
    return web.Response(text=_detail_page(kind, n), content_type="text/html")


_HIT_LOGS: list = []


@pytest.fixture(scope="module")
def matrix_site():
    port_holder = {}
    started = threading.Event()
    stop = threading.Event()

    async def stop_waiter():
        while not stop.is_set():
            await asyncio.sleep(0.1)

    def _run():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        app = web.Application()
        app.router.add_get("/{kind}-list", _list_handler)
        app.router.add_get("/{kind}-detail/{n}", _detail_handler)
        runner = web.AppRunner(app)
        loop.run_until_complete(runner.setup())
        site = web.TCPSite(runner, "127.0.0.1", 0)
        loop.run_until_complete(site.start())
        port_holder["port"] = site._server.sockets[0].getsockname()[1]
        started.set()
        loop.run_until_complete(stop_waiter())
        loop.run_until_complete(runner.cleanup())
        loop.close()

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    assert started.wait(timeout=10), "mock 站点启动超时"
    yield f"http://127.0.0.1:{port_holder['port']}"
    stop.set()
    thread.join(timeout=10)
    # 清理测试写入 Redis 的去重指纹（AioRedisFilter 跨进程持久）
    try:
        import redis as sync_redis
        client = sync_redis.from_url("redis://127.0.0.1:6379/0")
        for key in client.scan_iter("crawlo:*hybrid_matrix*"):
            client.delete(key)
        client.close()
    except Exception:
        pass


# ----------------------------------------------------------------------
# 收集管道：动态生成模块文件，item 写入 env 指定的 JSONL
# ----------------------------------------------------------------------

_PIPELINE_SRC = '''
import json
import os

from crawlo.pipelines import BasePipeline


class CollectPipeline(BasePipeline):
    @classmethod
    def from_crawler(cls, crawler):
        instance = cls()
        instance.path = os.environ["MATRIX_OUT"]
        return instance

    async def open_spider(self, spider):
        self._file = open(self.path, "a", encoding="utf-8")  # noqa: SIM115

    async def process_item(self, item, spider):
        self._file.write(json.dumps(dict(item), ensure_ascii=False) + "\\n")
        self._file.flush()
        return item

    async def close_spider(self, spider):
        self._file.close()
'''


# ----------------------------------------------------------------------
# Spider：列表 → 详情，页面种类由环境变量决定（运行时求值）
# ----------------------------------------------------------------------

_SPIDER_SRC = '''
import os

from crawlo.http import Request
from crawlo.items import Item
from crawlo.spider import Spider


class MatrixItem(Item):
    pass


class HybridMatrixSpider(Spider):
    name = "hybrid_matrix"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 每场景唯一 spider name：AioRedisFilter 指纹 key 含 spider_name 且
        # 跨进程持久于 Redis，场景间不隔离会互相拦截对方详情页（去重正确语义）
        self.name = f"hybrid_matrix_{os.environ['MATRIX_UID']}"
        base = os.environ["MATRIX_BASE"]
        list_kind = os.environ["MATRIX_LIST"]
        detail_kind = os.environ["MATRIX_DETAIL"]
        self.start_urls = [f"{base}/{list_kind}-list?target={detail_kind}"]

    def parse(self, response):
        links = response.css("a.detail-link::attr(href)").getall()
        print(f"[matrix] parse {response.url} -> {len(links)} links, "
              f"body_len={len(response.text)}", flush=True)
        for href in links:
            yield Request(
                url=response.urljoin(href),
                callback=self.parse_detail,
            )

    def parse_detail(self, response):
        title = response.css("h1.title::text").get("").strip()
        print(f"[matrix] detail {response.url} title={title!r}", flush=True)
        return MatrixItem(url=response.url, title=title)
'''


def _write_modules(tmp_path: Path) -> None:
    (tmp_path / "matrix_pipeline.py").write_text(_PIPELINE_SRC, encoding="utf-8")
    (tmp_path / "matrix_spider.py").write_text(_SPIDER_SRC, encoding="utf-8")


def _load(tmp_path: Path, name: str):
    import importlib
    import sys
    sys.path.insert(0, str(tmp_path))
    try:
        return importlib.import_module(name)
    finally:
        sys.path.remove(str(tmp_path))


# ----------------------------------------------------------------------
# 场景矩阵：(列表种类, 详情种类, HYBRID_DYNAMIC_URL_PATTERNS)
# ----------------------------------------------------------------------

SCENARIOS = {
    # 1 列表静态/详情动态：pattern 把 /d-detail 送进浏览器通道
    1: {"list": "s", "detail": "d", "patterns": [r"/d-"], "expect_prefix": "DYN-"},
    # 2 列表动态/详情静态：列表必须被渲染才能发现链接（拿不到链接=item 为 0=失败）
    2: {"list": "d", "detail": "s", "patterns": [r"/d-"], "expect_prefix": "STATIC-"},
    # 3 全动态
    3: {"list": "d", "detail": "d", "patterns": [r"/d-"], "expect_prefix": "DYN-", "concurrency": 1},
    # 4 全静态：无 pattern，纯协议通道
    4: {"list": "s", "detail": "s", "patterns": [], "expect_prefix": "STATIC-"},
}


def _run_scenario(tmp_path, monkeypatch, base_url, scenario: dict) -> list:
    from crawlo.core.initialization.core import CoreInitializer

    CoreInitializer().reset()
    _HIT_LOGS.clear()
    scenario_uid = uuid.uuid4().hex[:6]
    monkeypatch.setenv("MATRIX_UID", scenario_uid)

    out = tmp_path / "items.jsonl"
    _write_modules(tmp_path)
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.setenv("MATRIX_BASE", base_url)
    monkeypatch.setenv("MATRIX_LIST", scenario["list"])
    monkeypatch.setenv("MATRIX_DETAIL", scenario["detail"])
    monkeypatch.setenv("MATRIX_OUT", str(out))

    MatrixSpider = _load(tmp_path, "matrix_spider").HybridMatrixSpider

    from crawlo.crawler import CrawlerProcess

    settings = {
        "DOWNLOADER_TYPE": "hybrid",          # 短名走 DOWNLOADER_MAP
        # 注意：不关闭 DynamicRenderMiddleware（保持默认 enabled=True）。
        # 它只在 DYNAMIC_RENDER_* 显式配置命中时才打 meta 标记，未配置时
        # 不打标、交由本测试要验证的 HYBRID_DYNAMIC_URL_PATTERNS 生效
        # （修复前它会无条件打 use_protocol_loader 短路 HYBRID 规则）。
        "HYBRID_DEFAULT_PROTOCOL_DOWNLOADER": "httpx",
        "HYBRID_DEFAULT_DYNAMIC_DOWNLOADER": "playwright",
        "PLAYWRIGHT_REAL_CHROME": True,       # 复用系统 Chrome，免下载二进制
        "PLAYWRIGHT_SINGLE_BROWSER_MODE": True,
        "PLAYWRIGHT_SCROLL_COUNT": 1,
        "ROBOTSTXT_OBEY": False,
        "CONCURRENCY": scenario.get("concurrency", 4),
        "DOWNLOAD_DELAY": 0,
        "HYBRID_DYNAMIC_URL_PATTERNS": scenario["patterns"],
        "PIPELINES": {"matrix_pipeline.CollectPipeline": 100},
    }
    asyncio.run(
        asyncio.wait_for(CrawlerProcess().crawl(MatrixSpider, settings=settings), timeout=240)
    )
    # 场景间强制清理全局连接池：上一场景遗留的坏连接（event loop 已关闭的
    # Redis 连接）会让下一场景的去重过滤在 await 重连窗口内，触发引擎
    # idle 误判提前退出 → 详情请求静默丢失（真实框架问题，已单独记录）。
    try:
        from crawlo.utils.redis.pool import close_all_pools
        asyncio.run(close_all_pools())
    except Exception:
        pass

    assert out.exists(), "JSONL 输出缺失"
    print(f"[matrix] server hits: {_HIT_LOGS}", flush=True)
    records = [json.loads(x) for x in out.read_text(encoding="utf-8").strip().splitlines()]
    return records


# ----------------------------------------------------------------------
# 四种场景
# ----------------------------------------------------------------------

def test_scenario_1_static_list_dynamic_detail(matrix_site, tmp_path, monkeypatch):
    """场景 1：列表静态直出、详情需浏览器渲染。"""
    recs = _run_scenario(tmp_path, monkeypatch, matrix_site, SCENARIOS[1])
    assert len(recs) == 3, f"期望 3 条 item，实际 {len(recs)}: {recs}"
    for r in recs:
        assert r["title"].startswith("DYN-"), f"详情应经浏览器渲染，实际 title={r['title']!r}"
        assert "/d-detail/" in r["url"]


def test_scenario_2_dynamic_list_static_detail(matrix_site, tmp_path, monkeypatch):
    """场景 2：列表需浏览器渲染才能发现详情链接，详情走协议通道。"""
    recs = _run_scenario(tmp_path, monkeypatch, matrix_site, SCENARIOS[2])
    assert len(recs) == 3, (
        f"期望 3 条 item，实际 {len(recs)}——"
        "若为 0 说明动态列表被误交给协议下载器（JS 链接未发现）"
    )
    for r in recs:
        assert r["title"].startswith("STATIC-"), f"详情应走协议通道，实际 title={r['title']!r}"
        assert "/s-detail/" in r["url"]


def test_scenario_3_both_dynamic(matrix_site, tmp_path, monkeypatch):
    """场景 3：列表与详情全部需要浏览器渲染。"""
    recs = _run_scenario(tmp_path, monkeypatch, matrix_site, SCENARIOS[3])
    assert len(recs) == 3, f"期望 3 条 item，实际 {len(recs)}: {recs}"
    for r in recs:
        assert r["title"].startswith("DYN-"), f"title={r['title']!r}"
        assert "/d-detail/" in r["url"]


def test_scenario_4_both_static(matrix_site, tmp_path, monkeypatch):
    """场景 4：全静态，无任何 pattern，纯协议通道跑通且不触发 Playwright。"""
    recs = _run_scenario(tmp_path, monkeypatch, matrix_site, SCENARIOS[4])
    assert len(recs) == 3, f"期望 3 条 item，实际 {len(recs)}: {recs}"
    for r in recs:
        assert r["title"].startswith("STATIC-"), f"title={r['title']!r}"
        assert "/s-detail/" in r["url"]
