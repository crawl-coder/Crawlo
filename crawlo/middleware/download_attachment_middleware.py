#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
附件下载中间件
==============

提供自动下载网页中指定附件的功能，支持多种文件类型和灵活配置。
"""

import os
import aiofiles
from urllib.parse import urljoin, urlparse
from typing import Optional, Dict, Any, List
import mimetypes

from crawlo.middleware import BaseMiddleware
from crawlo.logging import get_logger


class DownloadAttachmentMiddleware(BaseMiddleware):
    """
    附件下载中间件 - 自动下载请求中指定的附件
    
    支持通过请求元数据控制附件下载行为，提供灵活的配置选项。
    """
    
    def __init__(self, crawler):
        self.settings = crawler.settings
        self.logger = get_logger(self.__class__.__name__)
        
        # 从设置中获取默认配置
        self.download_dir = self.settings.get('ATTACHMENT_DOWNLOAD_DIR', './attachments')
        self.allowed_extensions = self.settings.get(
            'ATTACHMENT_ALLOWED_EXTENSIONS', 
            ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.zip', '.rar', '.txt', '.jpg', '.jpeg', '.png', '.gif']
        )
        self.max_file_size = self.settings.get_int('ATTACHMENT_MAX_FILE_SIZE', 50 * 1024 * 1024)  # 50MB
        self.create_dirs = self.settings.get_bool('ATTACHMENT_CREATE_DIRS', True)
        self.rename_duplicates = self.settings.get_bool('ATTACHMENT_RENAME_DUPLICATES', True)
        self.verify_content_type = self.settings.get_bool('ATTACHMENT_VERIFY_CONTENT_TYPE', True)
        
        # 确保下载目录存在
        if self.create_dirs:
            os.makedirs(self.download_dir, exist_ok=True)
    
    async def process_response(self, request, response, spider):
        """
        处理响应，检查是否需要下载附件
        
        Args:
            request: 请求对象
            response: 响应对象
            spider: 爬虫实例
            
        Returns:
            Response: 处理后的响应对象
        """
        # 检查请求元数据中是否包含下载附件的标志
        download_meta = request.meta.get('download_attachment')
        if download_meta:
            # 支持布尔值或字典配置
            if isinstance(download_meta, bool) and download_meta:
                # 使用默认配置下载
                attachment_info = await self.download_file(response, request)
            elif isinstance(download_meta, dict):
                # 使用自定义配置下载
                attachment_info = await self.download_file(response, request, **download_meta)
            else:
                attachment_info = None
            
            if attachment_info:
                # 将下载信息添加到response的meta中，供后续处理使用
                if not hasattr(response, 'meta'):
                    response.meta = {}
                response.meta['attachment_info'] = attachment_info
        
        return response
    
    async def download_file(self, response, request, 
                           filename: Optional[str] = None,
                           custom_dir: Optional[str] = None,
                           allowed_extensions: Optional[List[str]] = None,
                           max_file_size: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        下载文件的核心方法
        
        Args:
            response: 响应对象
            request: 请求对象
            filename: 自定义文件名
            custom_dir: 自定义下载目录
            allowed_extensions: 允许的文件扩展名列表
            max_file_size: 最大文件大小限制
            
        Returns:
            Dict: 下载信息字典，如果下载失败则返回None
        """
        try:
            # 获取配置参数，优先使用传入的参数，否则使用默认配置
            download_dir = custom_dir or self.download_dir
            allowed_exts = allowed_extensions or self.allowed_extensions
            max_size = max_file_size or self.max_file_size
            
            # 验证文件大小
            content_length = len(response.body)
            if content_length > max_size:
                self.logger.warning(f"文件过大，超过限制 ({content_length} > {max_size}): {request.url}")
                return None
            
            # 解析文件名
            actual_filename = await self._get_filename(request, response, filename)
            
            # 验证文件扩展名
            _, ext = os.path.splitext(actual_filename.lower())
            if allowed_exts and ext not in allowed_exts:
                self.logger.warning(f"文件扩展名不在允许列表中: {ext} (来自 {request.url})")
                return None
            
            # 验证内容类型（可选）
            if self.verify_content_type:
                content_type = response.headers.get('Content-Type', b'').decode('utf-8').lower()
                if content_type and not self._is_allowed_content_type(content_type, ext):
                    self.logger.warning(f"内容类型与扩展名不匹配: {content_type} vs {ext} (来自 {request.url})")
                    return None
            
            # 生成完整文件路径
            filepath = os.path.join(download_dir, actual_filename)
            
            # 处理重复文件名
            if self.rename_duplicates:
                filepath = self._handle_duplicate_filename(filepath)
            
            # 创建目录
            if self.create_dirs:
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            # 异步保存文件
            async with aiofiles.open(filepath, 'wb') as f:
                await f.write(response.body)
            
            self.logger.info(f"附件下载成功: {actual_filename} ({content_length} bytes)")
            
            return {
                'filename': actual_filename,
                'filepath': filepath,
                'size': content_length,
                'url': request.url,
                'content_type': response.headers.get('Content-Type', b'').decode('utf-8'),
                'success': True
            }
        except Exception as e:
            self.logger.error(f"下载附件失败 {request.url}: {e}")
            return None
    
    async def _get_filename(self, request, response, custom_filename: Optional[str] = None) -> str:
        """
        生成文件名
        
        Args:
            request: 请求对象
            response: 响应对象
            custom_filename: 自定义文件名
            
        Returns:
            str: 生成的文件名
        """
        # 优先使用自定义文件名
        if custom_filename:
            return custom_filename
        
        # 使用 Content-Disposition header 中的文件名
        content_disposition = response.headers.get('Content-Disposition', b'').decode('utf-8')
        if 'filename=' in content_disposition:
            import re
            match = re.search(r'filename[^;=\n]*=(([\'"]).*?\2|[^;\n]*)', content_disposition)
            if match:
                filename = match.group(1).strip('\'"')
                return self._sanitize_filename(filename)
        
        # 尝试从 URL 获取文件名
        parsed_url = urlparse(request.url)
        url_filename = os.path.basename(parsed_url.path)
        if url_filename and '.' in url_filename:
            return self._sanitize_filename(url_filename)
        
        # 使用 URL hash 作为文件名
        import hashlib
        url_hash = hashlib.md5(request.url.encode()).hexdigest()[:8]
        
        # 尝试从 Content-Type 推测扩展名
        content_type = response.headers.get('Content-Type', b'').decode('utf-8')
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
    
    def _handle_duplicate_filename(self, filepath: str) -> str:
        """
        处理重复文件名
        
        Args:
            filepath: 原始文件路径
            
        Returns:
            str: 解决冲突后的文件路径
        """
        if not os.path.exists(filepath):
            return filepath
        
        base, ext = os.path.splitext(filepath)
        counter = 1
        
        while True:
            new_filepath = f"{base}_{counter}{ext}"
            if not os.path.exists(new_filepath):
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
        # 简单的内容类型验证
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
        }
        
        allowed_types = content_type_map.get(extension, [])
        return not allowed_types or any(allowed in content_type for allowed in allowed_types)


# 导出所有公共API
__all__ = [
    'DownloadAttachmentMiddleware',
]