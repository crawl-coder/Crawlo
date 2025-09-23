#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
命令行工具公共模块
提供命令行工具的公共函数和工具
"""
import sys
import configparser
from pathlib import Path
from importlib import import_module
from typing import Optional, Tuple

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()


def get_project_root() -> Optional[Path]:
    """
    自动检测项目根目录：从当前目录向上查找 crawlo.cfg
    
    Returns:
        Path: 项目根目录路径，如果未找到返回 None
    """
    current = Path.cwd()
    for _ in range(10):  # 最多向上查找10层
        cfg_file = current / "crawlo.cfg"
        if cfg_file.exists():
            return current
        if current == current.parent:
            break
        current = current.parent
    return None


def validate_project_environment() -> Tuple[bool, Optional[str], Optional[str]]:
    """
    验证项目环境，确保在正确的 Crawlo 项目中
    
    Returns:
        Tuple[bool, Optional[str], Optional[str]]: 
        (是否有效, 项目包名, 错误信息)
    """
    # 1. 查找项目根目录
    project_root = get_project_root()
    if not project_root:
        return False, None, "找不到 'crawlo.cfg'。请在项目目录中运行此命令。"
    
    # 2. 将项目根加入 Python 路径
    project_root_str = str(project_root)
    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)
    
    # 3. 读取配置文件
    cfg_file = project_root / "crawlo.cfg"
    config = configparser.ConfigParser()
    
    try:
        config.read(cfg_file, encoding="utf-8")
    except Exception as e:
        return False, None, f"读取 crawlo.cfg 失败: {e}"
    
    if not config.has_section("settings") or not config.has_option("settings", "default"):
        return False, None, "无效的 crawlo.cfg：缺少 [settings] 部分或 'default' 选项"
    
    # 4. 获取项目包名
    settings_module = config.get("settings", "default")
    project_package = settings_module.split(".")[0]
    
    # 5. 验证项目包是否可导入
    try:
        import_module(project_package)
    except ImportError as e:
        return False, None, f"导入项目包 '{project_package}' 失败: {e}"
    
    return True, project_package, None


def show_error_panel(title: str, message: str, show_json: bool = False) -> None:
    """
    显示错误面板或JSON格式错误
    
    Args:
        title: 错误标题
        message: 错误消息
        show_json: 是否以JSON格式输出
    """
    if show_json:
        console.print_json(data={"success": False, "error": message})
    else:
        console.print(Panel(
            Text.from_markup(f"[bold red]{message}[/bold red]"),
            title=f"{title}",
            border_style="red",
            padding=(1, 2)
        ))


def show_success_panel(title: str, message: str, show_json: bool = False, data: dict = None) -> None:
    """
    显示成功面板或JSON格式结果
    
    Args:
        title: 成功标题
        message: 成功消息
        show_json: 是否以JSON格式输出
        data: JSON数据（当show_json=True时）
    """
    if show_json:
        result = {"success": True, "message": message}
        if data:
            result.update(data)
        console.print_json(data=result)
    else:
        console.print(Panel(
            Text.from_markup(f"[bold green]{message}[/bold green]"),
            title=f"{title}",
            border_style="green",
            padding=(1, 2)
        ))


def validate_spider_name(spider_name: str) -> bool:
    """
    验证爬虫名称是否符合规范
    
    Args:
        spider_name: 爬虫名称
        
    Returns:
        bool: 是否有效
    """
    import re
    # 清理爬虫名称中的不可见字符
    cleaned_name = ''.join(c for c in spider_name if not unicodedata.category(c).startswith('C'))
    
    # 爬虫名称应该是有效的Python标识符
    return cleaned_name.isidentifier() and re.match(r'^[a-z][a-z0-9_]*$', cleaned_name)


def format_file_size(size_bytes: int) -> str:
    """
    格式化文件大小
    
    Args:
        size_bytes: 字节数
        
    Returns:
        str: 格式化后的大小字符串
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def truncate_text(text: str, max_length: int = 80) -> str:
    """
    截断过长的文本
    
    Args:
        text: 原始文本
        max_length: 最大长度
        
    Returns:
        str: 截断后的文本
    """
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."


def is_valid_domain(domain: str) -> bool:
    """
    验证域名格式是否正确
    
    Args:
        domain: 域名
        
    Returns:
        bool: 是否有效
    """
    import re
    # 清理域名中的不可见字符
    cleaned_domain = ''.join(c for c in domain if not unicodedata.category(c).startswith('C'))
    
    pattern = re.compile(
        r'^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)*[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$'
    )
    return bool(pattern.match(cleaned_domain))


# 添加导入
import unicodedata