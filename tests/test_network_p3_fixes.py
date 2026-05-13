"""
Network 模块 P3 问题修复验证测试

验证所有 P3 优化项的修复：
1. Request 序列化/反序列化方法
2. Response 响应体大小限制
3. Request/Response 工厂方法
4. Request.copy() 性能优化
5. Response.xpath() 超时保护
"""
import pytest
import copy
from unittest.mock import Mock


class TestRequestSerialization:
    """Test 1: Request 序列化/反序列化方法"""
    
    def test_to_dict_basic(self):
        """测试基本序列化"""
        from crawlo.network.request import Request
        
        request = Request(
            url='http://example.com',
            method='POST',
            params={'page': 1},
            headers={'Content-Type': 'application/json'}
        )
        
        data = request.to_dict()
        
        assert data['url'] == 'http://example.com'
        assert data['method'] == 'POST'
        assert data['params'] == {'page': 1}
        assert data['headers']['Content-Type'] == 'application/json'
    
    def test_from_dict_basic(self):
        """测试基本反序列化"""
        from crawlo.network.request import Request
        
        data = {
            'url': 'http://example.com',
            'method': 'GET',
            'params': {'page': 1},
            'priority': 100,
        }
        
        request = Request.from_dict(data)
        
        assert request.url == 'http://example.com?page=1'
        assert request.method == 'GET'
    
    def test_serialization_roundtrip(self):
        """测试序列化往返一致性"""
        from crawlo.network.request import Request, RequestPriority
        
        original = Request(
            url='http://example.com/api',
            method='POST',
            json_body={'key': 'value'},
            priority=RequestPriority.HIGH,
            meta={'user': 'test'}
        )
        
        # 序列化
        data = original.to_dict()
        
        # 反序列化
        restored = Request.from_dict(data)
        
        # 验证一致性
        assert restored.url == original.url
        assert restored.method == original.method
        assert restored._json_body == original._json_body
        assert restored._meta == original._meta
    
    def test_to_dict_preserves_priority(self):
        """测试序列化保留优先级"""
        from crawlo.network.request import Request, RequestPriority
        
        request = Request(url='http://example.com', priority=RequestPriority.URGENT)
        
        data = request.to_dict()
        
        # priority 应该是正值 200
        assert data['priority'] == 200
        
        # 反序列化后应该保持一致
        restored = Request.from_dict(data)
        assert restored.priority == request.priority


class TestResponseBodyLimit:
    """Test 2: Response 响应体大小限制"""
    
    def test_normal_body_accepted(self):
        """测试正常大小的响应体被接受"""
        from crawlo.network.response import Response
        
        body = b'x' * (1024 * 1024)  # 1MB
        
        response = Response(
            url='http://example.com',
            body=body
        )
        
        assert len(response.body) == 1024 * 1024
    
    def test_oversized_body_rejected(self):
        """测试超大响应体被拒绝"""
        from crawlo.network.response import Response
        
        # 超过 100MB 限制
        body = b'x' * (Response.MAX_BODY_SIZE + 1)
        
        with pytest.raises(ValueError, match="Response body too large"):
            Response(
                url='http://example.com',
                body=body
            )
    
    def test_max_body_size_constant(self):
        """测试 MAX_BODY_SIZE 常量存在"""
        from crawlo.network.response import Response
        
        assert hasattr(Response, 'MAX_BODY_SIZE')
        assert Response.MAX_BODY_SIZE == 100 * 1024 * 1024  # 100MB


class TestFactoryMethods:
    """Test 3: Request/Response 工厂方法"""
    
    def test_request_get_factory(self):
        """测试 Request.get() 工厂方法"""
        from crawlo.network.request import Request
        
        request = Request.get('http://example.com', params={'page': 1})
        
        assert request.method == 'GET'
        assert 'page=1' in request.url
    
    def test_request_post_factory(self):
        """测试 Request.post() 工厂方法"""
        from crawlo.network.request import Request
        
        request = Request.post(
            'http://example.com/api',
            json_body={'key': 'value'}
        )
        
        assert request.method == 'POST'
        assert request._json_body == {'key': 'value'}
    
    def test_response_from_text_factory(self):
        """测试 Response.from_text() 工厂方法"""
        from crawlo.network.response import Response
        
        response = Response.from_text(
            'http://example.com',
            '<html><body>Test</body></html>'
        )
        
        assert response.url == 'http://example.com'
        assert b'<html>' in response.body
        assert '<html>' in response.text
    
    def test_response_from_json_factory(self):
        """测试 Response.from_json() 工厂方法"""
        from crawlo.network.response import Response
        
        data = {'name': 'test', 'value': 123}
        response = Response.from_json('http://api.example.com', data)
        
        assert response.url == 'http://api.example.com'
        assert response.headers['Content-Type'] == 'application/json'
        
        # 验证 JSON 解析
        parsed = response.json()
        assert parsed['name'] == 'test'
        assert parsed['value'] == 123


class TestCopyOptimization:
    """Test 4: Request.copy() 性能优化"""
    
    def test_shallow_copy_exists(self):
        """测试 __copy__ 方法存在"""
        from crawlo.network.request import Request
        
        request = Request(url='http://example.com')
        
        # 应该支持 copy.copy()
        copied = copy.copy(request)
        
        assert copied.url == request.url
        assert copied.method == request.method
    
    def test_shallow_vs_deep_copy(self):
        """测试浅拷贝与深拷贝的区别"""
        from crawlo.network.request import Request
        
        original = Request(
            url='http://example.com',
            meta={'data': {'nested': 'value'}}
        )
        
        # 浅拷贝
        shallow = copy.copy(original)
        
        # 浅拷贝的 meta 应该指向同一个对象
        assert shallow.meta is original.meta
        
        # 深拷贝（使用 copy() 方法）
        deep = original.copy()
        
        # 深拷贝的 meta 应该是独立对象
        assert deep.meta is not original.meta
        assert deep.meta == original.meta


class TestXpathTimeout:
    """Test 5: Response.xpath() 超时保护"""
    
    def test_xpath_has_timeout_parameter(self):
        """测试 xpath() 方法有 timeout 参数"""
        from crawlo.network.response import Response
        import inspect
        
        sig = inspect.signature(Response.xpath)
        params = sig.parameters
        
        assert 'timeout' in params
        assert params['timeout'].default == 5.0
    
    def test_css_has_timeout_parameter(self):
        """测试 css() 方法有 timeout 参数"""
        from crawlo.network.response import Response
        import inspect
        
        sig = inspect.signature(Response.css)
        params = sig.parameters
        
        assert 'timeout' in params
        assert params['timeout'].default == 5.0
    
    def test_xpath_timeout_works(self):
        """测试 xpath 超时机制工作正常"""
        from crawlo.network.response import Response
        
        response = Response(
            url='http://example.com',
            body=b'<html><body><div class="test">Content</div></body></html>'
        )
        
        # 正常查询应该在超时前完成
        result = response.xpath('//div[@class="test"]', timeout=1.0)
        assert len(result) == 1
    
    def test_css_timeout_propagates(self):
        """测试 css 超时传递给 xpath"""
        from crawlo.network.response import Response
        
        response = Response(
            url='http://example.com',
            body=b'<html><body><div class="test">Content</div></body></html>'
        )
        
        # css() 应该将 timeout 传递给 xpath()
        result = response.css('div.test', timeout=1.0)
        assert len(result) == 1


class IntegrationTest:
    """集成测试：验证多个修复点协同工作"""
    
    def test_request_serialization_with_factory(self):
        """测试序列化与工厂方法结合"""
        from crawlo.network.request import Request
        
        # 使用工厂方法创建
        original = Request.post(
            'http://api.example.com/data',
            json_body={'key': 'value'},
            headers={'Authorization': 'Bearer token'}
        )
        
        # 序列化
        data = original.to_dict()
        
        # 反序列化
        restored = Request.from_dict(data)
        
        # 验证
        assert restored.method == 'POST'
        assert restored._json_body == {'key': 'value'}
        assert restored.headers['Authorization'] == 'Bearer token'
    
    def test_response_factory_with_body_limit(self):
        """测试 Response 工厂方法与大小限制结合"""
        from crawlo.network.response import Response
        
        # 正常大小的 JSON 响应
        data = {'key': 'value'}
        response = Response.from_json('http://api.example.com', data)
        
        assert response is not None
        assert response.json()['key'] == 'value'
