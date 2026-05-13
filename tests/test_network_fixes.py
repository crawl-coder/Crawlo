"""
Network 模块修复验证测试

验证所有 P1/P2 问题的修复：
1. Response 类级别缓存清理机制
2. Request._safe_deepcopy_meta 递归深度限制
3. ujson 导入失败降级方案
4. Request 优先级语义文档
5. Response.xpath/css 异常处理优化
6. Request._add_params_to_url 参数覆盖
7. Response 自适应选择器动态配置
"""
import pytest
import asyncio
import atexit
import logging
import json
from unittest.mock import Mock, patch


class TestResponseAdaptiveCacheCleanup:
    """Test 1: Response 类级别缓存清理机制"""
    
    def test_cleanup_registered_on_init(self):
        """测试初始化时注册清理函数"""
        from crawlo.network.response import Response
        
        # 重置状态
        Response._cleanup_registered = False
        Response._adaptive_initialized = False
        Response._adaptive_enabled_global = None
        
        # 触发初始化
        Response._adaptive_initialized = False
        result = Response._is_adaptive_enabled()
        
        # 验证清理函数已注册
        assert Response._cleanup_registered is True
    
    def test_cleanup_method_releases_resources(self):
        """测试清理方法释放资源"""
        from crawlo.network.response import Response
        
        # 模拟已初始化
        Response._adaptive_storage = Mock()
        Response._adaptive_matcher = Mock()
        Response._adaptive_enabled_global = True
        Response._adaptive_initialized = True
        
        # 调用清理
        Response.cleanup_adaptive()
        
        # 验证资源已释放
        assert Response._adaptive_storage is None
        assert Response._adaptive_matcher is None
        assert Response._adaptive_enabled_global is None
        assert Response._adaptive_initialized is False
    
    def test_cleanup_handles_exception_gracefully(self):
        """测试清理方法优雅处理异常"""
        from crawlo.network.response import Response
        
        # 模拟有问题的存储对象
        Response._adaptive_storage = Mock()
        Response._adaptive_storage.close.side_effect = Exception("cleanup error")
        Response._adaptive_matcher = Mock()
        
        # 不应该抛出异常
        try:
            Response.cleanup_adaptive()
            success = True
        except Exception:
            success = False
        
        assert success is True


class TestRequestMetaRecursionLimit:
    """Test 2: Request._safe_deepcopy_meta 递归深度限制"""
    
    def test_deep_nesting_raises_error(self):
        """测试深度嵌套时抛出错误"""
        from crawlo.network.request import Request
        
        # 创建深度嵌套的 meta（超过 50 层）
        meta = {'data': 'value'}
        current = meta
        for i in range(55):
            current['nested'] = {}
            current = current['nested']
        
        # 应该抛出 ValueError
        with pytest.raises(ValueError, match="Meta nesting too deep"):
            Request._safe_deepcopy_meta(meta)
    
    def test_normal_nesting_works(self):
        """测试正常嵌套深度可以工作"""
        from crawlo.network.request import Request
        
        # 创建合理嵌套的 meta
        meta = {
            'level1': {
                'level2': {
                    'level3': 'value'
                }
            }
        }
        
        # 应该成功
        result = Request._safe_deepcopy_meta(meta)
        assert result['level1']['level2']['level3'] == 'value'
    
    def test_logger_removed_before_copy(self):
        """测试 logger 在复制前被移除"""
        from crawlo.network.request import Request
        
        logger = logging.getLogger('test')
        meta = {
            'logger': logger,
            'custom_logger': logger,
            'data': {'nested_logger': logger},
            'normal': 'value'
        }
        
        result = Request._safe_deepcopy_meta(meta)
        
        # 验证 logger 已移除
        assert 'logger' not in result
        assert 'custom_logger' not in result
        assert 'nested_logger' not in result.get('data', {})
        assert result['normal'] == 'value'


class TestUjsonFallback:
    """Test 3: ujson 导入失败降级方案"""
    
    def test_json_module_available(self):
        """测试 JSON 模块可用"""
        from crawlo.network.response import json_module, USE_UJSON
        
        # 应该至少有一个模块可用
        assert json_module is not None
        assert hasattr(json_module, 'loads')
        assert hasattr(json_module, 'dumps')
    
    def test_json_parsing_works(self):
        """测试 JSON 解析工作正常"""
        from crawlo.network.response import Response
        
        # 创建响应
        response = Response(
            url='http://example.com/api',
            body=b'{"name": "test", "value": 123}',
            headers={'Content-Type': 'application/json'}
        )
        
        # 应该能解析
        data = response.json()
        assert data['name'] == 'test'
        assert data['value'] == 123
    
    def test_json_parse_error_with_default(self):
        """测试 JSON 解析错误时返回默认值"""
        from crawlo.network.response import Response
        
        response = Response(
            url='http://example.com/api',
            body=b'not valid json',
            headers={'Content-Type': 'text/html'}
        )
        
        # 应该返回默认值
        result = response.json(default={'fallback': True})
        assert result['fallback'] is True


class TestRequestPriorityDocs:
    """Test 4: Request 优先级语义"""
    
    def test_positive_priority_negated(self):
        """测试正数优先级被取反"""
        from crawlo.network.request import Request, RequestPriority
        
        # 创建请求
        request = Request(url='http://example.com', priority=RequestPriority.HIGH)
        
        # HIGH=100，内部存储应为 -100
        assert request.priority == -100
    
    def test_urgent_priority(self):
        """测试紧急优先级"""
        from crawlo.network.request import Request, RequestPriority
        
        request = Request(url='http://example.com', priority=RequestPriority.URGENT)
        
        # URGENT=200，内部存储应为 -200
        assert request.priority == -200


class TestSelectorErrorHandling:
    """Test 5: Response.xpath/css 异常处理优化"""
    
    def test_get_strict_mode_raises(self):
        """测试严格模式下抛出异常"""
        from crawlo.network.response import Response
        
        response = Response(
            url='http://example.com',
            body=b'<html><body>Test</body></html>'
        )
        
        # 无效选择器在严格模式下应该抛出异常
        with pytest.raises(Exception):
            response.get('invalid:::selector', strict=True)
    
    def test_get_non_strict_returns_default(self):
        """测试非严格模式下返回默认值"""
        from crawlo.network.response import Response
        
        response = Response(
            url='http://example.com',
            body=b'<html><body>Test</body></html>'
        )
        
        # 无效选择器应该返回默认值
        result = response.get('invalid:::selector', default='fallback')
        assert result == 'fallback'
    
    def test_getall_strict_mode_raises(self):
        """测试 getall 严格模式"""
        from crawlo.network.response import Response
        
        response = Response(
            url='http://example.com',
            body=b'<html><body>Test</body></html>'
        )
        
        with pytest.raises(Exception):
            response.getall('invalid:::selector', strict=True)
    
    def test_getall_non_strict_returns_empty(self):
        """测试 getall 非严格模式返回空列表"""
        from crawlo.network.response import Response
        
        response = Response(
            url='http://example.com',
            body=b'<html><body>Test</body></html>'
        )
        
        result = response.getall('invalid:::selector')
        assert result == []


class TestAddParamsToUrl:
    """Test 6: Request._add_params_to_url 参数覆盖"""
    
    def test_replace_mode_overwrites(self):
        """测试覆盖模式替换已有参数"""
        from crawlo.network.request import Request
        
        url = 'http://example.com?page=1'
        params = {'page': 2, 'sort': 'desc'}
        
        result = Request._add_params_to_url(url, params, replace=True)
        
        # page 应该被覆盖为 2
        assert 'page=2' in result
        assert 'sort=desc' in result
    
    def test_append_mode_keeps_existing(self):
        """测试追加模式保留已有参数"""
        from crawlo.network.request import Request
        
        url = 'http://example.com?page=1'
        params = {'page': 2, 'sort': 'desc'}
        
        result = Request._add_params_to_url(url, params, replace=False)
        
        # page 应该保留为 1
        assert 'page=1' in result
        assert 'sort=desc' in result
    
    def test_default_is_replace(self):
        """测试默认是覆盖模式"""
        from crawlo.network.request import Request
        
        url = 'http://example.com?page=1'
        params = {'page': 2}
        
        result = Request._add_params_to_url(url, params)
        assert 'page=2' in result


class TestAdaptiveDynamicConfig:
    """Test 7: Response 自适应选择器动态配置"""
    
    def test_can_initialize_with_defaults(self):
        """测试可以使用默认配置初始化"""
        from crawlo.network.response import Response
        
        # 重置状态
        Response._cleanup_registered = False
        Response._adaptive_initialized = False
        Response._adaptive_enabled_global = None
        
        # 应该能初始化
        result = Response._is_adaptive_enabled()
        
        # 如果依赖可用，应该返回 True
        # 注意：这取决于 FingerprintStorage 和 SimilarityMatcher 是否可用
        # 所以不严格断言结果
        assert isinstance(result, bool)


class IntegrationTest:
    """集成测试：验证多个修复点协同工作"""
    
    def test_request_copy_with_deep_meta(self):
        """测试 Request copy 与深度 meta 处理"""
        from crawlo.network.request import Request
        
        meta = {
            'data': {'key': 'value'},
            'list': [1, 2, 3],
            'normal': 'string'
        }
        
        original = Request(url='http://example.com', meta=meta)
        copied = original.copy()
        
        # 验证是深拷贝
        assert copied.meta is not original.meta
        assert copied.meta['data'] is not meta['data']
        assert copied.meta['list'] is not meta['list']
        assert copied.meta == original.meta
    
    def test_response_json_with_various_content_types(self):
        """测试 Response JSON 解析不同内容类型"""
        from crawlo.network.response import Response
        
        # JSON 内容
        response1 = Response(
            url='http://example.com',
            body=b'{"test": true}',
            headers={'Content-Type': 'application/json'}
        )
        assert response1.json()['test'] is True
        
        # 非 JSON 内容（使用默认值）
        response2 = Response(
            url='http://example.com',
            body=b'<html></html>',
            headers={'Content-Type': 'text/html'}
        )
        assert response2.json(default=None) is None
