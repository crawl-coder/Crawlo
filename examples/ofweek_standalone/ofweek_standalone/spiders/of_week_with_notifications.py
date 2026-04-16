# -*- coding: utf-8 -*-
"""
===================================
集成通知功能的 ofweek 爬虫示例
===================================

展示如何在实际爬虫中集成 Crawlo 通知系统
"""
import time
import asyncio
import random
from crawlo.spider import Spider
from crawlo import Request, Response
from ..items import OfWeekStandaloneItem
from crawlo.bot.models import ChannelType
from crawlo.bot.handlers import send_crawler_status
from crawlo.bot import (
    send_template_notification, 
    Template,
    get_template_parameters,
    render_resource_monitor_template,
    ResourceTemplate,
    send_crawler_alert
)



class OfWeekSpiderWithNotifications(Spider):
    """集成通知功能的 ofweek 爬虫"""
    
    name = 'of_week_with_notifications'
    allowed_domains = ['ee.ofweek.com']
    start_urls = ['https://ee.ofweek.com/']
    custom_settings = {}
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stats = {
            'total_requests': 0,
            'successful_items': 0,
            'failed_requests': 0,
            'start_time': None
        }
    
    def start_requests(self):
        """生成初始请求 - 带启动通知"""
        # 使用模板发送爬虫启动通知
        response = send_template_notification(
            Template.task_startup,
            task_name='ofweek爬虫',
            target='OFweek电子工程网',
            estimated_time='5-10分钟',
            channel=ChannelType.DINGTALK
        )
        if not response.success:
            self.logger.warning(f"发送启动通知失败: {response.message}")
        
        # 发送系统资源监控通知（模拟）
        resource_response = send_template_notification(
            Template.resource_monitor,
            memory_usage='65',
            cpu_usage='45',
            disk_usage='30',
            active_connections='45',
            channel=ChannelType.DINGTALK
        )
        
        # 测试资源监控模板 - MySQL连接池监控
        mysql_monitor_response = send_template_notification(
            Template.task_startup,  # 使用通用模板，但传递MySQL监控参数
            task_name='MySQL连接池监控',
            target='MySQL数据库',
            estimated_time='持续监控',
            channel=ChannelType.DINGTALK
        )
        
        # 测试优化后的通知格式
        try:
            # 发送任务启动通知（测试简化格式）
            startup_result = send_template_notification(
                Template.task_startup,
                task_name='ofweek爬虫',
                target='OFweek电子工程网',
                estimated_time='5-10分钟',
                channel=ChannelType.DINGTALK
            )
            self.logger.info(f"🚀 任务启动通知: {startup_result.message}")
            
            # 发送进度通知
            progress_result = send_template_notification(
                Template.task_progress,
                task_name='ofweek爬虫',
                percentage='10',
                current_count=5,
                channel=ChannelType.DINGTALK
            )
            self.logger.info(f"📊 进度通知: {progress_result.message}")
            
            # 发送告警通知
            alert_result = send_template_notification(
                Template.error_alert,
                task_name='ofweek爬虫',
                error_message='测试告警消息',
                error_time=time.strftime('%Y-%m-%d %H:%M:%S'),
                channel=ChannelType.DINGTALK
            )
            self.logger.info(f"🚨 告警通知: {alert_result.message}")
            
        except Exception as e:
            self.logger.warning(f"发送测试通知失败: {e}")
        
        # 测试资源监控模板 - 使用专用资源监控模板
        try:
            from crawlo.bot import render_resource_monitor_template, ResourceTemplate
            mysql_monitor_result = render_resource_monitor_template(
                ResourceTemplate.MYSQL_CONNECTION_POOL_MONITOR.value,
                pool_status="正常",
                active_connections=15,
                idle_connections=5,
                max_connections=50,
                waiting_connections=0,
                timestamp=time.strftime('%Y-%m-%d %H:%M:%S')
            )
            if mysql_monitor_result:
                send_crawler_status(
                    title=mysql_monitor_result['title'],
                    content=mysql_monitor_result['content'],
                    channel=ChannelType.DINGTALK
                )
        except Exception as e:
            self.logger.warning(f"发送MySQL监控通知失败: {e}")
        
        # 测试资源监控模板 - Redis内存监控
        try:
            redis_monitor_result = render_resource_monitor_template(
                ResourceTemplate.REDIS_MEMORY_MONITOR.value,
                used_memory="2.5GB",
                max_memory="4GB",
                memory_usage_percent=62.5,
                memory_fragmentation_ratio=1.2,
                hit_rate=98.5,
                timestamp=time.strftime('%Y-%m-%d %H:%M:%S')
            )
            if redis_monitor_result:
                send_crawler_status(
                    title=redis_monitor_result['title'],
                    content=redis_monitor_result['content'],
                    channel=ChannelType.DINGTALK
                )
        except Exception as e:
            self.logger.warning(f"发送Redis监控通知失败: {e}")
        
        # 测试消息去重功能 - 发送相同的消息两次，第二次应该被去重
        duplicate_test_response1 = send_template_notification(
            Template.task_startup,
            task_name='去重测试任务',
            target='测试网站',
            estimated_time='1分钟',
            channel=ChannelType.DINGTALK
        )
        self.logger.info(f"第一次去重测试结果: {duplicate_test_response1.message}")
        
        # 立即发送相同的消息，应该被去重机制拦截
        duplicate_test_response2 = send_template_notification(
            Template.task_startup,
            task_name='去重测试任务',
            target='测试网站',
            estimated_time='1分钟',
            channel=ChannelType.DINGTALK
        )
        self.logger.info(f"第二次去重测试结果: {duplicate_test_response2.message}")
        
        # 测试查询模板参数功能
        try:
            startup_params = get_template_parameters(Template.task_startup)
            self.logger.info(f"task_startup模板参数: {startup_params}")
        except Exception as e:
            self.logger.warning(f"查询模板参数失败: {e}")
        
        self.stats['start_time'] = self.get_current_time()
        self.logger.info("爬虫启动通知已发送")
        
        # 原有的起始请求逻辑
        max_pages = 2
        start_urls = []
        for page in range(1, max_pages + 1):
            url = f'https://ee.ofweek.com/CATList-2800-8100-ee-{page}.html'
            start_urls.append(url)
        
        self.logger.info(f"生成了 {len(start_urls)} 个起始URL")
        
        for url in start_urls:
            self.stats['total_requests'] += 1
            yield Request(url, callback=self.parse, dont_filter=True)
    
    async def parse(self, response: Response):
        """解析响应 - 带进度和异常通知"""
        try:
            # 检查响应状态
            if response.status != 200:
                self.stats['failed_requests'] += 1
                error_msg = f"页面返回非200状态码: {response.status}"
                self.logger.warning(f"{error_msg}, URL: {response.url}")
                
                # 保存原始响应信息
                original_url = response.url
                original_status = response.status
                
                # 发送HTTP错误通知（每10次错误发送一次，避免过于频繁）
                if self.stats['failed_requests'] % 10 == 1:
                    http_error_response = send_template_notification(
                        Template.http_error,
                        status_code=original_status,
                        url=original_url,
                        response_time='2500',
                        retry_count='3',
                        channel=ChannelType.DINGTALK
                    )
                
                    if not http_error_response.success:
                        self.logger.warning(f"发送HTTP错误通知失败: {http_error_response.message}")
                        
                    # 同时发送资源监控模板中的错误相关模板
                    try:
                        mysql_slow_query_result = render_resource_monitor_template(
                            ResourceTemplate.MYSQL_SLOW_QUERY_ALERT.value,
                            sql_statement=f"SELECT * FROM pages WHERE url = '{original_url}'",
                            execution_time=2.5,
                            affected_rows=1,
                            target_table="pages",
                            query_source="ofweek_spider"
                        )
                        if mysql_slow_query_result:
                            send_crawler_alert(
                                title=mysql_slow_query_result['title'],
                                content=mysql_slow_query_result['content'],
                                channel=ChannelType.DINGTALK
                            )
                    except Exception as e:
                        self.logger.warning(f"发送MySQL慢查询告警失败: {e}")
                return
            
            # 检查页面内容是否为空
            if not response.text or len(response.text.strip()) == 0:
                self.stats['failed_requests'] += 1
                self.logger.warning(f"页面内容为空: {response.url}")
                
                # 发送解析失败通知（每10次错误发送一次）
                if self.stats['failed_requests'] % 10 == 1:
                    parse_error_response = send_template_notification(
                        Template.parse_failure,
                        parse_success='否',
                        data_count='0',
                        error_type='内容为空',
                        url=response.url,
                        channel=ChannelType.DINGTALK
                    )
                    
                    # 同时发送MongoDB监控模板（模拟数据库操作）
                    try:
                        mongodb_result = render_resource_monitor_template(
                            ResourceTemplate.MONGODB_SLOW_OPERATION_ALERT.value,
                            operation_type="find",
                            execution_time=1.8,
                            collection_name="pages",
                            documents_affected=0,
                            operation_source="ofweek_spider"
                        )
                        if mongodb_result:
                            send_crawler_alert(
                                title=mongodb_result['title'],
                                content=mongodb_result['content'],
                                channel=ChannelType.DINGTALK
                            )
                    except Exception as e:
                        self.logger.warning(f"发送MongoDB慢操作告警失败: {e}")
                return
            
            # 随机模拟验证码检测（降低频率）
            if random.random() < 0.01:  # 1%概率
                captcha_response = send_template_notification(
                    Template.captcha_detected,
                    captcha_status='检测到',
                    url=response.url,
                    user_agent='Mozilla/5.0',
                    error_time=self.get_current_time_str(),
                    channel=ChannelType.DINGTALK
                )
                
                # 发送安全告警
                security_response = send_template_notification(
                    Template.security_alert,
                    security_alert='验证码检测',
                    auth_status='正常',
                    access_denied='否',
                    error_time=self.get_current_time_str(),
                    channel=ChannelType.DINGTALK
                )

            # 数据提取
            rows = response.xpath('//div[@class="main_left"]/div[@class="list_model"]/div[@class="model_right model_right2"]')
            self.logger.info(f"在页面 {response.url} 中找到 {len(rows)} 个条目")
            
            # 发送进度通知（每处理10个页面发送一次，避免过于频繁）
            if self.stats['total_requests'] % 10 == 0:
                progress_response = send_template_notification(
                    Template.task_progress,
                    task_name='ofweek爬虫',
                    percentage=f"{min(100, (self.stats['total_requests'] / 20) * 100):.1f}",
                    current_count=self.stats['total_requests'],
                    channel=ChannelType.DINGTALK
                )
                if not progress_response.success:
                    self.logger.warning(f"发送进度通知失败: {progress_response.message}")
                
                # 同时发送Redis连接监控
                try:
                    redis_conn_result = render_resource_monitor_template(
                        ResourceTemplate.REDIS_CONNECTION_MONITOR.value,
                        connection_status="健康",
                        connected_clients=120,
                        max_clients=1000,
                        input_kbps=1024,
                        output_kbps=2048,
                        timestamp=time.strftime('%Y-%m-%d %H:%M:%S')
                    )
                    if redis_conn_result:
                        send_crawler_status(
                            title=redis_conn_result['title'],
                            content=redis_conn_result['content'],
                            channel=ChannelType.DINGTALK
                        )
                except Exception as e:
                    self.logger.warning(f"发送Redis连接监控失败: {e}")
            
            for row in rows:
                try:
                    # 提取URL和标题
                    url = row.xpath('./h3/a/@href').extract_first()
                    title = row.xpath('./h3/a/text()').extract_first()
                    
                    # 容错处理
                    if not url or not title:
                        continue
                    
                    # 确保 URL 是绝对路径
                    absolute_url = response.urljoin(url)
                    
                    # 创建请求 - 使用正确的参数
                    yield Request(
                        url=absolute_url,
                        callback=self.parse_detail,
                        err_back=self.handle_error,
                        meta={'title': title}
                    )
                    
                except Exception as e:
                    self.logger.error(f"处理行数据时出错: {e}")
                    # 发送数据处理错误通知（降低频率）
                    if self.stats['failed_requests'] % 20 == 1:
                        data_error_response = send_template_notification(
                            Template.error_alert,
                            task_name='ofweek爬虫',
                            error_message=f'数据处理错误: {str(e)}',
                            error_time=self.get_current_time_str(),
                            channel=ChannelType.DINGTALK
                        )
                        
                        # 同时发送通用资源泄露告警
                        try:
                            general_leak_result = render_resource_monitor_template(
                                ResourceTemplate.GENERAL_RESOURCE_LEAK_ALERT.value,
                                resource_type="内存",
                                leak_details=f"处理数据时发生异常: {str(e)}",
                                growth_trend="异常增长",
                                severity_level="高",
                                discovery_time=time.strftime('%Y-%m-%d %H:%M:%S'),
                                affected_service="ofweek_spider"
                            )
                            if general_leak_result:
                                send_crawler_alert(
                                    title=general_leak_result['title'],
                                    content=general_leak_result['content'],
                                    channel=ChannelType.DINGTALK
                                )
                        except Exception as leak_e:
                            self.logger.warning(f"发送资源泄露告警失败: {leak_e}")
        
        except Exception as e:
            self.stats['failed_requests'] += 1
            error_msg = f"解析页面时发生异常: {e}"
            original_url = response.url
            
            # 发送严重错误告警（降低频率）
            if self.stats['failed_requests'] % 5 == 1:
                severe_error_response = send_template_notification(
                    Template.error_alert,
                    task_name='ofweek爬虫',
                    error_message=error_msg,
                    error_time=self.get_current_time_str(),
                    channel=ChannelType.DINGTALK
                )
                
                # 发送MySQL死锁告警（模拟）
                try:
                    mysql_deadlock_result = render_resource_monitor_template(
                        ResourceTemplate.MYSQL_DEADLOCK_ALERT.value,
                        transaction_id="TXN_123456",
                        wait_time=30,
                        involved_transactions="2",
                        lock_type="行锁",
                        affected_table="pages"
                    )
                    if mysql_deadlock_result:
                        send_crawler_alert(
                            title=mysql_deadlock_result['title'],
                            content=mysql_deadlock_result['content'],
                            channel=ChannelType.DINGTALK
                        )
                except Exception as deadlock_e:
                    self.logger.warning(f"发送MySQL死锁告警失败: {deadlock_e}")
                
                if not severe_error_response.success:
                    self.logger.warning(f"发送严重错误通知失败: {severe_error_response.message}")
    
    async def parse_detail(self, response):
        """解析详情页面 - 带数据统计通知"""
        try:
            self.logger.info(f'正在解析详情页: {response.url}')
            
            # 检查响应状态
            if response.status != 200:
                self.stats['failed_requests'] += 1
                self.logger.warning(f"详情页返回非200状态码: {response.status}")
                
                # 发送HTTP错误通知（降低频率）
                if self.stats['failed_requests'] % 5 == 1:
                    http_error_response = send_template_notification(
                        Template.http_error,
                        status_code=response.status,
                        url=response.url,
                        response_time='1800',
                        retry_count='1',
                        channel=ChannelType.DINGTALK
                    )
                    
                    # 同时发送Redis Key过期监控（模拟缓存相关错误）
                    try:
                        redis_ttl_result = render_resource_monitor_template(
                            ResourceTemplate.REDIS_KEY_TTL_MONITOR.value,
                            key_name=f"page_cache:{response.url}",
                            ttl_seconds=0,
                            business_type="页面缓存",
                            key_size_bytes=1024,
                            storage_location="Redis集群A"
                        )
                        if redis_ttl_result:
                            send_crawler_alert(
                                title=redis_ttl_result['title'],
                                content=redis_ttl_result['content'],
                                channel=ChannelType.DINGTALK
                            )
                    except Exception as e:
                        self.logger.warning(f"发送Redis Key过期监控失败: {e}")
                return
            
            title = response.meta.get('title', '')
            
            # 提取内容
            content_elements = response.xpath('//div[@class="TRS_Editor"]|//*[@id="articleC"]')
            if content_elements:
                content = content_elements.xpath('.//text()').extract()
                content = '\n'.join([text.strip() for text in content if text.strip()])
            else:
                content = ''
            
            # 提取发布时间和来源
            publish_time = response.xpath('//div[@class="time fl"]/text()').extract_first()
            source = response.xpath('//div[@class="source-name"]/text()').extract_first()
            
            # 创建数据项
            item = OfWeekStandaloneItem()
            item['title'] = title.strip() if title else ''
            item['publish_time'] = publish_time.strip() if publish_time else ''
            item['url'] = response.url
            item['source'] = source.strip() if source else ''
            item['content'] = content
            
            self.stats['successful_items'] += 1
            
            # 每成功处理100条数据发送一次进度通知
            if self.stats['successful_items'] % 100 == 0:
                progress_response = send_template_notification(
                    Template.task_progress,
                    task_name='ofweek爬虫',
                    percentage=f"{min(100, (self.stats['successful_items'] / 500) * 100):.1f}",
                    current_count=self.stats['successful_items'],
                    channel=ChannelType.DINGTALK
                )
                if not progress_response.success:
                    self.logger.warning(f"发送数据统计通知失败: {progress_response.message}")
                
                # 同时发送MongoDB连接监控
                try:
                    mongodb_conn_result = render_resource_monitor_template(
                        ResourceTemplate.MONGODB_CONNECTION_MONITOR.value,
                        pool_status="健康",
                        current_connections=8,
                        available_connections=12,
                        pending_requests=0,
                        timestamp=time.strftime('%Y-%m-%d %H:%M:%S')
                    )
                    if mongodb_conn_result:
                        send_crawler_status(
                            title=mongodb_conn_result['title'],
                            content=mongodb_conn_result['content'],
                            channel=ChannelType.DINGTALK
                        )
                except Exception as e:
                    self.logger.warning(f"发送MongoDB连接监控失败: {e}")
            
            # 随机模拟性能警告（降低频率）
            if random.random() < 0.005:  # 0.5%概率
                perf_warning_response = send_template_notification(
                    Template.performance_warning,
                    metric_name='响应时间',
                    current_value='3.5s',
                    threshold='2.0s',
                    task_name='ofweek爬虫',
                    channel=ChannelType.DINGTALK
                )
                
                # 同时发送MySQL资源泄露告警（模拟）
                try:
                    mysql_leak_result = render_resource_monitor_template(
                        ResourceTemplate.MYSQL_RESOURCE_LEAK_ALERT.value,
                        current_connections=45,
                        max_connections=50,
                        leak_type="连接泄露",
                        leak_tag="HIGH_USAGE",
                        discovery_time=time.strftime('%Y-%m-%d %H:%M:%S'),
                        impact_scope="ofweek_spider"
                    )
                    if mysql_leak_result:
                        send_crawler_alert(
                            title=mysql_leak_result['title'],
                            content=mysql_leak_result['content'],
                            channel=ChannelType.DINGTALK
                        )
                except Exception as e:
                    self.logger.warning(f"发送MySQL资源泄露告警失败: {e}")
            
            # 随机模拟登录状态监控（降低频率）
            if random.random() < 0.01:  # 1%概率
                login_status_response = send_template_notification(
                    Template.login_failed,
                    login_status='正常' if random.random() > 0.5 else '异常',
                    cookie_status='有效' if random.random() > 0.3 else '失效',
                    session_status='活跃' if random.random() > 0.4 else '过期',
                    error_time=self.get_current_time_str(),
                    channel=ChannelType.DINGTALK
                )
                
                # 同时发送Redis资源泄露告警（模拟）
                try:
                    redis_leak_result = render_resource_monitor_template(
                        ResourceTemplate.REDIS_RESOURCE_LEAK_ALERT.value,
                        current_connections=0,  # Redis不适用此字段
                        current_memory_mb=2560,
                        leak_trend="持续增长",
                        leak_identifier="HIGH_MEMORY_USAGE",
                        discovery_time=time.strftime('%Y-%m-%d %H:%M:%S'),
                        impact_scope="缓存服务"
                    )
                    if redis_leak_result:
                        send_crawler_alert(
                            title=redis_leak_result['title'],
                            content=redis_leak_result['content'],
                            channel=ChannelType.DINGTALK
                        )
                except Exception as e:
                    self.logger.warning(f"发送Redis资源泄露告警失败: {e}")
            
            yield item
            
        except Exception as e:
            self.stats['failed_requests'] += 1
            self.logger.error(f"解析详情页 {response.url} 时出错: {e}")
            
            # 发送解析失败通知（降低频率）
            if self.stats['failed_requests'] % 10 == 1:
                parse_error_response = send_template_notification(
                    Template.parse_failure,
                    parse_success='否',
                    data_count='0',
                    error_type=f'{type(e).__name__}: {str(e)}',
                    url=response.url,
                    channel=ChannelType.DINGTALK
                )
                
                # 同时发送MongoDB索引缺失告警
                try:
                    mongodb_index_result = render_resource_monitor_template(
                        ResourceTemplate.MONGODB_INDEX_MISS_ALERT.value,
                        collection_name="articles",
                        query_condition=f"title: {response.meta.get('title', 'unknown')}",
                        scanned_documents=10000,
                        returned_documents=1,
                        recommended_index="{title: 1}"
                    )
                    if mongodb_index_result:
                        send_crawler_alert(
                            title=mongodb_index_result['title'],
                            content=mongodb_index_result['content'],
                            channel=ChannelType.DINGTALK
                        )
                except Exception as e:
                    self.logger.warning(f"发送MongoDB索引缺失告警失败: {e}")
    
    async def closed(self, reason):
        """爬虫关闭时的回调 - 发送总结通知"""
        # 计算运行时长
        run_duration = self.get_run_duration()
        
        # 发送任务完成总结通知
        response = send_template_notification(
            Template.task_completion,
            task_name='ofweek爬虫',
            success_count=self.stats['successful_items'],
            duration=run_duration,
            channel=ChannelType.DINGTALK
        )
        if not response.success:
            self.logger.warning(f"发送完成通知失败: {response.message}")
        
        # 发送每日报告统计
        daily_report_response = send_template_notification(
            Template.daily_report,
            date=self.get_current_date(),
            new_count=self.stats['successful_items'],
            total_count=self.stats['total_requests'],
            success_rate=f"{(self.stats['successful_items']/max(1,self.stats['total_requests'])*100):.2f}",
            channel=ChannelType.DINGTALK
        )
        
        # 发送性能总结（只有在有失败请求时才发送）
        if self.stats['failed_requests'] > 0:
            error_summary_response = send_template_notification(
                Template.weekly_report,  # 用作错误汇总
                date=self.get_current_date(),
                new_count=self.stats['failed_requests'],
                total_count=self.stats['total_requests'],
                success_rate=f"{((self.stats['total_requests']-self.stats['failed_requests'])/max(1,self.stats['total_requests'])*100):.2f}",
                period='错误汇总',
                channel=ChannelType.DINGTALK
            )
        
        # 发送资源使用情况（只在有足够数据时才发送）
        if self.stats['successful_items'] > 0 or self.stats['failed_requests'] > 0:
            resource_response = send_template_notification(
                Template.resource_monitor,
                memory_usage='75',
                cpu_usage='60',
                disk_usage='40',
                active_connections='56',
                channel=ChannelType.DINGTALK
            )
            
            # 发送最终的资源监控总结
            try:
                final_mysql_monitor = render_resource_monitor_template(
                    ResourceTemplate.MYSQL_CONNECTION_POOL_MONITOR.value,
                    pool_status="正常" if self.stats['failed_requests'] < 10 else "压力",
                    active_connections=min(50, 10 + self.stats['successful_items'] // 10),
                    idle_connections=max(1, 15 - self.stats['failed_requests'] // 5),
                    max_connections=50,
                    waiting_connections=0,
                    timestamp=time.strftime('%Y-%m-%d %H:%M:%S')
                )
                if final_mysql_monitor:
                    send_crawler_status(
                        title=final_mysql_monitor['title'],
                        content=final_mysql_monitor['content'],
                        channel=ChannelType.DINGTALK
                    )
            except Exception as e:
                self.logger.warning(f"发送最终MySQL监控失败: {e}")
            
            try:
                final_redis_monitor = render_resource_monitor_template(
                    ResourceTemplate.REDIS_MEMORY_MONITOR.value,
                    used_memory=f"{2.0 + self.stats['successful_items']*0.01:.1f}GB",
                    max_memory="4GB",
                    memory_usage_percent=min(90, (2.0 + self.stats['successful_items']*0.01)/4.0*100),
                    memory_fragmentation_ratio=round(1.0 + random.random()*0.5, 2),
                    hit_rate=max(80, 98.5 - self.stats['failed_requests']*0.1),
                    timestamp=time.strftime('%Y-%m-%d %H:%M:%S')
                )
                if final_redis_monitor:
                    send_crawler_status(
                        title=final_redis_monitor['title'],
                        content=final_redis_monitor['content'],
                        channel=ChannelType.DINGTALK
                    )
            except Exception as e:
                self.logger.warning(f"发送最终Redis监控失败: {e}")
        
        # 发送安全告警（只有在有错误时才发送）
        if self.stats['failed_requests'] > 0:
            security_response = send_template_notification(
                Template.security_alert,
                security_alert='爬虫运行异常',
                auth_status='正常',
                access_denied='否',
                error_time=self.get_current_time_str(),
                channel=ChannelType.DINGTALK
            )
            
            # 发送最终的资源泄露监控
            try:
                final_leak_monitor = render_resource_monitor_template(
                    ResourceTemplate.GENERAL_RESOURCE_LEAK_ALERT.value,
                    resource_type="连接数",
                    leak_details=f"总请求数: {self.stats['total_requests']}, 失败请求数: {self.stats['failed_requests']}",
                    growth_trend="稳定" if self.stats['failed_requests'] < 5 else "增长",
                    severity_level="低" if self.stats['failed_requests'] < 5 else "中等",
                    discovery_time=time.strftime('%Y-%m-%d %H:%M:%S'),
                    affected_service="ofweek_spider"
                )
                if final_leak_monitor:
                    send_crawler_alert(
                        title=final_leak_monitor['title'],
                        content=final_leak_monitor['content'],
                        channel=ChannelType.DINGTALK
                    )
            except Exception as e:
                self.logger.warning(f"发送最终资源泄露监控失败: {e}")
        
        self.logger.info("爬虫完成总结通知已发送")

    def get_current_date(self):
        """获取当前日期"""
        from datetime import datetime
        return datetime.now().strftime('%Y-%m-%d')
    
    def get_current_time(self):
        """获取当前时间"""
        from datetime import datetime
        return datetime.now()
    
    def get_run_duration(self):
        """计算运行时长"""
        if not self.stats['start_time']:
            return "未知"
        
        from datetime import datetime
        duration = datetime.now() - self.stats['start_time']
        hours, remainder = divmod(duration.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours}小时{minutes}分钟{seconds}秒"
    
    def get_current_time_str(self):
        """获取当前时间字符串"""
        return self.get_current_time().strftime('%Y-%m-%d %H:%M:%S')
    
    def handle_error(self, failure):
        """处理请求错误"""
        self.logger.error(f"请求失败: {failure}")
        self.stats['failed_requests'] += 1


# 使用示例
def run_spider_with_notifications():
    """运行带通知的爬虫示例"""
    print("🚀 启动集成通知功能的 ofweek 爬虫...")
    
    # 这里应该是实际的爬虫运行代码
    # 由于这是示例，我们只演示通知功能
    
    async def demo():
        # 模拟爬虫运行过程中的通知
        await send_crawler_status(
            title="【示例】爬虫通知功能演示",
            content="这是演示如何在爬虫中使用通知功能的示例",
            channel=ChannelType.DINGTALK
        )
    
    asyncio.run(demo())
    print("✅ 演示完成！")


if __name__ == "__main__":
    run_spider_with_notifications()