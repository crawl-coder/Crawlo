#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
# @Time    : 2025-08-31 22:35
# @Author  : crawl-coder
# @Desc    : 命令行入口：crawlo check，检查所有爬虫定义是否合规。
"""
import sys
import ast
import astor
import re
import time
from pathlib import Path
import configparser
from importlib import import_module

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from crawlo.crawler import CrawlerProcess
from crawlo.utils.log import get_logger


logger = get_logger(__name__)
console = Console()


def get_project_root():
    """
    从当前目录向上查找 crawlo.cfg，确定项目根目录
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


def auto_fix_spider_file(spider_cls, file_path: Path):
    """自动修复 spider 文件中的常见问题"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()

        fixed = False
        tree = ast.parse(source)

        # 查找 Spider 类定义
        class_node = None
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == spider_cls.__name__:
                class_node = node
                break

        if not class_node:
            return False, "Could not find class definition in file."

        # 1. 修复 name 为空或缺失
        name_assign = None
        for node in class_node.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "name":
                        name_assign = node
                        break

        if not name_assign or (
            isinstance(name_assign.value, ast.Constant) and not name_assign.value.value
        ):
            # 生成默认 name：类名转 snake_case
            default_name = re.sub(r'(?<!^)(?=[A-Z])', '_', spider_cls.__name__).lower().replace("_spider", "")
            new_assign = ast.Assign(
                targets=[ast.Name(id="name", ctx=ast.Store())],
                value=ast.Constant(value=default_name)
            )
            if name_assign:
                index = class_node.body.index(name_assign)
                class_node.body[index] = new_assign
            else:
                class_node.body.insert(0, new_assign)
            fixed = True

        # 2. 修复 start_urls 是字符串
        start_urls_assign = None
        for node in class_node.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "start_urls":
                        start_urls_assign = node
                        break

        if start_urls_assign and isinstance(start_urls_assign.value, ast.Constant) and isinstance(start_urls_assign.value.value, str):
            new_value = ast.List(elts=[ast.Constant(value=start_urls_assign.value.value)], ctx=ast.Load())
            start_urls_assign.value = new_value
            fixed = True

        # 3. 修复缺少 parse 方法
        has_parse = any(
            isinstance(node, ast.FunctionDef) and node.name == "parse"
            for node in class_node.body
        )
        if not has_parse:
            parse_method = ast.FunctionDef(
                name="parse",
                args=ast.arguments(
                    posonlyargs=[],
                    args=[ast.arg(arg="self"), ast.arg(arg="response")],
                    kwonlyargs=[],
                    kw_defaults=[],
                    defaults=[],
                    vararg=None,
                    kwarg=None
                ),
                body=[
                    ast.Expr(value=ast.Constant(value="默认 parse 方法，返回 item 或继续请求")),
                    ast.Pass()
                ],
                decorator_list=[],
                returns=None
            )
            class_node.body.append(parse_method)
            fixed = True

        # 4. 修复 allowed_domains 是字符串
        allowed_domains_assign = None
        for node in class_node.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "allowed_domains":
                        allowed_domains_assign = node
                        break

        if allowed_domains_assign and isinstance(allowed_domains_assign.value, ast.Constant) and isinstance(allowed_domains_assign.value.value, str):
            new_value = ast.List(elts=[ast.Constant(value=allowed_domains_assign.value.value)], ctx=ast.Load())
            allowed_domains_assign.value = new_value
            fixed = True

        # 5. 修复缺失 custom_settings
        has_custom_settings = any(
            isinstance(node, ast.Assign) and
            any(isinstance(t, ast.Name) and t.id == "custom_settings" for t in node.targets)
            for node in class_node.body
        )
        if not has_custom_settings:
            new_assign = ast.Assign(
                targets=[ast.Name(id="custom_settings", ctx=ast.Store())],
                value=ast.Dict(keys=[], values=[])
            )
            # 插入在 name 之后
            insert_index = 1
            for i, node in enumerate(class_node.body):
                if isinstance(node, ast.Assign) and any(
                    isinstance(t, ast.Name) and t.id == "name" for t in node.targets
                ):
                    insert_index = i + 1
                    break
            class_node.body.insert(insert_index, new_assign)
            fixed = True

        # 6. 修复缺失 start_requests 方法
        has_start_requests = any(
            isinstance(node, ast.FunctionDef) and node.name == "start_requests"
            for node in class_node.body
        )
        if not has_start_requests:
            start_requests_method = ast.FunctionDef(
                name="start_requests",
                args=ast.arguments(
                    posonlyargs=[],
                    args=[ast.arg(arg="self")],
                    kwonlyargs=[],
                    kw_defaults=[],
                    defaults=[],
                    vararg=None,
                    kwarg=None
                ),
                body=[
                    ast.Expr(value=ast.Constant(value="默认 start_requests，从 start_urls 生成请求")),
                    ast.For(
                        target=ast.Name(id="url", ctx=ast.Store()),
                        iter=ast.Attribute(value=ast.Name(id="self", ctx=ast.Load()), attr="start_urls", ctx=ast.Load()),
                        body=[
                            ast.Expr(
                                value=ast.Call(
                                    func=ast.Attribute(value=ast.Name(id="self", ctx=ast.Load()), attr="make_request", ctx=ast.Load()),
                                    args=[ast.Name(id="url", ctx=ast.Load())],
                                    keywords=[]
                                )
                            )
                        ],
                        orelse=[]
                    )
                ],
                decorator_list=[],
                returns=None
            )
            # 插入在 custom_settings 或 name 之后，parse 之前
            insert_index = 2
            for i, node in enumerate(class_node.body):
                if isinstance(node, ast.FunctionDef) and node.name == "parse":
                    insert_index = i
                    break
                elif isinstance(node, ast.Assign) and any(
                    isinstance(t, ast.Name) and t.id in ("name", "custom_settings") for t in node.targets
                ):
                    insert_index = i + 1
            class_node.body.insert(insert_index, start_requests_method)
            fixed = True

        if fixed:
            fixed_source = astor.to_source(tree)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(fixed_source)
            return True, "File auto-fixed successfully."
        else:
            return False, "No fixable issues found."

    except Exception as e:
        return False, f"Failed to auto-fix: {e}"


class SpiderChangeHandler(FileSystemEventHandler):
    def __init__(self, project_root, spider_modules, show_fix=False, console=None):
        self.project_root = project_root
        self.spider_modules = spider_modules
        self.show_fix = show_fix
        self.console = console or Console()

    def on_modified(self, event):
        if event.is_directory:
            return
        if event.src_path.endswith(".py") and "spiders" in event.src_path:
            file_path = Path(event.src_path)
            spider_name = file_path.stem
            self.console.print(f"\n:eyes: [bold blue]Detected change in[/bold blue] [cyan]{file_path}[/cyan]")
            self.check_and_fix_spider(spider_name)

    def check_and_fix_spider(self, spider_name):
        try:
            process = CrawlerProcess(spider_modules=self.spider_modules)
            if spider_name not in process.get_spider_names():
                self.console.print(f"[yellow]⚠️  {spider_name} is not a registered spider.[/yellow]")
                return

            cls = process.get_spider_class(spider_name)
            issues = []

            # 简化检查
            if not getattr(cls, "name", None):
                issues.append("missing or empty 'name' attribute")
            if not callable(getattr(cls, "start_requests", None)):
                issues.append("missing 'start_requests' method")
            if hasattr(cls, "start_urls") and isinstance(cls.start_urls, str):
                issues.append("'start_urls' is string")
            if hasattr(cls, "allowed_domains") and isinstance(cls.allowed_domains, str):
                issues.append("'allowed_domains' is string")

            try:
                spider = cls.create_instance(None)
                if not callable(getattr(spider, "parse", None)):
                    issues.append("no 'parse' method")
            except Exception:
                issues.append("failed to instantiate")

            if issues:
                self.console.print(f"[red]❌ {spider_name} has issues:[/red]")
                for issue in issues:
                    self.console.print(f"  • {issue}")

                if self.show_fix:
                    file_path = Path(cls.__file__)
                    fixed, msg = auto_fix_spider_file(cls, file_path)
                    if fixed:
                        self.console.print(f"[green]✅ Auto-fixed: {msg}[/green]")
                    else:
                        self.console.print(f"[yellow]⚠️  Could not fix: {msg}[/yellow]")
            else:
                self.console.print(f"[green]✅ {spider_name} is compliant.[/green]")

        except Exception as e:
            self.console.print(f"[red]❌ Error checking {spider_name}: {e}[/red]")


def watch_spiders(project_root, project_package, show_fix=False):
    console = Console()
    spider_path = project_root / project_package / "spiders"
    if not spider_path.exists():
        console.print(f"[red]❌ Spiders directory not found: {spider_path}[/red]")
        return

    spider_modules = [f"{project_package}.spiders"]
    event_handler = SpiderChangeHandler(project_root, spider_modules, show_fix, console)
    observer = Observer()
    observer.schedule(event_handler, str(spider_path), recursive=False)

    console.print(Panel(
        f":eyes: [bold blue]Watching for changes in[/bold blue] [cyan]{spider_path}[/cyan]\n"
        "Edit any spider file to trigger auto-check...",
        title="🚀 Watch Mode Started",
        border_style="blue"
    ))

    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        console.print("\n[bold red]🛑 Watch mode stopped.[/bold red]")
        observer.stop()
    observer.join()


def main(args):
    """
    主函数：检查所有爬虫定义的合规性
    用法:
        crawlo check
        crawlo check --fix
        crawlo check --ci
        crawlo check --json
        crawlo check --watch
    """
    show_fix = "--fix" in args or "-f" in args
    show_ci = "--ci" in args
    show_json = "--json" in args
    show_watch = "--watch" in args

    valid_args = {"--fix", "-f", "--ci", "--json", "--watch"}
    if any(arg not in valid_args for arg in args):
        console.print("[bold red]❌ Error:[/bold red] Usage: [blue]crawlo check[/blue] [--fix] [--ci] [--json] [--watch]")
        return 1

    try:
        # 1. 查找项目根目录
        project_root = get_project_root()
        if not project_root:
            msg = ":cross_mark: [bold red]Cannot find 'crawlo.cfg'[/bold red]\n💡 Run this command inside your project directory."
            if show_json:
                console.print_json(data={"success": False, "error": "Project root not found"})
                return 1
            elif show_ci:
                console.print("❌ Project root not found. crawlo.cfg missing.")
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

        # 2. 读取 crawlo.cfg
        cfg_file = project_root / "crawlo.cfg"
        if not cfg_file.exists():
            msg = f"Config file not found: {cfg_file}"
            if show_json:
                console.print_json(data={"success": False, "error": msg})
                return 1
            elif show_ci:
                console.print(f"❌ {msg}")
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
            elif show_ci:
                console.print(f"❌ {msg}")
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
            elif show_ci:
                console.print(f"❌ {msg}")
                return 1
            else:
                console.print(Panel(msg, title="❌ Import Error", border_style="red"))
                return 1

        # 4. 加载爬虫
        spider_modules = [f"{project_package}.spiders"]
        process = CrawlerProcess(spider_modules=spider_modules)
        spider_names = process.get_spider_names()

        if not spider_names:
            msg = "No spiders found."
            if show_json:
                console.print_json(data={"success": True, "warning": msg})
                return 0
            elif show_ci:
                console.print("📭 No spiders found.")
                return 0
            else:
                console.print(Panel(
                    Text.from_markup(
                        ":envelope_with_arrow: [bold]No spiders found[/bold]\n\n"
                        "[bold]💡 Make sure:[/bold]\n"
                        "  • Spiders are defined in '[cyan]spiders[/cyan]' module\n"
                        "  • They have a [green]`name`[/green] attribute\n"
                        "  • Modules are properly imported"
                    ),
                    title="📭 No Spiders Found",
                    border_style="yellow",
                    padding=(1, 2)
                ))
                return 0

        # 5. 如果启用 watch 模式，启动监听
        if show_watch:
            console.print("[bold blue]:eyes: Starting watch mode...[/bold blue]")
            watch_spiders(project_root, project_package, show_fix)
            return 0  # watch 是长期运行，不返回

        # 6. 开始检查（非 watch 模式）
        if not show_ci and not show_json:
            console.print(f":mag: [bold]Checking {len(spider_names)} spider(s)...[/bold]\n")

        issues_found = False
        results = []

        for name in sorted(spider_names):
            cls = process.get_spider_class(name)
            issues = []

            # 检查 name 属性
            if not getattr(cls, "name", None):
                issues.append("missing or empty 'name' attribute")
            elif not isinstance(cls.name, str):
                issues.append("'name' is not a string")

            # 检查 start_requests 是否可调用
            if not callable(getattr(cls, "start_requests", None)):
                issues.append("missing or non-callable 'start_requests' method")

            # 检查 start_urls 类型（不应是字符串）
            if hasattr(cls, "start_urls") and isinstance(cls.start_urls, str):
                issues.append("'start_urls' is a string; should be list or tuple")

            # 检查 allowed_domains 类型
            if hasattr(cls, "allowed_domains") and isinstance(cls.allowed_domains, str):
                issues.append("'allowed_domains' is a string; should be list or tuple")

            # 实例化并检查 parse 方法
            try:
                spider = cls.create_instance(None)
                if not callable(getattr(spider, "parse", None)):
                    issues.append("no 'parse' method defined (recommended)")
            except Exception as e:
                issues.append(f"failed to instantiate spider: {e}")

            # 自动修复（如果启用）
            if issues and show_fix:
                try:
                    file_path = Path(cls.__file__)
                    fixed, msg = auto_fix_spider_file(cls, file_path)
                    if fixed:
                        if not show_ci and not show_json:
                            console.print(f"[green]🔧 Auto-fixed {name} → {msg}[/green]")
                        issues = []  # 认为已修复
                    else:
                        if not show_ci and not show_json:
                            console.print(f"[yellow]⚠️  Could not auto-fix {name}: {msg}[/yellow]")
                except Exception as e:
                    if not show_ci and not show_json:
                        console.print(f"[yellow]⚠️  Failed to locate source file for {name}: {e}[/yellow]")

            results.append({
                "name": name,
                "class": cls.__name__,
                "file": getattr(cls, "__file__", "unknown"),
                "issues": issues
            })

            if issues:
                issues_found = True

        # 7. 生成报告数据
        report = {
            "success": not issues_found,
            "total_spiders": len(spider_names),
            "issues": [
                {"name": r["name"], "class": r["class"], "file": r["file"], "problems": r["issues"]}
                for r in results if r["issues"]
            ]
        }

        # 8. 输出（根据模式）
        if show_json:
            console.print_json(data=report)
            return 1 if issues_found else 0

        if show_ci:
            if issues_found:
                console.print("❌ Compliance check failed.")
                for r in results:
                    if r["issues"]:
                        console.print(f"  • {r['name']}: {', '.join(r['issues'])}")
            else:
                console.print("✅ All spiders compliant.")
            return 1 if issues_found else 0

        # 9. 默认 rich 输出
        table = Table(
            title="🔍 Spider Compliance Check Results",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold magenta",
            title_style="bold green"
        )
        table.add_column("Status", style="bold", width=4)
        table.add_column("Name", style="cyan")
        table.add_column("Class", style="green")
        table.add_column("Issues", style="yellow", overflow="fold")

        for res in results:
            if res["issues"]:
                status = "[red]❌[/red]"
                issues_text = "\n".join(f"• {issue}" for issue in res["issues"])
            else:
                status = "[green]✅[/green]"
                issues_text = "—"

            table.add_row(status, res["name"], res["class"], issues_text)

        console.print(table)
        console.print()

        if issues_found:
            console.print(Panel(
                ":warning: [bold red]Some spiders have issues.[/bold red]\nPlease fix them before running.",
                title="⚠️  Compliance Check Failed",
                border_style="red",
                padding=(1, 2)
            ))
            return 1
        else:
            console.print(Panel(
                ":tada: [bold green]All spiders are compliant and well-defined![/bold green]\nReady to crawl! 🕷️🚀",
                title="🎉 Check Passed",
                border_style="green",
                padding=(1, 2)
            ))
            return 0

    except Exception as e:
        logger.exception("Exception in 'crawlo check'")
        if show_json:
            console.print_json(data={"success": False, "error": str(e)})
        elif show_ci:
            console.print(f"❌ Unexpected error: {e}")
        else:
            console.print(f"[bold red]❌ Unexpected error during check:[/bold red] {e}")
        return 1


if __name__ == "__main__":
    """
    支持直接运行：
        python -m crawlo.commands.check
    """
    sys.exit(main(sys.argv[1:]))