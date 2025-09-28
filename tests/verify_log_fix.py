#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
验证日志级别修复效果
创建一个简化的测试来验证控制台和日志文件级别的一致性
"""
import sys
import os
import tempfile

# 添加项目根目录到Python路径
sys.path.insert(0, '/')

from crawlo.utils.log import LoggerManager, get_logger


def main():
    """验证日志级别修复效果"""
    print("🔧 验证日志级别修复效果")
    print("=" * 50)
    
    # 创建临时日志文件
    temp_log = tempfile.NamedTemporaryFile(mode='w+', suffix='.log', delete=False)
    temp_log_path = temp_log.name
    temp_log.close()
    
    try:
        # 重置LoggerManager状态
        LoggerManager.reset()
        
        # 使用INFO级别配置
        LoggerManager.configure(
            LOG_LEVEL='INFO',
            LOG_FILE=temp_log_path,
            LOG_FORMAT='%(asctime)s - [%(name)s] - %(levelname)s: %(message)s'
        )
        
        print(f"✅ 配置完成:")
        print(f"   默认级别: {LoggerManager._default_level}")
        print(f"   控制台级别: {LoggerManager._default_console_level}")
        print(f"   文件级别: {LoggerManager._default_file_level}")
        print(f"   日志文件: {temp_log_path}")
        
        # 创建测试logger
        test_logger = get_logger('crawlo.test')
        
        # 检查handler配置
        print(f"\n📋 Handler配置:")
        for i, handler in enumerate(test_logger.handlers):
            handler_type = type(handler).__name__
            handler_level = handler.level
            print(f"   Handler {i} ({handler_type}): 级别 {handler_level}")
        
        # 测试日志输出
        print(f"\n📝 测试日志输出（控制台）:")
        test_logger.debug("这是DEBUG级别日志 - 不应该显示")
        test_logger.info("这是INFO级别日志 - 应该显示")
        test_logger.warning("这是WARNING级别日志 - 应该显示")
        test_logger.error("这是ERROR级别日志 - 应该显示")
        
        # 检查日志文件内容
        print(f"\n📄 检查日志文件内容:")
        with open(temp_log_path, 'r', encoding='utf-8') as f:
            log_content = f.read()
            if log_content:
                print("日志文件内容:")
                print(log_content)
            else:
                print("❌ 日志文件为空")
        
        # 分析结果
        lines = log_content.strip().split('\n') if log_content.strip() else []
        debug_lines = [line for line in lines if '- DEBUG:' in line]
        info_lines = [line for line in lines if '- INFO:' in line]
        warning_lines = [line for line in lines if '- WARNING:' in line]
        error_lines = [line for line in lines if '- ERROR:' in line]
        
        print(f"\n📊 分析结果:")
        print(f"   DEBUG级别日志: {len(debug_lines)}条 {'✅ 正确' if len(debug_lines) == 0 else '❌ 错误'}")
        print(f"   INFO级别日志: {len(info_lines)}条 {'✅ 正确' if len(info_lines) >= 1 else '❌ 错误'}")
        print(f"   WARNING级别日志: {len(warning_lines)}条 {'✅ 正确' if len(warning_lines) >= 1 else '❌ 错误'}")
        print(f"   ERROR级别日志: {len(error_lines)}条 {'✅ 正确' if len(error_lines) >= 1 else '❌ 错误'}")
        
        # 判断修复是否成功
        success = (len(debug_lines) == 0 and len(info_lines) >= 1 and 
                  len(warning_lines) >= 1 and len(error_lines) >= 1)
        
        print(f"\n🎯 修复结果: {'✅ 成功' if success else '❌ 失败'}")
        
        if success:
            print("📋 控制台和日志文件现在使用相同的INFO级别")
            print("🎉 日志级别一致性问题已解决")
        else:
            print("❌ 仍存在日志级别不一致问题，需要进一步调试")
            
    except Exception as e:
        print(f"❌ 验证过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        # 清理临时文件
        try:
            os.unlink(temp_log_path)
        except:
            pass
            
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())