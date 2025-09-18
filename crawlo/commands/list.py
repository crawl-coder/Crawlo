#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
# @Time    : 2025-08-31 22:33
# @Author  : crawl-coder
# @Desc    : 命令行入口：crawlo list，用于列出所有已注册的爬虫
"""
import sys
from pathlib import Path
from importlib import import_module

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box

from crawlo.crawler import CrawlerProcess
from crawlo.utils.log import get_logger
from .utils import validate_project_environment, show_error_panel

logger = get_logger(__name__)
console = Console()


def main(args):
    """
    主函数：列出所有可用爬虫
    用法: crawlo list [--json]
    """
    show_json = "--json" in args
    
    # 过滤掉参数后检查是否有额外参数
    filtered_args = [arg for arg in args if not arg.startswith('--')]
    if filtered_args:
        if show_json:
            console.print_json(data={"success": False, "error": "用法: crawlo list [--json]"})
        else:
            console.print("[bold red]❌ 错误:[/bold red] 用法: [blue]crawlo list[/blue] [--json]")
        return 1

    try:
        # 验证项目环境
        is_valid, project_package, error_msg = validate_project_environment()
        if not is_valid:
            if show_json:
                console.print_json(data={"success": False, "error": error_msg})
            else:
                show_error_panel("非Crawlo项目", error_msg)
            return 1

        # 初始化 CrawlerProcess 并加载爬虫模块
        spider_modules = [f"{project_package}.spiders"]
        process = CrawlerProcess(spider_modules=spider_modules)

        # 获取所有爬虫名称
        spider_names = process.get_spider_names()
        if not spider_names:
            if show_json:
                console.print_json(data={
                    "success": True, 
                    "spiders": [],
                    "message": "项目中未找到爬虫"
                })
            else:
                console.print(Panel(
                    Text.from_markup(
                        ":envelope_with_arrow: [bold]未找到爬虫[/bold] 于 '[cyan]spiders/[/cyan]' 目录。\n\n"
                        "[bold]💡 确保:[/bold]\n"
                        "  • 爬虫类继承自 [blue]`crawlo.spider.Spider`[/blue]\n"
                        "  • 每个爬虫都有 [green]`name`[/green] 属性\n"
                        "  • 爬虫已在 [cyan]`spiders/__init__.py`[/cyan] 中导入 (如果使用包)"
                    ),
                    title="📭 未找到爬虫",
                    border_style="yellow",
                    padding=(1, 2)
                ))
            return 0

        # 准备爬虫信息
        spider_info = []
        for name in sorted(spider_names):
            spider_cls = process.get_spider_class(name)
            module_name = spider_cls.__module__.replace(f"{project_package}.", "")
            
            # 获取额外信息
            start_urls_count = len(getattr(spider_cls, 'start_urls', []))
            allowed_domains = getattr(spider_cls, 'allowed_domains', [])
            custom_settings = getattr(spider_cls, 'custom_settings', {})
            
            spider_info.append({
                "name": name,
                "class": spider_cls.__name__,
                "module": module_name,
                "start_urls_count": start_urls_count,
                "allowed_domains": allowed_domains,
                "has_custom_settings": bool(custom_settings)
            })

        # JSON 输出
        if show_json:
            console.print_json(data={
                "success": True,
                "count": len(spider_info),
                "spiders": spider_info
            })
            return 0

        # 表格输出
        table = Table(
            title=f"📋 找到 {len(spider_names)} 个爬虫",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold magenta",
            title_style="bold green"
        )
        table.add_column("名称", style="cyan", no_wrap=True)
        table.add_column("类名", style="green")
        table.add_column("模块", style="dim")
        table.add_column("URL数", style="blue", justify="center")
        table.add_column("域名", style="yellow")
        table.add_column("自定义设置", style="magenta", justify="center")

        for info in spider_info:
            domains_display = ", ".join(info["allowed_domains"][:2])  # 显示前2个域名
            if len(info["allowed_domains"]) > 2:
                domains_display += f" (+{len(info['allowed_domains'])-2})"
            elif not domains_display:
                domains_display = "-"
                
            table.add_row(
                info["name"],
                info["class"],
                info["module"],
                str(info["start_urls_count"]),
                domains_display,
                "✓" if info["has_custom_settings"] else "-"
            )

        console.print(table)
        
        # 显示使用提示
        console.print("\n[bold]🚀 下一步操作:[/bold]")
        console.print("  [blue]crawlo run[/blue] <爬虫名称>    # 运行指定爬虫")
        console.print("  [blue]crawlo run[/blue] all             # 运行所有爬虫")
        console.print("  [blue]crawlo check[/blue] <爬虫名称>  # 检查爬虫有效性")
        
        return 0

    except Exception as e:
        if show_json:
            console.print_json(data={"success": False, "error": str(e)})
        else:
            console.print(f"[bold red]❌ 意外错误:[/bold red] {e}")
        logger.exception("执行 'crawlo list' 时发生异常")
        return 1