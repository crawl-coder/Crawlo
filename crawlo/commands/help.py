#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
# @Time    : 2025-09-12
# @Author  : crawl-coder
# @Desc    : 命令行入口：crawlo -h|--help，显示帮助信息。
"""
import sys
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box
from crawlo.utils.env_config import get_version

# 获取框架版本号
VERSION = get_version()

console = Console()


def main(args):
    """
    主函数：显示帮助信息
    用法:
        crawlo -h|--help
    """
    # 检查是否有无效参数
    if args and args[0] not in ['-h', '--help', 'help']:
        console.print("[bold red]无效参数:[/bold red] [yellow]{}[/yellow]".format(args[0]))
        console.print("[bold blue]提示:[/bold blue] 使用 [green]crawlo -h[/green] 或 [green]crawlo --help[/green] 查看帮助信息")
        return 1

    # 显示帮助信息
    show_help()
    return 0


def show_help():
    """显示完整的帮助信息"""
    # 显示框架标题和版本
    console.print(Panel(
        Text.from_markup(f"[bold blue]Crawlo[/bold blue] [bold white]v{VERSION}[/bold white] - 异步爬虫框架"),
        expand=False,
        border_style="blue"
    ))
    
    # 显示基本用法
    console.print("[bold green]基本用法:[/bold green]")
    console.print("  [blue]crawlo[/blue] [cyan]<command>[/cyan] [options]")
    console.print()
    
    # 显示可用命令
    console.print("[bold green]可用命令:[/bold green]")
    table = Table(box=box.SIMPLE, show_header=True, header_style="bold magenta")
    table.add_column("命令", style="cyan", width=15)
    table.add_column("描述", style="white")
    table.add_column("用法", style="yellow")
    
    table.add_row("startproject", "创建新项目", "crawlo startproject <project_name>")
    table.add_row("genspider", "生成爬虫模板", "crawlo genspider <spider_name> [domain]")
    table.add_row("run", "运行爬虫", "crawlo run <spider_name>|all [options]")
    table.add_row("check", "检查爬虫代码", "crawlo check [options]")
    table.add_row("list", "列出所有爬虫", "crawlo list")
    table.add_row("stats", "查看统计信息", "crawlo stats [spider_name]")
    table.add_row("help", "显示帮助信息", "crawlo -h|--help")
    
    console.print(table)
    console.print()
    
    # 显示全局选项
    console.print("[bold green]全局选项:[/bold green]")
    table = Table(box=box.SIMPLE, show_header=False)
    table.add_column("选项", style="cyan", width=15)
    table.add_column("描述", style="white")
    
    table.add_row("-h, --help", "显示帮助信息")
    table.add_row("-v, --version", "显示版本信息")
    
    console.print(table)
    console.print()
    
    # 显示各命令的详细用法
    console.print("[bold green]命令详细用法:[/bold green]")
    
    # run 命令
    console.print("[bold cyan]run[/bold cyan] - 运行爬虫")
    console.print("  用法: crawlo run <spider_name>|all [--json] [--no-stats]")
    console.print("  示例:")
    console.print("    crawlo run myspider")
    console.print("    crawlo run all")
    console.print("    crawlo run all --json --no-stats")
    console.print()
    

    
    # check 命令
    console.print("[bold cyan]check[/bold cyan] - 检查爬虫代码")
    console.print("  用法: crawlo check [--fix] [--ci] [--json] [--watch]")
    console.print("  示例:")
    console.print("    crawlo check")
    console.print("    crawlo check --fix")
    console.print("    crawlo check --ci --json")
    console.print()
    
    # startproject 命令
    console.print("[bold cyan]startproject[/bold cyan] - 创建新项目")
    console.print("  用法: crawlo startproject <project_name>")
    console.print("  示例:")
    console.print("    crawlo startproject myproject")
    console.print()
    
    # genspider 命令
    console.print("[bold cyan]genspider[/bold cyan] - 生成爬虫模板")
    console.print("  用法: crawlo genspider <spider_name> [domain]")
    console.print("  示例:")
    console.print("    crawlo genspider myspider example.com")
    console.print()
    
    # list 命令
    console.print("[bold cyan]list[/bold cyan] - 列出所有爬虫")
    console.print("  用法: crawlo list")
    console.print("  示例:")
    console.print("    crawlo list")
    console.print()
    
    # stats 命令
    console.print("[bold cyan]stats[/bold cyan] - 查看统计信息")
    console.print("  用法: crawlo stats [spider_name]")
    console.print("  示例:")
    console.print("    crawlo stats")
    console.print("    crawlo stats myspider")
    console.print()
    
    # 显示更多信息
    # console.print("[bold green]更多信息:[/bold green]")
    # console.print("  文档: https://crawlo.readthedocs.io/")
    # console.print("  源码: https://github.com/crawl-coder/Crawlo")
    # console.print("  问题: https://github.com/crawl-coder/Crawlo/issues")