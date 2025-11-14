#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
# -*- coding: utf-8 -*-
import asyncio
from asyncmy import create_pool

async def test_asyncmy_usage():
    """测试asyncmy库的正确使用方式"""
    try:
        # 创建连接池
        pool = await create_pool(
            host='127.0.0.1',
            port=3306,
            user='root',
            password='123456',
            db='test',
            minsize=1,
            maxsize=5
        )
        
        # 获取连接
        conn = await pool.acquire()
        try:
            # 获取游标
            cursor = await conn.cursor()
            try:
                # 执行SQL
                result = cursor.execute("SELECT 1")
                print(f"execute返回类型: {type(result)}")
                print(f"execute返回值: {result}")
                
                # 检查是否需要await
                if hasattr(result, '__await__'):
                    print("execute返回的是协程对象，需要await")
                    result = await result
                else:
                    print("execute返回的不是协程对象，不需要await")
                    
                # 提交事务
                await conn.commit()
                
            finally:
                await cursor.close()
        finally:
            pool.release(conn)
            
        # 关闭连接池
        pool.close()
        await pool.wait_closed()
        
        print("测试完成")
        
    except Exception as e:
        print(f"测试出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_asyncmy_usage())