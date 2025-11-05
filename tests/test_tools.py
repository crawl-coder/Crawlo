#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
工具包测试
"""
import asyncio
import unittest
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
    validate_chinese_id_card,
    validate_date,
    validate_number_range,
    
    # 请求处理工具
    build_url,
    add_query_params,
    merge_headers,
    
    # 反爬虫应对工具
    get_random_user_agent,
    rotate_proxy,
    
    # 分布式协调工具
    generate_task_id,
    get_cluster_info
)


class TestTools(unittest.TestCase):
    """工具包测试类"""

    def test_date_tools(self):
        """测试日期工具"""
        # 测试时间解析
        time_str = "2025-09-10 14:30:00"
        parsed_time = parse_time(time_str)
        self.assertIsNotNone(parsed_time)
        
        # 测试时间格式化
        formatted_time = format_time(parsed_time, "%Y-%m-%d")
        self.assertEqual(formatted_time, "2025-09-10")
        
        # 测试时间差计算
        time_str2 = "2025-09-11 14:30:00"
        parsed_time2 = parse_time(time_str2)
        diff = time_diff(parsed_time2, parsed_time)
        self.assertEqual(diff, 86400)  # 24小时 = 86400秒

    def test_data_cleaning_tools(self):
        """测试数据清洗工具"""
        # 测试文本清洗
        dirty_text = "<p>这是一个&nbsp;<b>测试</b>&amp;文本</p>"
        clean_result = clean_text(dirty_text)
        self.assertEqual(clean_result, "这是一个 测试&文本")
        
        # 测试货币格式化
        price = 1234.567
        formatted_price = format_currency(price, "¥", 2)
        self.assertEqual(formatted_price, "¥1,234.57")
        
        # 测试邮箱提取
        text_with_email = "联系邮箱: test@example.com, support@crawler.com"
        emails = extract_emails(text_with_email)
        self.assertIn("test@example.com", emails)
        self.assertIn("support@crawler.com", emails)

    def test_data_validation_tools(self):
        """测试数据验证工具"""
        # 测试邮箱验证
        self.assertTrue(validate_email("test@example.com"))
        self.assertFalse(validate_email("invalid-email"))
        
        # 测试URL验证
        self.assertTrue(validate_url("https://example.com"))
        self.assertFalse(validate_url("invalid-url"))
        
        # 测试电话验证
        self.assertTrue(validate_phone("13812345678"))
        self.assertFalse(validate_phone("12345"))
        
        # 测试身份证验证
        self.assertTrue(validate_chinese_id_card("110101199001011234"))
        self.assertFalse(validate_chinese_id_card("invalid-id"))
        
        # 测试日期验证
        self.assertTrue(validate_date("2025-09-10"))
        self.assertFalse(validate_date("invalid-date"))
        
        # 测试数值范围验证
        self.assertTrue(validate_number_range(50, 1, 100))
        self.assertFalse(validate_number_range(150, 1, 100))

    def test_request_handling_tools(self):
        """测试请求处理工具"""
        # 测试URL构建
        base_url = "https://api.example.com"
        path = "/v1/users"
        query_params = {"page": 1, "limit": 10}
        full_url = build_url(base_url, path, query_params)
        self.assertIn("https://api.example.com/v1/users", full_url)
        self.assertIn("page=1", full_url)
        self.assertIn("limit=10", full_url)
        
        # 测试添加查询参数
        existing_url = "https://api.example.com/v1/users?page=1"
        new_params = {"sort": "name"}
        updated_url = add_query_params(existing_url, new_params)
        self.assertIn("sort=name", updated_url)
        
        # 测试合并请求头
        base_headers = {"Content-Type": "application/json"}
        additional_headers = {"Authorization": "Bearer token123"}
        merged_headers = merge_headers(base_headers, additional_headers)
        self.assertEqual(merged_headers["Content-Type"], "application/json")
        self.assertEqual(merged_headers["Authorization"], "Bearer token123")

    def test_anti_crawler_tools(self):
        """测试反爬虫应对工具"""
        # 测试随机User-Agent
        user_agent = get_random_user_agent()
        self.assertIsInstance(user_agent, str)
        self.assertGreater(len(user_agent), 0)
        
        # 测试代理轮换
        proxy = rotate_proxy()
        self.assertIsInstance(proxy, dict)

    def test_distributed_coordinator_tools(self):
        """测试分布式协调工具"""
        # 测试任务ID生成
        task_id = generate_task_id("https://example.com", "test_spider")
        self.assertIsInstance(task_id, str)
        self.assertEqual(len(task_id), 32)  # MD5 hash长度
        
        # 测试集群信息获取（异步函数需要特殊处理）
        async def test_cluster_info():
            cluster_info = await get_cluster_info()
            self.assertIsInstance(cluster_info, dict)
            return cluster_info
            
        # 运行异步测试
        cluster_info = asyncio.run(test_cluster_info())
        self.assertIsInstance(cluster_info, dict)


if __name__ == '__main__':
    unittest.main()