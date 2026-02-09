#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Crawlo 机器人框架使用示例
===================================

演示如何在 Crawlo 项目中集成和使用机器人框架。
"""

from crawlo.bot.models import BotMessage, ChatType, Platform
from crawlo.bot.dispatcher import get_dispatcher
from crawlo.bot.commands.base import BotCommand
from crawlo.bot.models import BotResponse
from typing import List


class StockAnalysisCommand(BotCommand):
    """
    股票分析命令示例
    
    这是一个模拟的股票分析命令，展示了如何创建自定义命令。
    """
    
    @property
    def name(self) -> str:
        return "stock"
    
    @property
    def aliases(self) -> List[str]:
        return ["analyze", "股票", "分析"]
    
    @property
    def description(self) -> str:
        return "分析指定股票"
    
    @property
    def usage(self) -> str:
        return "/stock <股票代码>"
    
    def validate_args(self, args: List[str]) -> str:
        """验证股票代码参数"""
        if not args:
            return "请输入股票代码"
        
        code = args[0].upper()
        # 简单验证：股票代码应为2-6位字母或数字
        if not (2 <= len(code) <= 6 and code.isalnum()):
            return f"无效的股票代码: {code}"
        
        return None
    
    def execute(self, message: BotMessage, args: List[str]) -> BotResponse:
        """执行股票分析命令"""
        stock_code = args[0].upper()
        
        # 模拟股票分析
        analysis_result = f"""
📊 **股票分析结果**

• 股票代码: `{stock_code}`
• 当前状态: 正常交易
• 分析类型: 基础分析
• 分析时间: 2024-01-24

📈 趋势预测: 
   短期: 稳健上涨
   中期: 持续看好
   长期: 关注基本面

⚠️ 风险提示: 投资有风险，入市需谨慎
        """.strip()
        
        return BotResponse.markdown_response(analysis_result)


def main():
    """
    主函数：演示机器人框架的使用
    """
    print("🚀 Crawlo 机器人框架使用示例")
    print("=" * 50)
    
    # 获取分发器
    dispatcher = get_dispatcher()
    
    # 注册自定义命令
    dispatcher.register(StockAnalysisCommand())
    print(f"✅ 已注册自定义命令: stock")
    print(f"📋 当前可用命令数量: {len(dispatcher.list_commands())}")
    
    print("\n" + "=" * 50)
    print("🔍 测试各种命令:")
    
    # 测试帮助命令
    print("\n📝 测试 /help 命令:")
    help_msg = BotMessage(
        platform=Platform.TELEGRAM,
        message_id="msg_1",
        user_id="user_123",
        user_name="张三",
        chat_id="chat_123",
        chat_type=ChatType.GROUP,
        content="/help",
        raw_content="/help",
        mentioned=True
    )
    response = dispatcher.dispatch(help_msg)
    print(f"   {response.text.replace(chr(10), chr(10) + '   ')}")
    
    # 测试股票分析命令
    print("\n💹 测试 /stock 命令:")
    stock_msg = BotMessage(
        platform=Platform.FEISHU,
        message_id="msg_2",
        user_id="user_456",
        user_name="李四",
        chat_id="chat_456",
        chat_type=ChatType.PRIVATE,
        content="/stock TSLA",
        raw_content="/stock TSLA",
        mentioned=False
    )
    response = dispatcher.dispatch(stock_msg)
    print(f"   响应长度: {len(response.text)} 字符")
    print(f"   前 100 字符: {response.text[:100]}...")
    
    # 测试回声命令
    print("\n🔊 测试 /echo 命令:")
    echo_msg = BotMessage(
        platform=Platform.DINGTALK,
        message_id="msg_3",
        user_id="user_789",
        user_name="王五",
        chat_id="chat_789",
        chat_type=ChatType.GROUP,
        content="/echo Hello from DingTalk!",
        raw_content="/echo Hello from DingTalk!",
        mentioned=True
    )
    response = dispatcher.dispatch(echo_msg)
    print(f"   {response.text}")
    
    print("\n" + "=" * 50)
    print("🎯 机器人框架特性:")
    print("   • 统一的消息模型 (BotMessage)")
    print("   • 统一的响应模型 (BotResponse)")
    print("   • 命令分发机制")
    print("   • 参数验证")
    print("   • 权限控制")
    print("   • 频率限制")
    print("   • 多平台支持")
    
    print("\n✨ 机器人框架已成功集成到 Crawlo!")


if __name__ == "__main__":
    main()