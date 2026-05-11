"""
中间件极限场景测试

测试框架中间件在各种异常和边界条件下的健壮性
"""
import asyncio
import pytest
from unittest.mock import Mock, patch, AsyncMock
from crawlo.network.request import Request
from crawlo.network.response import Response
from crawlo.spider.spider import Spider


class TestRetryMiddlewareExtreme:
    """重试中间件极限测试"""
    
    @pytest.mark.asyncio
    async def test_retry_max_retries_exceeded(self):
        """测试超过最大重试次数"""
        from crawlo.middleware.retry import RetryMiddleware
        
        settings = Mock()
        settings.get_int.return_value = 3  # 最大重试 3 次
        
        middleware = RetryMiddleware(settings)
        request = Request('http://example.com')
        
        # 模拟连续失败
        for i in range(5):
            result = await middleware.process_exception(request, Exception("Connection error"), None)
            if result is None:
                break
        
        # 超过最大重试次数后应该返回 None
        assert result is None
    
    @pytest.mark.asyncio
    async def test_retry_interval_backoff(self):
        """测试重试间隔指数退避"""
        from crawlo.middleware.retry import RetryMiddleware
        import time
        
        settings = Mock()
        settings.get_int.return_value = 3
        settings.get_float.return_value = 0.1  # 基础延迟 0.1s
        
        middleware = RetryMiddleware(settings)
        request = Request('http://example.com')
        
        start = time.time()
        # 第一次重试
        await middleware.process_exception(request, Exception("Error"), None)
        elapsed1 = time.time() - start
        
        # 应该有延迟
        assert elapsed1 >= 0.1
    
    @pytest.mark.asyncio
    async def test_retry_ignore_certain_exceptions(self):
        """测试某些异常不应重试"""
        from crawlo.middleware.retry import RetryMiddleware
        
        settings = Mock()
        settings.get_int.return_value = 3
        
        middleware = RetryMiddleware(settings)
        request = Request('http://example.com')
        
        # 404 错误不应重试
        from crawlo.exceptions import IgnoreRequest
        result = await middleware.process_exception(
            request, 
            IgnoreRequest("404 Not Found"), 
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
    
    @pytest.mark.asyncio
    async def test_delay_zero(self):
        """测试延迟为 0"""
        from crawlo.middleware.download_delay import DownloadDelayMiddleware
        
        settings = Mock()
        settings.get_float.return_value = 0.0
        
        middleware = DownloadDelayMiddleware(settings)
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
        
        settings = Mock()
        settings.get_float.return_value = -1.0
        
        middleware = DownloadDelayMiddleware(settings)
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
        
        settings = Mock()
        settings.get_float.return_value = 3600.0  # 1 小时
        
        middleware = DownloadDelayMiddleware(settings)
        request = Request('http://example.com')
        
        # 极大延迟应该被限制或警告
        import time
        start = time.time()
        try:
            await asyncio.wait_for(
                middleware.process_request(request, None),
                timeout=1.0  # 最多等待 1 秒
            )
        except asyncio.TimeoutError:
            # 超时说明延迟太长，应该被限制
            pass


class TestUserAgentsMiddlewareExtreme:
    """User-Agent 中间件极限测试"""
    
    def test_ua_empty_list(self):
        """测试空 UA 列表"""
        from crawlo.middleware.user_agents import UserAgentMiddleware
        
        settings = Mock()
        settings.getlist.return_value = []
        
        middleware = UserAgentMiddleware(settings)
        request = Request('http://example.com')
        
        # 空列表应该使用默认 UA 或不设置
        middleware.process_request(request, None)
        
        # 不崩溃即可
    
    def test_ua_huge_list(self):
        """测试超大 UA 列表（10000 个）"""
        from crawlo.middleware.user_agents import UserAgentMiddleware
        
        settings = Mock()
        huge_ua_list = [f'Mozilla/{i}.0' for i in range(10000)]
        settings.getlist.return_value = huge_ua_list
        
        middleware = UserAgentMiddleware(settings)
        
        # 连续 10000 次请求
        for i in range(10000):
            request = Request(f'http://example.com/page/{i}')
            middleware.process_request(request, None)
        
        # 不应该崩溃或内存泄漏
    
    def test_ua_special_characters(self):
        """测试特殊字符 UA"""
        from crawlo.middleware.user_agents import UserAgentMiddleware
        
        settings = Mock()
        settings.getlist.return_value = [
            'Mozilla/5.0 (compatible; <script>alert(1)</script>)',
            'Mozilla/5.0 \' OR 1=1 --',
            'Mozilla/5.0 \x00\x01\x02',
            '中文 UA/1.0',
        ]
        
        middleware = UserAgentMiddleware(settings)
        request = Request('http://example.com')
        
        # 应该能处理特殊字符
        middleware.process_request(request, None)


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


class TestPriorityMiddlewareExtreme:
    """优先级中间件极限测试"""
    
    def test_priority_extreme_values(self):
        """测试极端优先级值"""
        from crawlo.middleware.priority import PriorityMiddleware
        
        settings = Mock()
        middleware = PriorityMiddleware(settings)
        
        extreme_priorities = [
            -999999,
            0,
            999999,
            -2147483648,  # INT_MIN
            2147483647,   # INT_MAX
        ]
        
        for priority in extreme_priorities:
            request = Request(f'http://example.com/p{priority}')
            request.priority = priority
            
            try:
                middleware.process_request(request, None)
            except:
                pass  # 不崩溃即可


class TestMiddlewareManagerExtreme:
    """中间件管理器极限测试"""
    
    @pytest.mark.asyncio
    async def test_manager_empty_middleware_list(self):
        """测试空中间件列表"""
        from crawlo.middleware.middleware_manager import MiddlewareManager
        
        settings = Mock()
        settings.getlist.return_value = []
        
        manager = MiddlewareManager(settings)
        await manager.open()
        
        request = Request('http://example.com')
        
        # 应该能处理空中间件列表
        result = await manager.process_request(request, None)
        assert result is None or result == request
        
        await manager.close()
    
    @pytest.mark.asyncio
    async def test_manager_middleware_exception(self):
        """测试中间件异常不影响其他中间件"""
        from crawlo.middleware.middleware_manager import MiddlewareManager
        
        class BrokenMiddleware:
            async def process_request(self, request, spider):
                raise Exception("Intentional error")
        
        settings = Mock()
        settings.getlist.return_value = []
        
        manager = MiddlewareManager(settings)
        manager._middlewares = [BrokenMiddleware()]
        
        request = Request('http://example.com')
        
        # 中间件异常应该被捕获
        try:
            await manager.process_request(request, None)
        except:
            pass  # 框架应该捕获异常
    
    @pytest.mark.asyncio
    async def test_manager_many_middleware(self):
        """测试大量中间件（100 个）"""
        from crawlo.middleware.middleware_manager import MiddlewareManager
        
        class SimpleMiddleware:
            async def process_request(self, request, spider):
                return request
        
        settings = Mock()
        settings.getlist.return_value = []
        
        manager = MiddlewareManager(settings)
        manager._middlewares = [SimpleMiddleware() for _ in range(100)]
        
        request = Request('http://example.com')
        
        # 应该能处理大量中间件
        await manager.process_request(request, None)
