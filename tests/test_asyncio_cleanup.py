#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
测试 Windows asyncio 传输关闭警告修复

验证点:
1. apply_windows_patches() 正确修补 __del__
2. crawlo 包导入时自动应用补丁
3. run_with_cleanup() 行为与 asyncio.run 一致
4. CrawlerProcess 包含 _shutdown_loop_transports 方法
"""
import asyncio
import sys
import pytest


class TestAutoPatch:
    """测试 crawlo 包导入时自动应用补丁"""

    def test_patches_applied_on_import(self):
        """测试导入 crawlo 后补丁已自动应用（仅 Windows）"""
        import crawlo
        if sys.platform != 'win32':
            pytest.skip("Windows-only test")

        # 验证 _ProactorBasePipeTransport.__del__ 已被修补
        import asyncio.proactor_events
        del_method = asyncio.proactor_events._ProactorBasePipeTransport.__del__
        # 修补后的函数名包含 "patched"
        assert 'patched' in del_method.__code__.co_name.lower() or '_patched' in del_method.__qualname__

    def test_subprocess_transport_patched_on_import(self):
        """测试 BaseSubprocessTransport.__del__ 已被修补（仅 Windows）"""
        import crawlo
        if sys.platform != 'win32':
            pytest.skip("Windows-only test")

        import asyncio.base_subprocess
        del_method = asyncio.base_subprocess.BaseSubprocessTransport.__del__
        assert 'patched' in del_method.__code__.co_name.lower() or '_patched' in del_method.__qualname__


class TestAsyncioUtils:
    """测试 asyncio 工具函数"""

    def test_apply_windows_patches_idempotent(self):
        """测试重复调用不会报错"""
        from crawlo.utils.asyncio_utils import apply_windows_patches
        apply_windows_patches()
        apply_windows_patches()  # 不应抛异常

    def test_run_with_cleanup(self):
        """测试 run_with_cleanup 行为与 asyncio.run 一致"""
        from crawlo.utils.asyncio_utils import run_with_cleanup

        async def sample_coroutine():
            await asyncio.sleep(0.01)
            return "success"

        result = run_with_cleanup(sample_coroutine())
        assert result == "success"

    def test_run_with_cleanup_exception(self):
        """测试 run_with_cleanup 正确传播异常"""
        from crawlo.utils.asyncio_utils import run_with_cleanup

        async def failing_coroutine():
            raise ValueError("Test exception")

        with pytest.raises(ValueError, match="Test exception"):
            run_with_cleanup(failing_coroutine())

    def test_import_asyncio_utils(self):
        """测试模块导出"""
        from crawlo.utils import asyncio_utils

        assert hasattr(asyncio_utils, 'run_with_cleanup')
        assert hasattr(asyncio_utils, 'apply_windows_patches')
        # 旧函数已移除
        assert not hasattr(asyncio_utils, 'cleanup_event_loop_sync')
        assert not hasattr(asyncio_utils, 'suppress_asyncio_warnings')
        assert not hasattr(asyncio_utils, 'suppress_asyncio_destructor_warnings')


class TestCrawlerProcessCleanup:
    """测试 CrawlerProcess 中的 transport 清理"""

    def test_has_shutdown_loop_transports(self):
        """测试 CrawlerProcess 包含 _shutdown_loop_transports 方法"""
        from crawlo.crawler_process import CrawlerProcess
        assert hasattr(CrawlerProcess, '_shutdown_loop_transports')

    def test_crawl_has_finally_cleanup(self):
        """测试 crawl 方法在 finally 中调用 _shutdown_loop_transports"""
        import inspect
        from crawlo.crawler_process import CrawlerProcess

        source = inspect.getsource(CrawlerProcess.crawl)
        assert '_shutdown_loop_transports' in source
        assert 'finally' in source


class TestInitAutoPatch:
    """测试 __init__.py 自动应用补丁"""

    def test_init_imports_patch(self):
        """测试 __init__.py 包含自动补丁代码"""
        import inspect
        import crawlo

        source = inspect.getsource(crawlo)
        assert 'apply_windows_patches' in source


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
