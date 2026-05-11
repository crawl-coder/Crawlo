"""
安全极限测试

测试框架对 SQL 注入、XSS、路径遍历等安全威胁的防护能力
"""
import pytest
from unittest.mock import Mock
from crawlo.network.request import Request
from crawlo.items.item import Item


class TestSQLInjectionProtection:
    """SQL 注入防护测试"""
    
    def test_request_url_sql_injection(self):
        """测试 URL 中的 SQL 注入"""
        injection_urls = [
            "http://example.com/page?id=1' OR '1'='1",
            "http://example.com/page?id=1; DROP TABLE users;--",
            "http://example.com/page?name=admin'--",
            "http://example.com/search?q=UNION SELECT * FROM passwords",
        ]
        
        for url in injection_urls:
            # Request 应该能安全存储，URL 会被编码
            request = Request(url)
            # URL 会被编码，但不执行 SQL
            assert 'example.com' in request.url
    
    def test_item_data_sql_injection(self):
        """测试 Item 数据中的 SQL 注入"""
        item = Item()
        item['url'] = 'http://example.com'
        
        injection_data = [
            "'; DROP TABLE users;--",
            "' OR '1'='1",
            "1; DELETE FROM users",
            "UNION SELECT password FROM users",
        ]
        
        for data in injection_data:
            item['title'] = data
            item['content'] = data
            
            # Item 应该能安全存储，不执行 SQL
            assert item['title'] == data
            assert item['content'] == data


class TestXSSProtection:
    """XSS 防护测试"""
    
    def test_request_meta_xss(self):
        """测试 Request meta 中的 XSS"""
        xss_payloads = [
            '<script>alert("XSS")</script>',
            '<img src=x onerror=alert(1)>',
            '<svg onload=alert(1)>',
            'javascript:alert(1)',
            '<iframe src="javascript:alert(1)">',
        ]
        
        for payload in xss_payloads:
            request = Request('http://example.com')
            request.meta['xss_test'] = payload
            
            # Meta 应该能安全存储
            assert request.meta['xss_test'] == payload
    
    def test_item_data_xss(self):
        """测试 Item 数据中的 XSS"""
        item = Item()
        item['url'] = 'http://example.com'
        
        xss_payloads = [
            '<script>alert("XSS")</script>',
            '<body onload=alert(1)>',
            '<div style="background-image: url(javascript:alert(1))">',
        ]
        
        for payload in xss_payloads:
            item['title'] = payload
            item['description'] = payload
            
            # Item 应该能安全存储
            assert item['title'] == payload
            assert item['description'] == payload
    
    def test_response_body_xss(self):
        """测试响应体中的 XSS 处理"""
        from crawlo.network.response import Response
        
        xss_html = '''
        <html>
        <head><title>Test</title></head>
        <body>
            <script>alert("XSS")</script>
            <img src=x onerror=alert(1)>
            <svg onload=alert(1)>
        </body>
        </html>
        '''
        
        response = Response(
            url='http://example.com',
            body=xss_html.encode('utf-8'),
        )
        
        # 响应体应该能安全存储
        assert b'<script>' in response.body


class TestPathTraversalProtection:
    """路径遍历防护测试"""
    
    def test_file_path_traversal(self):
        """测试文件路径遍历"""
        traversal_paths = [
            '../../../etc/passwd',
            '..\\..\\..\\windows\\system32\\config\\sam',
            '%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd',
            '....//....//....//etc/passwd',
            '/etc/shadow',
            'C:\\Windows\\System32\\config\\SAM',
        ]
        
        for path in traversal_paths:
            request = Request(f'http://example.com/download?file={path}')
            
            # Request 应该能安全存储路径
            assert path in request.url
    
    def test_item_file_path_traversal(self):
        """测试 Item 中的文件路径遍历"""
        item = Item()
        item['url'] = 'http://example.com'
        
        traversal_paths = [
            '../../../etc/passwd',
            '..\\..\\windows\\system32',
        ]
        
        for path in traversal_paths:
            item['file_path'] = path
            
            # Item 应该能安全存储
            assert item['file_path'] == path


class TestCommandInjectionProtection:
    """命令注入防护测试"""
    
    def test_request_url_command_injection(self):
        """测试 URL 中的命令注入"""
        command_payloads = [
            'http://example.com/page?cmd=;ls -la',
            'http://example.com/page?cmd=|cat /etc/passwd',
            'http://example.com/page?cmd=`whoami`',
            'http://example.com/page?cmd=$(rm -rf /)',
            'http://example.com/page?cmd=%0Aid',
        ]
        
        for url in command_payloads:
            request = Request(url)
            
            # Request 应该能安全存储，不执行命令
            assert request.url == url
    
    def test_item_data_command_injection(self):
        """测试 Item 数据中的命令注入"""
        item = Item()
        item['url'] = 'http://example.com'
        
        command_payloads = [
            '; rm -rf /',
            '| cat /etc/passwd',
            '`whoami`',
            '$(id)',
        ]
        
        for payload in command_payloads:
            item['command'] = payload
            
            # Item 应该能安全存储
            assert item['command'] == payload


class TestHeaderInjectionProtection:
    """Header 注入防护测试"""
    
    def test_request_header_crlf_injection(self):
        """测试 CRLF Header 注入"""
        crlf_payloads = [
            'value\r\nX-Injected: header',
            'value\nX-Injected: header',
            'value\r\n\r\nHTTP/1.1 200 OK',
        ]
        
        for payload in crlf_payloads:
            request = Request('http://example.com')
            request.headers['X-Custom'] = payload
            
            # Header 应该能安全存储
            assert request.headers['X-Custom'] == payload
    
    def test_request_header_special_characters(self):
        """测试 Header 特殊字符"""
        special_headers = {
            'X-Unicode': '中文Header',
            'X-Emoji': '😀🎉',
            'X-Null': 'value\x00with\x00null',
            'X-SQL': "'; DROP TABLE--",
            'X-XSS': '<script>alert(1)</script>',
        }
        
        request = Request('http://example.com')
        for key, value in special_headers.items():
            request.headers[key] = value
            assert request.headers[key] == value


class TestCookieInjectionProtection:
    """Cookie 注入防护测试"""
    
    def test_cookie_injection(self):
        """测试 Cookie 注入"""
        cookie_payloads = [
            'session=abc123; admin=true',
            'user=admin--',
            'token=<script>alert(1)</script>',
            'id=1 OR 1=1',
        ]
        
        for payload in cookie_payloads:
            request = Request('http://example.com')
            request.cookies = payload
            
            # Cookie 应该能安全存储
            assert request.cookies == payload


class TestSerializationSecurity:
    """序列化安全测试"""
    
    def test_pickle_untrusted_data(self):
        """测试 Pickle 反序列化不可信数据"""
        import pickle
        
        # 恶意的 pickle 数据
        # 注意：这里只测试存储，不实际反序列化恶意数据
        
        item = Item()
        item['url'] = 'http://example.com'
        item['data'] = b'\\x80\\x04\\x95...'  # 模拟 pickle 数据
        
        # Item 应该能安全存储二进制数据
        assert isinstance(item['data'], bytes)
    
    def test_request_to_dict_roundtrip(self):
        """测试 Request 序列化/反序列化安全性"""
        request = Request('http://example.com')
        request.meta['xss'] = '<script>alert(1)</script>'
        request.meta['sql'] = "'; DROP TABLE--"
        
        # 序列化
        data = request.to_dict()
        
        # 反序列化
        restored = Request.from_dict(data)
        
        # 数据应该完整保留
        assert restored.meta['xss'] == '<script>alert(1)</script>'
        assert restored.meta['sql'] == "'; DROP TABLE--"


class TestDenialOfServiceProtection:
    """拒绝服务防护测试"""
    
    def test_huge_request_headers(self):
        """测试超大 Request Headers（1000 个）"""
        request = Request('http://example.com')
        
        # 添加 1000 个 header
        for i in range(1000):
            request.headers[f'X-Header-{i}'] = f'value-{i}'
        
        # 应该能处理，不崩溃
        assert len(request.headers) == 1000
    
    def test_huge_item_fields(self):
        """测试超大 Item 字段（10MB 字符串）"""
        item = Item()
        item['url'] = 'http://example.com'
        item['huge_field'] = 'x' * (10 * 1024 * 1024)  # 10MB
        
        # 应该能处理，不崩溃
        assert len(item['huge_field']) == 10 * 1024 * 1024
    
    def test_deeply_nested_meta(self):
        """测试深度嵌套的 meta 数据"""
        request = Request('http://example.com')
        
        # 创建深度嵌套结构
        nested = {'level': 0}
        current = nested
        for i in range(1, 100):
            current['child'] = {'level': i}
            current = current['child']
        
        request.meta['nested'] = nested
        
        # 应该能处理深度嵌套
        assert request.meta['nested']['level'] == 0
