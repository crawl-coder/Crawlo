#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""Command-line utility functions for Crawlo CLI"""
import sys
import re
import unicodedata
from pathlib import Path
from importlib import import_module
from typing import Optional, Tuple, Dict

from crawlo.project import read_crawlo_cfg

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()

# Maximum directory levels to search upward for project root
MAX_SEARCH_DEPTH = 10


def get_project_root() -> Optional[Path]:
    """
    Automatically detect project root directory by searching upward for crawlo.cfg
    
    Returns:
        Path: Project root directory path, or None if not found
    """
    current = Path.cwd()
    for _ in range(MAX_SEARCH_DEPTH):
        cfg_file = current / "crawlo.cfg"
        if cfg_file.exists():
            return current
        if current == current.parent:
            break
        current = current.parent
    return None


def validate_project_environment() -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Validate project environment to ensure running in proper Crawlo project
    
    Returns:
        Tuple[bool, Optional[str], Optional[str]]: 
        (is_valid, project_package_name, error_message)
    """
    # 1. Find project root directory
    project_root = get_project_root()
    if not project_root:
        return False, None, "Cannot find 'crawlo.cfg'. Please run this command in project directory."
    
    # 2. Add project root to Python path
    project_root_str = str(project_root)
    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)
    
    # 3. Read configuration file
    cfg_file = str(project_root / "crawlo.cfg")
    settings_module = read_crawlo_cfg(cfg_file)
    
    if not settings_module:
        return False, None, "crawlo.cfg is invalid or missing: no [settings] section or 'default' option"
    
    # 4. Get project package name
    project_package = settings_module.split(".")[0]
    
    # 5. Verify project package is importable
    try:
        import_module(project_package)
    except ImportError as e:
        return False, None, f"Failed to import project package '{project_package}': {e}"
    
    return True, project_package, None


def show_error_panel(title: str, message: str, show_json: bool = False) -> None:
    """
    Display error panel or JSON format error
    
    Args:
        title: Error title
        message: Error message
        show_json: Whether to output in JSON format
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


def show_success_panel(title: str, message: str, show_json: bool = False, data: Optional[Dict] = None) -> None:
    """
    Display success panel or JSON format result
    
    Args:
        title: Success title
        message: Success message
        show_json: Whether to output in JSON format
        data: JSON data (when show_json=True)
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
    Validate spider name conforms to standards
    
    Args:
        spider_name: Spider name
        
    Returns:
        bool: Whether valid
    """
    # Clean invisible characters from spider name
    cleaned_name = ''.join(c for c in spider_name if not unicodedata.category(c).startswith('C'))
    
    # Spider name should be a valid Python identifier
    return cleaned_name.isidentifier() and re.match(r'^[a-z][a-z0-9_]*$', cleaned_name)


def format_file_size(size_bytes: int) -> str:
    """
    Format file size
    
    Args:
        size_bytes: Number of bytes
        
    Returns:
        str: Formatted size string
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def truncate_text(text: str, max_length: int = 80) -> str:
    """
    Truncate overly long text
    
    Args:
        text: Original text
        max_length: Maximum length
        
    Returns:
        str: Truncated text
    """
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."


def is_valid_domain(domain: str) -> bool:
    """
    Validate domain name format
    
    Args:
        domain: Domain name
        
    Returns:
        bool: Whether valid
    """
    # Clean invisible characters from domain name
    cleaned_domain = ''.join(c for c in domain if not unicodedata.category(c).startswith('C'))
    
    pattern = re.compile(
        r'^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)*[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$'
    )
    return bool(pattern.match(cleaned_domain))


# Remove import unicodedata from line 192