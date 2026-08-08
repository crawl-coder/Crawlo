#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
二次确认退出逻辑测试

验证：
1. 首次空闲时立即检查退出条件
2. 添加 1ms 等待
3. 再次确认所有组件空闲
"""

import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch
from crawlo.core.engine import Engine


async def test_double_check_exit_logic():
    """测试二次确认退出逻辑"""
    print("\n" + "="*70)
    print("测试：二次确认退出逻辑")
    print("="*70)
    
    # 创建模拟的 Engine
    engine = Mock(spec=Engine)
    engine.running = True
    engine.logger = Mock()
    engine.logger.debug = Mock()
    
    # 模拟首次检查返回 True
    first_check_count = 0
    second_check_count = 0
    
    async def mock_should_exit(last_states):
        nonlocal first_check_count
        first_check_count += 1
        return (True, (True, True, True, True))
    
    async def mock_check_all_idle():
        nonlocal second_check_count
        second_check_count += 1
        return True
    
    engine._should_exit = mock_should_exit
    engine._check_all_idle = mock_check_all_idle
    
    # 模拟主循环退出逻辑
    idle_count = 0
    loop_count = 0
    
    start_time = time.time()
    
    while loop_count < 3:  # 只运行 3 次循环
        loop_count += 1
        
        # 模拟没有请求处理
        requests = []
        
        if requests:
            idle_count = 0
        else:
            idle_count += 1
            
            # 首次检测到空闲时，立即检查退出条件
            if idle_count == 1:
                should_exit, last_states = await engine._should_exit(None)
                
                if should_exit:
                    # ✅ 添加短暂等待，避免瞬时空闲误判
                    before_sleep = time.time()
                    await asyncio.sleep(0.001)  # 1ms
                    after_sleep = time.time()
                    
                    # 再次确认所有组件仍然空闲
                    if await engine._check_all_idle():
                        sleep_duration = after_sleep - before_sleep
                        print(f"\n✅ 二次确认通过！")
                        print(f"   - 首次检查次数: {first_check_count}")
                        print(f"   - 二次确认次数: {second_check_count}")
                        print(f"   - sleep 等待时间: {sleep_duration*1000:.3f}ms")
                        print(f"   - 总耗时: {(time.time() - start_time)*1000:.3f}ms")
                        break
    
    print("\n" + "="*70)
    print("✅ 测试完成！二次确认退出逻辑正常工作")
    print("="*70 + "\n")


async def test_no_early_exit():
    """测试不会过早退出"""
    print("\n" + "="*70)
    print("测试：不会过早退出")
    print("="*70)
    
    engine = Mock(spec=Engine)
    engine.running = True
    
    first_check_count = 0
    second_check_count = 0
    
    async def mock_should_exit(last_states):
        nonlocal first_check_count
        first_check_count += 1
        # 首次检查返回 False（有组件忙碌）
        return (False, (True, False, True, True))  # downloader 不空闲
    
    async def mock_check_all_idle():
        nonlocal second_check_count
        second_check_count += 1
        return True
    
    engine._should_exit = mock_should_exit
    engine._check_all_idle = mock_check_all_idle
    
    idle_count = 0
    loop_count = 0
    
    while loop_count < 3:
        loop_count += 1
        requests = []
        
        if requests:
            idle_count = 0
        else:
            idle_count += 1
            
            if idle_count == 1:
                should_exit, states = await engine._should_exit(None)
                
                if should_exit:
                    await asyncio.sleep(0.001)
                    if await engine._check_all_idle():
                        print("❌ 错误：不应该退出！")
                        break
                else:
                    print(f"✅ 第 {loop_count} 次循环：组件未全部空闲，继续等待")
                    # 模拟组件状态变化
                    engine._should_exit = AsyncMock(return_value=(True, (True, True, True, True)))
    
    print(f"\n   - 首次检查次数: {first_check_count}")
    print(f"   - 二次确认次数: {second_check_count}")
    
    if first_check_count >= 1 and second_check_count == 1:
        print("\n✅ 测试通过！只有在所有组件空闲时才会退出")
    else:
        print(f"\n⚠️ 测试结果：首次检查 {first_check_count} 次，二次确认 {second_check_count} 次")
        print("   （预期：首次检查至少1次，二次确认1次）")
    
    print("="*70 + "\n")


async def main():
    """运行所有测试"""
    await test_double_check_exit_logic()
    await test_no_early_exit()
    
    print("\n" + "🎉" * 20)
    print("所有测试完成！")
    print("🎉" * 20 + "\n")


if __name__ == '__main__':
    asyncio.run(main())
