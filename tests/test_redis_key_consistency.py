#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试Redis key一致性
验证所有Redis key都正确包含spider_name
"""
import asyncio
import sys
import os
import redis

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def test_redis_key_consistency():
    """测试Redis key一致性"""
    print("测试Redis key一致性...")
    print("=" * 50)
    
    try:
        # 创建Redis连接
        redis_client = redis.Redis(
            host='127.0.0.1',
            port=6379,
            db=0,
            decode_responses=True
        )
        
        # 测试连接
        redis_client.ping()
        print("✅ Redis连接成功")
        
        # 获取所有key
        all_keys_result = redis_client.keys('crawlo:*')
        all_keys = []
        for key in all_keys_result:
            all_keys.append(key)
        print(f"\n找到 {len(all_keys)} 个 crawlo 相关的key:")
        
        # 检查每个key是否包含spider_name
        expected_project = "ofweek_standalone"
        expected_spider = "of_week"
        expected_prefix = f"crawlo:{expected_project}:{expected_spider}"
        
        print(f"\n期望的前缀: {expected_prefix}")
        
        all_keys_correct = True
        for key in sorted(all_keys):
            print(f"  {key}")
            if not key.startswith(expected_prefix):
                print(f"    ❌ 错误: key不包含期望的前缀")
                all_keys_correct = False
            else:
                print(f"    ✅ 正确: key包含期望的前缀")
        
        if all_keys_correct:
            print(f"\n✅ 所有Redis key都正确包含spider_name!")
        else:
            print(f"\n❌ 发现不正确的Redis key!")
            return False
            
        # 验证key的结构
        print(f"\n验证key结构...")
        required_components = ['queue', 'filter', 'item']
        component_keys = {}
        
        for key in all_keys:
            parts = key.split(':')
            if len(parts) >= 4:
                component = parts[3]  # 第4个部分是组件类型
                if component in required_components:
                    if component not in component_keys:
                        component_keys[component] = []
                    component_keys[component].append(key)
        
        # 检查每个组件类型是否都有对应的key
        for component in required_components:
            if component in component_keys:
                print(f"  {component}: {len(component_keys[component])} 个key")
                for key in component_keys[component]:
                    print(f"    {key}")
            else:
                print(f"  {component}: 缺少对应的key ❌")
                all_keys_correct = False
        
        if all_keys_correct:
            print(f"\n🎉 Redis key一致性测试通过!")
            return True
        else:
            print(f"\n💥 Redis key一致性测试失败!")
            return False
        
    except Exception as e:
        print(f"❌ 测试过程中出错: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_redis_key_consistency()
    sys.exit(0 if success else 1)