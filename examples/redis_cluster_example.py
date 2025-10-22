#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Redis集群配置示例
演示如何在Crawlo框架中配置和使用Redis集群
"""
import os
import sys

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crawlo.config import CrawloConfig


def example_single_instance():
    """单实例Redis配置示例"""
    print("=== 单实例Redis配置示例 ===")
    
    # 方式1：通过配置文件配置
    config = CrawloConfig.distributed(
        project_name='single_instance_example',
        redis_host='127.0.0.1',
        redis_port=6379,
        redis_password='',
        redis_db=0,
        concurrency=8,
        download_delay=1.0
    )
    
    print("配置参数:")
    print(f"  项目名称: {config.get('PROJECT_NAME')}")
    print(f"  Redis URL: {config.get('REDIS_URL')}")
    print(f"  队列类型: {config.get('QUEUE_TYPE')}")
    print(f"  过滤器类: {config.get('FILTER_CLASS')}")
    print(f"  并发数: {config.get('CONCURRENCY')}")
    print()


def example_cluster_mode():
    """Redis集群配置示例"""
    print("=== Redis集群配置示例 ===")
    
    # 方式1：使用逗号分隔的节点列表
    config1 = CrawloConfig.distributed(
        project_name='cluster_example_1',
        redis_host='192.168.1.100:7000,192.168.1.101:7000,192.168.1.102:7000',
        redis_password='cluster_password',
        concurrency=16,
        download_delay=0.5
    )
    
    print("方式1 - 节点列表配置:")
    print(f"  项目名称: {config1.get('PROJECT_NAME')}")
    print(f"  Redis主机: {config1.get('REDIS_HOST')}")
    print(f"  Redis URL: {config1.get('REDIS_URL')}")
    print(f"  队列类型: {config1.get('QUEUE_TYPE')}")
    print(f"  过滤器类: {config1.get('FILTER_CLASS')}")
    print()
    
    # 方式2：使用集群URL格式
    config2 = CrawloConfig.distributed(
        project_name='cluster_example_2',
        redis_host='redis-cluster://192.168.1.100:7000,192.168.1.101:7000,192.168.1.102:7000',
        redis_password='cluster_password',
        concurrency=32,
        download_delay=0.25
    )
    
    print("方式2 - 集群URL配置:")
    print(f"  项目名称: {config2.get('PROJECT_NAME')}")
    print(f"  Redis主机: {config2.get('REDIS_HOST')}")
    print(f"  Redis URL: {config2.get('REDIS_URL')}")
    print(f"  队列类型: {config2.get('QUEUE_TYPE')}")
    print(f"  过滤器类: {config2.get('FILTER_CLASS')}")
    print()


def example_cli_usage():
    """CLI使用示例"""
    print("=== CLI使用示例 ===")
    
    print("通过命令行参数运行爬虫:")
    print("  crawlo run myspider --config settings.py")
    print()
    print("在settings.py中配置Redis集群:")
    print("  config = CrawloConfig.distributed(")
    print("      project_name='my_project',")
    print("      redis_host='192.168.1.100:7000,192.168.1.101:7000,192.168.1.102:7000',")
    print("      redis_password='your_password',")
    print("      concurrency=16,")
    print("      download_delay=1.0")
    print("  )")
    print()


def main():
    """主函数"""
    print("Crawlo框架Redis集群配置示例")
    print("=" * 50)
    
    # 演示各种配置方式
    example_single_instance()
    example_cluster_mode()
    example_cli_usage()
    
    print("所有配置示例演示完成！")
    print("\n详细使用说明请参考: REDIS_CLUSTER_USAGE.md")


if __name__ == "__main__":
    main()