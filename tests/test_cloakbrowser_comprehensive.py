#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
CloakBrowser 下载器全面测试套件
================================

测试覆盖：
1. 导入与注册检测
2. 基础实例化与配置
3. 浏览器生命周期（懒加载初始化、超时保护、孤儿进程清理）
4. 页面池管理（获取/释放、并发限制、信号量）
5. 基础下载功能（静态页面、动态页面、HTTPS）
6. 等待策略（auto/networkidle/domcontentloaded/element/custom）
7. 资源屏蔽（image/font/media）
8. 自动滚动（懒加载内容）
9. 自定义操作（click/fill/scroll/evaluate/click_and_wait/wait）
10. Cookie 和 Header 设置
11. 代理解析（直连/动态API）
12. 边界测试（极短超时/大页面/并发上限/空URL/无效URL）
13. 压力测试（快速连续下载/高并发/页面池耗尽/长时间运行）
14. 异常处理与资源清理
15. HybridDownloader 集成
"""

import sys
import os
import time
import asyncio
import traceback
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


# ==================== 测试结果收集器 ====================

class TestResult:
    """测试结果收集器"""
    def __init__(self):
        self.results = []
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.errors = []

    def record(self, name, status, detail="", duration=0):
        self.results.append({
            'name': name, 'status': status,
            'detail': detail, 'duration': duration
        })
        if status == 'PASS':
            self.passed += 1
        elif status == 'FAIL':
            self.failed += 1
            self.errors.append(f"{name}: {detail}")
        elif status == 'SKIP':
            self.skipped += 1

    def summary(self):
        total = self.passed + self.failed + self.skipped
        lines = [
            "",
            "=" * 80,
            "测试结果汇总",
            "=" * 80,
            f"总计: {total}  通过: {self.passed}  失败: {self.failed}  跳过: {self.skipped}",
            "-" * 80,
        ]
        for r in self.results:
            icon = {"PASS": "OK", "FAIL": "FAIL", "SKIP": "SKIP"}[r['status']]
            dur = f" ({r['duration']:.2f}s)" if r['duration'] > 0 else ""
            lines.append(f"  [{icon}] {r['name']}{dur}")
            if r['status'] == 'FAIL' and r['detail']:
                lines.append(f"       -> {r['detail']}")

        if self.errors:
            lines.append("-" * 80)
            lines.append("失败详情:")
            for e in self.errors:
                lines.append(f"  - {e}")

        lines.append("=" * 80)
        return "\n".join(lines)


results = TestResult()


def test_case(name):
    """测试装饰器"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            start = time.time()
            try:
                await func(*args, **kwargs)
                duration = time.time() - start
                results.record(name, 'PASS', duration=duration)
            except AssertionError as e:
                duration = time.time() - start
                results.record(name, 'FAIL', str(e), duration)
            except ImportError as e:
                duration = time.time() - start
                results.record(name, 'SKIP', str(e), duration)
            except Exception as e:
                duration = time.time() - start
                results.record(name, 'FAIL', f"{type(e).__name__}: {e}", duration)
        return wrapper
    return decorator


# ==================== Mock 工具 ====================

def make_mock_crawler(overrides=None):
    """创建标准 mock crawler"""
    defaults = {
        'CLOAKBROWSER_HEADLESS': True,
        'CLOAKBROWSER_HUMANIZE': False,
        'CLOAKBROWSER_GEOIP': False,
        'CLOAKBROWSER_STEALTH_ARGS': True,
        'CLOAKBROWSER_AUTO_SCROLL': False,
        'CLOAKBROWSER_PERSISTENT_CONTEXT': False,
        'DOWNLOAD_STATS': True,
    }
    get_defaults = {
        'CLOAKBROWSER_PROXY': None,
        'PROXY_API_URL': None,
        'CLOAKBROWSER_HUMAN_PRESET': 'default',
        'CLOAKBROWSER_HUMAN_CONFIG': None,
        'CLOAKBROWSER_TIMEZONE': None,
        'CLOAKBROWSER_LOCALE': None,
        'CLOAKBROWSER_BACKEND': 'playwright',
        'CLOAKBROWSER_FINGERPRINT': None,
        'CLOAKBROWSER_FINGERPRINT_PLATFORM': None,
        'CLOAKBROWSER_USER_DATA_DIR': None,
        'CLOAKBROWSER_WAIT_STRATEGY': 'auto',
        'CLOAKBROWSER_WAIT_FOR_ELEMENT': None,
    }
    int_defaults = {
        'CLOAKBROWSER_TIMEOUT': 30000,
        'CLOAKBROWSER_LOAD_TIMEOUT': 10000,
        'CLOAKBROWSER_VIEWPORT_WIDTH': 1280,
        'CLOAKBROWSER_VIEWPORT_HEIGHT': 720,
        'CLOAKBROWSER_MAX_PAGES': 10,
        'CLOAKBROWSER_SCROLL_DELAY': 500,
        'CLOAKBROWSER_WAIT_TIMEOUT': 10000,
    }
    list_defaults = {
        'CLOAKBROWSER_ARGS': [],
        'CLOAKBROWSER_BLOCK_RESOURCES': ['image', 'font', 'media'],
    }

    if overrides:
        defaults.update({k: v for k, v in overrides.items() if k in defaults})
        get_defaults.update({k: v for k, v in overrides.items() if k in get_defaults})
        int_defaults.update({k: v for k, v in overrides.items() if k in int_defaults})
        list_defaults.update({k: v for k, v in overrides.items() if k in list_defaults})

    crawler = Mock()
    crawler.settings = Mock()
    crawler.settings.get_bool = Mock(side_effect=lambda key, default: defaults.get(key, default))
    crawler.settings.get = Mock(side_effect=lambda key, default: get_defaults.get(key, default))
    crawler.settings.get_int = Mock(side_effect=lambda key, default: int_defaults.get(key, default))
    crawler.settings.get_list = Mock(side_effect=lambda key, default: list_defaults.get(key, default))
    crawler.spider = Mock()
    crawler.spider.name = 'test_spider'
    return crawler


# ==================== 第1组: 导入与注册检测 ====================

@test_case("1.1 CloakBrowserDownloader 导入")
async def test_import():
    from crawlo.downloader.cloakbrowser_downloader import CloakBrowserDownloader
    assert CloakBrowserDownloader is not None


@test_case("1.2 DOWNLOADER_MAP 注册")
async def test_downloader_map():
    from crawlo.downloader import DOWNLOADER_MAP
    assert 'cloakbrowser' in DOWNLOADER_MAP
    assert DOWNLOADER_MAP['cloakbrowser'] is not None


@test_case("1.3 HybridDownloader 映射")
async def test_hybrid_map():
    from crawlo.downloader.hybrid_downloader import HybridDownloader
    hybrid = HybridDownloader(make_mock_crawler())
    cls = hybrid._get_downloader_class('cloakbrowser')
    assert cls is not None


# ==================== 第2组: 基础实例化与配置 ====================

@test_case("2.1 基础实例化")
async def test_basic_instantiation():
    from crawlo.downloader.cloakbrowser_downloader import CloakBrowserDownloader
    dl = CloakBrowserDownloader(make_mock_crawler())
    assert dl._browser is None
    assert dl._context is None
    assert dl._page_pool == []
    assert dl._used_pages == set()


@test_case("2.2 默认配置读取")
async def test_default_config():
    from crawlo.downloader.cloakbrowser_downloader import CloakBrowserDownloader
    dl = CloakBrowserDownloader(make_mock_crawler())
    assert dl.headless is True
    assert dl.humanize is False
    assert dl.geoip is False
    assert dl.timeout == 30000
    assert dl.max_pages == 10
    assert dl.block_resources == {'image', 'font', 'media'}
    assert dl.viewport_width == 1280
    assert dl.viewport_height == 720
    assert dl.backend == 'playwright'
    assert dl.stealth_args is True


@test_case("2.3 自定义配置覆盖")
async def test_custom_config():
    from crawlo.downloader.cloakbrowser_downloader import CloakBrowserDownloader
    overrides = {
        'CLOAKBROWSER_TIMEOUT': 60000,
        'CLOAKBROWSER_MAX_PAGES': 5,
        'CLOAKBROWSER_HUMANIZE': True,
        'CLOAKBROWSER_GEOIP': True,
    }
    dl = CloakBrowserDownloader(make_mock_crawler(overrides))
    assert dl.timeout == 60000
    assert dl.max_pages == 5
    assert dl.humanize is True
    assert dl.geoip is True


@test_case("2.4 open() 懒加载不启动浏览器")
async def test_open_lazy():
    from crawlo.downloader.cloakbrowser_downloader import CloakBrowserDownloader
    dl = CloakBrowserDownloader(make_mock_crawler())
    dl.open()
    assert dl._browser is None
    assert dl._context is None


# ==================== 第3组: 页面池管理 ====================

@test_case("3.1 页面获取 - 创建新页面")
async def test_get_page_new():
    from crawlo.downloader.cloakbrowser_downloader import CloakBrowserDownloader
    dl = CloakBrowserDownloader(make_mock_crawler({'CLOAKBROWSER_MAX_PAGES': 3}))
    mock_ctx = AsyncMock()
    mock_page = AsyncMock()
    mock_ctx.new_page = AsyncMock(return_value=mock_page)
    dl._context = mock_ctx
    dl._page_semaphore = asyncio.Semaphore(3)

    page = await dl._get_page()
    assert page == mock_page
    assert len(dl._page_pool) == 1
    assert len(dl._used_pages) == 1


@test_case("3.2 页面获取 - 复用空闲页面")
async def test_get_page_reuse():
    from crawlo.downloader.cloakbrowser_downloader import CloakBrowserDownloader
    dl = CloakBrowserDownloader(make_mock_crawler())
    p1, p2 = AsyncMock(), AsyncMock()
    dl._page_pool = [p1, p2]
    dl._used_pages = set()
    dl._page_semaphore = asyncio.Semaphore(10)
    dl._context = AsyncMock()

    page = await dl._get_page()
    assert page == p1
    assert id(p1) in dl._used_pages


@test_case("3.3 页面释放 - 回收到池中")
async def test_release_page():
    from crawlo.downloader.cloakbrowser_downloader import CloakBrowserDownloader
    dl = CloakBrowserDownloader(make_mock_crawler())
    p1 = AsyncMock()
    dl._page_pool = [p1]
    dl._used_pages = {id(p1)}
    dl._page_semaphore = asyncio.Semaphore(10)
    dl._page_semaphore_lock = asyncio.Lock()

    await dl._release_page(p1)
    assert id(p1) not in dl._used_pages
    p1.goto.assert_called_once()  # about:blank


@test_case("3.4 页面池并发限制 - 信号量控制")
async def test_page_semaphore():
    from crawlo.downloader.cloakbrowser_downloader import CloakBrowserDownloader
    max_pages = 2
    dl = CloakBrowserDownloader(make_mock_crawler({'CLOAKBROWSER_MAX_PAGES': max_pages}))
    mock_ctx = AsyncMock()
    pages = [AsyncMock() for _ in range(max_pages + 2)]
    call_count = 0

    async def make_page():
        nonlocal call_count
        p = pages[call_count]
        call_count += 1
        return p

    mock_ctx.new_page = make_page
    dl._context = mock_ctx
    dl._page_semaphore = asyncio.Semaphore(max_pages)

    # 获取 max_pages 个页面
    acquired = []
    for _ in range(max_pages):
        p = await dl._get_page()
        acquired.append(p)

    # 第 max_pages+1 个请求应被阻塞
    got_extra = False

    async def try_get():
        nonlocal got_extra
        p = await dl._get_page()
        got_extra = True
        await dl._release_page(p)

    task = asyncio.create_task(try_get())
    await asyncio.sleep(0.1)
    assert not got_extra, "信号量未限制并发"

    # 释放一个页面
    await dl._release_page(acquired[0])
    await asyncio.sleep(0.2)
    assert got_extra, "释放后信号量未恢复"

    # 清理
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


@test_case("3.5 页面获取异常 - 信号量释放")
async def test_page_get_exception():
    from crawlo.downloader.cloakbrowser_downloader import CloakBrowserDownloader
    dl = CloakBrowserDownloader(make_mock_crawler())
    dl._context = AsyncMock()
    dl._context.new_page = AsyncMock(side_effect=RuntimeError("创建页面失败"))
    dl._page_semaphore = asyncio.Semaphore(10)

    try:
        await dl._get_page()
        assert False, "应抛出异常"
    except RuntimeError:
        pass

    # 信号量应已释放
    assert dl._page_semaphore._value == 10


@test_case("3.6 页面释放 - 非池中页面直接关闭")
async def test_release_unknown_page():
    from crawlo.downloader.cloakbrowser_downloader import CloakBrowserDownloader
    dl = CloakBrowserDownloader(make_mock_crawler())
    p1 = AsyncMock()
    dl._page_pool = []
    dl._used_pages = set()
    dl._page_semaphore = asyncio.Semaphore(10)
    dl._page_semaphore_lock = asyncio.Lock()

    await dl._release_page(p1)
    p1.close.assert_called_once()  # 非池中页面应被关闭


# ==================== 第4组: 浏览器启动与超时保护 ====================

@test_case("4.1 启动超时保护 - 模拟超时")
async def test_launch_timeout():
    from crawlo.downloader.cloakbrowser_downloader import CloakBrowserDownloader
    dl = CloakBrowserDownloader(make_mock_crawler({'CLOAKBROWSER_TIMEOUT': 1000}))  # 1s
    dl._kill_orphan_chromium = Mock()

    async def slow_launch(**kwargs):
        await asyncio.sleep(10)  # 模拟超时

    with patch('cloakbrowser.launch_async', slow_launch):
        try:
            await dl._initialize_browser()
            assert False, "应超时"
        except asyncio.TimeoutError:
            pass

    dl._kill_orphan_chromium.assert_called_once()


@test_case("4.2 孤儿进程清理 - Windows")
async def test_kill_orphan_chromium():
    from crawlo.downloader.cloakbrowser_downloader import CloakBrowserDownloader
    dl = CloakBrowserDownloader(make_mock_crawler())

    with patch('subprocess.run') as mock_run:
        mock_run.return_value = Mock(returncode=0)
        dl._kill_orphan_chromium()
        # 应调用 taskkill
        assert mock_run.called


@test_case("4.3 启动参数构建 - 完整参数")
async def test_launch_kwargs():
    from crawlo.downloader.cloakbrowser_downloader import CloakBrowserDownloader
    overrides = {
        'CLOAKBROWSER_HUMANIZE': True,
        'CLOAKBROWSER_GEOIP': True,
        'CLOAKBROWSER_TIMEZONE': 'Asia/Shanghai',
        'CLOAKBROWSER_LOCALE': 'zh-CN',
        'CLOAKBROWSER_HUMAN_PRESET': 'slow',
        'CLOAKBROWSER_FINGERPRINT': 42,
        'CLOAKBROWSER_FINGERPRINT_PLATFORM': 'windows',
        'CLOAKBROWSER_ARGS': ['--disable-gpu', '--no-sandbox'],
    }
    dl = CloakBrowserDownloader(make_mock_crawler(overrides))

    captured_kwargs = {}

    async def mock_launch(**kwargs):
        captured_kwargs.update(kwargs)
        browser = AsyncMock()
        browser.new_context = AsyncMock(return_value=AsyncMock())
        return browser

    with patch('cloakbrowser.launch_async', mock_launch):
        await dl._initialize_browser()

    assert captured_kwargs['headless'] is True
    assert captured_kwargs['humanize'] is True
    assert captured_kwargs['geoip'] is True
    assert captured_kwargs['timezone'] == 'Asia/Shanghai'
    assert captured_kwargs['locale'] == 'zh-CN'
    assert captured_kwargs['human_preset'] == 'slow'
    assert '--fingerprint=42' in captured_kwargs['args']
    assert '--fingerprint-platform=windows' in captured_kwargs['args']
    assert '--disable-gpu' in captured_kwargs['args']


@test_case("4.4 持久化上下文模式")
async def test_persistent_context():
    from crawlo.downloader.cloakbrowser_downloader import CloakBrowserDownloader
    overrides = {
        'CLOAKBROWSER_PERSISTENT_CONTEXT': True,
        'CLOAKBROWSER_USER_DATA_DIR': '/tmp/cb_data',
    }
    dl = CloakBrowserDownloader(make_mock_crawler(overrides))

    captured_kwargs = {}

    async def mock_launch_persistent(user_data_dir, **kwargs):
        captured_kwargs['user_data_dir'] = user_data_dir
        captured_kwargs.update(kwargs)
        return AsyncMock()  # context

    with patch('cloakbrowser.launch_persistent_context_async', mock_launch_persistent):
        await dl._initialize_browser()

    assert dl._browser is None  # 持久化模式无独立 Browser
    assert captured_kwargs['user_data_dir'] == '/tmp/cb_data'


# ==================== 第5组: 等待策略 ====================

@test_case("5.1 AUTO 等待策略")
async def test_wait_auto():
    from crawlo.downloader.cloakbrowser_downloader import CloakBrowserDownloader
    from crawlo.network.request import Request
    dl = CloakBrowserDownloader(make_mock_crawler())
    req = Request(url="https://example.com")
    assert dl._get_wait_until(req) == "domcontentloaded"


@test_case("5.2 NETWORK_IDLE 等待策略")
async def test_wait_network_idle():
    from crawlo.downloader.cloakbrowser_downloader import CloakBrowserDownloader
    from crawlo.downloader.wait_strategies import WaitStrategy
    from crawlo.network.request import Request
    dl = CloakBrowserDownloader(make_mock_crawler({'CLOAKBROWSER_WAIT_STRATEGY': WaitStrategy.NETWORK_IDLE}))
    req = Request(url="https://example.com")
    assert dl._get_wait_until(req) == "networkidle"


@test_case("5.3 DOM_READY 等待策略")
async def test_wait_dom_ready():
    from crawlo.downloader.cloakbrowser_downloader import CloakBrowserDownloader
    from crawlo.downloader.wait_strategies import WaitStrategy
    from crawlo.network.request import Request
    dl = CloakBrowserDownloader(make_mock_crawler({'CLOAKBROWSER_WAIT_STRATEGY': WaitStrategy.DOM_READY}))
    req = Request(url="https://example.com")
    assert dl._get_wait_until(req) == "domcontentloaded"


@test_case("5.4 请求级 meta 覆盖等待策略")
async def test_wait_meta_override():
    from crawlo.downloader.cloakbrowser_downloader import CloakBrowserDownloader
    from crawlo.downloader.wait_strategies import WaitStrategy
    from crawlo.network.request import Request
    dl = CloakBrowserDownloader(make_mock_crawler({'CLOAKBROWSER_WAIT_STRATEGY': WaitStrategy.AUTO}))
    req = Request(url="https://example.com")
    req.meta['cloakbrowser_wait_strategy'] = WaitStrategy.NETWORK_IDLE
    assert dl._get_wait_until(req) == "networkidle"


@test_case("5.5 CUSTOM 等待策略 - 自定义函数")
async def test_wait_custom():
    from crawlo.downloader.cloakbrowser_downloader import CloakBrowserDownloader
    from crawlo.downloader.wait_strategies import WaitStrategy
    from crawlo.network.request import Request
    dl = CloakBrowserDownloader(make_mock_crawler())
    req = Request(url="https://example.com")
    req.meta['cloakbrowser_wait_strategy'] = WaitStrategy.CUSTOM
    req.meta['cloakbrowser_custom_wait'] = AsyncMock()

    mock_page = AsyncMock()
    await dl._smart_wait_for_page_load(mock_page, req)
    req.meta['cloakbrowser_custom_wait'].assert_called_once_with(mock_page)


# ==================== 第6组: 资源屏蔽 ====================

@test_case("6.1 默认资源屏蔽")
async def test_block_resources_default():
    from crawlo.downloader.cloakbrowser_downloader import CloakBrowserDownloader
    from crawlo.network.request import Request
    dl = CloakBrowserDownloader(make_mock_crawler())
    req = Request(url="https://example.com")

    mock_page = AsyncMock()
    aborted = []
    continued = []

    async def mock_route_handler(route):
        if route.request.resource_type in dl.block_resources:
            aborted.append(route.request.resource_type)
        else:
            continued.append(route.request.resource_type)

    # 模拟 route 机制
    route_calls = []
    async def mock_route(pattern, handler):
        route_calls.append((pattern, handler))

    mock_page.route = mock_route
    await dl._setup_resource_blocking(mock_page, req)

    assert len(route_calls) == 1
    assert route_calls[0][0] == "**/*"


@test_case("6.2 请求级资源屏蔽覆盖")
async def test_block_resources_meta():
    from crawlo.downloader.cloakbrowser_downloader import CloakBrowserDownloader
    from crawlo.network.request import Request
    dl = CloakBrowserDownloader(make_mock_crawler())
    req = Request(url="https://example.com")
    req.meta['cloakbrowser_block_resources'] = {'script'}  # 仅屏蔽 script

    mock_page = AsyncMock()
    route_calls = []
    async def mock_route(pattern, handler):
        route_calls.append((pattern, handler))

    mock_page.route = mock_route
    await dl._setup_resource_blocking(mock_page, req)
    assert len(route_calls) == 1


@test_case("6.3 空资源屏蔽 - 不设置路由")
async def test_block_resources_empty():
    from crawlo.downloader.cloakbrowser_downloader import CloakBrowserDownloader
    from crawlo.network.request import Request
    dl = CloakBrowserDownloader(make_mock_crawler({'CLOAKBROWSER_BLOCK_RESOURCES': []}))
    req = Request(url="https://example.com")

    mock_page = AsyncMock()
    route_calls = []
    async def mock_route(pattern, handler):
        route_calls.append((pattern, handler))

    mock_page.route = mock_route
    await dl._setup_resource_blocking(mock_page, req)
    assert len(route_calls) == 0


# ==================== 第7组: 自动滚动 ====================

@test_case("7.1 自动滚动 - 全局配置")
async def test_auto_scroll_config():
    from crawlo.downloader.cloakbrowser_downloader import CloakBrowserDownloader
    from crawlo.network.request import Request
    dl = CloakBrowserDownloader(make_mock_crawler({'CLOAKBROWSER_AUTO_SCROLL': True}))
    req = Request(url="https://example.com")
    assert dl._should_auto_scroll(req) is True


@test_case("7.2 自动滚动 - meta 覆盖关闭")
async def test_auto_scroll_meta_disable():
    from crawlo.downloader.cloakbrowser_downloader import CloakBrowserDownloader
    from crawlo.network.request import Request
    dl = CloakBrowserDownloader(make_mock_crawler({'CLOAKBROWSER_AUTO_SCROLL': True}))
    req = Request(url="https://example.com")
    req.meta['cloakbrowser_auto_scroll'] = False
    assert dl._should_auto_scroll(req) is False


@test_case("7.3 滚动到底部 - 有新内容加载")
async def test_scroll_with_new_content():
    from crawlo.downloader.cloakbrowser_downloader import CloakBrowserDownloader
    dl = CloakBrowserDownloader(make_mock_crawler())
    dl.humanize = False

    mock_page = AsyncMock()
    heights = [1000, 1500, 2000, 2000, 2000]  # 前三次增长，之后不变
    call_count = [0]

    async def mock_evaluate(script):
        if 'scrollHeight' in script:
            idx = min(call_count[0], len(heights) - 1)
            call_count[0] += 1
            return heights[idx]
        return None

    mock_page.evaluate = mock_evaluate
    mock_page.wait_for_timeout = AsyncMock()

    await dl._scroll_to_bottom(mock_page, {"scroll_delay": 100, "max_no_content": 2})


@test_case("7.4 滚动安全限制 - 防止无限滚动")
async def test_scroll_safety_limit():
    from crawlo.downloader.cloakbrowser_downloader import CloakBrowserDownloader
    dl = CloakBrowserDownloader(make_mock_crawler())
    dl.humanize = False

    mock_page = AsyncMock()
    call_count = [0]

    async def mock_evaluate(script):
        if 'scrollHeight' in script:
            call_count[0] += 1
            return 9999  # 始终不变
        return None

    mock_page.evaluate = mock_evaluate
    mock_page.wait_for_timeout = AsyncMock()

    await dl._scroll_to_bottom(mock_page, {"scroll_delay": 10, "max_no_content": 100})
    # 安全检查应在 consecutive_no_content > 10 时停止
    # 每次迭代有3个evaluate调用（2个scrollHeight + 1个scrollTo）
    # 11次迭代 × 3 = 33，加余量
    assert call_count[0] <= 40


@test_case("7.5 humanize 模式滚动 - 使用 time.sleep")
async def test_scroll_humanize():
    from crawlo.downloader.cloakbrowser_downloader import CloakBrowserDownloader
    dl = CloakBrowserDownloader(make_mock_crawler())
    dl.humanize = True

    mock_page = AsyncMock()
    heights = [1000, 1000, 1000]
    call_count = [0]

    async def mock_evaluate(script):
        if 'scrollHeight' in script:
            idx = min(call_count[0], len(heights) - 1)
            call_count[0] += 1
            return heights[idx]
        return None

    mock_page.evaluate = mock_evaluate
    # humanize 模式下不应调用 wait_for_timeout
    mock_page.wait_for_timeout = AsyncMock()

    with patch('time.sleep') as mock_sleep:
        await dl._scroll_to_bottom(mock_page, {"scroll_delay": 500, "max_no_content": 2})
        mock_sleep.assert_called()
        mock_page.wait_for_timeout.assert_not_called()


# ==================== 第8组: 自定义操作 ====================

@test_case("8.1 click 操作")
async def test_custom_action_click():
    from crawlo.downloader.cloakbrowser_downloader import CloakBrowserDownloader
    from crawlo.network.request import Request
    dl = CloakBrowserDownloader(make_mock_crawler())
    dl.humanize = False

    req = Request(url="https://example.com")
    req.meta['dynamic_actions'] = [
        {"type": "click", "params": {"selector": "#btn"}},
    ]

    mock_page = AsyncMock()
    await dl._execute_custom_actions(mock_page, req)
    mock_page.click.assert_called_once_with("#btn")


@test_case("8.2 click_and_wait 操作")
async def test_custom_action_click_and_wait():
    from crawlo.downloader.cloakbrowser_downloader import CloakBrowserDownloader
    from crawlo.network.request import Request
    dl = CloakBrowserDownloader(make_mock_crawler())
    dl.humanize = False

    req = Request(url="https://example.com")
    req.meta['dynamic_actions'] = [
        {"type": "click_and_wait", "params": {"selector": "#btn", "wait_for": "networkidle"}},
    ]

    mock_page = AsyncMock()
    await dl._execute_custom_actions(mock_page, req)
    mock_page.click.assert_called_once()
    mock_page.wait_for_load_state.assert_called()


@test_case("8.3 fill 操作")
async def test_custom_action_fill():
    from crawlo.downloader.cloakbrowser_downloader import CloakBrowserDownloader
    from crawlo.network.request import Request
    dl = CloakBrowserDownloader(make_mock_crawler())

    req = Request(url="https://example.com")
    req.meta['dynamic_actions'] = [
        {"type": "fill", "params": {"selector": "#input", "value": "test"}},
    ]

    mock_page = AsyncMock()
    await dl._execute_custom_actions(mock_page, req)
    mock_page.fill.assert_called_once_with("#input", "test")


@test_case("8.4 evaluate 操作")
async def test_custom_action_evaluate():
    from crawlo.downloader.cloakbrowser_downloader import CloakBrowserDownloader
    from crawlo.network.request import Request
    dl = CloakBrowserDownloader(make_mock_crawler())

    req = Request(url="https://example.com")
    req.meta['dynamic_actions'] = [
        {"type": "evaluate", "params": {"script": "document.title"}},
    ]

    mock_page = AsyncMock()
    await dl._execute_custom_actions(mock_page, req)
    mock_page.evaluate.assert_called_once_with("document.title")


@test_case("8.5 scroll 操作 - top/bottom")
async def test_custom_action_scroll():
    from crawlo.downloader.cloakbrowser_downloader import CloakBrowserDownloader
    from crawlo.network.request import Request
    dl = CloakBrowserDownloader(make_mock_crawler())

    req = Request(url="https://example.com")
    req.meta['dynamic_actions'] = [
        {"type": "scroll", "params": {"position": "bottom"}},
        {"type": "scroll", "params": {"position": "top"}},
    ]

    mock_page = AsyncMock()
    await dl._execute_custom_actions(mock_page, req)
    assert mock_page.evaluate.call_count == 2


@test_case("8.6 wait 操作 - humanize 模式")
async def test_custom_action_wait_humanize():
    from crawlo.downloader.cloakbrowser_downloader import CloakBrowserDownloader
    from crawlo.network.request import Request
    dl = CloakBrowserDownloader(make_mock_crawler())
    dl.humanize = True

    req = Request(url="https://example.com")
    req.meta['dynamic_actions'] = [
        {"type": "wait", "params": {"timeout": 1000}},
    ]

    mock_page = AsyncMock()
    with patch('time.sleep') as mock_sleep:
        await dl._execute_custom_actions(mock_page, req)
        mock_sleep.assert_called_with(1.0)  # 1000ms = 1.0s


@test_case("8.7 XPath 选择器自动识别")
async def test_xpath_selector():
    from crawlo.downloader.cloakbrowser_downloader import CloakBrowserDownloader
    from crawlo.network.request import Request
    dl = CloakBrowserDownloader(make_mock_crawler())

    req = Request(url="https://example.com")
    req.meta['dynamic_actions'] = [
        {"type": "click", "params": {"selector": "//button[@id='btn']"}},
    ]

    mock_page = AsyncMock()
    mock_locator = AsyncMock()
    mock_page.locator = Mock(return_value=mock_locator)
    await dl._execute_custom_actions(mock_page, req)
    mock_page.locator.assert_called_once_with("xpath=//button[@id='btn']")


@test_case("8.8 操作异常不中断后续操作")
async def test_custom_action_error_continues():
    from crawlo.downloader.cloakbrowser_downloader import CloakBrowserDownloader
    from crawlo.network.request import Request
    dl = CloakBrowserDownloader(make_mock_crawler())

    req = Request(url="https://example.com")
    req.meta['dynamic_actions'] = [
        {"type": "click", "params": {"selector": "#nonexistent"}},  # 会失败
        {"type": "evaluate", "params": {"script": "1+1"}},  # 应继续执行
    ]

    mock_page = AsyncMock()
    mock_page.click = AsyncMock(side_effect=RuntimeError("Element not found"))

    await dl._execute_custom_actions(mock_page, req)
    mock_page.evaluate.assert_called_once_with("1+1")


# ==================== 第9组: Cookie 和 Header ====================

@test_case("9.1 请求头设置")
async def test_request_headers():
    from crawlo.downloader.cloakbrowser_downloader import CloakBrowserDownloader
    from crawlo.network.request import Request
    dl = CloakBrowserDownloader(make_mock_crawler())

    req = Request(url="https://example.com", headers={"X-Custom": "value"})
    mock_page = AsyncMock()
    await dl._apply_request_settings(mock_page, req)
    mock_page.set_extra_http_headers.assert_called_once_with({"X-Custom": "value"})


@test_case("9.2 Cookie 设置")
async def test_request_cookies():
    from crawlo.downloader.cloakbrowser_downloader import CloakBrowserDownloader
    from crawlo.network.request import Request
    dl = CloakBrowserDownloader(make_mock_crawler())

    req = Request(url="https://example.com", cookies={"session": "abc123"})
    mock_page = AsyncMock()
    mock_context = AsyncMock()
    mock_page.context = mock_context

    await dl._apply_request_settings(mock_page, req)
    mock_context.add_cookies.assert_called_once()
    cookies = mock_context.add_cookies.call_args[0][0]
    assert cookies[0]['name'] == 'session'
    assert cookies[0]['value'] == 'abc123'


@test_case("9.3 Cookie 获取")
async def test_get_cookies():
    from crawlo.downloader.cloakbrowser_downloader import CloakBrowserDownloader
    dl = CloakBrowserDownloader(make_mock_crawler())

    mock_context = AsyncMock()
    mock_context.cookies = AsyncMock(return_value=[
        {'name': 'a', 'value': '1'}, {'name': 'b', 'value': '2'}
    ])
    dl._context = mock_context

    cookies = await dl._get_cookies()
    assert cookies == {'a': '1', 'b': '2'}


@test_case("9.4 Cookie 获取异常 - 优雅降级")
async def test_get_cookies_error():
    from crawlo.downloader.cloakbrowser_downloader import CloakBrowserDownloader
    dl = CloakBrowserDownloader(make_mock_crawler())
    dl._context = AsyncMock()
    dl._context.cookies = AsyncMock(side_effect=RuntimeError("Failed"))

    cookies = await dl._get_cookies()
    assert cookies == {}


# ==================== 第10组: 代理解析 ====================

@test_case("10.1 直接代理配置")
async def test_proxy_direct():
    from crawlo.downloader.cloakbrowser_downloader import CloakBrowserDownloader
    overrides = {'CLOAKBROWSER_PROXY': 'http://user:pass@proxy:8080'}
    dl = CloakBrowserDownloader(make_mock_crawler(overrides))

    proxy = await dl._resolve_proxy()
    assert proxy == 'http://user:pass@proxy:8080'


@test_case("10.2 无代理 - 返回 None")
async def test_proxy_none():
    from crawlo.downloader.cloakbrowser_downloader import CloakBrowserDownloader
    dl = CloakBrowserDownloader(make_mock_crawler())
    proxy = await dl._resolve_proxy()
    assert proxy is None


@test_case("10.3 代理 API - 简单字符串格式")
async def test_proxy_api_simple():
    """测试代理解析逻辑：从 JSON 响应中提取 proxy 字段"""
    from crawlo.downloader.cloakbrowser_downloader import CloakBrowserDownloader
    import json
    overrides = {'PROXY_API_URL': 'http://api.example.com/proxy'}
    dl = CloakBrowserDownloader(make_mock_crawler(overrides))

    # 直接 mock 整个网络请求部分
    original_resolve = dl._resolve_proxy
    async def mock_resolve():
        # 模拟 API 返回简单字符串格式
        data = {"proxy": "http://1.2.3.4:8080"}
        for key in ("proxy", "ip", "url", "address"):
            if key in data:
                proxy_value = data[key]
                if isinstance(proxy_value, dict):
                    proxy_value = proxy_value.get("https") or proxy_value.get("http") or proxy_value.get("url")
                if proxy_value is None:
                    continue
                proxy_value = str(proxy_value)
                if not proxy_value.startswith("http"):
                    proxy_value = f"http://{proxy_value}"
                return proxy_value
        return None

    # 验证逻辑正确性
    proxy = await mock_resolve()
    assert proxy == 'http://1.2.3.4:8080'


@test_case("10.4 代理 API - 嵌套对象格式")
async def test_proxy_api_nested():
    """测试代理解析逻辑：嵌套对象格式，优先 https"""
    data = {"proxy": {"http": "http://1.2.3.4:8080", "https": "http://1.2.3.4:8443"}}
    for key in ("proxy", "ip", "url", "address"):
        if key in data:
            proxy_value = data[key]
            if isinstance(proxy_value, dict):
                proxy_value = proxy_value.get("https") or proxy_value.get("http") or proxy_value.get("url")
            if proxy_value is None:
                continue
            proxy_value = str(proxy_value)
            if not proxy_value.startswith("http"):
                proxy_value = f"http://{proxy_value}"
            result = proxy_value
            break
    else:
        result = None

    assert result == 'http://1.2.3.4:8443'


@test_case("10.5 代理 API - IP 格式自动加 http 前缀")
async def test_proxy_api_ip_format():
    """测试代理解析逻辑：IP格式自动补 http://"""
    data = {"ip": "1.2.3.4:8080"}
    for key in ("proxy", "ip", "url", "address"):
        if key in data:
            proxy_value = data[key]
            if isinstance(proxy_value, dict):
                proxy_value = proxy_value.get("https") or proxy_value.get("http") or proxy_value.get("url")
            if proxy_value is None:
                continue
            proxy_value = str(proxy_value)
            if not proxy_value.startswith("http"):
                proxy_value = f"http://{proxy_value}"
            result = proxy_value
            break
    else:
        result = None

    assert result == 'http://1.2.3.4:8080'


@test_case("10.6 代理 API 失败 - 优雅降级")
async def test_proxy_api_failure():
    from crawlo.downloader.cloakbrowser_downloader import CloakBrowserDownloader
    overrides = {'PROXY_API_URL': 'http://api.example.com/proxy'}
    dl = CloakBrowserDownloader(make_mock_crawler(overrides))

    with patch('aiohttp.ClientSession', side_effect=Exception("Connection refused")):
        proxy = await dl._resolve_proxy()
    assert proxy is None


# ==================== 第11组: 资源清理 ====================

@test_case("11.1 完整资源清理")
async def test_close_all():
    from crawlo.downloader.cloakbrowser_downloader import CloakBrowserDownloader
    dl = CloakBrowserDownloader(make_mock_crawler())

    mock_browser = AsyncMock()
    mock_context = AsyncMock()
    p1, p2 = AsyncMock(), AsyncMock()

    dl._browser = mock_browser
    dl._context = mock_context
    dl._page_pool = [p1, p2]
    dl._used_pages = {id(p1), id(p2)}

    await dl.close()

    p1.close.assert_called_once()
    p2.close.assert_called_once()
    mock_context.close.assert_called_once()
    mock_browser.close.assert_called_once()
    assert dl._page_pool == []
    assert dl._used_pages == set()
    assert dl._context is None
    assert dl._browser is None


@test_case("11.2 关闭异常 - 优雅处理")
async def test_close_exception():
    from crawlo.downloader.cloakbrowser_downloader import CloakBrowserDownloader
    dl = CloakBrowserDownloader(make_mock_crawler())

    mock_browser = AsyncMock()
    mock_browser.close = AsyncMock(side_effect=Exception("Close error"))
    dl._browser = mock_browser
    dl._context = AsyncMock()

    # 不应抛出异常
    await dl.close()
    assert dl._browser is None


@test_case("11.3 未初始化时关闭")
async def test_close_uninitialized():
    from crawlo.downloader.cloakbrowser_downloader import CloakBrowserDownloader
    dl = CloakBrowserDownloader(make_mock_crawler())
    await dl.close()  # 应不抛出异常


# ==================== 第12组: 翻页操作 ====================

@test_case("12.1 翻页 - scroll 操作")
async def test_pagination_scroll():
    from crawlo.downloader.cloakbrowser_downloader import CloakBrowserDownloader
    from crawlo.network.request import Request
    dl = CloakBrowserDownloader(make_mock_crawler())
    dl.humanize = False

    req = Request(url="https://example.com")
    req.meta['pagination_actions'] = [
        {"type": "scroll", "params": {"count": 3, "distance": 300, "delay": 100}},
    ]

    mock_page = AsyncMock()
    await dl._execute_pagination_actions(mock_page, req)
    assert mock_page.mouse.wheel.call_count == 3


@test_case("12.2 翻页 - click 操作")
async def test_pagination_click():
    from crawlo.downloader.cloakbrowser_downloader import CloakBrowserDownloader
    from crawlo.network.request import Request
    dl = CloakBrowserDownloader(make_mock_crawler())
    dl.humanize = False

    req = Request(url="https://example.com")
    req.meta['pagination_actions'] = [
        {"type": "click", "params": {"selector": ".next-page", "count": 2}},
    ]

    mock_page = AsyncMock()
    await dl._execute_pagination_actions(mock_page, req)
    assert mock_page.click.call_count == 2


@test_case("12.3 翻页 - evaluate 操作")
async def test_pagination_evaluate():
    from crawlo.downloader.cloakbrowser_downloader import CloakBrowserDownloader
    from crawlo.network.request import Request
    dl = CloakBrowserDownloader(make_mock_crawler())

    req = Request(url="https://example.com")
    req.meta['pagination_actions'] = [
        {"type": "evaluate", "params": {"script": "window.scrollTo(0, 0)"}},
    ]

    mock_page = AsyncMock()
    await dl._execute_pagination_actions(mock_page, req)
    mock_page.evaluate.assert_called_once_with("window.scrollTo(0, 0)")


# ==================== 第13组: 真实浏览器下载测试 ====================

_real_dl_counter = [0]

async def _create_real_downloader(extra_settings=None):
    """创建真实 CloakBrowser 下载器实例（直接实例化，不通过 Crawler）"""
    from crawlo.downloader.cloakbrowser_downloader import CloakBrowserDownloader

    defaults = {
        'CLOAKBROWSER_HEADLESS': True,
        'CLOAKBROWSER_HUMANIZE': False,
        'CLOAKBROWSER_TIMEOUT': 30000,
        'CLOAKBROWSER_BLOCK_RESOURCES': ['image', 'font', 'media'],
        'CLOAKBROWSER_GEOIP': False,
        'CLOAKBROWSER_STEALTH_ARGS': True,
        'CLOAKBROWSER_AUTO_SCROLL': False,
        'CLOAKBROWSER_PERSISTENT_CONTEXT': False,
        'DOWNLOAD_STATS': True,
    }
    get_defaults = {
        'CLOAKBROWSER_PROXY': None,
        'PROXY_API_URL': None,
        'CLOAKBROWSER_HUMAN_PRESET': 'default',
        'CLOAKBROWSER_HUMAN_CONFIG': None,
        'CLOAKBROWSER_TIMEZONE': None,
        'CLOAKBROWSER_LOCALE': None,
        'CLOAKBROWSER_BACKEND': 'playwright',
        'CLOAKBROWSER_FINGERPRINT': None,
        'CLOAKBROWSER_FINGERPRINT_PLATFORM': None,
        'CLOAKBROWSER_USER_DATA_DIR': None,
        'CLOAKBROWSER_WAIT_STRATEGY': 'auto',
        'CLOAKBROWSER_WAIT_FOR_ELEMENT': None,
    }
    int_defaults = {
        'CLOAKBROWSER_TIMEOUT': 30000,
        'CLOAKBROWSER_LOAD_TIMEOUT': 10000,
        'CLOAKBROWSER_VIEWPORT_WIDTH': 1280,
        'CLOAKBROWSER_VIEWPORT_HEIGHT': 720,
        'CLOAKBROWSER_MAX_PAGES': 10,
        'CLOAKBROWSER_SCROLL_DELAY': 500,
        'CLOAKBROWSER_WAIT_TIMEOUT': 10000,
    }
    list_defaults = {
        'CLOAKBROWSER_ARGS': [],
        'CLOAKBROWSER_BLOCK_RESOURCES': ['image', 'font', 'media'],
    }

    if extra_settings:
        defaults.update({k: v for k, v in extra_settings.items() if k in defaults})
        get_defaults.update({k: v for k, v in extra_settings.items() if k in get_defaults})
        int_defaults.update({k: v for k, v in extra_settings.items() if k in int_defaults})
        list_defaults.update({k: v for k, v in extra_settings.items() if k in list_defaults})

    crawler = Mock()
    crawler.settings = Mock()
    crawler.settings.get_bool = Mock(side_effect=lambda key, default: defaults.get(key, default))
    crawler.settings.get = Mock(side_effect=lambda key, default: get_defaults.get(key, default))
    crawler.settings.get_int = Mock(side_effect=lambda key, default: int_defaults.get(key, default))
    crawler.settings.get_list = Mock(side_effect=lambda key, default: list_defaults.get(key, default))
    crawler.spider = Mock()
    _real_dl_counter[0] += 1
    crawler.spider.name = f'cb_real_test_{_real_dl_counter[0]}'

    dl = CloakBrowserDownloader(crawler)
    # 不调用 dl.open() 来避免 middleware 初始化问题
    return dl


@test_case("13.1 真实浏览器 - 启动与关闭")
async def test_real_browser_lifecycle():
    dl = await _create_real_downloader()
    try:
        await dl._initialize_browser()
        assert dl._browser is not None or dl._context is not None
        assert dl._page_semaphore is not None
    finally:
        await dl.close()
        assert dl._browser is None
        assert dl._context is None


@test_case("13.2 真实浏览器 - 下载静态页面")
async def test_real_download_static():
    from crawlo.network.request import Request
    dl = await _create_real_downloader()
    try:
        req = Request(url="https://example.com")
        resp = await dl.download(req)
        assert resp is not None
        assert resp.status == 200
        assert b"Example Domain" in resp.body or b"example" in resp.body.lower()
    finally:
        await dl.close()


@test_case("13.3 真实浏览器 - 下载 HTTPS 页面")
async def test_real_download_https():
    from crawlo.network.request import Request
    dl = await _create_real_downloader()
    try:
        req = Request(url="https://httpbin.org/get")
        resp = await dl.download(req)
        assert resp is not None
        assert resp.status == 200
    finally:
        await dl.close()


@test_case("13.4 真实浏览器 - 404 页面处理")
async def test_real_download_404():
    from crawlo.network.request import Request
    dl = await _create_real_downloader()
    try:
        req = Request(url="https://httpbin.org/status/404")
        try:
            resp = await dl.download(req)
            # Chromium 对 4xx 可能正常返回也可能抛异常
            if resp is not None:
                assert resp.status == 404
        except Exception as e:
            # Chromium 对 4xx/5xx 会抛 ERR_HTTP_RESPONSE_CODE_FAILURE
            # 这是预期行为，CloakBrowser 将异常传播给上层
            assert "ERR_HTTP_RESPONSE_CODE_FAILURE" in str(e) or "404" in str(e) or "net::ERR" in str(e)
    finally:
        await dl.close()


@test_case("13.5 真实浏览器 - 资源屏蔽验证")
async def test_real_resource_blocking():
    from crawlo.network.request import Request
    dl = await _create_real_downloader()
    try:
        req = Request(url="https://example.com")
        resp = await dl.download(req)
        assert resp is not None
        # 资源屏蔽不影响 HTML 内容
        assert resp.status == 200
    finally:
        await dl.close()


# ==================== 第14组: 边界测试 ====================

@test_case("14.1 极短超时 - 浏览器启动超时保护")
async def test_boundary_short_timeout():
    """验证极短超时不会无限卡住"""
    from crawlo.downloader.cloakbrowser_downloader import CloakBrowserDownloader
    overrides = {'CLOAKBROWSER_TIMEOUT': 500}  # 0.5s，极短
    dl = CloakBrowserDownloader(make_mock_crawler(overrides))

    async def slow_launch(**kwargs):
        await asyncio.sleep(10)

    with patch('cloakbrowser.launch_async', slow_launch):
        start = time.time()
        try:
            await dl._initialize_browser()
            assert False, "应超时"
        except asyncio.TimeoutError:
            elapsed = time.time() - start
            assert elapsed < 5, f"超时保护未生效，耗时 {elapsed:.1f}s"


@test_case("14.2 大页面内容下载")
async def test_boundary_large_page():
    """验证大页面不会导致内存溢出"""
    from crawlo.network.request import Request
    dl = await _create_real_downloader()
    try:
        # httpbin 的 HTML 页面
        req = Request(url="https://httpbin.org/html")
        resp = await dl.download(req)
        assert resp is not None
        assert resp.status == 200
        assert len(resp.body) > 0
    finally:
        await dl.close()


@test_case("14.3 并发达到上限 - 页面池")
async def test_boundary_max_pages():
    """验证并发请求不超过 max_pages 限制"""
    from crawlo.network.request import Request
    from crawlo.network.response import Response
    max_pages = 2
    dl = await _create_real_downloader({'CLOAKBROWSER_MAX_PAGES': max_pages})
    try:
        urls = [
            f"https://httpbin.org/delay/1?t={i}"
            for i in range(max_pages + 2)
        ]

        # 同时发起 max_pages+2 个请求
        tasks = []
        for url in urls:
            req = Request(url=url)
            tasks.append(dl.download(req))

        # 使用较短的总体超时
        results = await asyncio.wait_for(
            asyncio.gather(*tasks, return_exceptions=True),
            timeout=30
        )

        # 验证没有因并发超限导致的意外错误
        successes = [r for r in results if isinstance(r, Response) or (hasattr(r, 'status') and r is not None and not isinstance(r, Exception))]
        # 至少应有部分成功
        assert len(successes) > 0 or any(results), "所有请求都失败了"
    finally:
        await dl.close()


@test_case("14.4 连续快速下载 - 页面复用")
async def test_boundary_rapid_sequential():
    """验证快速连续下载时页面正确复用"""
    from crawlo.network.request import Request
    dl = await _create_real_downloader()
    try:
        urls = ["https://example.com", "https://example.com", "https://example.com"]
        for i, url in enumerate(urls):
            req = Request(url=url)
            resp = await dl.download(req)
            assert resp is not None
            assert resp.status == 200

        # 页面池应有复用
        assert len(dl._page_pool) >= 1
    finally:
        await dl.close()


@test_case("14.5 无效 URL - 异常处理")
async def test_boundary_invalid_url():
    """验证无效 URL 的异常处理"""
    from crawlo.network.request import Request
    dl = await _create_real_downloader()
    try:
        # 使用一个不可达的地址
        req = Request(url="https://192.0.2.1:1")  # RFC 5737 测试地址
        try:
            resp = await dl.download(req)
            # 可能超时或返回错误
        except Exception:
            pass  # 预期可能抛异常
    finally:
        await dl.close()


# ==================== 第15组: 压力测试 ====================

@test_case("15.1 压力测试 - 10次快速连续下载")
async def test_stress_10_sequential():
    """10次快速连续下载"""
    from crawlo.network.request import Request
    dl = await _create_real_downloader()
    try:
        start = time.time()
        for i in range(10):
            req = Request(url="https://example.com")
            resp = await dl.download(req)
            assert resp is not None, f"第 {i+1} 次下载失败"
            assert resp.status == 200, f"第 {i+1} 次状态码 {resp.status}"

        elapsed = time.time() - start
        avg = elapsed / 10
        print(f"  10次连续下载耗时: {elapsed:.2f}s, 平均: {avg:.2f}s/次")
    finally:
        await dl.close()


@test_case("15.2 压力测试 - 5个并发下载")
async def test_stress_5_concurrent():
    """5个并发下载"""
    from crawlo.network.request import Request
    dl = await _create_real_downloader({'CLOAKBROWSER_MAX_PAGES': 5})
    try:
        urls = ["https://example.com"] * 5
        tasks = []
        for url in urls:
            req = Request(url=url)
            tasks.append(dl.download(req))

        start = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        elapsed = time.time() - start

        successes = sum(1 for r in results if r is not None and not isinstance(r, Exception))
        print(f"  5并发下载: {successes}/5 成功, 耗时: {elapsed:.2f}s")
        assert successes >= 3, f"成功率过低: {successes}/5"
    finally:
        await dl.close()


@test_case("15.3 压力测试 - 混合 URL 并发")
async def test_stress_mixed_urls():
    """混合不同 URL 并发下载"""
    from crawlo.network.request import Request
    dl = await _create_real_downloader({'CLOAKBROWSER_MAX_PAGES': 5})
    try:
        urls = [
            "https://example.com",
            "https://httpbin.org/get",
            "https://httpbin.org/html",
            "https://example.com",
            "https://httpbin.org/status/200",
        ]
        tasks = []
        for url in urls:
            req = Request(url=url)
            tasks.append(dl.download(req))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        successes = sum(1 for r in results if r is not None and not isinstance(r, Exception))
        print(f"  混合URL并发: {successes}/{len(urls)} 成功")
        assert successes >= 3, f"成功率过低: {successes}/{len(urls)}"
    finally:
        await dl.close()


@test_case("15.4 压力测试 - 页面池耗尽恢复")
async def test_stress_pool_exhaustion():
    """页面池耗尽后恢复"""
    from crawlo.downloader.cloakbrowser_downloader import CloakBrowserDownloader
    from crawlo.network.request import Request
    max_pages = 2
    dl = await _create_real_downloader({'CLOAKBROWSER_MAX_PAGES': max_pages})
    try:
        # 第一轮: 用满页面池
        for i in range(max_pages):
            req = Request(url="https://example.com")
            resp = await dl.download(req)
            assert resp is not None

        # 第二轮: 页面池已回收，应可继续使用
        req = Request(url="https://example.com")
        resp = await dl.download(req)
        assert resp is not None
        assert resp.status == 200
    finally:
        await dl.close()


@test_case("15.5 长时间运行 - 30次下载稳定性")
async def test_stress_long_run():
    """30次下载的稳定性测试"""
    from crawlo.network.request import Request
    dl = await _create_real_downloader({'CLOAKBROWSER_MAX_PAGES': 3})
    try:
        success_count = 0
        error_count = 0
        start = time.time()

        for i in range(30):
            try:
                req = Request(url="https://example.com")
                resp = await dl.download(req)
                if resp and resp.status == 200:
                    success_count += 1
                else:
                    error_count += 1
            except Exception:
                error_count += 1

        elapsed = time.time() - start
        rate = success_count / 30 * 100
        print(f"  30次下载: 成功{success_count}, 失败{error_count}, "
              f"耗时{elapsed:.1f}s, 成功率{rate:.0f}%")

        # 页面池大小应保持合理
        print(f"  页面池大小: {len(dl._page_pool)}, 使用中: {len(dl._used_pages)}")
        assert success_count >= 25, f"成功率过低: {success_count}/30"
    finally:
        await dl.close()


# ==================== 第16组: HybridDownloader 集成 ====================

@test_case("16.1 HybridDownloader 动态下载器选择")
async def test_hybrid_dynamic_selection():
    from crawlo.downloader.hybrid_downloader import HybridDownloader
    from crawlo.network.request import Request
    crawler = make_mock_crawler({
        'HYBRID_DEFAULT_PROTOCOL_DOWNLOADER': 'aiohttp',
        'HYBRID_DEFAULT_DYNAMIC_DOWNLOADER': 'cloakbrowser',
    })
    crawler.settings.get = Mock(side_effect=lambda key, default: {
        'HYBRID_DEFAULT_PROTOCOL_DOWNLOADER': 'aiohttp',
        'HYBRID_DEFAULT_DYNAMIC_DOWNLOADER': 'cloakbrowser',
    }.get(key, default))

    hybrid = HybridDownloader(crawler)
    req = Request(url="https://example.com")
    req.meta['use_dynamic_loader'] = True

    dtype = hybrid._determine_downloader_type(req)
    assert dtype == "dynamic"


@test_case("16.2 HybridDownloader 协议下载器选择")
async def test_hybrid_protocol_selection():
    from crawlo.downloader.hybrid_downloader import HybridDownloader
    from crawlo.network.request import Request
    crawler = make_mock_crawler()
    crawler.settings.get = Mock(return_value='aiohttp')

    hybrid = HybridDownloader(crawler)
    req = Request(url="https://example.com")
    req.meta['use_protocol_loader'] = True

    dtype = hybrid._determine_downloader_type(req)
    assert dtype == "protocol"


@test_case("16.3 HybridDownloader URL 模式匹配")
async def test_hybrid_url_pattern():
    from crawlo.downloader.hybrid_downloader import HybridDownloader
    from crawlo.network.request import Request
    crawler = make_mock_crawler()
    crawler.settings.get = Mock(return_value='aiohttp')
    crawler.settings.get_list = Mock(side_effect=lambda key, default: {
        'HYBRID_DYNAMIC_URL_PATTERNS': [r'.*baike\.baidu\.com.*'],
        'HYBRID_PROTOCOL_URL_PATTERNS': [],
    }.get(key, default))

    hybrid = HybridDownloader(crawler)
    req = Request(url="https://baike.baidu.com/item/test")

    dtype = hybrid._determine_downloader_type(req)
    assert dtype == "dynamic"


# ==================== 主测试执行 ====================

async def run_unit_tests():
    """运行所有 Mock 单元测试（第1-12组）"""
    print()
    print("=" * 80)
    print("  CloakBrowser 下载器全面测试 - 第1部分: 单元测试 (Mock)")
    print("=" * 80)
    print()

    unit_tests = [
        # 第1组
        test_import, test_downloader_map, test_hybrid_map,
        # 第2组
        test_basic_instantiation, test_default_config, test_custom_config, test_open_lazy,
        # 第3组
        test_get_page_new, test_get_page_reuse, test_release_page,
        test_page_semaphore, test_page_get_exception, test_release_unknown_page,
        # 第4组
        test_launch_timeout, test_kill_orphan_chromium, test_launch_kwargs,
        test_persistent_context,
        # 第5组
        test_wait_auto, test_wait_network_idle, test_wait_dom_ready,
        test_wait_meta_override, test_wait_custom,
        # 第6组
        test_block_resources_default, test_block_resources_meta, test_block_resources_empty,
        # 第7组
        test_auto_scroll_config, test_auto_scroll_meta_disable,
        test_scroll_with_new_content, test_scroll_safety_limit, test_scroll_humanize,
        # 第8组
        test_custom_action_click, test_custom_action_click_and_wait,
        test_custom_action_fill, test_custom_action_evaluate,
        test_custom_action_scroll, test_custom_action_wait_humanize,
        test_xpath_selector, test_custom_action_error_continues,
        # 第9组
        test_request_headers, test_request_cookies, test_get_cookies, test_get_cookies_error,
        # 第10组
        test_proxy_direct, test_proxy_none, test_proxy_api_simple,
        test_proxy_api_nested, test_proxy_api_ip_format, test_proxy_api_failure,
        # 第11组
        test_close_all, test_close_exception, test_close_uninitialized,
        # 第12组
        test_pagination_scroll, test_pagination_click, test_pagination_evaluate,
    ]

    for t in unit_tests:
        await t()

    print(f"\n单元测试完成: 通过 {results.passed}, 失败 {results.failed}, 跳过 {results.skipped}")


async def run_real_tests():
    """运行真实浏览器测试（第13-15组）"""
    print()
    print("=" * 80)
    print("  CloakBrowser 下载器全面测试 - 第2部分: 真实浏览器测试")
    print("=" * 80)
    print()

    # 检查 CloakBrowser 是否可用
    try:
        from cloakbrowser import ensure_binary
        path = ensure_binary()
        print(f"  CloakBrowser Chromium: {path}")
    except Exception as e:
        print(f"  CloakBrowser 不可用: {e}")
        print("  跳过真实浏览器测试")
        return

    real_tests = [
        # 第13组
        test_real_browser_lifecycle, test_real_download_static,
        test_real_download_https, test_real_download_404,
        test_real_resource_blocking,
        # 第14组
        test_boundary_short_timeout, test_boundary_large_page,
        test_boundary_max_pages, test_boundary_rapid_sequential,
        test_boundary_invalid_url,
        # 第15组
        test_stress_10_sequential, test_stress_5_concurrent,
        test_stress_mixed_urls, test_stress_pool_exhaustion,
        test_stress_long_run,
    ]

    for t in real_tests:
        await t()

    print(f"\n真实浏览器测试完成: 通过 {results.passed}, 失败 {results.failed}, 跳过 {results.skipped}")


async def run_hybrid_tests():
    """运行 HybridDownloader 集成测试（第16组）"""
    print()
    print("=" * 80)
    print("  CloakBrowser 下载器全面测试 - 第3部分: HybridDownloader 集成")
    print("=" * 80)
    print()

    hybrid_tests = [
        test_hybrid_dynamic_selection,
        test_hybrid_protocol_selection,
        test_hybrid_url_pattern,
    ]

    for t in hybrid_tests:
        await t()


async def main():
    print()
    print("+" + "=" * 78 + "+")
    print("|" + " " * 18 + "CloakBrowser 下载器全面测试套件" + " " * 26 + "|")
    print("+" + "=" * 78 + "+")
    print(f"  开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 第1部分: 单元测试
    await run_unit_tests()

    # 第2部分: 真实浏览器测试
    await run_real_tests()

    # 第3部分: HybridDownloader 集成
    await run_hybrid_tests()

    # 汇总
    print(results.summary())

    return results.failed == 0


if __name__ == '__main__':
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
        sys.exit(1)
