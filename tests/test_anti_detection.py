#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
反反爬虫功能全面测试
=====================

测试 Crawlo 框架的反反爬虫能力：
1. Stealth Scripts 反检测脚本
2. Playwright 反检测配置
3. DrissionPage 反检测配置
4. Camoufox 隐身浏览器
5. CloudflareBypassMiddleware 绕过中间件
"""

import sys
import os
import unittest
from unittest.mock import Mock, MagicMock, AsyncMock, patch

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


class TestStealthScripts(unittest.TestCase):
    """测试反检测脚本模块"""
    
    def test_import_stealth_scripts(self):
        """测试导入反检测脚本"""
        try:
            from crawlo.downloader.stealth_scripts import (
                NAVIGATOR_STEALTH_SCRIPT,
                CHROME_RUNTIME_SCRIPT,
                WEBGL_STEALTH_SCRIPT,
                CANVAS_STEALTH_SCRIPT,
                DRISSIONPAGE_STEALTH_SCRIPT,
                DRISSIONPAGE_ADVANCED_SCRIPT,
                get_stealth_scripts,
                get_drissionpage_stealth_script,
            )
            print("✓ 成功导入所有反检测脚本")
        except ImportError as e:
            self.fail(f"导入反检测脚本失败: {e}")
    
    def test_navigator_stealth_script(self):
        """测试 Navigator 反检测脚本"""
        from crawlo.downloader.stealth_scripts import NAVIGATOR_STEALTH_SCRIPT
        
        self.assertIn('webdriver', NAVIGATOR_STEALTH_SCRIPT)
        self.assertIn('plugins', NAVIGATOR_STEALTH_SCRIPT)
        self.assertIn('languages', NAVIGATOR_STEALTH_SCRIPT)
        print("✓ Navigator 反检测脚本包含必要内容")
    
    def test_chrome_runtime_script(self):
        """测试 Chrome Runtime 反检测脚本"""
        from crawlo.downloader.stealth_scripts import CHROME_RUNTIME_SCRIPT
        
        has_runtime = 'runtime' in CHROME_RUNTIME_SCRIPT.lower()
        has_connect = 'connect' in CHROME_RUNTIME_SCRIPT
        self.assertTrue(has_runtime and has_connect)
        print("✓ Chrome Runtime 反检测脚本包含必要内容")
    
    def test_webgl_stealth_script(self):
        """测试 WebGL 反检测脚本"""
        from crawlo.downloader.stealth_scripts import WEBGL_STEALTH_SCRIPT
        
        self.assertIn('WebGL', WEBGL_STEALTH_SCRIPT)
        self.assertIn('getParameter', WEBGL_STEALTH_SCRIPT)
        print("✓ WebGL 反检测脚本包含必要内容")
    
    def test_canvas_stealth_script(self):
        """测试 Canvas 反检测脚本"""
        from crawlo.downloader.stealth_scripts import CANVAS_STEALTH_SCRIPT
        
        has_canvas = 'Canvas' in CANVAS_STEALTH_SCRIPT
        has_method = 'toDataURL' in CANVAS_STEALTH_SCRIPT or 'getImageData' in CANVAS_STEALTH_SCRIPT
        self.assertTrue(has_canvas and has_method)
        print("✓ Canvas 反检测脚本包含必要内容")
    
    def test_get_stealth_scripts_none(self):
        """测试获取 none 级别的脚本"""
        from crawlo.downloader.stealth_scripts import get_stealth_scripts
        
        result = get_stealth_scripts('none')
        self.assertEqual(result, '')
        print("✓ none 级别返回空字符串")
    
    def test_get_stealth_scripts_basic(self):
        """测试获取 basic 级别的脚本"""
        from crawlo.downloader.stealth_scripts import get_stealth_scripts
        
        result = get_stealth_scripts('basic')
        self.assertIn('webdriver', result)
        self.assertNotIn('WebGL', result)
        print("✓ basic 级别仅包含 Navigator 脚本")
    
    def test_get_stealth_scripts_advanced(self):
        """测试获取 advanced 级别的脚本"""
        from crawlo.downloader.stealth_scripts import get_stealth_scripts
        
        result = get_stealth_scripts('advanced')
        has_webdriver = 'webdriver' in result
        has_webgl = 'WebGL' in result or 'webgl' in result.lower()
        has_canvas = 'Canvas' in result or 'canvas' in result.lower()
        self.assertTrue(has_webdriver and has_webgl and has_canvas)
        print("✓ advanced 级别包含所有反检测脚本")
    
    def test_get_drissionpage_stealth_script(self):
        """测试获取 DrissionPage 反检测脚本"""
        from crawlo.downloader.stealth_scripts import get_drissionpage_stealth_script
        
        basic_script = get_drissionpage_stealth_script('basic')
        advanced_script = get_drissionpage_stealth_script('advanced')
        
        self.assertIn('webdriver', basic_script)
        self.assertIn('Canvas', advanced_script)
        print("✓ DrissionPage 反检测脚本正确返回")


class TestCloudflareBypassMiddleware(unittest.TestCase):
    """测试 Cloudflare 绕过中间件"""
    
    def test_import_middleware(self):
        """测试导入中间件"""
        try:
            from crawlo.middleware.cloudflare_bypass import CloudflareBypassMiddleware
            print("✓ 成功导入 CloudflareBypassMiddleware")
        except ImportError as e:
            self.fail(f"导入 CloudflareBypassMiddleware 失败: {e}")
    
    def test_cloudflare_detection_patterns(self):
        """测试 Cloudflare 检测模式"""
        from crawlo.middleware.cloudflare_bypass import CloudflareBypassMiddleware
        
        # 创建模拟的 crawler
        mock_crawler = Mock()
        mock_crawler.settings.get.return_value = 'camoufox'
        mock_crawler.settings.get_int.return_value = 2
        
        middleware = CloudflareBypassMiddleware(mock_crawler)
        
        # 测试不同的 Cloudflare 挑战页面
        challenge_pages = [
            b'<html><body>cf-ray: 12345</body></html>',
            b'<html><body>cf_chl_opt</body></html>',
            b'<html><body>challenge-platform</body></html>',
            b'<html><body>Just a moment</body></html>',
        ]
        
        for page in challenge_pages:
            mock_response = Mock()
            mock_response.status_code = 503
            mock_response.body = page
            mock_response.headers = {}
            
            self.assertTrue(
                middleware._is_cloudflare_challenge(mock_response),
                f"应该检测到 Cloudflare 挑战: {page[:50]}..."
            )
        
        print("✓ Cloudflare 挑战页面检测正常")
    
    def test_non_cloudflare_response(self):
        """测试非 Cloudflare 响应"""
        from crawlo.middleware.cloudflare_bypass import CloudflareBypassMiddleware
        
        mock_crawler = Mock()
        mock_crawler.settings.get.return_value = 'camoufox'
        mock_crawler.settings.get_int.return_value = 2
        
        middleware = CloudflareBypassMiddleware(mock_crawler)
        
        # 正常页面
        normal_response = Mock()
        normal_response.status_code = 200
        normal_response.body = b'<html><body><h1>Welcome</h1></body></html>'
        normal_response.headers = {}
        
        self.assertFalse(
            middleware._is_cloudflare_challenge(normal_response),
            "正常页面不应被检测为 Cloudflare 挑战"
        )
        
        print("✓ 非 Cloudflare 响应检测正常")
    
    def test_status_code_detection(self):
        """测试状态码检测"""
        from crawlo.middleware.cloudflare_bypass import CloudflareBypassMiddleware
        
        mock_crawler = Mock()
        mock_crawler.settings.get.return_value = 'camoufox'
        mock_crawler.settings.get_int.return_value = 2
        
        middleware = CloudflareBypassMiddleware(mock_crawler)
        
        # Cloudflare 常见状态码
        cloudflare_status_codes = [403, 503, 520, 521, 522, 523, 524]
        
        for status in cloudflare_status_codes:
            mock_response = Mock()
            mock_response.status = status
            mock_response.text = 'cf-chl-bypass'
            
            # 状态码+特征应该被检测
            self.assertIn(status, middleware.CHALLENGE_STATUS_CODES)
        
        print("✓ Cloudflare 状态码检测正常")


class TestDownloaderStealthConfig(unittest.TestCase):
    """测试下载器的反检测配置"""
    
    def test_playwright_stealth_level_config(self):
        """测试 Playwright stealth_level 配置"""
        from crawlo.downloader.playwright_downloader import PlaywrightDownloader
        
        # 测试 stealth_level 为 none
        mock_crawler = Mock()
        mock_crawler.settings.get = lambda key, default=None: {
            'PLAYWRIGHT_STEALTH_LEVEL': 'none',
            'PLAYWRIGHT_HEADLESS': True,
            'PLAYWRIGHT_BROWSER_TYPE': 'chromium',
            'PLAYWRIGHT_VIEWPORT_WIDTH': 1920,
            'PLAYWRIGHT_VIEWPORT_HEIGHT': 1080,
            'PLAYWRIGHT_BLOCK_WEBRTC': False,
            'PLAYWRIGHT_ALLOW_WEBGL': True,
            'PLAYWRIGHT_HIDE_CANVAS': False,
            'PLAYWRIGHT_REAL_CHROME': False,
            'PLAYWRIGHT_GOOGLE_REFERER': True,
            'PLAYWRIGHT_IGNORE_HTTPS_ERRORS': True,
        }.get(key, default)
        mock_crawler.settings.get_bool = lambda key, default=False: {
            'PLAYWRIGHT_HEADLESS': True,
            'PLAYWRIGHT_BLOCK_WEBRTC': False,
            'PLAYWRIGHT_ALLOW_WEBGL': True,
            'PLAYWRIGHT_HIDE_CANVAS': False,
            'PLAYWRIGHT_REAL_CHROME': False,
            'PLAYWRIGHT_GOOGLE_REFERER': True,
            'PLAYWRIGHT_IGNORE_HTTPS_ERRORS': True,
            'PLAYWRIGHT_SINGLE_BROWSER_MODE': True,
        }.get(key, default)
        mock_crawler.settings.get_int = lambda key, default=0: {
            'PLAYWRIGHT_TIMEOUT': 30000,
            'PLAYWRIGHT_LOAD_TIMEOUT': 10000,
            'PLAYWRIGHT_VIEWPORT_WIDTH': 1920,
            'PLAYWRIGHT_VIEWPORT_HEIGHT': 1080,
            'PLAYWRIGHT_MAX_PAGES_PER_BROWSER': 10,
            'PLAYWRIGHT_WAIT_TIMEOUT': 10000,
        }.get(key, default)
        mock_crawler.settings.get_list = lambda key, default=None: {
            'PLAYWRIGHT_BLOCK_RESOURCES': ['image', 'font', 'media'],
        }.get(key, default)
        
        downloader = PlaywrightDownloader(mock_crawler)
        self.assertEqual(downloader.stealth_level, 'none')
        print("✓ Playwright stealth_level=none 配置正确")
    
    def test_drissionpage_stealth_level_config(self):
        """测试 DrissionPage stealth_level 配置"""
        from crawlo.downloader.drissionpage_downloader import DrissionPageDownloader
        
        mock_crawler = Mock()
        mock_crawler.settings.get = lambda key, default=None: {
            'DRISSIONPAGE_STEALTH_LEVEL': 'advanced',
            'DRISSIONPAGE_HEADLESS': True,
            'DRISSIONPAGE_TIMEOUT': 30,
            'DRISSIONPAGE_BLOCK_WEBRTC': False,
            'DRISSIONPAGE_ALLOW_WEBGL': True,
            'DRISSIONPAGE_HIDE_CANVAS': False,
        }.get(key, default)
        
        downloader = DrissionPageDownloader(mock_crawler)
        self.assertEqual(downloader.stealth_level, 'advanced')
        print("✓ DrissionPage stealth_level=advanced 配置正确")
    
    def test_camoufox_config(self):
        """测试 Camoufox 配置"""
        from crawlo.downloader.camoufox_downloader import CamoufoxDownloader
        
        mock_crawler = Mock()
        mock_crawler.settings.get_bool = lambda key, default=False: {
            'CAMOUFOX_HEADLESS': True,
            'CAMOUFOX_HUMANIZE': True,
            'CAMOUFOX_SOLVE_CLOUDFLARE': True,
            'CAMOUFOX_AUTO_SCROLL': False,
        }.get(key, default)
        mock_crawler.settings.get = lambda key, default=None: {
            'CAMOUFOX_PROXY': None,
            'CAMOUFOX_BLOCK_RESOURCES': ['image', 'font', 'media'],
            'CAMOUFOX_WAIT_STRATEGY': 'auto',
            'CAMOUFOX_WAIT_FOR_ELEMENT': None,
        }.get(key, default)
        mock_crawler.settings.get_int = lambda key, default=0: {
            'CAMOUFOX_TIMEOUT': 30000,
            'CAMOUFOX_LOAD_TIMEOUT': 10000,
            'CAMOUFOX_VIEWPORT_WIDTH': 1920,
            'CAMOUFOX_VIEWPORT_HEIGHT': 1080,
            'CAMOUFOX_MAX_PAGES': 10,
            'CAMOUFOX_SCROLL_DELAY': 500,
            'CAMOUFOX_WAIT_TIMEOUT': 10000,
        }.get(key, default)
        mock_crawler.settings.get_list = lambda key, default=None: {
            'CAMOUFOX_BLOCK_RESOURCES': ['image', 'font', 'media'],
        }.get(key, default)
        
        downloader = CamoufoxDownloader(mock_crawler)
        
        self.assertTrue(downloader.headless)
        self.assertTrue(downloader.humanize)
        self.assertTrue(downloader.solve_cloudflare)
        print("✓ Camoufox 配置正确")


class TestDefaultSettings(unittest.TestCase):
    """测试默认配置中的反反爬虫参数"""
    
    def test_playwright_stealth_settings(self):
        """测试 Playwright 反检测配置"""
        from crawlo.settings import default_settings
        
        self.assertTrue(hasattr(default_settings, 'PLAYWRIGHT_STEALTH_LEVEL'))
        self.assertEqual(default_settings.PLAYWRIGHT_STEALTH_LEVEL, 'basic')
        print("✓ PLAYWRIGHT_STEALTH_LEVEL 配置存在")
    
    def test_drissionpage_stealth_settings(self):
        """测试 DrissionPage 反检测配置"""
        from crawlo.settings import default_settings
        
        self.assertTrue(hasattr(default_settings, 'DRISSIONPAGE_STEALTH_LEVEL'))
        self.assertEqual(default_settings.DRISSIONPAGE_STEALTH_LEVEL, 'basic')
        print("✓ DRISSIONPAGE_STEALTH_LEVEL 配置存在")
    
    def test_camoufox_settings(self):
        """测试 Camoufox 配置"""
        from crawlo.settings import default_settings
        
        settings_to_check = [
            'CAMOUFOX_HEADLESS',
            'CAMOUFOX_TIMEOUT',
            'CAMOUFOX_HUMANIZE',
            'CAMOUFOX_SOLVE_CLOUDFLARE',
            'CAMOUFOX_MAX_PAGES',
        ]
        
        for setting in settings_to_check:
            self.assertTrue(
                hasattr(default_settings, setting),
                f"缺少配置: {setting}"
            )
        
        print("✓ Camoufox 配置完整")
    
    def test_cloudflare_bypass_settings(self):
        """测试 Cloudflare 绕过配置"""
        from crawlo.settings import default_settings
        
        self.assertTrue(hasattr(default_settings, 'CLOUDFLARE_BYPASS_DOWNLOADER'))
        self.assertEqual(default_settings.CLOUDFLARE_BYPASS_DOWNLOADER, 'camoufox')
        print("✓ CLOUDFLARE_BYPASS_DOWNLOADER 配置正确")


def run_tests():
    """运行所有测试"""
    print("=" * 70)
    print("Crawlo 反反爬虫功能全面测试")
    print("=" * 70)
    print()
    
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试类
    suite.addTests(loader.loadTestsFromTestCase(TestStealthScripts))
    suite.addTests(loader.loadTestsFromTestCase(TestCloudflareBypassMiddleware))
    suite.addTests(loader.loadTestsFromTestCase(TestDownloaderStealthConfig))
    suite.addTests(loader.loadTestsFromTestCase(TestDefaultSettings))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 输出总结
    print()
    print("=" * 70)
    print("测试总结")
    print("=" * 70)
    print(f"运行测试数: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")
    
    if result.wasSuccessful():
        print("\n✓ 所有测试通过！反反爬虫功能正常。")
    else:
        print("\n✗ 部分测试失败，请检查错误信息。")
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
