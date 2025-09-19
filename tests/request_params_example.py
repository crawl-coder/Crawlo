#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Request参数处理示例
"""
from crawlo.network.request import Request


def demo_get_params():
    """演示GET参数处理"""
    print("=== GET参数处理演示 ===\n")
    
    # 使用get_params参数
    params = {"page": 1, "limit": 10, "search": "python"}
    request = Request(
        url="https://api.example.com/articles",
        method="GET",
        get_params=params
    )
    
    print(f"URL: {request.url}")
    print(f"Method: {request.method}")
    print()


def demo_form_data_with_get():
    """演示GET请求使用form_data"""
    print("=== GET请求使用form_data演示 ===\n")
    
    # GET请求使用form_data参数
    form_data = {"category": "technology", "sort": "date"}
    request = Request(
        url="https://api.example.com/posts",
        method="GET",
        form_data=form_data
    )
    
    print(f"URL: {request.url}")
    print(f"Method: {request.method}")
    print()


def demo_form_data_with_post():
    """演示POST请求使用form_data"""
    print("=== POST请求使用form_data演示 ===\n")
    
    # POST请求使用form_data参数
    form_data = {"username": "testuser", "password": "secret"}
    request = Request(
        url="https://api.example.com/login",
        method="POST",
        form_data=form_data
    )
    
    print(f"URL: {request.url}")
    print(f"Method: {request.method}")
    print(f"Body: {request.body.decode('utf-8')}")
    print(f"Content-Type: {request.headers.get('Content-Type')}")
    print()


def demo_json_body():
    """演示JSON请求体"""
    print("=== JSON请求体演示 ===\n")
    
    # 使用json_body参数
    json_data = {"name": "John Doe", "email": "john@example.com", "age": 30}
    request = Request(
        url="https://api.example.com/users",
        method="POST",
        json_body=json_data
    )
    
    print(f"URL: {request.url}")
    print(f"Method: {request.method}")
    print(f"Body: {request.body.decode('utf-8')}")
    print(f"Content-Type: {request.headers.get('Content-Type')}")
    print()


def demo_combined_usage():
    """演示组合使用"""
    print("=== 组合使用演示 ===\n")
    
    # 复杂的请求示例
    request = Request(
        url="https://api.example.com/search",
        method="GET",
        get_params={"q": "python爬虫", "lang": "zh"},
        headers={"User-Agent": "Crawlo/1.0", "Accept": "application/json"},
        meta={"retries": 3, "priority": 1}
    )
    
    print(f"URL: {request.url}")
    print(f"Method: {request.method}")
    print(f"Headers: {request.headers}")
    print(f"Meta: {request.meta}")
    print()


if __name__ == '__main__':
    # 运行演示
    demo_get_params()
    demo_form_data_with_get()
    demo_form_data_with_post()
    demo_json_body()
    demo_combined_usage()
    
    print("=== 在爬虫中使用Request参数 ===\n")
    print("在爬虫项目中，您可以这样使用Request参数:")
    print("""
from crawlo import Spider, Request

class ExampleSpider(Spider):
    def start_requests(self):
        # GET请求带参数
        yield Request(
            url="https://api.example.com/articles",
            method="GET",
            get_params={"page": 1, "limit": 20},
            callback=self.parse_articles
        )
        
        # POST请求带表单数据
        yield Request(
            url="https://api.example.com/login",
            method="POST",
            form_data={"username": "user", "password": "pass"},
            callback=self.parse_login
        )
        
        # POST请求带JSON数据
        yield Request(
            url="https://api.example.com/users",
            method="POST",
            json_body={"name": "John", "email": "john@example.com"},
            callback=self.parse_user
        )
    
    async def parse_articles(self, response):
        # 处理文章列表
        pass
        
    async def parse_login(self, response):
        # 处理登录响应
        pass
        
    async def parse_user(self, response):
        # 处理用户创建响应
        pass
    """)