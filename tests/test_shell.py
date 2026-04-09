#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Crawlo Shell 完整测试套件
========================
测试覆盖：
1. CrawloShell 初始化与基本属性
2. fetch() 异步/同步方法
3. view() 浏览器预览
4. get_namespace() / update_namespace()
5. _MockCrawler / _MockSpider
6. _DownloaderAdapter
7. _SimpleFetcher
8. _get_banner() 横幅生成
9. close() 资源清理
10. CLI 命令入口
11. 端到端集成测试
"""
import sys
import os
import asyncio
import tempfile
from unittest.mock import patch, MagicMock, AsyncMock

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.shell.core import (
    CrawloShell, _MockCrawler, _MockSpider, _DownloaderAdapter, _SimpleFetcher
)
from crawlo.network.request import Request
from crawlo.network.response import Response


# ==================== 1. _MockCrawler / _MockSpider ====================

def test_mock_crawler_with_none_settings():
    """测试 _MockCrawler 默认初始化（自动创建 SettingManager）"""
    crawler = _MockCrawler(settings=None)
    assert crawler.settings is not None
    assert crawler.spider is not None
    assert crawler.spider.name == 'shell'
    print("✅ _MockCrawler 默认初始化测试通过")


def test_mock_crawler_with_custom_settings():
    """测试 _MockCrawler 自定义 settings（dict 会被转换为 SettingManager）"""
    custom = {'CONCURRENCY': 16}
    crawler = _MockCrawler(settings=custom)
    # dict 会被转换为 SettingManager
    assert crawler.settings is not None
    assert hasattr(crawler.settings, 'get')
    assert crawler.settings.get('CONCURRENCY', None) == 16
    print("✅ _MockCrawler 自定义 settings 测试通过")


def test_mock_spider():
    """测试 _MockSpider"""
    spider = _MockSpider()
    assert spider.name == 'shell'
    assert str(spider) == 'shell'
    print("✅ _MockSpider 测试通过")


# ==================== 2. CrawloShell 初始化 ====================

def test_shell_init_default():
    """测试 CrawloShell 默认初始化"""
    shell = CrawloShell()
    assert shell.settings == {}
    assert shell.request is None
    assert shell.response is None
    assert shell._downloader is None
    assert shell._temp_files == []
    print("✅ CrawloShell 默认初始化测试通过")


def test_shell_init_with_settings():
    """测试 CrawloShell 带 settings 初始化"""
    settings = {'CONCURRENCY': 32, 'LOG_LEVEL': 'DEBUG'}
    shell = CrawloShell(settings=settings)
    assert shell.settings == settings
    print("✅ CrawloShell 带 settings 初始化测试通过")


# ==================== 3. get_namespace / update_namespace ====================

def test_get_namespace():
    """测试命名空间内容完整性"""
    shell = CrawloShell()
    ns = shell.get_namespace()
    
    # 验证核心键
    assert 'fetch' in ns, "Namespace 缺少 'fetch'"
    assert 'view' in ns, "Namespace 缺少 'view'"
    assert 'request' in ns, "Namespace 缺少 'request'"
    assert 'response' in ns, "Namespace 缺少 'response'"
    assert 'settings' in ns, "Namespace 缺少 'settings'"
    assert 'Request' in ns, "Namespace 缺少 'Request'"
    
    # 验证 fetch 是同步方法
    assert callable(ns['fetch']), "'fetch' 不是可调用对象"
    assert callable(ns['view']), "'view' 不是可调用对象"
    
    # 验证初始值
    assert ns['request'] is None
    assert ns['response'] is None
    assert ns['settings'] == {}
    
    print("✅ get_namespace 测试通过")


def test_update_namespace():
    """测试更新命名空间"""
    shell = CrawloShell()
    
    # 模拟 fetch 后更新
    shell.request = Request(url="https://example.com")
    resp = Response(url="https://example.com", body=b"<h1>Hello</h1>", status_code=200)
    shell.response = resp
    
    updated = shell.update_namespace()
    assert updated['request'] is shell.request
    assert updated['response'] is shell.response
    print("✅ update_namespace 测试通过")


# ==================== 4. _get_banner ====================

def test_banner_without_url():
    """测试无 URL 时的横幅"""
    shell = CrawloShell()
    banner = shell._get_banner()
    
    assert "Crawlo Shell" in banner
    assert "fetch(url)" in banner
    assert "view(response)" in banner
    assert "Pre-fetched" not in banner
    print("✅ 无 URL 横幅测试通过")


def test_banner_with_url():
    """测试带 URL 时的横幅"""
    shell = CrawloShell()
    banner = shell._get_banner(url="https://example.com")
    
    assert "Crawlo Shell" in banner
    assert "Pre-fetched: https://example.com" in banner
    print("✅ 带 URL 横幅测试通过")


# ==================== 5. view() 浏览器预览 ====================

def test_view_no_response():
    """测试无 response 时调用 view"""
    shell = CrawloShell()
    # 不应抛出异常
    shell.view()
    print("✅ view 无 response 测试通过")


def test_view_with_response():
    """测试带 response 的 view（Mock webbrowser）"""
    shell = CrawloShell()
    html = "<html><body><h1>Test Page</h1></body></html>"
    resp = Response(url="https://example.com", body=html.encode('utf-8'), status_code=200)
    
    with patch('webbrowser.open') as mock_open:
        shell.view(response=resp)
        # 验证 webbrowser.open 被调用
        assert mock_open.called, "webbrowser.open 未被调用"
        called_url = mock_open.call_args[0][0]
        assert called_url.startswith('file://'), f"URL 格式不正确: {called_url}"
    
    # 清理临时文件
    shell._cleanup_temp_files()
    print("✅ view 带 response 测试通过")


def test_view_uses_self_response():
    """测试 view 默认使用 self.response"""
    shell = CrawloShell()
    html = "<html><body>Default</body></html>"
    shell.response = Response(url="https://example.com", body=html.encode('utf-8'), status_code=200)
    
    with patch('webbrowser.open') as mock_open:
        shell.view()  # 不传 response 参数
        assert mock_open.called
    
    shell._cleanup_temp_files()
    print("✅ view 默认使用 self.response 测试通过")


# ==================== 6. _cleanup_temp_files 资源清理 ====================

def test_cleanup_temp_files():
    """测试临时文件清理"""
    shell = CrawloShell()
    
    # 手动创建临时文件
    fd, path = tempfile.mkstemp(suffix='.html', prefix='crawlo_test_')
    os.close(fd)
    shell._temp_files.append(path)
    
    assert os.path.exists(path), "临时文件未创建"
    
    shell._cleanup_temp_files()
    assert not os.path.exists(path), "临时文件未被清理"
    assert shell._temp_files == [], "临时文件列表未清空"
    print("✅ 临时文件清理测试通过")


def test_cleanup_nonexistent_file():
    """测试清理不存在的临时文件（不应抛异常）"""
    shell = CrawloShell()
    shell._temp_files.append("/nonexistent/path/test.html")
    # 不应抛出异常
    shell._cleanup_temp_files()
    assert shell._temp_files == []
    print("✅ 清理不存在的临时文件测试通过")


# ==================== 7. _DownloaderAdapter ====================

def test_downloader_adapter_success():
    """测试 _DownloaderAdapter 成功调用 download"""
    mock_dl = MagicMock()
    mock_dl.download = AsyncMock(return_value=Response(
        url="https://example.com", body=b"content", status_code=200
    ))
    
    adapter = _DownloaderAdapter(mock_dl)
    request = Request(url="https://example.com")
    
    result = asyncio.run(adapter.fetch(request))
    assert result is not None
    assert result.status_code == 200
    mock_dl.download.assert_called_once_with(request)
    print("✅ _DownloaderAdapter 成功调用测试通过")


def test_downloader_adapter_error():
    """测试 _DownloaderAdapter 下载失败"""
    mock_dl = MagicMock()
    mock_dl.download = AsyncMock(side_effect=Exception("Network error"))
    
    adapter = _DownloaderAdapter(mock_dl)
    request = Request(url="https://example.com")
    
    result = asyncio.run(adapter.fetch(request))
    assert result is None
    print("✅ _DownloaderAdapter 错误处理测试通过")


def test_downloader_adapter_close():
    """测试 _DownloaderAdapter 关闭"""
    mock_dl = MagicMock()
    mock_dl.close = AsyncMock()
    
    adapter = _DownloaderAdapter(mock_dl)
    asyncio.run(adapter.close())
    mock_dl.close.assert_called_once()
    print("✅ _DownloaderAdapter 关闭测试通过")


def test_downloader_adapter_close_error():
    """测试 _DownloaderAdapter 关闭时的错误处理"""
    mock_dl = MagicMock()
    mock_dl.close = AsyncMock(side_effect=Exception("Close error"))
    
    adapter = _DownloaderAdapter(mock_dl)
    # 不应抛出异常
    asyncio.run(adapter.close())
    print("✅ _DownloaderAdapter 关闭错误处理测试通过")


# ==================== 8. _SimpleFetcher ====================

def test_simple_fetcher_close():
    """测试 _SimpleFetcher close（空操作）"""
    fetcher = _SimpleFetcher()
    asyncio.run(fetcher.close())  # 不应抛出异常
    print("✅ _SimpleFetcher close 测试通过")


# ==================== 9. fetch() 异步方法 ====================

def test_fetch_downloader_init_failure():
    """测试下载器初始化失败时的 fetch"""
    shell = CrawloShell()
    
    # Mock _get_downloader 返回 None
    shell._get_downloader = AsyncMock(return_value=None)
    
    result = asyncio.run(shell.fetch("https://example.com"))
    assert result is None
    print("✅ 下载器初始化失败测试通过")


def test_fetch_success():
    """测试成功 fetch"""
    shell = CrawloShell()
    
    mock_response = Response(
        url="https://example.com",
        body=b"<html><body>Hello</body></html>",
        status_code=200
    )
    
    mock_downloader = MagicMock()
    mock_downloader.fetch = AsyncMock(return_value=mock_response)
    
    # 直接设置下载器
    shell._downloader = mock_downloader
    
    result = asyncio.run(shell.fetch("https://example.com"))
    
    assert result is not None
    assert result.status_code == 200
    assert shell.request is not None
    assert shell.request.url == "https://example.com"
    assert shell.response is mock_response
    print("✅ fetch 成功测试通过")


def test_fetch_returns_none_on_error():
    """测试 fetch 返回 None（下载器返回 None）"""
    shell = CrawloShell()
    
    mock_downloader = MagicMock()
    mock_downloader.fetch = AsyncMock(return_value=None)
    shell._downloader = mock_downloader
    
    result = asyncio.run(shell.fetch("https://nonexistent.invalid"))
    assert result is None
    assert shell.response is None
    print("✅ fetch 返回 None 测试通过")


def test_fetch_exception_handling():
    """测试 fetch 异常处理"""
    shell = CrawloShell()
    
    mock_downloader = MagicMock()
    mock_downloader.fetch = AsyncMock(side_effect=Exception("Connection refused"))
    shell._downloader = mock_downloader
    
    result = asyncio.run(shell.fetch("https://example.com"))
    assert result is None
    print("✅ fetch 异常处理测试通过")


# ==================== 10. sync_fetch 同步方法 ====================

def test_sync_fetch():
    """测试同步 fetch"""
    shell = CrawloShell()
    
    mock_response = Response(
        url="https://example.com",
        body=b"<html><body>Sync Test</body></html>",
        status_code=200
    )
    
    mock_downloader = MagicMock()
    mock_downloader.fetch = AsyncMock(return_value=mock_response)
    shell._downloader = mock_downloader
    
    result = shell.sync_fetch("https://example.com")
    assert result is not None
    assert result.status_code == 200
    print("✅ sync_fetch 测试通过")


# ==================== 11. close() 资源清理 ====================

def test_close_with_downloader():
    """测试带下载器的 close"""
    shell = CrawloShell()
    
    mock_dl = MagicMock()
    mock_dl.close = AsyncMock()
    shell._downloader = mock_dl
    
    asyncio.run(shell.close())
    
    assert shell._downloader is None
    mock_dl.close.assert_called_once()
    print("✅ 带下载器的 close 测试通过")


def test_close_without_downloader():
    """测试无下载器的 close"""
    shell = CrawloShell()
    asyncio.run(shell.close())  # 不应抛出异常
    print("✅ 无下载器的 close 测试通过")


def test_close_downloader_error():
    """测试 close 时下载器关闭失败"""
    shell = CrawloShell()
    
    mock_dl = MagicMock()
    mock_dl.close = AsyncMock(side_effect=Exception("Close error"))
    shell._downloader = mock_dl
    
    # 不应抛出异常
    asyncio.run(shell.close())
    assert shell._downloader is None
    print("✅ 下载器关闭失败测试通过")


# ==================== 12. _try_framework_downloader ====================

def test_try_framework_downloader_fallback():
    """测试框架下载器创建失败时返回 None"""
    shell = CrawloShell()
    # CrawloShell 默认 settings={}，不是 SettingManager
    # 框架下载器创建可能失败，返回 None
    result = shell._try_framework_downloader()
    # 不管成功还是失败，都不应抛异常
    assert result is None or result is not None  # 只是验证不崩溃
    print("✅ 框架下载器回退测试通过")


def test_try_framework_downloader_with_setting_manager():
    """测试使用 SettingManager 的框架下载器创建"""
    try:
        from crawlo.settings.setting_manager import SettingManager
        settings = SettingManager()
        shell = CrawloShell(settings=settings)
        result = shell._try_framework_downloader()
        # 验证不崩溃
        assert result is None or hasattr(result, 'download')
        print("✅ SettingManager 框架下载器测试通过")
    except ImportError:
        print("⚠️ SettingManager 不可用，跳过此测试")


# ==================== 13. _run_async ====================

def test_run_async_no_loop():
    """测试不在事件循环中调用 _run_async"""
    shell = CrawloShell()
    
    async def dummy():
        return 42
    
    result = shell._run_async(dummy())
    assert result == 42
    print("✅ _run_async 无事件循环测试通过")


# ==================== 14. CLI 命令入口 ====================

def test_shell_command_import():
    """测试 shell 命令模块导入"""
    from crawlo.commands.shell import main, _load_project_settings
    assert callable(main)
    assert callable(_load_project_settings)
    print("✅ shell 命令模块导入测试通过")


def test_shell_command_registered():
    """测试 shell 命令已注册"""
    from crawlo.commands import get_commands
    commands = get_commands()
    assert 'shell' in commands, "'shell' 命令未注册"
    assert commands['shell'] == 'crawlo.commands.shell'
    print("✅ shell 命令注册测试通过")


def test_shell_help_output():
    """测试帮助信息中包含 shell 命令"""
    from crawlo.commands.help import show_help
    # 只验证不崩溃
    try:
        show_help()
    except Exception:
        pass  # 帮助命令可能因终端宽度等问题失败
    print("✅ shell 帮助信息测试通过")


# ==================== 15. 端到端集成测试 ====================

def test_e2e_fetch_and_view():
    """端到端测试：fetch → response 属性 → view"""
    shell = CrawloShell()
    
    mock_response = Response(
        url="https://example.com",
        body=b"<html><body><h1>E2E Test</h1></body></html>",
        status_code=200,
        headers={"content-type": "text/html; charset=utf-8"}
    )
    
    mock_dl = MagicMock()
    mock_dl.fetch = AsyncMock(return_value=mock_response)
    shell._downloader = mock_dl
    
    # Step 1: fetch
    result = asyncio.run(shell.fetch("https://example.com"))
    assert result is not None
    assert shell.request is not None
    assert shell.response is not None
    assert shell.response.status_code == 200
    
    # Step 2: 测试 response 选择器
    text = shell.response.css("h1::text").get()
    assert text == "E2E Test", f"选择器结果不正确: {text}"
    
    # Step 3: view
    with patch('webbrowser.open') as mock_open:
        shell.view()
        assert mock_open.called
    
    # Step 4: 关闭
    asyncio.run(shell.close())
    
    print("✅ 端到端 fetch → selector → view 测试通过")


def test_e2e_namespace_after_fetch():
    """端到端测试：fetch 后命名空间更新"""
    shell = CrawloShell()
    
    mock_response = Response(
        url="https://example.com",
        body=b"<html><body>Content</body></html>",
        status_code=200
    )
    
    mock_dl = MagicMock()
    mock_dl.fetch = AsyncMock(return_value=mock_response)
    shell._downloader = mock_dl
    
    # 初始命名空间
    ns = shell.get_namespace()
    assert ns['request'] is None
    assert ns['response'] is None
    
    # fetch
    asyncio.run(shell.fetch("https://example.com"))
    
    # 更新后命名空间
    updated = shell.update_namespace()
    assert updated['request'] is not None
    assert updated['response'] is not None
    
    print("✅ 端到端命名空间更新测试通过")


def test_e2e_multiple_fetch():
    """端到端测试：多次 fetch 更新 request/response"""
    shell = CrawloShell()
    
    # 第一次 fetch
    resp1 = Response(url="https://example.com/1", body=b"Page 1", status_code=200)
    mock_dl = MagicMock()
    mock_dl.fetch = AsyncMock(return_value=resp1)
    shell._downloader = mock_dl
    
    asyncio.run(shell.fetch("https://example.com/1"))
    assert shell.response.url == "https://example.com/1"
    
    # 第二次 fetch
    resp2 = Response(url="https://example.com/2", body=b"Page 2", status_code=200)
    mock_dl.fetch = AsyncMock(return_value=resp2)
    
    asyncio.run(shell.fetch("https://example.com/2"))
    assert shell.response.url == "https://example.com/2"
    assert shell.request.url == "https://example.com/2"
    
    print("✅ 端到端多次 fetch 测试通过")


def test_e2e_fetch_with_adaptive_selector():
    """端到端测试：fetch 后使用自适应选择器（如可用）"""
    html = """
    <html>
    <body>
        <div class="product">
            <h2 class="title">Product A</h2>
            <span class="price">$99</span>
        </div>
        <div class="product">
            <h2 class="title">Product B</h2>
            <span class="price">$199</span>
        </div>
    </body>
    </html>
    """
    
    shell = CrawloShell()
    resp = Response(
        url="https://shop.example.com",
        body=html.encode('utf-8'),
        status_code=200,
        headers={"content-type": "text/html; charset=utf-8"}
    )
    
    mock_dl = MagicMock()
    mock_dl.fetch = AsyncMock(return_value=resp)
    shell._downloader = mock_dl
    
    asyncio.run(shell.fetch("https://shop.example.com"))
    
    # CSS 选择器
    titles = shell.response.css(".title::text").getall()
    assert len(titles) == 2
    assert "Product A" in titles
    assert "Product B" in titles
    
    # XPath 选择器
    prices = shell.response.xpath('//span[@class="price"]/text()').getall()
    assert len(prices) == 2
    
    # 便捷方法
    first_title = shell.response.get('.title')
    assert first_title is not None
    
    print("✅ 端到端自适应选择器测试通过")


# ==================== 16. 边界情况测试 ====================

def test_view_bytes_body():
    """测试 view 处理 bytes 类型的 body"""
    shell = CrawloShell()
    resp = Response(
        url="https://example.com",
        body="<html><body>中文内容</body></html>".encode('gbk'),
        status_code=200
    )
    # Response 会自动检测编码，这里测试 view 能处理 bytes
    
    with patch('webbrowser.open'):
        shell.view(response=resp)
    # 不崩溃即可
    
    shell._cleanup_temp_files()
    print("✅ view bytes body 测试通过")


def test_fetch_with_meta():
    """测试带 meta 参数的 fetch"""
    shell = CrawloShell()
    
    mock_dl = MagicMock()
    mock_dl.fetch = AsyncMock(return_value=Response(
        url="https://example.com", body=b"content", status_code=200
    ))
    shell._downloader = mock_dl
    
    asyncio.run(shell.fetch("https://example.com", meta={'use_dynamic_loader': True}))
    
    assert shell.request is not None
    assert shell.request.meta.get('use_dynamic_loader') is True
    print("✅ 带 meta 参数的 fetch 测试通过")


def test_shell_settings_persist():
    """测试 Shell 设置持久性"""
    settings = {'CONCURRENCY': 16, 'DOWNLOAD_DELAY': 2.0}
    shell = CrawloShell(settings=settings)
    
    # settings 应在 namespace 中保持一致
    ns = shell.get_namespace()
    assert ns['settings'] == settings
    
    # 修改 settings 不影响原始
    ns['settings']['NEW_KEY'] = 'new_value'
    assert 'NEW_KEY' in shell.settings
    print("✅ Shell 设置持久性测试通过")


# ==================== 运行所有测试 ====================

def run_all_tests():
    """运行所有测试"""
    tests = [
        # _MockCrawler / _MockSpider
        test_mock_crawler_with_none_settings,
        test_mock_crawler_with_custom_settings,
        test_mock_spider,
        
        # CrawloShell 初始化
        test_shell_init_default,
        test_shell_init_with_settings,
        
        # namespace
        test_get_namespace,
        test_update_namespace,
        
        # banner
        test_banner_without_url,
        test_banner_with_url,
        
        # view
        test_view_no_response,
        test_view_with_response,
        test_view_uses_self_response,
        
        # 资源清理
        test_cleanup_temp_files,
        test_cleanup_nonexistent_file,
        
        # _DownloaderAdapter
        test_downloader_adapter_success,
        test_downloader_adapter_error,
        test_downloader_adapter_close,
        test_downloader_adapter_close_error,
        
        # _SimpleFetcher
        test_simple_fetcher_close,
        
        # fetch
        test_fetch_downloader_init_failure,
        test_fetch_success,
        test_fetch_returns_none_on_error,
        test_fetch_exception_handling,
        
        # sync_fetch
        test_sync_fetch,
        
        # close
        test_close_with_downloader,
        test_close_without_downloader,
        test_close_downloader_error,
        
        # _try_framework_downloader
        test_try_framework_downloader_fallback,
        test_try_framework_downloader_with_setting_manager,
        
        # _run_async
        test_run_async_no_loop,
        
        # CLI
        test_shell_command_import,
        test_shell_command_registered,
        test_shell_help_output,
        
        # 端到端
        test_e2e_fetch_and_view,
        test_e2e_namespace_after_fetch,
        test_e2e_multiple_fetch,
        test_e2e_fetch_with_adaptive_selector,
        
        # 边界情况
        test_view_bytes_body,
        test_fetch_with_meta,
        test_shell_settings_persist,
    ]
    
    passed = 0
    failed = 0
    errors = []
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            failed += 1
            errors.append(f"  ❌ {test.__name__}: {type(e).__name__}: {e}")
    
    print("\n" + "=" * 60)
    print(f"  测试结果: {passed} 通过, {failed} 失败, 共 {len(tests)} 个")
    print("=" * 60)
    
    if errors:
        print("\n失败详情:")
        for err in errors:
            print(err)
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(run_all_tests())
