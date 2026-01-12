#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
附件下载工具
============

提供灵活的附件下载功能，可在爬虫中直接使用。
"""

import aiohttp
import aiofiles
import os
from urllib.parse import urlparse
from typing import Optional, Dict, Any, List
import mimetypes
from pathlib import Path

from crawlo.logging import get_logger


class AttachmentDownloader:
    """
    附件下载工具类
    
    提供灵活的附件下载功能，支持多种配置选项和错误处理。
    """
    
    def __init__(self, 
                 download_dir: str = './attachments', 
                 allowed_extensions: Optional[List[str]] = None,
                 max_file_size: int = 50 * 1024 * 1024,  # 50MB
                 create_dirs: bool = True,
                 rename_duplicates: bool = True,
                 verify_content_type: bool = True,
                 timeout: int = 30):
        """
        初始化附件下载器
        
        Args:
            download_dir: 下载目录
            allowed_extensions: 允许的文件扩展名列表
            max_file_size: 最大文件大小限制
            create_dirs: 是否自动创建目录
            rename_duplicates: 是否重命名重复文件
            verify_content_type: 是否验证内容类型
            timeout: 下载超时时间（秒）
        """
        self.download_dir = Path(download_dir)
        self.allowed_extensions = allowed_extensions or [
            '.pdf', '.doc', '.docx', '.xls', '.xlsx', 
            '.zip', '.rar', '.txt', '.jpg', '.jpeg', 
            '.png', '.gif', '.mp3', '.mp4', '.avi'
        ]
        self.max_file_size = max_file_size
        self.create_dirs = create_dirs
        self.rename_duplicates = rename_duplicates
        self.verify_content_type = verify_content_type
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.logger = get_logger(self.__class__.__name__)
        
        # 确保下载目录存在
        if self.create_dirs:
            self.download_dir.mkdir(parents=True, exist_ok=True)
    
    async def download(self, 
                     url: str, 
                     filename: Optional[str] = None, 
                     headers: Optional[Dict] = None,
                     custom_dir: Optional[str] = None,
                     allowed_extensions: Optional[List[str]] = None,
                     max_file_size: Optional[int] = None) -> Dict[str, Any]:
        """
        下载附件的主要方法
        
        Args:
            url: 要下载的URL
            filename: 自定义文件名
            headers: 请求头
            custom_dir: 自定义下载目录
            allowed_extensions: 自定义允许的扩展名列表
            max_file_size: 自定义最大文件大小
            
        Returns:
            Dict: 包含下载结果的字典
        """
        download_dir = Path(custom_dir) if custom_dir else self.download_dir
        allowed_exts = allowed_extensions or self.allowed_extensions
        max_size = max_file_size or self.max_file_size
        
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(url, headers=headers or {}) as response:
                    if response.status != 200:
                        return {
                            'success': False,
                            'error': f'HTTP {response.status}',
                            'url': url
                        }
                    
                    # 读取响应内容
                    content = await response.read()
                    
                    # 验证文件大小
                    if len(content) > max_size:
                        return {
                            'success': False,
                            'error': f'File too large ({len(content)} > {max_size})',
                            'url': url
                        }
                    
                    # 生成文件名
                    actual_filename = await self._generate_filename(url, response, filename)
                    
                    # 验证文件扩展名
                    _, ext = os.path.splitext(actual_filename.lower())
                    if ext not in allowed_exts:
                        return {
                            'success': False,
                            'error': f'Extension {ext} not allowed',
                            'url': url
                        }
                    
                    # 验证内容类型（可选）
                    if self.verify_content_type:
                        content_type = response.headers.get('Content-Type', '').lower()
                        if content_type and not self._is_allowed_content_type(content_type, ext):
                            return {
                                'success': False,
                                'error': f'Content type mismatch: {content_type} vs {ext}',
                                'url': url
                            }
                    
                    # 生成完整文件路径
                    filepath = download_dir / actual_filename
                    
                    # 处理重复文件名
                    if self.rename_duplicates:
                        filepath = self._handle_duplicate_filename(filepath)
                    
                    # 创建目录
                    if self.create_dirs:
                        filepath.parent.mkdir(parents=True, exist_ok=True)
                    
                    # 保存文件
                    async with aiofiles.open(filepath, 'wb') as f:
                        await f.write(content)
                    
                    self.logger.info(f"附件下载成功: {actual_filename}")
                    
                    return {
                        'success': True,
                        'filepath': str(filepath),
                        'filename': actual_filename,
                        'size': len(content),
                        'url': url,
                        'content_type': response.headers.get('Content-Type', ''),
                        'download_time': len(content)  # 这里简化处理
                    }
        
        except Exception as e:
            self.logger.error(f"下载附件失败 {url}: {e}")
            return {
                'success': False,
                'error': str(e),
                'url': url
            }
    
    async def download_batch(self, urls: List[str], 
                           headers: Optional[Dict] = None,
                           concurrency: int = 5) -> List[Dict[str, Any]]:
        """
        批量下载附件
        
        Args:
            urls: 要下载的URL列表
            headers: 请求头
            concurrency: 并发数
            
        Returns:
            List: 下载结果列表
        """
        import asyncio
        semaphore = asyncio.Semaphore(concurrency)
        
        async def download_with_semaphore(url):
            async with semaphore:
                return await self.download(url, headers=headers)
        
        tasks = [download_with_semaphore(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理可能的异常
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    'success': False,
                    'error': str(result),
                    'url': urls[i]
                })
            else:
                processed_results.append(result)
        
        return processed_results
    
    async def _generate_filename(self, url: str, response, custom_filename: Optional[str] = None) -> str:
        """
        生成文件名
        
        Args:
            url: 文件URL
            response: 响应对象
            custom_filename: 自定义文件名
            
        Returns:
            str: 生成的文件名
        """
        # 优先使用自定义文件名
        if custom_filename:
            return self._sanitize_filename(custom_filename)
        
        # 尝试从Content-Disposition获取文件名
        content_disposition = response.headers.get('Content-Disposition', '')
        if 'filename=' in content_disposition:
            import re
            match = re.search(r'filename[^;=\n]*=(([\'"]).*?\2|[^;\n]*)', content_disposition)
            if match:
                filename = match.group(1).strip('\'"')
                return self._sanitize_filename(filename)
        
        # 从URL获取文件名
        parsed_url = urlparse(url)
        url_filename = os.path.basename(parsed_url.path)
        if url_filename and '.' in url_filename:
            return self._sanitize_filename(url_filename)
        
        # 使用URL哈希生成文件名
        import hashlib
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
        
        # 尝试从Content-Type推测扩展名
        content_type = response.headers.get('Content-Type', '')
        if content_type:
            ext = mimetypes.guess_extension(content_type.split(';')[0])
            if ext:
                return f"attachment_{url_hash}{ext}"
        
        # 默认扩展名
        return f"attachment_{url_hash}.bin"
    
    def _sanitize_filename(self, filename: str) -> str:
        """
        清理文件名，移除非法字符
        
        Args:
            filename: 原始文件名
            
        Returns:
            str: 清理后的文件名
        """
        # 移除路径分隔符，防止路径遍历攻击
        filename = filename.replace('/', '_').replace('\\', '_')
        
        # 移除其他可能的危险字符
        dangerous_chars = '<>:"|?*'
        for char in dangerous_chars:
            filename = filename.replace(char, '_')
        
        # 限制文件名长度
        if len(filename) > 200:
            name, ext = os.path.splitext(filename)
            filename = name[:190] + ext
        
        return filename
    
    def _handle_duplicate_filename(self, filepath: Path) -> Path:
        """
        处理重复文件名
        
        Args:
            filepath: 原始文件路径
            
        Returns:
            Path: 解决冲突后的文件路径
        """
        if not filepath.exists():
            return filepath
        
        stem = filepath.stem
        suffix = filepath.suffix
        parent = filepath.parent
        
        counter = 1
        while True:
            new_filepath = parent / f"{stem}_{counter}{suffix}"
            if not new_filepath.exists():
                return new_filepath
            counter += 1
    
    def _is_allowed_content_type(self, content_type: str, extension: str) -> bool:
        """
        验证内容类型是否与扩展名匹配
        
        Args:
            content_type: 内容类型
            extension: 文件扩展名
            
        Returns:
            bool: 是否匹配
        """
        content_type_map = {
            '.pdf': ['application/pdf'],
            '.doc': ['application/msword'],
            '.docx': ['application/vnd.openxmlformats-officedocument.wordprocessingml.document'],
            '.xls': ['application/vnd.ms-excel'],
            '.xlsx': ['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'],
            '.zip': ['application/zip', 'application/x-zip-compressed'],
            '.txt': ['text/plain'],
            '.jpg': ['image/jpeg'],
            '.jpeg': ['image/jpeg'],
            '.png': ['image/png'],
            '.gif': ['image/gif'],
            '.mp3': ['audio/mpeg'],
            '.mp4': ['video/mp4'],
            '.avi': ['video/x-msvideo'],
        }
        
        allowed_types = content_type_map.get(extension, [])
        return not allowed_types or any(allowed in content_type for allowed in allowed_types)


# 导出所有公共API
__all__ = [
    'AttachmentDownloader',
]