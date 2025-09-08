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
        console.print("[bold red]❌ Usage:[/bold red] [blue]crawlo run[/blue] <spider_name>|all [bold yellow][--json] [--no-stats][/bold yellow]")
        console.print("💡 Examples:")
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
            msg = ":cross_mark: [bold red]Cannot find 'crawlo.cfg'[/bold red]\n💡 Run this command inside your project directory."
            if show_json:
                console.print_json(data={"success": False, "error": "Project root not found"})
                return 1
            else:
                console.print(Panel(
                    Text.from_markup(msg),
                    title="❌ Not in a Crawlo Project",
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
            msg = f"crawlo.cfg not found in {project_root}"
            if show_json:
                console.print_json(data={"success": False, "error": msg})
                return 1
            else:
                console.print(Panel(msg, title="❌ Missing Config", border_style="red"))
                return 1

        config = configparser.ConfigParser()
        config.read(cfg_file, encoding="utf-8")

        if not config.has_section("settings") or not config.has_option("settings", "default"):
            msg = "Missing [settings] section or 'default' option in crawlo.cfg"
            if show_json:
                console.print_json(data={"success": False, "error": msg})
                return 1
            else:
                console.print(Panel(msg, title="❌ Invalid Config", border_style="red"))
                return 1

        settings_module = config.get("settings", "default")
        project_package = settings_module.split(".")[0]

        # 3. 确保项目包可导入
        try:
            import_module(project_package)
        except ImportError as e:
            msg = f"Failed to import project package '{project_package}': {e}"
            if show_json:
                console.print_json(data={"success": False, "error": msg})
                return 1
            else:
                console.print(Panel(msg, title="❌ Import Error", border_style="red"))
                return 1

        # 4. 加载 settings 和爬虫模块
        settings = get_settings()
        spider_modules = [f"{project_package}.spiders"]
        process = CrawlerProcess(settings=settings, spider_modules=spider_modules)

        # === 情况1：运行所有爬虫 ===
        if spider_arg.lower() == "all":
            spider_names = process.get_spider_names()
            if not spider_names:
                msg = "No spiders found."
                if show_json:
                    console.print_json(data={"success": False, "error": msg})
                    return 1
                else:
                    console.print(Panel(
                        Text.from_markup(
                            ":cross_mark: [bold red]No spiders found.[/bold red]\n\n"
                            "[bold]💡 Make sure:[/bold]\n"
                            "  • Spiders are defined in '[cyan]spiders/[/cyan]'\n"
                            "  • They have a [green]`name`[/green] attribute\n"
                            "  • Modules are imported (e.g. via [cyan]__init__.py[/cyan])"
                        ),
                        title="❌ No Spiders",
                        border_style="red",
                        padding=(1, 2)
                    ))
                    return 1

            # 显示即将运行的爬虫列表
            table = Table(
                title=f"🚀 Starting ALL {len(spider_names)} spider(s)",
                box=box.ROUNDED,
                show_header=True,
                header_style="bold magenta"
            )
            table.add_column("Name", style="cyan")
            table.add_column("Class", style="green")

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
                task = progress.add_task("Running all spiders...", total=None)
                asyncio.run(process.crawl(spider_names))

            if show_json:
                console.print_json(data={"success": True, "spiders": spider_names})
            else:
                console.print(Panel(
                    ":tada: [bold green]All spiders completed successfully![/bold green]",
                    title="✅ All Done",
                    border_style="green"
                ))
            return 0

        # === 情况2：运行单个爬虫 ===
        spider_name = spider_arg
        if not process.is_spider_registered(spider_name):
            available = process.get_spider_names()
            msg = f"Spider '[cyan]{spider_name}[/cyan]' not found."
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
                    panel_content.append("\n💡 Available spiders:\n")
                    for name in sorted(available):
                        cls = process.get_spider_class(name)
                        panel_content.append(f"  • [cyan]{name}[/cyan] ([green]{cls.__name__}[/green])\n")
                else:
                    panel_content.append("\n💡 No spiders found. Check your spiders module.")

                console.print(Panel(
                    panel_content,
                    title="❌ Spider Not Found",
                    border_style="red",
                    padding=(1, 2)
                ))
                return 1

        spider_class = process.get_spider_class(spider_name)

        # 显示启动信息
        if not show_json:
            info_table = Table(
                title=f"🚀 Starting Spider: [bold cyan]{spider_name}[/bold cyan]",
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
            task = progress.add_task(f"Running {spider_name}...", total=None)
            asyncio.run(process.crawl(spider_name))

        if show_json:
            console.print_json(data={"success": True, "spider": spider_name})
        else:
            console.print(Panel(
                f":tada: [bold green]Spider '[cyan]{spider_name}[/cyan]' completed successfully![/bold green]",
                title="✅ Done",
                border_style="green"
            ))
        return 0

    except KeyboardInterrupt:
        msg = "⚠️  Spider interrupted by user."
        if show_json:
            console.print_json(data={"success": False, "error": msg})
        else:
            console.print(f"[bold yellow]{msg}[/bold yellow]")
        return 1
    except Exception as e:
        logger.exception("Exception during 'crawlo run'")
        msg = f"Unexpected error: {e}"
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