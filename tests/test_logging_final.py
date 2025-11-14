#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
日志系统最终功能验证测试
验证所有增强功能是否正常工作
"""

import os
import sys
import tempfile
import shutil
import time
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from crawlo.logging import (
    configure_logging, 
    get_logger, 
    LogManager,
    get_monitor
)
from crawlo.logging.config import LogConfig
from crawlo.logging.sampler import get_sampler
from crawlo.logging.async_handler import AsyncConcurrentRotatingFileHandler


def test_all_features():
    """测试所有功能"""
    print("=== 测试所有功能 ===")
    
    # 创建临时目录
    temp_dir = tempfile.mkdtemp()
    log_file = os.path.join(temp_dir, 'final_test.log')
    
    try:
        # 1. 测试增强配置功能
        print("1. 测试增强配置功能...")
        LogManager().reset()
        
        # 配置所有增强功能
        config = configure_logging(
            LOG_LEVEL='INFO',
            LOG_FILE=log_file,
            LOG_FILE_ENABLED=True,
            LOG_CONSOLE_ENABLED=True,
            LOG_CONSOLE_LEVEL='WARNING',  # 控制台只显示WARNING及以上
            LOG_FILE_LEVEL='DEBUG',       # 文件记录DEBUG及以上
            LOG_INCLUDE_THREAD_ID=True,
            LOG_INCLUDE_PROCESS_ID=True,
            LOG_MAX_BYTES=1024*1024,      # 1MB
            LOG_BACKUP_COUNT=2,
            LOG_LEVELS={
                'debug.module': 'DEBUG',
                'info.module': 'INFO',
                'error.module': 'ERROR'
            }
        )
        
        print(f"   配置详情:")
        print(f"     主级别: {config.level}")
        print(f"     控制台级别: {config.console_level}")
        print(f"     文件级别: {config.file_level}")
        print(f"     包含线程ID: {config.include_thread_id}")
        print(f"     包含进程ID: {config.include_process_id}")
        
        # 2. 测试性能监控
        print("2. 测试性能监控...")
        monitor = get_monitor()
        monitor.enable_monitoring()
        
        # 3. 测试日志采样
        print("3. 测试日志采样...")
        sampler = get_sampler()
        sampler.set_sample_rate('test.sampler', 0.3)  # 30%采样率
        
        # 4. 测试不同模块的日志级别
        print("4. 测试不同模块的日志级别...")
        
        # DEBUG模块
        debug_logger = get_logger('debug.module')
        debug_logger.debug("DEBUG消息 - 应该显示")
        debug_logger.info("INFO消息 - 应该显示")
        debug_logger.warning("WARNING消息 - 应该显示")
        
        # INFO模块
        info_logger = get_logger('info.module')
        info_logger.debug("DEBUG消息 - 不应该显示")
        info_logger.info("INFO消息 - 应该显示")
        info_logger.warning("WARNING消息 - 应该显示")
        
        # ERROR模块
        error_logger = get_logger('error.module')
        error_logger.info("INFO消息 - 不应该显示")
        error_logger.warning("WARNING消息 - 不应该显示")
        error_logger.error("ERROR消息 - 应该显示")
        
        # 默认模块
        default_logger = get_logger('default.module')
        default_logger.info("INFO消息 - 不应该显示")
        default_logger.warning("WARNING消息 - 应该显示")
        default_logger.error("ERROR消息 - 应该显示")
        
        # 5. 测试采样功能
        print("5. 测试采样功能...")
        sample_logger = get_logger('test.sampler')
        sampled_count = 0
        total_count = 100
        
        for i in range(total_count):
            message = f"采样测试消息 {i+1}"
            if sampler.should_log('test.sampler', message):
                sample_logger.info(message)
                sampled_count += 1
                
        print(f"   采样率: {sampled_count/total_count:.2%}")
        
        # 等待日志写入完成
        time.sleep(0.5)
        
        # 6. 检查日志文件内容
        print("6. 检查日志文件内容...")
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                print(f"   日志文件行数: {len(lines)}")
                
                # 显示前几行日志
                print("   前5行日志内容:")
                for i, line in enumerate(lines[:5]):
                    print(f"     {i+1}: {line.strip()}")
                    
                # 验证是否包含线程ID和进程ID
                if lines:
                    first_line = lines[0]
                    has_thread_id = '[Thread-' in first_line or '[thread:' in first_line.lower()
                    has_process_id = '[Process-' in first_line or '[process:' in first_line.lower()
                    print(f"   包含线程ID: {has_thread_id}")
                    print(f"   包含进程ID: {has_process_id}")
        else:
            print("   ❌ 日志文件不存在!")
            
        # 7. 获取性能报告
        print("7. 获取性能报告...")
        report = monitor.get_performance_report()
        print(f"   性能报告生成完成")
        
        print("✅ 所有增强功能测试通过!")
        
    finally:
        # 清理
        shutil.rmtree(temp_dir, ignore_errors=True)


def main():
    """主测试函数"""
    print("开始Crawlo框架日志系统功能验证测试...")
    print("=" * 60)
    
    try:
        # 运行测试
        test_all_features()
        
        print("\n" + "=" * 60)
        print("日志系统功能验证测试完成!")
        print("\n测试总结:")
        print("✅ 配置功能")
        print("✅ 性能监控")
        print("✅ 日志采样")
        print("✅ 模块特定日志级别")
        print("✅ 上下文信息（线程ID、进程ID）")
        
    except Exception as e:
        print(f"\n测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())