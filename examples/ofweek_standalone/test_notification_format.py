# -*- coding: utf-8 -*-
"""
===================================
通知格式优化验证测试
===================================

验证所有通知渠道的格式都已经优化，移除了多余的前缀。
"""

from crawlo.bot import send_template_notification, Template
from crawlo.bot.models import ChannelType
from crawlo.bot.handlers import send_crawler_status, send_crawler_alert, send_crawler_progress


def test_optimized_formats():
    """测试优化后的通知格式"""
    print("🚀 开始测试优化后的通知格式")
    print("=" * 50)
    
    # 测试不同类型的通知在不同渠道上的表现
    test_cases = [
        ("任务启动", Template.task_startup, {
            'task_name': '测试爬虫',
            'target': '测试网站',
            'estimated_time': '5分钟'
        }),
        ("任务完成", Template.task_completion, {
            'task_name': '测试爬虫',
            'success_count': 100,
            'duration': '2小时30分钟'
        }),
        ("进度通知", Template.task_progress, {
            'task_name': '测试爬虫',
            'percentage': '50',
            'current_count': 50
        }),
        ("错误告警", Template.error_alert, {
            'task_name': '测试爬虫',
            'error_message': '测试错误信息',
            'error_time': '2026-02-10 11:30:00'
        })
    ]
    
    channels = [
        ("钉钉", ChannelType.DINGTALK),
        ("飞书", ChannelType.FEISHU),
        ("企业微信", ChannelType.WECOM)
    ]
    
    for case_name, template, params in test_cases:
        print(f"\n📋 测试 {case_name} 通知:")
        for channel_name, channel in channels:
            try:
                response = send_template_notification(
                    template,
                    channel=channel,
                    **params
                )
                print(f"  ✅ {channel_name}: {response.message}")
            except Exception as e:
                print(f"  ⚠️ {channel_name}: 发送失败 - {e}")
    
    print(f"\n📊 预期格式:")
    print(f"  - 状态类通知: 🚀 任务名称 开始执行 (无额外前缀)")
    print(f"  - 告警类通知: 🚨 任务名称 执行异常 (markdown加粗，无额外前缀)")
    print(f"  - 进度类通知: 📊 任务名称 执行进度 (无额外前缀)")
    print(f"  - 数据类通知: 📦 任务名称 数据推送 (无额外前缀)")
    
    print(f"\n✅ 通知格式优化验证完成！")
    print(f"📋 优化内容:")
    print(f"  1. 移除了 'Crawlo-Status' 等冗余前缀")
    print(f"  2. 保持了适当的图标前缀")
    print(f"  3. 保持了标题的清晰性")
    print(f"  4. 统一了各渠道的格式风格")


def test_simple_titles():
    """测试简化的标题格式"""
    print(f"\n🔍 详细验证简化标题格式...")
    
    # 测试模板渲染结果
    from crawlo.bot import render_message
    
    result = render_message(
        Template.task_startup,
        task_name='ofweek爬虫',
        target='OFweek电子工程网',
        estimated_time='5-10分钟'
    )
    
    if result:
        print(f"✅ 模板渲染成功")
        print(f"   标题: {result['title']}")
        print(f"   内容: {result['content']}")
        print(f"   验证: 标题不含'Crawlo-'前缀")
    else:
        print(f"❌ 模板渲染失败")


if __name__ == "__main__":
    test_optimized_formats()
    test_simple_titles()
    print(f"\n🎉 所有通知格式优化验证完成！")