#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
网络诊断工具
提供网络连接问题的诊断和解决方案
"""

import asyncio
import socket
import time
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

import aiohttp
from crawlo.utils.log import get_logger


class NetworkDiagnostic:
    """网络诊断工具类"""
    
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        self._dns_cache: Dict[str, str] = {}
    
    async def diagnose_url(self, url: str) -> Dict[str, any]:
        """
        诊断URL的网络连接问题
        
        Args:
            url: 要诊断的URL
            
        Returns:
            诊断结果字典
        """
        parsed = urlparse(url)
        hostname = parsed.hostname
        port = parsed.port or (443 if parsed.scheme == 'https' else 80)
        
        result = {
            'url': url,
            'hostname': hostname,
            'port': port,
            'dns_resolution': None,
            'tcp_connection': None,
            'http_response': None,
            'recommendations': []
        }
        
        # DNS解析测试
        dns_result = await self._test_dns_resolution(hostname)
        result['dns_resolution'] = dns_result
        
        if dns_result['success']:
            # TCP连接测试
            tcp_result = await self._test_tcp_connection(hostname, port)
            result['tcp_connection'] = tcp_result
            
            if tcp_result['success']:
                # HTTP响应测试
                http_result = await self._test_http_response(url)
                result['http_response'] = http_result
        
        # 生成建议
        result['recommendations'] = self._generate_recommendations(result)
        
        return result
    
    async def _test_dns_resolution(self, hostname: str) -> Dict[str, any]:
        """测试DNS解析"""
        try:
            start_time = time.time()
            
            # 使用asyncio的DNS解析
            loop = asyncio.get_event_loop()
            addr_info = await loop.getaddrinfo(hostname, None)
            
            resolution_time = time.time() - start_time
            ip_addresses = list(set([addr[4][0] for addr in addr_info]))
            
            # 缓存DNS结果
            if ip_addresses:
                self._dns_cache[hostname] = ip_addresses[0]
            
            return {
                'success': True,
                'ip_addresses': ip_addresses,
                'resolution_time': resolution_time,
                'error': None
            }
            
        except socket.gaierror as e:
            return {
                'success': False,
                'ip_addresses': [],
                'resolution_time': None,
                'error': {
                    'type': 'DNSError',
                    'code': e.errno,
                    'message': str(e)
                }
            }
        except Exception as e:
            return {
                'success': False,
                'ip_addresses': [],
                'resolution_time': None,
                'error': {
                    'type': type(e).__name__,
                    'message': str(e)
                }
            }
    
    async def _test_tcp_connection(self, hostname: str, port: int) -> Dict[str, any]:
        """测试TCP连接"""
        try:
            start_time = time.time()
            
            # 尝试TCP连接
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(hostname, port),
                timeout=10.0
            )
            
            connection_time = time.time() - start_time
            
            # 关闭连接
            writer.close()
            await writer.wait_closed()
            
            return {
                'success': True,
                'connection_time': connection_time,
                'error': None
            }
            
        except asyncio.TimeoutError:
            return {
                'success': False,
                'connection_time': None,
                'error': {
                    'type': 'TimeoutError',
                    'message': 'Connection timeout'
                }
            }
        except Exception as e:
            return {
                'success': False,
                'connection_time': None,
                'error': {
                    'type': type(e).__name__,
                    'message': str(e)
                }
            }
    
    async def _test_http_response(self, url: str) -> Dict[str, any]:
        """测试HTTP响应"""
        try:
            start_time = time.time()
            
            timeout = aiohttp.ClientTimeout(total=30, connect=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    response_time = time.time() - start_time
                    
                    return {
                        'success': True,
                        'status_code': response.status,
                        'response_time': response_time,
                        'headers': dict(response.headers),
                        'error': None
                    }
                    
        except aiohttp.ClientError as e:
            return {
                'success': False,
                'status_code': None,
                'response_time': None,
                'headers': {},
                'error': {
                    'type': type(e).__name__,
                    'message': str(e)
                }
            }
        except Exception as e:
            return {
                'success': False,
                'status_code': None,
                'response_time': None,
                'headers': {},
                'error': {
                    'type': type(e).__name__,
                    'message': str(e)
                }
            }
    
    def _generate_recommendations(self, result: Dict[str, any]) -> List[str]:
        """根据诊断结果生成建议"""
        recommendations = []
        
        dns_result = result.get('dns_resolution', {})
        tcp_result = result.get('tcp_connection', {})
        http_result = result.get('http_response', {})
        
        # DNS问题建议
        if not dns_result.get('success'):
            error = dns_result.get('error', {})
            if error.get('code') == 8:  # nodename nor servname provided, or not known
                recommendations.extend([
                    "DNS解析失败 - 检查域名是否正确",
                    "检查网络连接是否正常",
                    "尝试使用不同的DNS服务器（如8.8.8.8或1.1.1.1）",
                    "检查本地hosts文件是否有相关配置",
                    "确认域名是否可以从外部访问"
                ])
            elif error.get('code') == 2:  # Name or service not known
                recommendations.extend([
                    "域名不存在或无法解析",
                    "检查域名拼写是否正确",
                    "确认域名是否已注册且配置了DNS记录"
                ])
        
        # TCP连接问题建议
        elif not tcp_result.get('success'):
            error = tcp_result.get('error', {})
            if error.get('type') == 'TimeoutError':
                recommendations.extend([
                    "TCP连接超时 - 服务器可能无响应",
                    "检查防火墙设置是否阻止了连接",
                    "尝试增加连接超时时间",
                    "检查代理设置"
                ])
        
        # HTTP问题建议
        elif not http_result.get('success'):
            error = http_result.get('error', {})
            recommendations.extend([
                f"HTTP请求失败: {error.get('message', 'Unknown error')}",
                "检查URL是否正确",
                "确认服务器是否正常运行"
            ])
        
        # 性能建议
        if dns_result.get('success') and dns_result.get('resolution_time', 0) > 1.0:
            recommendations.append("DNS解析时间较长，考虑使用DNS缓存或更快的DNS服务器")
        
        if tcp_result.get('success') and tcp_result.get('connection_time', 0) > 2.0:
            recommendations.append("TCP连接时间较长，可能存在网络延迟问题")
        
        if http_result.get('success') and http_result.get('response_time', 0) > 5.0:
            recommendations.append("HTTP响应时间较长，服务器可能负载较高")
        
        return recommendations
    
    async def batch_diagnose(self, urls: List[str]) -> Dict[str, Dict[str, any]]:
        """批量诊断多个URL"""
        tasks = []
        for url in urls:
            task = asyncio.create_task(self.diagnose_url(url))
            tasks.append((url, task))
        
        results = {}
        for url, task in tasks:
            try:
                result = await task
                results[url] = result
            except Exception as e:
                results[url] = {
                    'url': url,
                    'error': f"诊断过程出错: {e}",
                    'recommendations': ["诊断工具本身出现问题，请检查网络环境"]
                }
        
        return results
    
    def format_diagnostic_report(self, result: Dict[str, any]) -> str:
        """格式化诊断报告"""
        lines = [
            f"=== 网络诊断报告 ===",
            f"URL: {result['url']}",
            f"主机: {result['hostname']}:{result['port']}",
            ""
        ]
        
        # DNS解析结果
        dns = result.get('dns_resolution', {})
        if dns.get('success'):
            lines.extend([
                "✅ DNS解析: 成功",
                f"   IP地址: {', '.join(dns['ip_addresses'])}",
                f"   解析时间: {dns['resolution_time']:.3f}秒"
            ])
        else:
            error = dns.get('error', {})
            lines.extend([
                "❌ DNS解析: 失败",
                f"   错误类型: {error.get('type', 'Unknown')}",
                f"   错误信息: {error.get('message', 'Unknown error')}"
            ])
        
        lines.append("")
        
        # TCP连接结果
        tcp = result.get('tcp_connection', {})
        if tcp and tcp.get('success'):
            lines.extend([
                "✅ TCP连接: 成功",
                f"   连接时间: {tcp['connection_time']:.3f}秒"
            ])
        elif tcp:
            error = tcp.get('error', {})
            lines.extend([
                "❌ TCP连接: 失败",
                f"   错误类型: {error.get('type', 'Unknown')}",
                f"   错误信息: {error.get('message', 'Unknown error')}"
            ])
        
        lines.append("")
        
        # HTTP响应结果
        http = result.get('http_response', {})
        if http and http.get('success'):
            lines.extend([
                "✅ HTTP响应: 成功",
                f"   状态码: {http['status_code']}",
                f"   响应时间: {http['response_time']:.3f}秒"
            ])
        elif http:
            error = http.get('error', {})
            lines.extend([
                "❌ HTTP响应: 失败",
                f"   错误类型: {error.get('type', 'Unknown')}",
                f"   错误信息: {error.get('message', 'Unknown error')}"
            ])
        
        # 建议
        recommendations = result.get('recommendations', [])
        if recommendations:
            lines.extend([
                "",
                "🔧 建议:",
            ])
            for i, rec in enumerate(recommendations, 1):
                lines.append(f"   {i}. {rec}")
        
        return "\n".join(lines)


# 便捷函数
async def diagnose_url(url: str) -> Dict[str, any]:
    """诊断单个URL的网络问题"""
    diagnostic = NetworkDiagnostic()
    return await diagnostic.diagnose_url(url)


async def diagnose_urls(urls: List[str]) -> Dict[str, Dict[str, any]]:
    """批量诊断URL的网络问题"""
    diagnostic = NetworkDiagnostic()
    return await diagnostic.batch_diagnose(urls)


def format_report(result: Dict[str, any]) -> str:
    """格式化诊断报告"""
    diagnostic = NetworkDiagnostic()
    return diagnostic.format_diagnostic_report(result)