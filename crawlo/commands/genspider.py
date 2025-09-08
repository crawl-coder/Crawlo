#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
# @Time    : 2025-08-31 22:36
# @Author  : crawl-coder
# @Desc    : 命令行入口：crawlo genspider baidu，创建爬虫。
"""
import sys
from pathlib import Path
import configparser
import importlib
from rich.console import Console

from .utils import (
    get_project_root, 
    validate_project_environment, 
    show_error_panel, 
    show_success_panel,
    validate_spider_name,
    is_valid_domain
)

# 初始化 rich 控制台
console = Console()

TEMPLATES_DIR = Path(__file__).parent.parent / 'templates'


def _render_template(tmpl_path, context):
    """读取模板文件，替换 {{key}} 为 context 中的值"""
    with open(tmpl_path, 'r', encoding='utf-8') as f:
        content = f.read()
    for key, value in context.items():
        content = content.replace(f'{{{{{key}}}}}', str(value))
    return content


def main(args):
    if len(args) < 2:
        console.print("[bold red]Error:[/bold red] Usage: [blue]crawlo genspider[/blue] <spider_name> <domain>")
        console.print("💡 Examples:")
        console.print("   [blue]crawlo genspider[/blue] news_spider news.example.com")
        console.print("   [blue]crawlo genspider[/blue] product_spider shop.example.com")
        return 1

    spider_name = args[0]
    domain = args[1]
    
    # 验证爬虫名称
    if not validate_spider_name(spider_name):
        show_error_panel(
            "Invalid Spider Name", 
            f"Spider name '[cyan]{spider_name}[/cyan]' is invalid.\n"
            "💡 Spider name should:\n"
            "  • Start with lowercase letter\n"
            "  • Contain only lowercase letters, numbers, and underscores\n"
            "  • Be a valid Python identifier"
        )
        return 1
    
    # 验证域名格式
    if not is_valid_domain(domain):
        show_error_panel(
            "Invalid Domain", 
            f"Domain '[cyan]{domain}[/cyan]' format is invalid.\n"
            "💡 Please provide a valid domain name like 'example.com'"
        )
        return 1

    # 验证项目环境
    is_valid, project_package, error_msg = validate_project_environment()
    if not is_valid:
        show_error_panel("Not a Crawlo Project", error_msg)
        return 1
    
    project_root = get_project_root()

    # 确定 items 模块的路径
    items_module_path = f"{project_package}.items"

    # 尝试导入 items 模块
    default_item_class = "ExampleItem"  # 默认回退
    try:
        items_module = importlib.import_module(items_module_path)
        # 获取模块中所有大写开头的类
        item_classes = [
            cls for cls in items_module.__dict__.values()
            if isinstance(cls, type) and cls.__name__[0].isupper()  # 首字母大写
        ]

        if item_classes:
            default_item_class = item_classes[0].__name__
        else:
            console.print("[yellow]:warning: Warning:[/yellow] No item class found in [cyan]items.py[/cyan], using [green]ExampleItem[/green].")

    except ImportError as e:
        console.print(f"[yellow]:warning: Warning:[/yellow] Failed to import [cyan]{items_module_path}[/cyan]: {e}")
        # 仍使用默认 ExampleItem，不中断流程

    # 创建爬虫文件
    spiders_dir = project_root / project_package / 'spiders'
    spiders_dir.mkdir(parents=True, exist_ok=True)

    spider_file = spiders_dir / f'{spider_name}.py'
    if spider_file.exists():
        show_error_panel(
            "Spider Already Exists", 
            f"Spider '[cyan]{spider_name}[/cyan]' already exists at\n[green]{spider_file}[/green]"
        )
        return 1

    # 模板路径
    tmpl_path = TEMPLATES_DIR / 'spider' / 'spider.py.tmpl'
    if not tmpl_path.exists():
        show_error_panel(
            "Template Not Found", 
            f"Template file not found at [cyan]{tmpl_path}[/cyan]"
        )
        return 1

    # 生成类名
    class_name = f"{spider_name.replace('_', '').capitalize()}Spider"

    context = {
        'spider_name': spider_name,
        'domain': domain,
        'project_name': project_package,
        'item_class': default_item_class,
        'class_name': class_name
    }

    try:
        content = _render_template(tmpl_path, context)
        with open(spider_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        console.print(f":white_check_mark: [green]Spider '[bold]{spider_name}[/bold]' created successfully![/green]")
        console.print(f"  → Location: [cyan]{spider_file}[/cyan]")
        console.print(f"  → Class: [yellow]{class_name}[/yellow]")
        console.print(f"  → Domain: [blue]{domain}[/blue]")
        console.print("\n[bold]Next steps:[/bold]")
        console.print(f"  [blue]crawlo run[/blue] {spider_name}")
        console.print(f"  [blue]crawlo check[/blue] {spider_name}")
        
        return 0
        
    except Exception as e:
        show_error_panel(
            "Creation Failed", 
            f"Failed to create spider: {e}"
        )
        return 1