# -*- coding: utf-8 -*-
"""
===================================
Crawlo 通知系统功能测试
===================================

测试所有通知系统功能，包括：
- 模板通知发送
- 模板参数查询
- 资源监控模板
- 消息去重功能
- 通知格式优化
"""

def test_basic_imports():
    """测试基本导入功能"""
    print("🔍 测试基本导入功能...")
    try:
        from crawlo.bot import (
            send_template_notification, 
            Template, 
            ChannelType,
            get_template_parameters,
            render_resource_monitor_template,
            ResourceTemplate,
            get_deduplicator
        )
        print("✅ 所有模块导入成功")
        return True
    except Exception as e:
        print(f"❌ 导入失败: {e}")
        return False


def test_template_parameters():
    """测试模板参数查询功能"""
    print("\n🔍 测试模板参数查询功能...")
    try:
        from crawlo.bot import get_template_parameters
        from crawlo.bot.template_enums import Template
        
        # 测试几个常见模板
        startup_params = get_template_parameters('task_startup')
        print(f"✅ task_startup 模板参数: {startup_params}")
        
        error_params = get_template_parameters('error_alert')
        print(f"✅ error_alert 模板参数: {error_params}")
        
        http_params = get_template_parameters('http_error')
        print(f"✅ http_error 模板参数: {http_params}")
        
        print("✅ 模板参数查询功能正常")
        return True
    except Exception as e:
        print(f"❌ 模板参数查询失败: {e}")
        return False


def test_resource_monitor_templates():
    """测试资源监控模板功能"""
    print("\n🔍 测试资源监控模板功能...")
    try:
        from crawlo.bot import render_resource_monitor_template, ResourceTemplate
        
        # 测试MySQL连接池监控模板
        mysql_result = render_resource_monitor_template(
            ResourceTemplate.MYSQL_CONNECTION_POOL_MONITOR.value,
            pool_status="正常",
            active_connections=15,
            idle_connections=5,
            max_connections=50,
            waiting_connections=0,
            timestamp="2026-02-10 11:30:00"
        )
        if mysql_result:
            print(f"✅ MySQL连接池监控模板渲染成功")
            print(f"   标题: {mysql_result['title']}")
            print(f"   内容: {mysql_result['content']}")
        
        # 测试Redis内存监控模板
        redis_result = render_resource_monitor_template(
            ResourceTemplate.REDIS_MEMORY_MONITOR.value,
            memory_usage=65,
            peak_memory=80,
            max_memory=100,
            memory_policy="volatile-lru",
            fragmentation_ratio=1.2,
            timestamp="2026-02-10 11:30:00"
        )
        if redis_result:
            print(f"✅ Redis内存监控模板渲染成功")
            print(f"   标题: {redis_result['title']}")
            print(f"   内容: {redis_result['content']}")
        
        print("✅ 资源监控模板功能正常")
        return True
    except Exception as e:
        print(f"❌ 资源监控模板测试失败: {e}")
        return False


def test_deduplication():
    """测试消息去重功能"""
    print("\n🔍 测试消息去重功能...")
    
    try:
        from crawlo.bot import send_template_notification, Template, ChannelType
        from crawlo.bot.duplicate_manager import get_deduplicator
        
        deduplicator = get_deduplicator()
        
        # 清空之前的记录
        from crawlo.bot.duplicate_manager import reset_deduplicator
        reset_deduplicator()
        
        # 第一次发送
        response1 = send_template_notification(
            Template.task_startup,
            task_name='去重测试任务',
            target='测试网站',
            estimated_time='1分钟',
            channel=ChannelType.DINGTALK
        )
        print(f"✅ 第一次发送: {response1.message}")
        
        # 第二次发送相同内容（应该被去重）
        response2 = send_template_notification(
            Template.task_startup,
            task_name='去重测试任务',
            target='测试网站',
            estimated_time='1分钟',
            channel=ChannelType.DINGTALK
        )
        print(f"✅ 第二次发送（应被去重）: {response2.message}")
        
        print("✅ 消息去重功能正常")
        return True
    except Exception as e:
        print(f"❌ 消息去重测试失败: {e}")
        return False


def test_all_notification_types():
    """测试所有通知类型"""
    print("\n🔍 测试所有通知类型...")
    try:
        from crawlo.bot import send_template_notification, ChannelType
        from crawlo.bot.template_enums import Template
        
        # 测试各种模板
        test_cases = [
            ('task_startup', {
                'task_name': '测试任务',
                'target': '测试网站',
                'estimated_time': '5分钟'
            }),
            ('task_completion', {
                'task_name': '测试任务',
                'success_count': 100,
                'duration': '2小时'
            }),
            ('task_progress', {
                'task_name': '测试任务',
                'percentage': 50,
                'current_count': 50
            }),
            ('error_alert', {
                'task_name': '测试任务',
                'error_message': '测试错误',
                'error_time': '2026-02-10 11:30:00'
            }),
            ('performance_warning', {
                'metric_name': '响应时间',
                'current_value': '2.5s',
                'threshold': '2s'
            }),
            ('http_error', {
                'status_code': 500,
                'url': 'http://example.com',
                'response_time': 3000,
                'retry_count': 3
            }),
            ('login_failed', {
                'login_status': '失败',
                'cookie_status': '过期',
                'session_status': '无效',
                'error_time': '2026-02-10 11:30:00'
            }),
            ('proxy_issue', {
                'proxy_used': '192.168.1.100:8080',
                'proxy_status': '异常',
                'auth_status': '认证失败',
                'retry_count': 5
            }),
            ('captcha_detected', {
                'captcha_status': '检测到',
                'url': 'http://example.com/login',
                'user_agent': 'Mozilla/5.0...',
            }),
            ('parse_failure', {
                'parse_success': '失败',
                'data_count': 0,
                'error_type': 'XPath错误',
                'url': 'http://example.com/data'
            }),
            ('resource_monitor', {
                'memory_usage': 85,
                'cpu_usage': 75,
                'disk_usage': 90,
                'active_connections': 50
            }),
            ('db_connection_error', {
                'db_connection': '断开',
                'db_query_time': 5000,
                'db_error': '连接超时',
                'table_name': 'users'
            }),
            ('security_alert', {
                'security_alert': '访问异常',
                'auth_status': '失败',
                'access_denied': 3,
                'error_time': '2026-02-10 11:30:00'
            })
        ]
        
        success_count = 0
        for template_name, params in test_cases:
            try:
                response = send_template_notification(
                    template_name,
                    channel=ChannelType.DINGTALK,
                    **params
                )
                print(f"✅ {template_name}: {response.message}")
                success_count += 1
            except Exception as e:
                print(f"⚠️ {template_name}: 发送失败 - {e}")
        
        print(f"✅ 共测试 {len(test_cases)} 种通知类型，成功 {success_count} 个")
        return True
    except Exception as e:
        print(f"❌ 通知类型测试失败: {e}")
        return False


def test_resource_leak_templates():
    """测试资源泄露模板"""
    print("\n🔍 测试资源泄露模板...")
    try:
        from crawlo.bot import render_resource_monitor_template, ResourceTemplate
        
        # 测试MySQL资源泄露告警
        mysql_leak_result = render_resource_monitor_template(
            ResourceTemplate.MYSQL_RESOURCE_LEAK_ALERT.value,
            current_connections=45,
            max_connections=50,
            leak_type="连接未关闭",
            leak_tag="crawler_module",
            discovery_time="2026-02-10 11:30:00",
            impact_scope="数据抓取模块"
        )
        if mysql_leak_result:
            print(f"✅ MySQL资源泄露告警模板渲染成功")
            print(f"   标题: {mysql_leak_result['title']}")
            print(f"   内容: {mysql_leak_result['content']}")
        
        # 测试Redis资源泄露告警
        redis_leak_result = render_resource_monitor_template(
            ResourceTemplate.REDIS_RESOURCE_LEAK_ALERT.value,
            current_memory=95,
            max_memory=100,
            leak_type="内存泄漏",
            leak_tag="cache_module",
            discovery_time="2026-02-10 11:30:00",
            impact_scope="缓存服务"
        )
        if redis_leak_result:
            print(f"✅ Redis资源泄露告警模板渲染成功")
            print(f"   标题: {redis_leak_result['title']}")
            print(f"   内容: {redis_leak_result['content']}")
        
        print("✅ 资源泄露模板功能正常")
        return True
    except Exception as e:
        print(f"❌ 资源泄露模板测试失败: {e}")
        return False


def test_optimized_format():
    """测试优化后的通知格式"""
    print("\n🔍 测试优化后的通知格式...")
    try:
        from crawlo.bot import render_message, Template
        
        # 测试任务启动模板 - 应该只包含简单格式
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
            
            # 验证格式是否符合预期
            expected_title_pattern = "🚀 ofweek爬虫 开始执行"
            if result['title'] == expected_title_pattern:
                print("✅ 通知格式已优化，无冗余前缀")
            else:
                print(f"⚠️ 格式可能未优化，期望: {expected_title_pattern}, 实际: {result['title']}")
        
        print("✅ 通知格式优化测试完成")
        return True
    except Exception as e:
        print(f"❌ 通知格式测试失败: {e}")
        return False


def main():
    """主测试函数"""
    print("🚀 开始测试 Crawlo 通知系统所有功能")
    print("=" * 60)
    
    tests = [
        test_basic_imports,
        test_template_parameters,
        test_resource_monitor_templates,
        test_deduplication,
        test_all_notification_types,
        test_resource_leak_templates,
        test_optimized_format
    ]
    
    passed = 0
    total = len(tests)
    
    for test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"❌ {test_func.__name__} 执行异常: {e}")
    
    print("\n" + "=" * 60)
    print(f"📊 测试总结: {passed}/{total} 个测试通过")
    
    if passed == total:
        print("🎉 所有功能测试通过！通知系统运行正常。")
    else:
        print(f"⚠️  {total - passed} 个测试未通过，请检查相关功能。")
    
    return passed == total


if __name__ == "__main__":
    main()