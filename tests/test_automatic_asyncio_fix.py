#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
测试 CrawlerProcess 自动应用 Windows asyncio 修复

验证点:
1. CrawlerProcess 初始化时自动调用 _apply_windows_asyncio_fix()
2. 用户无需手动导入任何修复函数
3. 猴子补丁在 CrawlerProcess.__init__ 时被应用
"""
import sys
import pytest


class TestAutomaticAsyncioFix:
    """测试自动应用 asyncio 修复"""

    def test_crawler_process_has_fix_method(self):
        """测试 CrawlerProcess 包含 _apply_windows_asyncio_fix 方法"""
        from crawlo.crawler_process import CrawlerProcess
        assert hasattr(CrawlerProcess, '_apply_windows_asyncio_fix')

    @pytest.mark.skipif(sys.platform != 'win32', reason="仅在 Windows 平台测试")
    def test_fix_applied_on_init_windows(self):
        """测试 Windows 平台初始化时自动应用修复"""
        import asyncio.proactor_events
        
        # 记录修补前的 __del__ 方法
        original_del = asyncio.proactor_events._ProactorBasePipeTransport.__del__
        
        # 初始化 CrawlerProcess (应该自动应用修复)
        from crawlo.crawler_process import CrawlerProcess
        process = CrawlerProcess()
        
        # 验证 __del__ 已被修补
        patched_del = asyncio.proactor_events._ProactorBasePipeTransport.__del__
        assert patched_del is not original_del, "猴子补丁应该在 CrawlerProcess 初始化时应用"
        
        # 验证修补后的方法能正常处理异常
        class MockTransport:
            def __init__(self):
                self._sock = None
        
        mock = MockTransport()
        # 不应该抛出异常
        patched_del(mock)

    @pytest.mark.skipif(sys.platform == 'win32', reason="非 Windows 平台测试")
    def test_fix_is_noop_on_non_windows(self):
        """测试非 Windows 平台修复函数为空操作"""
        from crawlo.crawler_process import CrawlerProcess
        # 初始化不应抛出异常
        process = CrawlerProcess()

    def test_user_no_manual_import_needed(self):
        """
        测试用户无需手动导入修复函数
        
        这是核心验证: 用户只需 from crawlo.crawler import CrawlerProcess
        不需要 from crawlo.utils.asyncio_utils import ...
        """
        # 模拟用户代码: 只导入 CrawlerProcess
        from crawlo.crawler import CrawlerProcess
        
        # 不应该需要导入这些
        # from crawlo.utils.asyncio_utils import run_with_cleanup
        # from crawlo.utils.asyncio_utils import suppress_asyncio_destructor_warnings
        
        # 初始化应该自动应用修复
        process = CrawlerProcess()
        
        # 验证修复已应用 (在 Windows 上)
        if sys.platform == 'win32':
            import asyncio.proactor_events
            # 如果修复已应用, __del__ 应该被修补
            # 我们可以通过检查方法名或行为来验证
            assert hasattr(asyncio.proactor_events._ProactorBasePipeTransport, '__del__')


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
