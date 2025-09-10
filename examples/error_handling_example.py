#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
错误处理使用示例
展示如何在实际项目中使用增强版错误处理工具
"""
import sys
import os
import asyncio
import time
from typing import Optional

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.utils.enhanced_error_handler import (
    EnhancedErrorHandler, 
    ErrorContext, 
    DetailedException, 
    handle_exception
)


# 创建错误处理器实例
error_handler = EnhancedErrorHandler("example_module")


class DatabaseConnectionError(DetailedException):
    """数据库连接错误"""
    pass


class NetworkTimeoutError(DetailedException):
    """网络超时错误"""
    pass


@handle_exception(context="数据库连接", module="database", function="connect_to_db", error_code="DB001")
def connect_to_db(host: str, port: int) -> bool:
    """模拟数据库连接"""
    print(f"正在连接数据库 {host}:{port}...")
    
    # 模拟连接失败
    if host == "invalid.host":
        raise DatabaseConnectionError(
            "无法连接到数据库服务器",
            context=ErrorContext(context="数据库连接失败", module="database", function="connect_to_db"),
            error_code="DB001",
            host=host,
            port=port
        )
    
    # 模拟连接成功
    print("✅ 数据库连接成功")
    return True


@error_handler.retry_on_failure(max_retries=3, delay=0.5, backoff_factor=2.0)
async def fetch_data_from_api(url: str) -> dict:
    """模拟从API获取数据（带重试机制）"""
    print(f"正在从 {url} 获取数据...")
    
    # 模拟网络问题
    if url == "https://slow.api.com/data":
        time.sleep(2)  # 模拟慢速响应
        raise NetworkTimeoutError(
            "API响应超时",
            context=ErrorContext(context="API调用超时", module="api", function="fetch_data_from_api"),
            error_code="API001",
            url=url,
            timeout=1
        )
    
    if url == "https://error.api.com/data":
        raise NetworkTimeoutError(
            "API服务器错误",
            context=ErrorContext(context="API服务器错误", module="api", function="fetch_data_from_api"),
            error_code="API002",
            url=url,
            status_code=500
        )
    
    # 模拟成功响应
    print("✅ API数据获取成功")
    return {"data": "sample data", "status": "success"}


def process_data(data: dict) -> Optional[str]:
    """处理数据"""
    try:
        print("正在处理数据...")
        
        # 模拟处理错误
        if not data:
            raise ValueError("数据为空")
        
        if "error" in data:
            raise RuntimeError(f"数据处理失败: {data['error']}")
        
        # 模拟处理成功
        result = f"处理完成: {data.get('data', 'no data')}"
        print(f"✅ {result}")
        return result
        
    except Exception as e:
        # 使用错误处理器处理异常
        context = ErrorContext(context="数据处理", module="data_processor", function="process_data")
        error_handler.handle_error(e, context=context, raise_error=False)
        return None


async def main():
    """主函数"""
    print("🚀 错误处理使用示例")
    print("=" * 50)
    
    # 1. 测试数据库连接（成功情况）
    print("1. 测试数据库连接（成功情况）")
    try:
        connect_to_db("localhost", 5432)
    except Exception as e:
        print(f"❌ 意外错误: {e}")
    print()
    
    # 2. 测试数据库连接（失败情况）
    print("2. 测试数据库连接（失败情况）")
    try:
        connect_to_db("invalid.host", 5432)
    except Exception as e:
        print(f"❌ 预期的数据库连接错误: {e}")
    print()
    
    # 3. 测试API调用（成功情况）
    print("3. 测试API调用（成功情况）")
    try:
        data = await fetch_data_from_api("https://api.com/data")
        process_data(data)
    except Exception as e:
        print(f"❌ API调用错误: {e}")
    print()
    
    # 4. 测试API调用（失败情况，带重试）
    print("4. 测试API调用（失败情况，带重试）")
    try:
        data = await fetch_data_from_api("https://error.api.com/data")
        process_data(data)
    except Exception as e:
        print(f"❌ API调用错误（重试后仍然失败）: {e}")
    print()
    
    # 5. 测试数据处理（失败情况）
    print("5. 测试数据处理（失败情况）")
    process_data(None)  # 空数据
    process_data({"error": "invalid format"})  # 错误数据
    print()
    
    # 6. 查看错误历史
    print("6. 错误历史记录")
    history = error_handler.get_error_history()
    print(f"共记录 {len(history)} 个错误:")
    for i, record in enumerate(history, 1):
        print(f"  {i}. {record['exception_type']}: {record['message']}")
        if record['context']:
            print(f"     上下文: {record['context']}")
    print()
    
    print("=" * 50)
    print("🎉 示例运行完成")


if __name__ == "__main__":
    asyncio.run(main())