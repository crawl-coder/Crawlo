#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
高级工具测试
"""
import unittest
from crawlo.tools import (
    # 数据处理工具
    clean_text,
    format_currency,
    validate_email,
    validate_url,
    check_data_integrity,
    
    # 重试机制
    RetryMechanism,
    should_retry,
    exponential_backoff,
    
    # 反爬虫应对工具
    AntiCrawler,
    rotate_proxy,
    handle_captcha,
    detect_rate_limiting,
    
    # 分布式协调工具
    generate_pagination_tasks,
    distribute_tasks,
    DistributedCoordinator,
    TaskDistributor,
    DeduplicationTool
)


class TestAdvancedTools(unittest.TestCase):
    """高级工具测试类"""

    def test_data_processing_tools(self):
        """测试数据处理工具"""
        # 测试数据清洗
        dirty_text = "<p>这是一个&nbsp;<b>测试</b>&amp;文本</p>"
        clean_result = clean_text(dirty_text)
        self.assertEqual(clean_result, "这是一个 测试&文本")
        
        # 测试数据格式化
        price = 1234.567
        formatted_price = format_currency(price, "¥", 2)
        self.assertEqual(formatted_price, "¥1,234.57")
        
        # 测试字段验证
        self.assertTrue(validate_email("test@example.com"))
        self.assertFalse(validate_email("invalid-email"))
        
        self.assertTrue(validate_url("https://example.com"))
        self.assertFalse(validate_url("invalid-url"))
        
        # 测试数据完整性检查
        data = {
            "name": "张三",
            "email": "test@example.com",
            "phone": "13812345678"
        }
        required_fields = ["name", "email", "phone"]
        integrity_result = check_data_integrity(data, required_fields)
        self.assertTrue(integrity_result["is_valid"])

    def test_retry_mechanism(self):
        """测试重试机制"""
        # 测试指数退避
        delay = exponential_backoff(0)
        self.assertGreater(delay, 0)
        
        # 测试是否应该重试
        self.assertTrue(should_retry(status_code=500))
        self.assertTrue(should_retry(exception=ConnectionError()))
        self.assertFalse(should_retry(status_code=200))

    def test_anti_crawler_tools(self):
        """测试反爬虫应对工具"""
        # 测试反爬虫工具
        anti_crawler = AntiCrawler()
        
        # 测试随机User-Agent
        user_agent = anti_crawler.get_random_user_agent()
        self.assertIsInstance(user_agent, str)
        self.assertGreater(len(user_agent), 0)
        
        # 测试代理轮换
        proxy = anti_crawler.rotate_proxy()
        self.assertIsInstance(proxy, dict)
        
        # 测试验证码检测
        self.assertTrue(anti_crawler.handle_captcha("请输入验证码进行验证"))
        self.assertFalse(anti_crawler.handle_captcha("正常页面内容"))
        
        # 测试频率限制检测
        self.assertTrue(anti_crawler.detect_rate_limiting(429, {}))
        self.assertFalse(anti_crawler.detect_rate_limiting(200, {}))

    def test_distributed_coordinator_tools(self):
        """测试分布式协调工具"""
        # 测试任务分发器
        distributor = TaskDistributor()
        
        # 测试分页任务生成
        base_url = "https://example.com/products"
        pagination_tasks = distributor.generate_pagination_tasks(base_url, 1, 5)
        self.assertEqual(len(pagination_tasks), 5)
        
        # 测试任务分发
        tasks = list(range(1, 21))  # 20个任务
        distributed = distributor.distribute_tasks(tasks, 4)  # 分发给4个工作节点
        self.assertEqual(len(distributed), 4)
        self.assertEqual(sum(len(worker_tasks) for worker_tasks in distributed), 20)
        
        # 测试去重工具
        dedup_tool = DeduplicationTool()
        
        # 测试数据指纹生成
        fingerprint1 = dedup_tool.generate_fingerprint({"name": "test", "value": 123})
        fingerprint2 = dedup_tool.generate_fingerprint({"name": "test", "value": 123})
        self.assertEqual(fingerprint1, fingerprint2)
        
        # 测试去重功能
        self.assertFalse(dedup_tool.is_duplicate({"name": "test", "value": 123}))
        self.assertTrue(dedup_tool.add_to_dedup({"name": "test", "value": 123}))
        self.assertTrue(dedup_tool.is_duplicate({"name": "test", "value": 123}))
        self.assertFalse(dedup_tool.add_to_dedup({"name": "test", "value": 123}))
        
        # 测试分布式协调器
        coordinator = DistributedCoordinator()
        
        # 测试任务ID生成
        task_id = coordinator.generate_task_id("https://example.com", "test_spider")
        self.assertIsInstance(task_id, str)
        self.assertEqual(len(task_id), 32)  # MD5 hash长度
        
        # 测试分页任务生成
        pagination_tasks = coordinator.generate_pagination_tasks("https://example.com/products", 1, 5)
        self.assertEqual(len(pagination_tasks), 5)
        
        # 测试任务分发
        tasks = list(range(1, 21))  # 20个任务
        distributed = coordinator.distribute_tasks(tasks, 4)  # 分发给4个工作节点
        self.assertEqual(len(distributed), 4)


if __name__ == '__main__':
    unittest.main()