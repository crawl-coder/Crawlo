#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
# @Time    : 2025-08-31 22:36
# @Author  : crawl-coder
# @Desc    : 命令行入口：crawlo run <spider_name>|all，用于运行指定爬虫。
"""
import sys
import asyncio
import configparser
import os
from pathlib import Path
from importlib import import_module

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box
from rich.progress import Progress, SpinnerColumn, TextColumn

from crawlo.crawler import CrawlerProcess
from crawlo.utils.log import get_logger
from crawlo.project import get_settings
from crawlo.commands.stats import record_stats

logger = get_logger(__name__)
console = Console()


def get_project_root():
    """
    向上查找 crawlo.cfg 来确定项目根目录
    """
    current = Path.cwd()
    # 首先检查当前目录及其子目录
    for root, dirs, files in os.walk(current):
        if "crawlo.cfg" in files:
            return Path(root)
    
    # 如果在子目录中没找到，再向上查找
    for _ in range(10):
        cfg = current / "crawlo.cfg"
        if cfg.exists():
            return current
        if current == current.parent:
            break
        current = current.parent
    return None


def main(args):
    """
    主函数：运行指定爬虫
    用法:
        crawlo run <spider_name>|all [--json] [--no-stats]
    """
    if len(args) < 1:
        console.print("[bold red]❌ 用法:[/bold red] [blue]crawlo run[/blue] <爬虫名称>|all [bold yellow][--json] [--no-stats][/bold yellow]")
        console.print("💡 示例:")
        console.print("   [blue]crawlo run baidu[/blue]")
        console.print("   [blue]crawlo run all[/blue]")
        console.print("   [blue]crawlo run all --json --no-stats[/blue]")
        return 1

    # 解析参数
    spider_arg = args[0]
    show_json = "--json" in args
    no_stats = "--no-stats" in args

    try:
        # 1. 查找项目根目录
        project_root = get_project_root()
        if not project_root:
            msg = ":cross_mark: [bold red]找不到 'crawlo.cfg'[/bold red]\n💡 请在项目目录中运行此命令。"
            if show_json:
                console.print_json(data={"success": False, "error": "未找到项目根目录"})
                return 1
            else:
                console.print(Panel(
                    Text.from_markup(msg),
                    title="❌ 非Crawlo项目",
                    border_style="red",
                    padding=(1, 2)
                ))
                return 1

        project_root_str = str(project_root)
        if project_root_str not in sys.path:
            sys.path.insert(0, project_root_str)

        # 2. 读取 crawlo.cfg 获取 settings 模块
        cfg_file = project_root / "crawlo.cfg"
        if not cfg_file.exists():
            msg = f"在 {project_root} 中未找到 crawlo.cfg"
            if show_json:
                console.print_json(data={"success": False, "error": msg})
                return 1
            else:
                console.print(Panel(msg, title="❌ 缺少配置文件", border_style="red"))
                return 1

        config = configparser.ConfigParser()
        config.read(cfg_file, encoding="utf-8")

        if not config.has_section("settings") or not config.has_option("settings", "default"):
            msg = "crawlo.cfg 中缺少 [settings] 部分或 'default' 选项"
            if show_json:
                console.print_json(data={"success": False, "error": msg})
                return 1
            else:
                console.print(Panel(msg, title="❌ 无效配置", border_style="red"))
                return 1

        settings_module = config.get("settings", "default")
        project_package = settings_module.split(".")[0]

        # 3. 确保项目包可导入
        try:
            import_module(project_package)
        except ImportError as e:
            msg = f"导入项目包 '{project_package}' 失败: {e}"
            if show_json:
                console.print_json(data={"success": False, "error": msg})
                return 1
            else:
                console.print(Panel(msg, title="❌ 导入错误", border_style="red"))
                return 1

        # 4. 加载 settings 和爬虫模块
        settings = get_settings()
        spider_modules = [f"{project_package}.spiders"]
        process = CrawlerProcess(settings=settings, spider_modules=spider_modules)

        # === 情况1：运行所有爬虫 ===
        if spider_arg.lower() == "all":
            spider_names = process.get_spider_names()
            if not spider_names:
                msg = "未找到爬虫。"
                if show_json:
                    console.print_json(data={"success": False, "error": msg})
                    return 1
                else:
                    console.print(Panel(
                        Text.from_markup(
                            ":cross_mark: [bold red]未找到爬虫。[/bold red]\n\n"
                            "[bold]💡 确保:[/bold]\n"
                            "  • 爬虫定义于 '[cyan]spiders/[/cyan]' 目录\n"
                            "  • 具有 [green]`name`[/green] 属性\n"
                            "  • 模块已导入 (例如通过 [cyan]__init__.py[/cyan])"
                        ),
                        title="❌ 未找到爬虫",
                        border_style="red",
                        padding=(1, 2)
                    ))
                    return 1

            # 显示即将运行的爬虫列表
            table = Table(
                title=f"🚀 启动全部 {len(spider_names)} 个爬虫",
                box=box.ROUNDED,
                show_header=True,
                header_style="bold magenta"
            )
            table.add_column("名称", style="cyan")
            table.add_column("类名", style="green")

            for name in sorted(spider_names):
                cls = process.get_spider_class(name)
                table.add_row(name, cls.__name__)

            console.print(table)
            console.print()

            # 注册 stats 记录（除非 --no-stats）
            if not no_stats:
                for crawler in process.crawlers:
                    crawler.signals.connect(record_stats, signal="spider_closed")

            # 并行运行所有爬虫
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True,
            ) as progress:
                task = progress.add_task("正在运行所有爬虫...", total=None)
                asyncio.run(process.crawl(spider_names))

            if show_json:
                console.print_json(data={"success": True, "spiders": spider_names})
            else:
                console.print(Panel(
                    ":tada: [bold green]所有爬虫运行完成！[/bold green]",
                    title="✅ 全部完成",
                    border_style="green"
                ))
            return 0

        # === 情况2：运行单个爬虫 ===
        spider_name = spider_arg
        if not process.is_spider_registered(spider_name):
            available = process.get_spider_names()
            msg = f"爬虫 '[cyan]{spider_name}[/cyan]' 未找到。"
            if show_json:
                console.print_json(data={
                    "success": False,
                    "error": msg,
                    "available": available
                })
                return 1
            else:
                panel_content = Text.from_markup(msg + "\n")
                if available:
                    panel_content.append("\n💡 可用爬虫:\n")
                    for name in sorted(available):
                        cls = process.get_spider_class(name)
                        panel_content.append(f"  • [cyan]{name}[/cyan] ([green]{cls.__name__}[/green])\n")
                else:
                    panel_content.append("\n💡 未找到爬虫。请检查爬虫模块。")

                console.print(Panel(
                    panel_content,
                    title="❌ 爬虫未找到",
                    border_style="red",
                    padding=(1, 2)
                ))
                return 1

        spider_class = process.get_spider_class(spider_name)

        # 显示启动信息
        if not show_json:
            info_table = Table(
                title=f"🚀 启动爬虫: [bold cyan]{spider_name}[/bold cyan]",
                box=box.SIMPLE,
                show_header=False,
                title_style="bold green"
            )
            info_table.add_column("Key", style="yellow")
            info_table.add_column("Value", style="cyan")
            info_table.add_row("Project", project_package)
            info_table.add_row("Class", spider_class.__name__)
            info_table.add_row("Module", spider_class.__module__)
            console.print(info_table)
            console.print()

        # 注册 stats 记录
        if not no_stats:
            for crawler in process.crawlers:
                crawler.signals.connect(record_stats, signal="spider_closed")

        # 运行爬虫
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            task = progress.add_task(f"正在运行 {spider_name}...", total=None)
            asyncio.run(process.crawl(spider_name))

        if show_json:
            console.print_json(data={"success": True, "spider": spider_name})
        else:
            console.print(Panel(
                f":tada: [bold green]爬虫 '[cyan]{spider_name}[/cyan]' 运行完成！[/bold green]",
                title="✅ 完成",
                border_style="green"
            ))
        return 0

    except KeyboardInterrupt:
        msg = "⚠️  爬虫被用户中断。"
        if show_json:
            console.print_json(data={"success": False, "error": msg})
        else:
            console.print(f"[bold yellow]{msg}[/bold yellow]")
        return 1
    except Exception as e:
        logger.exception("Exception during 'crawlo run'")
        msg = f"意外错误: {e}"
        if show_json:
            console.print_json(data={"success": False, "error": msg})
        else:
            console.print(f"[bold red]❌ {msg}[/bold red]")
        return 1


if __name__ == "__main__":
    """
    支持直接运行：
        python -m crawlo.commands.run spider_name
    """
    sys.exit(main(sys.argv[1:]))