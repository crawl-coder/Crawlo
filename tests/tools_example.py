#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Crawlo框架工具包使用示例
"""
from crawlo.tools import (
    # 日期工具
    parse_time,
    format_time,
    time_diff,
    
    # 数据清洗工具
    clean_text,
    format_currency,
    extract_emails,
    
    # 数据验证工具
    validate_email,
    validate_url,
    validate_phone,
    
    # 请求处理工具
    build_url,
    add_query_params,
    merge_headers,
    
    # 反爬虫应对工具
    get_random_user_agent,
    rotate_proxy,
    
    # 带认证代理工具
    AuthenticatedProxy,
    create_proxy_config,
    get_proxy_info,
    
    # 分布式协调工具
    generate_task_id,
    get_cluster_info
)


def demo_date_tools():
    """演示日期工具的使用"""
    print("=== 日期工具演示 ===\n")
    
    # 解析时间
    time_str = "2025-09-10 14:30:00"
    parsed_time = parse_time(time_str)
    print(f"解析时间: {time_str} -> {parsed_time}")
    
    # 格式化时间
    formatted_time = format_time(parsed_time, "%Y年%m月%d日 %H:%M:%S")
    print(f"格式化时间: {parsed_time} -> {formatted_time}")
    
    # 时间差计算
    time_str2 = "2025-09-11 16:45:30"
    parsed_time2 = parse_time(time_str2)
    diff = time_diff(parsed_time2, parsed_time)
    print(f"时间差: {time_str2} - {time_str} = {diff} 秒")
    
    print()


def demo_data_cleaning_tools():
    """演示数据清洗工具的使用"""
    print("=== 数据清洗工具演示 ===\n")
    
    # 清洗文本
    dirty_text = "<p>这是一个&nbsp;<b>测试</b>&amp;文本</p>"
    clean_result = clean_text(dirty_text)
    print(f"清洗文本: {dirty_text} -> {clean_result}")
    
    # 格式化货币
    price = 1234.567
    formatted_price = format_currency(price, "¥", 2)
    print(f"格式化货币: {price} -> {formatted_price}")
    
    # 提取邮箱
    text_with_email = "联系邮箱: test@example.com, support@crawler.com"
    emails = extract_emails(text_with_email)
    print(f"提取邮箱: {text_with_email} -> {emails}")
    
    print()


def demo_data_validation_tools():
    """演示数据验证工具的使用"""
    print("=== 数据验证工具演示 ===\n")
    
    # 验证邮箱
    email = "test@example.com"
    is_valid_email = validate_email(email)
    print(f"验证邮箱: {email} -> {'有效' if is_valid_email else '无效'}")
    
    # 验证无效邮箱
    invalid_email = "invalid-email"
    is_valid_invalid = validate_email(invalid_email)
    print(f"验证邮箱: {invalid_email} -> {'有效' if is_valid_invalid else '无效'}")
    
    # 验证URL
    url = "https://example.com/path?param=value"
    is_valid_url = validate_url(url)
    print(f"验证URL: {url} -> {'有效' if is_valid_url else '无效'}")
    
    # 验证电话号码
    phone = "13812345678"
    is_valid_phone = validate_phone(phone)
    print(f"验证电话: {phone} -> {'有效' if is_valid_phone else '无效'}")
    
    print()


def demo_request_handling_tools():
    """演示请求处理工具的使用"""
    print("=== 请求处理工具演示 ===\n")
    
    # 构建URL
    base_url = "https://api.example.com"
    path = "/v1/users"
    query_params = {"page": 1, "limit": 10}
    full_url = build_url(base_url, path, query_params)
    print(f"构建URL: {base_url} + {path} + {query_params} -> {full_url}")
    
    # 添加查询参数
    existing_url = "https://api.example.com/v1/users?page=1"
    new_params = {"sort": "name", "order": "asc"}
    updated_url = add_query_params(existing_url, new_params)
    print(f"添加参数: {existing_url} + {new_params} -> {updated_url}")
    
    # 合并请求头
    base_headers = {"Content-Type": "application/json", "Accept": "application/json"}
    additional_headers = {"Authorization": "Bearer token123", "User-Agent": "Crawlo/1.0"}
    merged_headers = merge_headers(base_headers, additional_headers)
    print(f"合并请求头:")
    print(f"  基础头: {base_headers}")
    print(f"  额外头: {additional_headers}")
    print(f"  合并后: {merged_headers}")
    
    print()


def demo_anti_crawler_tools():
    """演示反爬虫应对工具的使用"""
    print("=== 反爬虫应对工具演示 ===\n")
    
    # 获取随机User-Agent
    user_agent = get_random_user_agent()
    print(f"随机User-Agent: {user_agent[:50]}...")
    
    # 轮换代理
    proxy = rotate_proxy()
    print(f"轮换代理: {proxy}")
    
    print()


def demo_authenticated_proxy_tools():
    """演示带认证代理工具的使用"""
    print("=== 带认证代理工具演示 ===\n")
    
    # 创建带认证的代理
    proxy_url = "http://username:password@proxy.example.com:8080"
    proxy = AuthenticatedProxy(proxy_url)
    
    print(f"代理URL: {proxy}")
    print(f"清洁URL: {proxy.clean_url}")
    print(f"用户名: {proxy.username}")
    print(f"密码: {proxy.password}")
    print(f"代理字典: {proxy.proxy_dict}")
    print(f"认证凭据: {proxy.get_auth_credentials()}")
    print(f"认证头: {proxy.get_auth_header()}")
    print(f"是否有效: {proxy.is_valid()}")
    
    # 创建代理配置
    proxy_config = create_proxy_config(proxy_url)
    print(f"\n代理配置: {proxy_config}")
    
    # 获取代理信息
    proxy_info = get_proxy_info(proxy_url)
    print(f"代理信息: {proxy_info}")
    
    print()


def demo_distributed_coordinator_tools():
    """演示分布式协调工具的使用"""
    print("=== 分布式协调工具演示 ===\n")
    
    # 生成任务ID
    url = "https://example.com/page/1"
    spider_name = "example_spider"
    task_id = generate_task_id(url, spider_name)
    print(f"生成任务ID: URL={url}, Spider={spider_name} -> {task_id}")
    
    # 获取集群信息
    cluster_info = get_cluster_info()
    print(f"集群信息: {cluster_info}")
    
    print()


if __name__ == '__main__':
    # 运行演示
    demo_date_tools()
    demo_data_cleaning_tools()
    demo_data_validation_tools()
    demo_request_handling_tools()
    demo_anti_crawler_tools()
    demo_authenticated_proxy_tools()
    demo_distributed_coordinator_tools()
    
    print("=== 在爬虫中使用工具包 ===\n")
    print("在爬虫项目中，您可以这样使用工具包:")
    print("""
from crawlo import Spider, Request
from crawlo.tools import (
    clean_text, 
    validate_email, 
    get_random_user_agent,
    build_url,
    AuthenticatedProxy
)

class ExampleSpider(Spider):
    def start_requests(self):
        headers = {"User-Agent": get_random_user_agent()}
        
        # 使用带认证的代理
        proxy_url = "http://username:password@proxy.example.com:8080"
        proxy = AuthenticatedProxy(proxy_url)
        
        request = Request("https://example.com", headers=headers)
        # 根据下载器类型设置代理
        downloader_type = self.crawler.settings.get("DOWNLOADER_TYPE", "aiohttp")
        if downloader_type == "aiohttp":
            request.proxy = proxy.clean_url
            auth = proxy.get_auth_credentials()
            if auth:
                request.meta["proxy_auth"] = auth
        else:
            request.proxy = proxy.proxy_dict
            
        yield request
    
    def parse(self, response):
        # 提取数据
        title = response.css('h1::text').get()
        email = response.css('.email::text').get()
        
        # 清洗和验证数据
        clean_title = clean_text(title) if title else None
        is_valid_email = validate_email(email) if email else False
        
        # 构建下一页URL
        next_page_url = build_url("https://example.com", "/page/2")
        
        # 处理数据...
    """)