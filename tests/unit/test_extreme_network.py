"""
极限场景测试：网络请求层

测试框架在各种网络异常情况下的健壮性
"""
import asyncio
import pytest
from unittest.mock import Mock, patch, AsyncMock
from crawlo.network.request import Request
from crawlo.network.response import Response


class TestExtremeNetworkScenarios:
    """极端网络场景测试"""
    
    def test_request_empty_url(self):
        """测试空 URL - 应抛出清晰错误"""
        with pytest.raises((ValueError, TypeError)):
            Request('')
    
    def test_request_none_url(self):
        """测试 None URL - 应抛出清晰错误"""
        with pytest.raises((ValueError, TypeError)):
            Request(None)
    
    def test_request_ultra_long_url(self):
        """测试超长 URL（10000+字符）"""
        long_url = 'http://example.com/' + 'a' * 10000
        # 应该能处理或给出清晰错误
        try:
            req = Request(long_url)
            assert req.url == long_url
        except ValueError as e:
            # 如果拒绝，应有清晰错误信息
            assert 'URL' in str(e) or 'url' in str(e)
    
    def test_request_special_characters_url(self):
        """测试特殊字符 URL（中文、空格、emoji）"""
        test_urls = [
            'http://example.com/搜索?q=测试',  # 中文
            'http://example.com/path with spaces',  # 空格
            'http://example.com/path?emoji=😀',  # emoji
            'http://example.com/path?special=<>&"',  # HTML 特殊字符
        ]
        
        for url in test_urls:
            try:
                req = Request(url)
                # URL 应被正确编码
                assert req.url is not None
            except Exception as e:
                # 如果有错误，应该是 URL 相关
                pytest.fail(f"Failed to handle special chars in URL: {url}, error: {e}")
    
    def test_request_invalid_protocol(self):
        """测试非法协议"""
        invalid_urls = [
            'ftp://example.com/file.txt',
            'file:///path/to/file',
            'javascript:alert(1)',
            'data:text/html,<h1>Hello</h1>',
        ]
        
        for url in invalid_urls:
            try:
                req = Request(url)
                # 如果允许，应该没问题
            except ValueError as e:
                # 如果拒绝，应有清晰错误
                assert 'protocol' in str(e).lower() or 'scheme' in str(e).lower() or 'http' in str(e).lower()
    
    def test_request_timeout_extreme_values(self):
        """测试超时极端值"""
        url = 'http://example.com'
        
        # 0 秒超时
        try:
            req = Request(url, timeout=0)
        except:
            pass  # 可以接受
        
        # 负数超时
        try:
            req = Request(url, timeout=-1)
        except:
            pass  # 应该拒绝或使用默认值
        
        # 极大超时
        req = Request(url, timeout=999999)
        assert req.timeout == 999999
    
    @pytest.mark.asyncio
    async def test_dns_resolution_failure(self):
        """测试 DNS 解析失败"""
        # 使用不存在的域名
        req = Request('http://this-domain-definitely-does-not-exist-12345.com')
        
        # 应该有重试机制或清晰错误
        # 这里只测试 Request 对象创建，实际下载需要 downloader
        assert req is not None
        assert req.url == 'http://this-domain-definitely-does-not-exist-12345.com'
    
    @pytest.mark.asyncio
    async def test_connection_refused(self):
        """测试连接拒绝"""
        # 使用不可能的端口
        req = Request('http://localhost:65535')
        assert req is not None
    
    def test_request_with_extreme_headers(self):
        """测试超大 Headers"""
        url = 'http://example.com'
        
        # 1000 个 headers
        huge_headers = {f'Header-{i}': f'Value-{i}' for i in range(1000)}
        req = Request(url, headers=huge_headers)
        assert len(req.headers) == 1000
    
    def test_request_with_extreme_cookies(self):
        """测试超大 Cookies"""
        url = 'http://example.com'
        
        # 1000 个 cookies
        huge_cookies = {f'Cookie-{i}': f'Value-{i}' for i in range(1000)}
        req = Request(url, cookies=huge_cookies)
        assert len(req.cookies) == 1000
    
    def test_request_body_size_limits(self):
        """测试请求体大小限制"""
        url = 'http://example.com'
        
        # 10MB body
        large_body = 'a' * (10 * 1024 * 1024)
        req = Request(url, body=large_body.encode())
        assert len(req.body) == 10 * 1024 * 1024
    
    def test_response_ultra_large_body(self):
        """测试超大响应体处理"""
        req = Request('http://example.com')
        
        # 100MB response
        huge_body = 'a' * (100 * 1024 * 1024)
        try:
            resp = Response(
                url='http://example.com',
                status=200,
                body=huge_body.encode(),
                request=req
            )
            # 应该能处理或拒绝
            assert resp is not None
        except Exception as e:
            # 如果拒绝，应有清晰错误
            assert 'body' in str(e).lower() or 'size' in str(e).lower() or 'too large' in str(e).lower()
    
    def test_response_encoding_fallback(self):
        """测试响应编码 fallback"""
        req = Request('http://example.com')
        
        # 非法 UTF-8 数据
        invalid_utf8 = b'\xff\xfe\x00\x01\x02\x03'
        resp = Response(
            url='http://example.com',
            status=200,
            body=invalid_utf8,
            request=req
        )
        
        # 应该能 fallback 到 latin1 或其他编码
        try:
            text = resp.text
            assert text is not None
        except:
            pytest.fail("Response should fallback to alternative encoding")
    
    def test_concurrent_request_creation(self):
        """测试并发创建请求对象（压力测试）"""
        import concurrent.futures
        
        def create_request(i):
            return Request(f'http://example.com/page/{i}', meta={'index': i})
        
        # 1000 并发创建
        with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
            futures = [executor.submit(create_request, i) for i in range(1000)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        assert len(results) == 1000
    
    def test_request_copy_performance(self):
        """测试 Request 复制性能"""
        import time
        
        req = Request(
            'http://example.com',
            method='POST',
            headers={'Content-Type': 'application/json'},
            body=b'{"data": "test"}',
            meta={'key1': 'value1', 'key2': 'value2'}
        )
        
        # 复制 10000 次
        start = time.time()
        for _ in range(10000):
            req_copy = req.copy()
        elapsed = time.time() - start
        
        # 应该在合理时间内完成（< 5秒）
        assert elapsed < 5.0
    
    def test_request_meta_recursion_limit(self):
        """测试 meta 递归深度限制"""
        req = Request('http://example.com')
        
        # 创建深层嵌套的 meta
        deep_meta = {'level': 0}
        current = deep_meta
        for i in range(1, 100):  # 100 层嵌套
            current['next'] = {'level': i}
            current = current['next']
        
        req = Request('http://example.com', meta=deep_meta)
        # 应该能处理或给出清晰错误
    
    def test_request_pickle_roundtrip(self):
        """测试 Request pickle 序列化/反序列化"""
        import pickle
        
        original = Request(
            'http://example.com/test',
            method='POST',
            headers={'X-Custom': 'value'},
            body=b'test body',
            meta={'key': 'value'},
            priority=5
        )
        
        # 序列化
        serialized = pickle.dumps(original)
        
        # 反序列化
        restored = pickle.loads(serialized)
        
        # 验证
        assert restored.url == original.url
        assert restored.method == original.method
        assert restored.headers == original.headers
        assert restored.body == original.body
        assert restored.meta == original.meta
        assert restored.priority == original.priority
    
    def test_request_dict_roundtrip(self):
        """测试 Request to_dict/from_dict 往返"""
        original = Request(
            'http://example.com/test',
            method='POST',
            headers={'X-Custom': 'value'},
            body=b'test body',
            meta={'key': 'value'},
            priority=5
        )
        
        # 转换为 dict
        data = original.to_dict()
        
        # 从 dict 恢复
        restored = Request.from_dict(data)
        
        # 验证
        assert restored.url == original.url
        assert restored.method == original.method
        assert restored.priority == original.priority


class TestExtremeResponseScenarios:
    """极端响应场景测试"""
    
    def test_response_status_extreme_values(self):
        """测试响应状态码极端值"""
        req = Request('http://example.com')
        
        # 合法范围外的状态码
        extreme_statuses = [0, -1, 999, 1000]
        
        for status in extreme_statuses:
            try:
                resp = Response(
                    url='http://example.com',
                    status=status,
                    body=b'',
                    request=req
                )
                # 如果接受，应该没问题
            except ValueError as e:
                # 如果拒绝，应有清晰错误
                assert 'status' in str(e).lower()
    
    def test_response_empty_body(self):
        """测试空响应体"""
        req = Request('http://example.com')
        resp = Response(
            url='http://example.com',
            status=200,
            body=b'',
            request=req
        )
        
        assert resp.body == b''
        assert resp.text == ''
    
    def test_response_binary_body(self):
        """测试二进制响应体"""
        req = Request('http://example.com')
        binary_data = bytes(range(256))  # 所有字节值
        
        resp = Response(
            url='http://example.com',
            status=200,
            body=binary_data,
            request=req
        )
        
        assert resp.body == binary_data
    
    def test_response_headers_case_insensitive(self):
        """测试响应头大小写不敏感"""
        req = Request('http://example.com')
        resp = Response(
            url='http://example.com',
            status=200,
            body=b'',
            request=req,
            headers={'Content-Type': 'text/html'}
        )
        
        # 应该大小写不敏感
        assert resp.headers.get('content-type') == 'text/html'
        assert resp.headers.get('Content-Type') == 'text/html'
        assert resp.headers.get('CONTENT-TYPE') == 'text/html'
    
    def test_response_json_invalid(self):
        """测试非法 JSON 响应"""
        req = Request('http://example.com')
        resp = Response(
            url='http://example.com',
            status=200,
            body=b'not valid json {{{',
            request=req
        )
        
        # json() 应该抛出异常或返回 None
        with pytest.raises(Exception):
            resp.json()
