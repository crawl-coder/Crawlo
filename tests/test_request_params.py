#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Request参数处理测试
"""
import unittest
from crawlo.network.request import Request


class TestRequestParams(unittest.TestCase):
    """Request参数处理测试类"""

    def test_get_params_handling(self):
        """测试GET参数处理"""
        # 测试GET请求带参数
        params = {"page": 1, "limit": 10, "search": "test"}
        request = Request(
            url="https://api.example.com/users",
            method="GET",
            get_params=params
        )
        
        # 验证参数是否正确附加到URL上
        self.assertIn("https://api.example.com/users?", request.url)
        self.assertIn("page=1", request.url)
        self.assertIn("limit=10", request.url)
        self.assertIn("search=test", request.url)
        self.assertEqual(request.method, "GET")

    def test_form_data_with_get(self):
        """测试GET请求使用form_data"""
        # 测试GET请求使用form_data参数
        form_data = {"category": "books", "sort": "name"}
        request = Request(
            url="https://api.example.com/products",
            method="GET",
            form_data=form_data
        )
        
        # 验证form_data是否正确作为GET参数附加到URL上
        self.assertIn("https://api.example.com/products?", request.url)
        self.assertIn("category=books", request.url)
        self.assertIn("sort=name", request.url)
        self.assertEqual(request.method, "GET")

    def test_form_data_with_post(self):
        """测试POST请求使用form_data"""
        # 测试POST请求使用form_data参数
        form_data = {"username": "testuser", "password": "testpass"}
        request = Request(
            url="https://api.example.com/login",
            method="POST",
            form_data=form_data
        )
        
        # 验证form_data是否作为请求体发送
        self.assertEqual(request.method, "POST")
        self.assertIn("username=testuser", request.body.decode('utf-8'))
        self.assertIn("password=testpass", request.body.decode('utf-8'))
        self.assertEqual(request.headers.get('Content-Type'), 'application/x-www-form-urlencoded')

    def test_json_body_with_post(self):
        """测试POST请求使用json_body"""
        # 测试POST请求使用json_body参数
        json_data = {"name": "John", "age": 30}
        request = Request(
            url="https://api.example.com/users",
            method="POST",
            json_body=json_data
        )
        
        # 验证json_body是否正确序列化
        self.assertEqual(request.method, "POST")
        import json
        self.assertEqual(json.loads(request.body.decode('utf-8')), json_data)
        self.assertEqual(request.headers.get('Content-Type'), 'application/json')

    def test_get_params_with_existing_query(self):
        """测试向已有查询参数的URL添加GET参数"""
        # 测试向已有查询参数的URL添加更多参数
        params = {"page": 2, "limit": 20}
        request = Request(
            url="https://api.example.com/users?category=active",
            method="GET",
            get_params=params
        )
        
        # 验证原有参数和新参数都存在
        self.assertIn("https://api.example.com/users?", request.url)
        self.assertIn("category=active", request.url)
        self.assertIn("page=2", request.url)
        self.assertIn("limit=20", request.url)

    def test_form_data_conversion_to_get(self):
        """测试form_data在GET请求中自动转换为URL参数"""
        # 测试form_data在GET请求中自动转换为URL参数的行为
        form_data = {"filter": "active", "sort": "date"}
        request = Request(
            url="https://api.example.com/posts",
            method="GET",
            form_data=form_data
        )
        
        # 验证form_data被正确转换为GET参数
        self.assertIn("https://api.example.com/posts?", request.url)
        self.assertIn("filter=active", request.url)
        self.assertIn("sort=date", request.url)
        self.assertEqual(request.method, "GET")


if __name__ == '__main__':
    unittest.main()