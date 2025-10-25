#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
# @Time    : 2025-08-31 22:36
# @Author  : crawl-coder
# @Desc    : 命令行入口：crawlo stats，查看最近运行的爬虫统计信息。
"""
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box

from crawlo.logging import get_logger


logger = get_logger(__name__)
console = Console()

# 默认存储目录（相对于项目根目录）
STATS_DIR = "logs/stats"


def get_stats_dir() -> Path:
    """
    获取统计文件存储目录，优先使用项目根下的 logs/stats/
    如果不在项目中，回退到当前目录
    """
    current = Path.cwd()
    for _ in range(10):
        if (current / "crawlo.cfg").exists():
            return current / STATS_DIR
        if current == current.parent:
            break
        current = current.parent
    return Path.cwd() / STATS_DIR


def record_stats(crawler):
    """
    【供爬虫运行时调用】记录爬虫结束后的统计信息到 JSON 文件
    需在 Crawler 的 closed 回调中调用
    """
    spider_name = getattr(crawler.spider, "name", "unknown")
    stats = crawler.stats.get_stats() if crawler.stats else {}

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    stats_dir = Path(get_stats_dir())
    stats_dir.mkdir(parents=True, exist_ok=True)

    filename = stats_dir / f"{spider_name}_{timestamp}.json"
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump({
                "spider": spider_name,
                "timestamp": datetime.now().isoformat(),
                "stats": stats
            }, f, ensure_ascii=False, indent=2, default=str)
        logger.info(f"Stats for spider '{spider_name}' saved to {filename}")
    except Exception as e:
        logger.error(f"保存 '{spider_name}' 的统计信息失败: {e}")


def load_all_stats() -> Dict[str, list]:
    """
    加载所有已保存的统计文件，按 spider name 分组
    返回: {spider_name: [stats_record, ...]}
    """
    stats_dir = get_stats_dir()
    if not stats_dir.exists():
        return {}

    result = {}
    json_files = sorted(stats_dir.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True)

    for file in json_files:
        try:
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)
            spider_name = data.get("spider", "unknown")
            result.setdefault(spider_name, []).append(data)
        except Exception as e:
            logger.warning(f"加载统计文件 {file} 失败: {e}")
    return result


def format_value(v: Any) -> str:
    """格式化值，防止太长或不可打印"""
    if isinstance(v, float):
        return f"{v:.4f}"
    s = str(v)
    if len(s) > 80:
        return s[:77] + "..."
    return s


def display_stats_table(stats_data: dict, title: str = "统计信息"):
    """通用函数：用 rich.table 展示统计数据"""
    table = Table(title=title, box=box.ROUNDED, show_header=True, header_style="bold magenta")
    table.add_column("键", style="cyan", no_wrap=True)
    table.add_column("值", style="green")

    for k in sorted(stats_data.keys()):
        table.add_row(k, format_value(stats_data[k]))

    console.print(table)


def main(args):
    """
    主函数：查看统计信息
    用法:
        crawlo stats                 → 显示所有爬虫最近一次运行
        crawlo stats myspider        → 显示指定爬虫所有历史记录
        crawlo stats myspider --all  → 显示所有历史（同上）
    """
    if len(args) > 2:
        console.print("[bold red]错误:[/bold red] 用法: [blue]crawlo stats[/blue] [爬虫名称] [--all]")
        return 1

    spider_name = None
    show_all = False

    if args:
        spider_name = args[0]
        show_all = "--all" in args or "-a" in args

    all_stats = load_all_stats()

    if not all_stats:
        console.print(Panel(
            Text.from_markup(
                "[bold]未找到统计信息。[/bold]\n"
                "先运行一个爬虫以生成统计信息。\n"
                f"统计目录: [cyan]{get_stats_dir()}[/cyan]"
            ),
            title="统计信息",
            border_style="yellow",
            padding=(1, 2)
        ))
        return 0

    # 显示所有爬虫最近一次运行
    if not spider_name:
        console.print(Panel(
            "[bold]最近的爬虫统计信息（上次运行）[/bold]",
            title="爬虫统计概览",
            border_style="green",
            padding=(0, 1)
        ))

        for name, runs in all_stats.items():
            latest = runs[0]
            ts = latest['timestamp'][:19]
            console.print(f" [bold cyan]{name}[/bold cyan] ([green]{ts}[/green])")
            display_stats_table(latest["stats"], title=f"{name} 的统计信息")
            console.print()  # 空行分隔

        return 0

    # 显示指定爬虫的历史
    if spider_name not in all_stats:
        console.print(f"[bold red]未找到爬虫 '[cyan]{spider_name}[/cyan]' 的统计信息[/bold red]")
        available = ', '.join(all_stats.keys())
        if available:
            console.print(f"可用爬虫: [green]{available}[/green]")
        return 1

    runs = all_stats[spider_name]
    if show_all:
        console.print(f"[bold]'[cyan]{spider_name}[/cyan]' 的所有运行记录 ({len(runs)} 次):[/bold]")
    else:
        runs = runs[:1]
        console.print(f"[bold]'[cyan]{spider_name}[/cyan]' 的上次运行:[/bold]")

    for i, run in enumerate(runs, 1):
        ts = run['timestamp']
        subtitle = f"运行 #{i} · {ts}" if show_all else f"上次运行 · {ts}"
        display_stats_table(run["stats"], title=f"{spider_name} 的统计信息 — {subtitle}")
        if i < len(runs):
            console.print("─" * 60)

    return 0