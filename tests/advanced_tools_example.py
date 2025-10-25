#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Crawlo框架高级工具使用示例
"""
from crawlo.tools import (
    # 数据处理工具
    clean_text,
    format_currency,
    validate_email,
    validate_url,
    check_data_integrity,
    
    # 重试机制
    RetryMechanism,
    retry,
    exponential_backoff,
    
    # 反爬虫应对工具
    AntiCrawler,
    rotate_proxy,
    handle_captcha,
    detect_rate_limiting,
    
    # 分布式协调工具
    generate_pagination_tasks,
    distribute_tasks,
    DistributedCoordinator
)


def demo_data_processing_tools():
    """演示数据处理工具的使用"""
    print("=== 数据处理工具演示 ===\n")
    
    # 数据清洗
    dirty_text = "<p>这是一个&nbsp;<b>测试</b>&amp;文本</p>"
    clean_result = clean_text(dirty_text)
    print(f"清洗文本: {dirty_text} -> {clean_result}")
    
    # 数据格式化
    price = 1234.567
    formatted_price = format_currency(price, "¥", 2)
    print(f"格式化货币: {price} -> {formatted_price}")
    
    # 字段验证
    email = "test@example.com"
    is_valid_email = validate_email(email)
    print(f"验证邮箱: {email} -> {'有效' if is_valid_email else '无效'}")
    
    url = "https://example.com"
    is_valid_url = validate_url(url)
    print(f"验证URL: {url} -> {'有效' if is_valid_url else '无效'}")
    
    # 数据完整性检查
    data = {
        "name": "张三",
        "email": "test@example.com",
        "phone": "13812345678"
    }
    required_fields = ["name", "email", "phone", "address"]
    integrity_result = check_data_integrity(data, required_fields)
    print(f"数据完整性检查: {integrity_result}")
    
    print()


def demo_retry_mechanism():
    """演示重试机制的使用"""
    print("=== 重试机制演示 ===\n")
    
    # 指数退避
    for attempt in range(5):
        delay = exponential_backoff(attempt)
        print(f"重试次数 {attempt}: 延迟 {delay:.2f} 秒")
    
    # 重试装饰器示例
    @retry(max_retries=3)
    def unreliable_function():
        import random
        if random.random() < 0.7:  # 70%概率失败
            raise ConnectionError("网络连接失败")
        return "成功执行"
    
    try:
        result = unreliable_function()
        print(f"函数执行结果: {result}")
    except Exception as e:
        print(f"函数执行失败: {e}")
    
    print()


def demo_anti_crawler_tools():
    """演示反爬虫应对工具的使用"""
    print("=== 反爬虫应对工具演示 ===\n")
    
    # 反爬虫工具
    anti_crawler = AntiCrawler()
    
    # 获取随机User-Agent
    user_agent = anti_crawler.get_random_user_agent()
    print(f"随机User-Agent: {user_agent[:50]}...")
    
    # 轮换代理
    proxy = anti_crawler.rotate_proxy()
    print(f"轮换代理: {proxy}")
    
    # 检测验证码
    response_with_captcha = "请输入验证码进行验证"
    has_captcha = anti_crawler.handle_captcha(response_with_captcha)
    print(f"检测验证码: {response_with_captcha} -> {'需要验证码' if has_captcha else '无需验证码'}")
    
    # 检测频率限制
    status_code = 429  # Too Many Requests
    response_headers = {"Retry-After": "60"}
    is_rate_limited = anti_crawler.detect_rate_limiting(status_code, response_headers)
    print(f"检测频率限制: 状态码{status_code} -> {'被限制' if is_rate_limited else '未限制'}")
    
    print()


def demo_distributed_coordinator_tools():
    """演示分布式协调工具的使用"""
    print("=== 分布式协调工具演示 ===\n")
    
    # 生成分页任务
    base_url = "https://example.com/products"
    pagination_tasks = generate_pagination_tasks(base_url, 1, 5)
    print(f"生成分页任务 ({len(pagination_tasks)} 个):")
    for i, task in enumerate(pagination_tasks[:3]):  # 只显示前3个
        print(f"  {i+1}. {task}")
    if len(pagination_tasks) > 3:
        print(f"  ... 还有 {len(pagination_tasks) - 3} 个任务")
    
    # 任务分发
    tasks = list(range(1, 21))  # 20个任务
    distributed = distribute_tasks(tasks, 4)  # 分发给4个工作节点
    print(f"\n任务分发 (20个任务分发给4个工作节点):")
    for i, worker_tasks in enumerate(distributed):
        print(f"  工作节点 {i+1}: {len(worker_tasks)} 个任务 -> {worker_tasks}")
    
    # 分布式协调器
    coordinator = DistributedCoordinator()
    cluster_info = coordinator.get_cluster_info()
    print(f"\n集群信息: {cluster_info}")
    
    print()


def demo_in_spider():
    """演示在爬虫中使用高级工具"""
    print("=== 在爬虫中使用高级工具 ===\n")
    print("在爬虫项目中，您可以这样使用高级工具:")
    print("""
import asyncio
from crawlo import Spider, Request
from crawlo.tools import (
    clean_text,
    validate_email,
    AntiCrawler,
    DistributedCoordinator,
    retry
)

class AdvancedSpider(Spider):
    def __init__(self):
        super().__init__()
        self.anti_crawler = AntiCrawler()
        self.coordinator = DistributedCoordinator()
    
    def start_requests(self):
        # 生成分页任务
        base_url = "https://api.example.com/products"
        pagination_tasks = self.coordinator.generate_pagination_tasks(base_url, 1, 100)
        
        for url in pagination_tasks:
            # 直接使用带认证的代理URL（框架原生支持）
            request = Request(
                url, 
                callback=self.parse,
                proxy="http://user:pass@proxy.example.com:8080"  # 所有下载器都支持
            )
            yield request
    
    @retry(max_retries=3)
    async def parse(self, response):
        # 检查是否遇到验证码
        if self.anti_crawler.handle_captcha(response.text):
            # 处理验证码逻辑
            print("遇到验证码，需要处理")
            return
            
        # 提取数据
        products = response.css('.product-item')
        for product in products:
            name = product.css('.product-name::text').get()
            email = product.css('.contact-email::text').get()
            
            # 数据清洗和验证
            clean_name = clean_text(name) if name else None
            is_valid_email = validate_email(email) if email else False
            
            # 检查数据是否重复
            if not await self.coordinator.is_duplicate({"name": clean_name}):
                await self.coordinator.add_to_dedup({"name": clean_name})
                # 处理产品数据...
                pass
    """)


if __name__ == '__main__':
    # 运行演示
    demo_data_processing_tools()
    demo_retry_mechanism()
    demo_anti_crawler_tools()
    demo_distributed_coordinator_tools()
    demo_in_spider()