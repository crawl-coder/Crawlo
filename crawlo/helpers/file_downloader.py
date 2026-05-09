#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Attachment Download Utility
===========================

Provides flexible file download capabilities for use in crawlers.
"""

import aiohttp
import aiofiles
import asyncio
import os
import re
import hashlib
import mimetypes
from pathlib import Path
from urllib.parse import urlparse
from typing import Optional, Dict, Any, List, Callable

from crawlo.logging import get_logger


# Constants
DEFAULT_MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
DEFAULT_TIMEOUT = 30  # seconds
CHUNK_SIZE = 8192  # 8KB


class FileDownloader:
    """
    文件下载工具类
    
    提供灵活的附件下载功能，支持多种配置选项和错误处理。
    """
    
    def __init__(self, 
                 download_dir: str = './attachments', 
                 allowed_extensions: Optional[List[str]] = None,
                 max_file_size: int = 50 * 1024 * 1024,  # 50MB
                 create_dirs: bool = True,
                 rename_duplicates: bool = True,
                 verify_content_type: bool = True,
                 timeout: int = 30,
                 proxy: Optional[str] = None,
                 verify_ssl: bool = True,
                 max_retries: int = 3,
                 retry_delay: float = 1.0,
                 progress_callback: Optional[Callable] = None):
        """
        初始化文件下载器
        
        Args:
            download_dir: 下载目录
            allowed_extensions: 允许的文件扩展名列表
            max_file_size: 最大文件大小限制
            create_dirs: 是否自动创建目录
            rename_duplicates: 是否重命名重复文件
            verify_content_type: 是否验证内容类型
            timeout: 下载超时时间（秒）
            proxy: 代理地址，如 'http://127.0.0.1:7890' 或 'socks5://127.0.0.1:1080'
            verify_ssl: 是否验证 SSL 证书
            max_retries: 最大重试次数
            retry_delay: 重试延迟（秒）
            progress_callback: 进度回调函数，签名为 callback(downloaded_bytes, total_bytes, filename)
        """
        # Default extensions
        DEFAULT_EXTENSIONS = [
            '.pdf', '.doc', '.docx', '.xls', '.xlsx', 
            '.zip', '.rar', '.txt', '.jpg', '.jpeg', 
            '.png', '.gif', '.mp3', '.mp4', '.avi'
        ]
        # Merge user-provided extensions with defaults
        if allowed_extensions:
            self.allowed_extensions = list(set(DEFAULT_EXTENSIONS + allowed_extensions))
        else:
            self.allowed_extensions = DEFAULT_EXTENSIONS
        self.download_dir = Path(download_dir)
        self.max_file_size = max_file_size
        self.create_dirs = create_dirs
        self.rename_duplicates = rename_duplicates
        self.verify_content_type = verify_content_type
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.proxy = proxy
        self.verify_ssl = verify_ssl
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.progress_callback = progress_callback
        self.logger = get_logger(self.__class__.__name__)
        
        # Ensure download directory exists
        if self.create_dirs:
            self.download_dir.mkdir(parents=True, exist_ok=True)
    
    async def download(self, 
                     url: str, 
                     filename: Optional[str] = None, 
                     headers: Optional[Dict] = None,
                     custom_dir: Optional[str] = None,
                     allowed_extensions: Optional[List[str]] = None,
                     max_file_size: Optional[int] = None,
                     proxy: Optional[str] = None,
                     verify_ssl: Optional[bool] = None,
                     max_retries: Optional[int] = None) -> Dict[str, Any]:
        """
        Main method for downloading attachments
        
        Args:
            url: URL to download
            filename: Custom filename
            headers: Request headers
            custom_dir: Custom download directory
            allowed_extensions: Custom allowed extensions list
            max_file_size: Custom max file size
            proxy: Override instance-level proxy settings
            verify_ssl: Override instance-level SSL verification settings
            max_retries: Override instance-level retry count
            
        Returns:
            Dict: Download result dictionary
        """
        download_dir = Path(custom_dir) if custom_dir else self.download_dir
        # Merge user-provided extensions with defaults
        if allowed_extensions:
            allowed_exts = list(set(self.allowed_extensions + allowed_extensions))
        else:
            allowed_exts = self.allowed_extensions
        max_size = max_file_size or self.max_file_size
        
        # 使用传入的参数或实例默认值
        effective_proxy = proxy if proxy is not None else self.proxy
        effective_verify_ssl = verify_ssl if verify_ssl is not None else self.verify_ssl
        effective_max_retries = max_retries if max_retries is not None else self.max_retries
        
        # Get file size for progress callback
        total_size = 0
        downloaded_size = 0
        
        for attempt in range(effective_max_retries):
            try:
                # Build request parameters
                request_headers = headers or {}
                
                # Create TCPConnector for SSL verification control
                connector = aiohttp.TCPConnector(ssl=effective_verify_ssl)
                
                async with aiohttp.ClientSession(timeout=self.timeout, connector=connector) as session:
                    async with session.get(url, headers=request_headers, proxy=effective_proxy) as response:
                        if response.status != 200:
                            if attempt < effective_max_retries - 1:
                                self.logger.warning(f"HTTP {response.status}, 正在重试 ({attempt + 1}/{effective_max_retries})...")
                                await asyncio.sleep(self.retry_delay)
                                continue
                            return {
                                'success': False,
                                'error': f'HTTP {response.status}',
                                'url': url
                            }
                        
                        # Get total size
                        total_size = int(response.headers.get('Content-Length', 0))
                        
                        # Generate filename
                        actual_filename = await self._generate_filename(url, response, filename)
                        
                        # Validate file extension
                        _, ext = os.path.splitext(actual_filename.lower())
                        if ext not in allowed_exts:
                            return {
                                'success': False,
                                'error': f'Extension {ext} not allowed',
                                'url': url
                            }
                        
                        # Validate content type (optional)
                        if self.verify_content_type:
                            content_type = response.headers.get('Content-Type', '').lower()
                            if content_type and not self._is_allowed_content_type(content_type, ext):
                                return {
                                    'success': False,
                                    'error': f'Content type mismatch: {content_type} vs {ext}',
                                    'url': url
                                }
                        
                        # Generate full file path
                        filepath = download_dir / actual_filename
                        
                        # Handle duplicate filenames
                        if self.rename_duplicates:
                            filepath = self._handle_duplicate_filename(filepath)
                        
                        # Create directory
                        if self.create_dirs:
                            filepath.parent.mkdir(parents=True, exist_ok=True)
                        
                        # Stream download with progress callback
                        async with aiofiles.open(filepath, 'wb') as f:
                            async for chunk in response.content.iter_chunked(8192):
                                await f.write(chunk)
                                downloaded_size += len(chunk)
                                # Invoke progress callback
                                if self.progress_callback:
                                    try:
                                        self.progress_callback(downloaded_size, total_size, actual_filename)
                                    except Exception as e:
                                        self.logger.warning(f"Progress callback failed: {e}")
                        
                        actual_size = downloaded_size
                        
                        # Validate file size
                        if max_size > 0 and actual_size > max_size:
                            # Delete oversized file
                            if filepath.exists():
                                filepath.unlink()
                            return {
                                'success': False,
                                'error': f'File too large ({actual_size} > {max_size})',
                                'url': url
                            }
                        
                        self.logger.info(f"附件下载成功: {actual_filename}")
                        
                        return {
                            'success': True,
                            'filepath': str(filepath),
                            'filename': actual_filename,
                            'size': actual_size,
                            'url': url,
                            'content_type': response.headers.get('Content-Type', ''),
                            'attempts': attempt + 1
                        }
            
            except Exception as e:
                if attempt < effective_max_retries - 1:
                    self.logger.warning(f"下载失败: {e}, 正在重试 ({attempt + 1}/{effective_max_retries})...")
                    await asyncio.sleep(self.retry_delay)
                    downloaded_size = 0
                    continue
                
                self.logger.error(f"附件下载失败 {url}: {e}")
                return {
                    'success': False,
                    'error': str(e),
                    'url': url,
                    'attempts': attempt + 1
                }
        
        return {
            'success': False,
            'error': 'Max retries exceeded',
            'url': url
        }
    
    async def download_batch(self, urls: List[str], 
                           headers: Optional[Dict] = None,
                           concurrency: int = 5) -> List[Dict[str, Any]]:
        """
        Batch download attachments
        
        Args:
            urls: List of URLs to download
            headers: Request headers
            concurrency: Concurrency level
            
        Returns:
            List: List of download results
        """
        semaphore = asyncio.Semaphore(concurrency)
        
        async def download_with_semaphore(url):
            async with semaphore:
                return await self.download(url, headers=headers)
        
        tasks = [download_with_semaphore(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle potential exceptions
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
    
    async def _generate_filename(self, url: str, response: aiohttp.ClientResponse, custom_filename: Optional[str] = None) -> str:
        """
        Generate filename
        
        Args:
            url: File URL
            response: Response object
            custom_filename: Custom filename
            
        Returns:
            str: Generated filename
        """
        # Prefer custom filename
        if custom_filename:
            return self._sanitize_filename(custom_filename)
        
        # Try to get filename from Content-Disposition
        content_disposition = response.headers.get('Content-Disposition', '')
        if 'filename=' in content_disposition:
            import re
            match = re.search(r'filename[^;=\n]*=(([\'"]).*?\2|[^;\n]*)', content_disposition)
            if match:
                filename = match.group(1).strip('\'"')
                return self._sanitize_filename(filename)
        
        # Get filename from URL
        parsed_url = urlparse(url)
        url_filename = os.path.basename(parsed_url.path)
        if url_filename and '.' in url_filename:
            return self._sanitize_filename(url_filename)
        
        # Generate filename from URL hash
        import hashlib
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
        
        # Try to infer extension from Content-Type
        content_type = response.headers.get('Content-Type', '')
        if content_type:
            ext = mimetypes.guess_extension(content_type.split(';')[0])
            if ext:
                return f"attachment_{url_hash}{ext}"
        
        # Default extension
        return f"attachment_{url_hash}.bin"
    
    def _sanitize_filename(self, filename: str) -> str:
        """
        Sanitize filename by removing illegal characters
        
        Args:
            filename: Original filename
            
        Returns:
            str: Sanitized filename
        """
        # Remove path separators to prevent path traversal attacks
        filename = filename.replace('/', '_').replace('\\', '_')
        
        # Remove other potentially dangerous characters
        dangerous_chars = '<>:"|?*'
        for char in dangerous_chars:
            filename = filename.replace(char, '_')
        
        # Limit filename length
        if len(filename) > 200:
            name, ext = os.path.splitext(filename)
            filename = name[:190] + ext
        
        return filename
    
    def _handle_duplicate_filename(self, filepath: Path) -> Path:
        """
        Handle duplicate filenames
        
        Args:
            filepath: Original file path
            
        Returns:
            Path: Resolved file path
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
        Validate content type matches extension
        
        Args:
            content_type: Content type
            extension: File extension
            
        Returns:
            bool: Whether it matches
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
    'FileDownloader',
]
