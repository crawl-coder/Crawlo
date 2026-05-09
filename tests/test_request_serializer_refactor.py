"""
RequestSerializer 重构验证测试

验证使用 to_dict() / from_dict() 的新版 RequestSerializer
"""
import pytest
import json
from unittest.mock import Mock


class TestRequestSerializerBasic:
    """Test basic serialization"""
    
    def test_serialize_simple_request(self):
        """Test serializing a simple request"""
        from crawlo.network import Request
        from crawlo.utils.request.request_serializer import RequestSerializer
        
        serializer = RequestSerializer()
        request = Request.get("http://example.com")
        
        # Serialize
        data = serializer.prepare_for_serialization(request)
        
        assert isinstance(data, dict)
        assert data['url'] == "http://example.com"
        assert data['method'] == "GET"
    
    def test_deserialize_simple_request(self):
        """Test deserializing a simple request"""
        from crawlo.network import Request
        from crawlo.utils.request.request_serializer import RequestSerializer
        
        serializer = RequestSerializer()
        data = {
            'url': 'http://example.com',
            'method': 'GET',
            'priority': 0,
        }
        
        # Deserialize
        request = serializer.restore_after_deserialization(data)
        
        assert request.url == "http://example.com"
        assert request.method == "GET"
    
    def test_roundtrip(self):
        """Test serialization roundtrip"""
        from crawlo.network import Request, RequestPriority
        from crawlo.utils.request.request_serializer import RequestSerializer
        
        serializer = RequestSerializer()
        
        # Create request
        original = Request.post(
            "http://api.example.com/data",
            json_body={"key": "value"},
            priority=RequestPriority.HIGH,
            headers={"Authorization": "Bearer token"}
        )
        
        # Serialize
        data = serializer.prepare_for_serialization(original)
        
        # Deserialize
        restored = serializer.restore_after_deserialization(data)
        
        # Verify
        assert restored.url == original.url
        assert restored.method == original.method
        assert restored._json_body == original._json_body
        assert restored.headers.get("Authorization") == "Bearer token"


class TestRequestSerializerCallback:
    """Test callback restoration"""
    
    def test_callback_saved_and_restored(self):
        """Test that callback info is saved and restored"""
        from crawlo.network import Request
        from crawlo.utils.request.request_serializer import RequestSerializer
        
        # Create mock spider with proper method
        class MockSpider:
            def parse_detail(self, response):
                pass
        
        spider = MockSpider()
        
        # Create request with callback
        request = Request(
            url="http://example.com",
            callback=spider.parse_detail
        )
        
        # Serialize
        serializer = RequestSerializer()
        data = serializer.prepare_for_serialization(request)
        
        # Verify callback info saved
        assert '_callback_info' in data['meta']
        assert data['meta']['_callback_info']['method_name'] == 'parse_detail'
        
        # Deserialize with spider
        restored = serializer.restore_after_deserialization(data, spider=spider)
        
        # Verify callback restored
        assert restored.callback is not None
        assert '_callback_info' not in restored._meta  # Should be removed


class TestRequestSerializerComplex:
    """Test complex request serialization"""
    
    def test_serialize_with_params(self):
        """Test request with GET params"""
        from crawlo.network import Request
        from crawlo.utils.request.request_serializer import RequestSerializer
        
        serializer = RequestSerializer()
        request = Request.get(
            "http://example.com/search",
            params={"q": "python", "page": 1}
        )
        
        data = serializer.prepare_for_serialization(request)
        
        assert data['url'] == "http://example.com/search"
        assert data['params'] == {"q": "python", "page": 1}
    
    def test_serialize_with_form_data(self):
        """Test request with form data"""
        from crawlo.network import Request
        from crawlo.utils.request.request_serializer import RequestSerializer
        
        serializer = RequestSerializer()
        request = Request.post(
            "http://example.com/login",
            form_data={"username": "admin", "password": "secret"}
        )
        
        data = serializer.prepare_for_serialization(request)
        
        assert data['form_data'] == {"username": "admin", "password": "secret"}
    
    def test_serialize_with_meta(self):
        """Test request with meta data"""
        from crawlo.network import Request
        from crawlo.utils.request.request_serializer import RequestSerializer
        
        serializer = RequestSerializer()
        request = Request.get(
            "http://example.com",
            meta={"user": "test", "retry_count": 3}
        )
        
        data = serializer.prepare_for_serialization(request)
        
        assert data['meta']['user'] == "test"
        assert data['meta']['retry_count'] == 3


class TestRequestSerializerFormats:
    """Test different serialization formats"""
    
    def test_pickle_format(self):
        """Test pickle format (default)"""
        from crawlo.utils.request.request_serializer import RequestSerializer
        
        serializer = RequestSerializer(serialization_format='pickle')
        assert serializer.serialization_format == 'pickle'
    
    def test_msgpack_format_with_import(self):
        """Test msgpack format when available"""
        from crawlo.utils.request.request_serializer import RequestSerializer, MSGPACK_AVAILABLE
        
        serializer = RequestSerializer(serialization_format='msgpack')
        
        if MSGPACK_AVAILABLE:
            assert serializer.serialization_format == 'msgpack'
        else:
            # Should fallback to pickle
            assert serializer.serialization_format == 'pickle'


class TestRequestSerializerEdgeCases:
    """Test edge cases"""
    
    def test_empty_request(self):
        """Test serializing minimal request"""
        from crawlo.network import Request
        from crawlo.utils.request.request_serializer import RequestSerializer
        
        serializer = RequestSerializer()
        request = Request(url="http://example.com")
        
        data = serializer.prepare_for_serialization(request)
        restored = serializer.restore_after_deserialization(data)
        
        assert restored.url == "http://example.com"
    
    def test_request_with_none_values(self):
        """Test request with None values"""
        from crawlo.network import Request
        from crawlo.utils.request.request_serializer import RequestSerializer
        
        serializer = RequestSerializer()
        request = Request(
            url="http://example.com",
            proxy=None,
            timeout=None
        )
        
        data = serializer.prepare_for_serialization(request)
        restored = serializer.restore_after_deserialization(data)
        
        assert restored.url == "http://example.com"
    
    def test_preserves_priority(self):
        """Test that priority is preserved"""
        from crawlo.network import Request, RequestPriority
        from crawlo.utils.request.request_serializer import RequestSerializer
        
        serializer = RequestSerializer()
        
        for priority in [RequestPriority.URGENT, RequestPriority.HIGH, RequestPriority.NORMAL]:
            request = Request(url="http://example.com", priority=priority)
            data = serializer.prepare_for_serialization(request)
            restored = serializer.restore_after_deserialization(data)
            
            assert restored.priority == request.priority, f"Failed for {priority}"
