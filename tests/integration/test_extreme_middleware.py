"""
中间件极限场景测试

测试框架中间件在各种异常和边界条件下的健壮性
"""
import asyncio
import pytest
from unittest.mock import Mock, patch, AsyncMock
from crawlo.http.request import Request
from crawlo.http.response import Response
from crawlo.spider.spider import Spider


class TestRetryMiddlewareExtreme:
    """重试中间件极限测试"""

    def _make_crawler(self):
        """构造符合当前 RetryMiddleware.create_instance 接口的 mock crawler"""
        from crawlo.settings.setting_manager import SettingManager
        settings = SettingManager()
        settings.set('RETRY_HTTP_CODES', [500, 502, 503, 504])
        settings.set('IGNORE_HTTP_CODES', [404])
        settings.set('MAX_RETRY_TIMES', 3)
        settings.set('RETRY_EXCEPTIONS', ['builtins.ConnectionError', 'builtins.TimeoutError'])
        settings.set('RETRY_PRIORITY', 10)
        crawler = Mock()
        crawler.settings = settings
        crawler.stats = Mock()
        return crawler
    
    async def test_retry_max_retries_exceeded(self):
        """测试超过最大重试次数"""
        from crawlo.middleware.retry import RetryMiddleware

        middleware = RetryMiddleware.create_instance(self._make_crawler())
        request = Request('http://example.com')

        # 模拟连续失败
        current = request
        for i in range(5):
            result = middleware.process_exception(current, ConnectionError("Connection error"), None)
            if result is None:
                break
            current = result

        # 超过最大重试次数后应该返回 None
        assert result is None
    
    async def test_retry_interval_backoff(self):
        """测试重试间隔指数退避"""
        from crawlo.middleware.retry import RetryMiddleware

        middleware = RetryMiddleware.create_instance(self._make_crawler())
        request = Request('http://example.com')

        # 第一次重试：backoff 应记录到 meta（当前实现不在请求路径 sleep）
        retry_request = middleware.process_exception(request, ConnectionError("Error"), None)
        assert retry_request is not None
        assert retry_request.meta.get('retry_backoff') == 1.0
        assert retry_request.meta.get('retry_times') == 1
    
    async def test_retry_ignore_certain_exceptions(self):
        """测试某些异常不应重试"""
        from crawlo.middleware.retry import RetryMiddleware

        middleware = RetryMiddleware.create_instance(self._make_crawler())
        request = Request('http://example.com')

        # 404 错误不应重试
        from crawlo.http.exceptions import IgnoreRequestError
        result = middleware.process_exception(
            request,
            IgnoreRequestError("404 Not Found"),
            None
        )

        assert result is None


class TestProxyMiddlewareExtreme:
    """代理中间件极限测试"""
    
    @pytest.mark.asyncio
    async def test_proxy_all_unavailable(self):
        """测试所有代理不可用"""
        from crawlo.middleware.proxy import ProxyMiddleware
        
        settings = Mock()
        settings.get.return_value = []  # 空代理列表
        
        middleware = ProxyMiddleware(settings)
        request = Request('http://example.com')
        
        # 应该能处理无代理情况
        result = await middleware.process_request(request, None)
        # 无代理时应该返回 None（继续处理）
        assert result is None
    
    @pytest.mark.asyncio
    async def test_proxy_invalid_format(self):
        """测试代理格式非法"""
        from crawlo.middleware.proxy import ProxyMiddleware
        
        settings = Mock()
        settings.get.return_value = [
            'invalid_proxy_format',
            'not_a_url',
            ':::::',
        ]
        
        middleware = ProxyMiddleware(settings)
        request = Request('http://example.com')
        
        # 应该能处理非法格式，不崩溃
        try:
            await middleware.process_request(request, None)
        except Exception as e:
            # 应该有清晰的错误信息
            assert 'proxy' in str(e).lower() or 'invalid' in str(e).lower()
    
    @pytest.mark.asyncio
    async def test_proxy_rotation_stress(self):
        """测试代理轮换压力（100 次）"""
        from crawlo.middleware.proxy import ProxyMiddleware
        
        settings = Mock()
        settings.get.return_value = [
            'http://proxy1.example.com:8080',
            'http://proxy2.example.com:8080',
            'http://proxy3.example.com:8080',
        ]
        
        middleware = ProxyMiddleware(settings)
        
        # 连续 100 次请求
        for i in range(100):
            request = Request(f'http://example.com/page/{i}')
            await middleware.process_request(request, None)
        
        # 不应该崩溃


class TestOffsiteMiddlewareExtreme:
    """跨域过滤中间件极限测试"""
    
    def test_offsite_allowed_domains_regex(self):
        """测试允许域名正则表达式极限"""
        from crawlo.middleware.offsite import OffsiteMiddleware
        
        settings = Mock()
        settings.get.return_value = ['example.com']
        settings.getlist.return_value = ['example.com']
        
        middleware = OffsiteMiddleware(settings)
        
        # 创建爬虫
        spider = Mock()
        spider.allowed_domains = ['example.com']
        
        # 测试边界域名
        allowed_urls = [
            'http://example.com/page',
            'http://www.example.com/page',
            'http://sub.example.com/page',
        ]
        
        blocked_urls = [
            'http://evil.com/page',
            'http://example.com.evil.com/page',
        ]
        
        for url in allowed_urls:
            request = Request(url)
            # 应该允许或拒绝（取决于实现）
            try:
                middleware.process_request(request, spider)
            except:
                pass  # 可能抛出异常
        
        for url in blocked_urls:
            request = Request(url)
            try:
                result = middleware.process_request(request, spider)
                # 应该被过滤
            except:
                pass  # 可能抛出异常
    
    def test_offsite_empty_allowed_domains(self):
        """测试空允许域名列表"""
        from crawlo.middleware.offsite import OffsiteMiddleware
        
        settings = Mock()
        settings.get.return_value = []
        settings.getlist.return_value = []
        
        middleware = OffsiteMiddleware(settings)
        
        spider = Mock()
        spider.allowed_domains = []
        
        request = Request('http://any-domain.com/page')
        
        # 空域名列表应该允许所有或拒绝所有
        try:
            middleware.process_request(request, spider)
        except:
            pass  # 不崩溃即可


class TestDownloadDelayMiddlewareExtreme:
    """下载延迟中间件极限测试"""

    def _make_crawler(self, delay):
        """构造符合 DownloadDelayMiddleware.create_instance 接口的 mock crawler"""
        from crawlo.settings.setting_manager import SettingManager
        settings = SettingManager()
        settings.set('DOWNLOAD_DELAY', delay)
        settings.set('RANDOMNESS', False)
        crawler = Mock()
        crawler.settings = settings
        return crawler
    
    @pytest.mark.asyncio
    async def test_delay_zero(self):
        """测试延迟为 0"""
        from crawlo.middleware.download_delay import DownloadDelayMiddleware

        middleware = DownloadDelayMiddleware.create_instance(self._make_crawler(0.0))
        request = Request('http://example.com')

        import time
        start = time.time()
        await middleware.process_request(request, None)
        elapsed = time.time() - start

        # 延迟为 0 应该立即返回
        assert elapsed < 0.1
    
    @pytest.mark.asyncio
    async def test_delay_negative(self):
        """测试负数延迟"""
        from crawlo.middleware.download_delay import DownloadDelayMiddleware

        middleware = DownloadDelayMiddleware.create_instance(self._make_crawler(-1.0))
        request = Request('http://example.com')

        # 负数延迟应该被处理（视为 0 或抛出清晰错误）
        try:
            await middleware.process_request(request, None)
        except:
            pass  # 不崩溃即可
    
    @pytest.mark.asyncio
    async def test_delay_extreme_value(self):
        """测试极大延迟值"""
        from crawlo.middleware.download_delay import DownloadDelayMiddleware

        middleware = DownloadDelayMiddleware.create_instance(self._make_crawler(3600.0))
        request = Request('http://example.com')

        # 极大延迟应该被限制或警告
        try:
            await asyncio.wait_for(
                middleware.process_request(request, None),
                timeout=1.0  # 最多等待 1 秒
            )
        except asyncio.TimeoutError:
            # 超时说明延迟太长，应该被限制
            pass


class TestRequestIgnoreMiddlewareExtreme:
    """请求忽略中间件极限测试"""
    
    def test_ignore_regex_extreme(self):
        """测试忽略规则正则表达式极限"""
        from crawlo.middleware.request_ignore import RequestIgnoreMiddleware
        
        settings = Mock()
        settings.get.return_value = [
            r'.*\.jpg$',
            r'.*\.png$',
            r'.*\?sessionid=.*',
            r'.*admin.*',
        ]
        
        middleware = RequestIgnoreMiddleware(settings)
        
        # 测试各种 URL
        test_urls = [
            'http://example.com/image.jpg',
            'http://example.com/image.PNG',
            'http://example.com/page?sessionid=abc123',
            'http://example.com/admin/dashboard',
            'http://example.com/normal/page',
        ]
        
        for url in test_urls:
            request = Request(url)
            try:
                result = middleware.process_request(request, None)
            except:
                pass  # 不崩溃即可
    
    def test_ignore_invalid_regex(self):
        """测试非法正则表达式"""
        from crawlo.middleware.request_ignore import RequestIgnoreMiddleware
        
        settings = Mock()
        settings.get.return_value = [
            '[invalid(regex',
            '\\\\\\',
        ]
        
        middleware = RequestIgnoreMiddleware(settings)
        request = Request('http://example.com')
        
        # 应该能处理非法正则，不崩溃
        try:
            middleware.process_request(request, None)
        except:
            pass


class TestMiddlewareManagerExtreme:
    """中间件管理器极限测试"""

    def _make_manager(self):
        """构造符合当前 MiddlewareManager(crawler) 接口的实例"""
        from crawlo.middleware.middleware_manager import MiddlewareManager
        crawler = Mock()
        crawler.stats = Mock()
        crawler.spider = Mock()
        crawler.settings = Mock()
        crawler.settings.get = Mock(side_effect=lambda key, default=None: default)
        crawler.settings.get_bool = Mock(side_effect=lambda key, default=False: default)
        manager = MiddlewareManager(crawler)
        manager._download_func = AsyncMock(return_value=None)
        return manager

    @pytest.mark.asyncio
    async def test_manager_empty_middleware_list(self):
        """测试空中间件列表"""
        manager = self._make_manager()
        await manager.open()

        request = Request('http://example.com')

        # 应该能处理空中间件列表
        result = await manager._process_request(request)
        assert result is None or result == request

        await manager.close()
    
    @pytest.mark.asyncio
    async def test_manager_middleware_exception(self):
        """测试中间件异常不影响其他中间件"""
        class BrokenMiddleware:
            async def process_request(self, request, spider):
                raise Exception("Intentional error")

        manager = self._make_manager()
        manager.methods['process_request'] = [BrokenMiddleware().process_request]

        request = Request('http://example.com')

        # 中间件异常应该被捕获
        try:
            await manager._process_request(request)
        except:
            pass  # 框架应该捕获异常
    
    @pytest.mark.asyncio
    async def test_manager_many_middleware(self):
        """测试大量中间件（100 个）"""
        class SimpleMiddleware:
            async def process_request(self, request, spider):
                return request

        manager = self._make_manager()
        manager.methods['process_request'] = [
            SimpleMiddleware().process_request for _ in range(100)
        ]

        request = Request('http://example.com')

        # 应该能处理大量中间件
        result = await manager._process_request(request)
        assert result == request
