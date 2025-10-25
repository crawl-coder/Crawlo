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
from crawlo.logging import get_logger


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
            return False, "在文件中找不到类定义。"

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
            return True, "文件自动修复成功。"
        else:
            return False, "未找到可修复的问题。"

    except Exception as e:
        return False, f"自动修复失败: {e}"


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
            self.console.print(f"\n[bold blue]检测到变更[/bold blue] [cyan]{file_path}[/cyan]")
            self.check_and_fix_spider(spider_name)

    def check_and_fix_spider(self, spider_name):
        try:
            process = CrawlerProcess(spider_modules=self.spider_modules)
            if spider_name not in process.get_spider_names():
                self.console.print(f"[yellow]{spider_name} 不是已注册的爬虫。[/yellow]")
                return

            cls = process.get_spider_class(spider_name)
            issues = []

            # 简化检查
            if not getattr(cls, "name", None):
                issues.append("缺少或为空的 'name' 属性")
            if not callable(getattr(cls, "start_requests", None)):
                issues.append("缺少 'start_requests' 方法")
            if hasattr(cls, "start_urls") and isinstance(cls.start_urls, str):
                issues.append("'start_urls' 是字符串")
            if hasattr(cls, "allowed_domains") and isinstance(cls.allowed_domains, str):
                issues.append("'allowed_domains' 是字符串")

            try:
                spider = cls.create_instance(None)
                if not callable(getattr(spider, "parse", None)):
                    issues.append("缺少 'parse' 方法")
            except Exception:
                issues.append("实例化失败")

            if issues:
                self.console.print(f"[red]{spider_name} 存在问题:[/red]")
                for issue in issues:
                    self.console.print(f"  • {issue}")

                if self.show_fix:
                    file_path = Path(cls.__file__)
                    fixed, msg = auto_fix_spider_file(cls, file_path)
                    if fixed:
                        self.console.print(f"[green]自动修复: {msg}[/green]")
                    else:
                        self.console.print(f"[yellow]无法修复: {msg}[/yellow]")
            else:
                self.console.print(f"[green]{spider_name} 合规。[/green]")

        except Exception as e:
            self.console.print(f"[red]检查 {spider_name} 时出错: {e}[/red]")


def watch_spiders(project_root: Path, project_package: str, show_fix: bool):
    """监听 spiders 目录变化并自动检查"""
    spider_path = project_root / project_package / "spiders"
    if not spider_path.exists():
        console.print(f"[bold red]Spider 目录未找到:[/bold red] {spider_path}")
        return

    spider_modules = [f"{project_package}.spiders"]
    event_handler = SpiderChangeHandler(project_root, spider_modules, show_fix, console)
    observer = Observer()
    observer.schedule(event_handler, str(spider_path), recursive=False)

    console.print(Panel(
        f"[bold blue]监听[/bold blue] [cyan]{spider_path}[/cyan] 中的变更\n"
        "编辑任何爬虫文件以触发自动检查...",
        title="已启动监听模式",
        border_style="blue"
    ))

    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        console.print("\n[bold red]🛑 监听模式已停止。[/bold red]")
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
        console.print("[bold red]错误:[/bold red] 用法: [blue]crawlo check[/blue] [--fix] [--ci] [--json] [--watch]")
        return 1

    try:
        # 1. 查找项目根目录
        project_root = get_project_root()
        if not project_root:
            msg = "[bold red]找不到 'crawlo.cfg'[/bold red]\n请在项目目录中运行此命令。"
            if show_json:
                console.print_json(data={"success": False, "error": "未找到项目根目录"})
                return 1
            elif show_ci:
                console.print("未找到项目根目录。缺少 crawlo.cfg。")
                return 1
            else:
                console.print(Panel(
                    Text.from_markup(msg),
                    title="非Crawlo项目",
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
            msg = f"配置文件未找到: {cfg_file}"
            if show_json:
                console.print_json(data={"success": False, "error": msg})
                return 1
            elif show_ci:
                console.print(f"{msg}")
                return 1
            else:
                console.print(Panel(msg, title="缺少配置文件", border_style="red"))
                return 1

        config = configparser.ConfigParser()
        config.read(cfg_file, encoding="utf-8")

        if not config.has_section("settings") or not config.has_option("settings", "default"):
            msg = "crawlo.cfg 中缺少 [settings] 部分或 'default' 选项"
            if show_json:
                console.print_json(data={"success": False, "error": msg})
                return 1
            elif show_ci:
                console.print(f"{msg}")
                return 1
            else:
                console.print(Panel(msg, title="无效配置", border_style="red"))
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
            elif show_ci:
                console.print(f"{msg}")
                return 1
            else:
                console.print(Panel(msg, title="导入错误", border_style="red"))
                return 1

        # 4. 加载爬虫
        spider_modules = [f"{project_package}.spiders"]
        process = CrawlerProcess(spider_modules=spider_modules)
        spider_names = process.get_spider_names()

        if not spider_names:
            msg = "未找到爬虫。"
            if show_json:
                console.print_json(data={"success": True, "warning": msg})
                return 0
            elif show_ci:
                console.print("未找到爬虫。")
                return 0
            else:
                console.print(Panel(
                    Text.from_markup(
                        "[bold]未找到爬虫[/bold]\n\n"
                        "[bold]确保:[/bold]\n"
                        "  • 爬虫定义于 '[cyan]spiders[/cyan]' 模块\n"
                        "  • 具有 [green]`name`[/green] 属性\n"
                        "  • 模块已正确导入"
                    ),
                    title="未找到爬虫",
                    border_style="yellow",
                    padding=(1, 2)
                ))
                return 0

        # 5. 如果启用 watch 模式，启动监听
        if show_watch:
            console.print("[bold blue]启动监听模式...[/bold blue]")
            watch_spiders(project_root, project_package, show_fix)
            return 0  # watch 是长期运行，不返回

        # 6. 开始检查（非 watch 模式）
        if not show_ci and not show_json:
            console.print(f"[bold]正在检查 {len(spider_names)} 个爬虫...[/bold]\n")

        issues_found = False
        results = []

        for name in sorted(spider_names):
            cls = process.get_spider_class(name)
            issues = []

            # 检查 name 属性
            if not getattr(cls, "name", None):
                issues.append("缺少或为空的 'name' 属性")
            elif not isinstance(cls.name, str):
                issues.append("'name' 不是字符串")

            # 检查 start_requests 是否可调用
            if not callable(getattr(cls, "start_requests", None)):
                issues.append("缺少或不可调用的 'start_requests' 方法")

            # 检查 start_urls 类型（不应是字符串）
            if hasattr(cls, "start_urls") and isinstance(cls.start_urls, str):
                issues.append("'start_urls' 是字符串；应为列表或元组")

            # 检查 allowed_domains 类型
            if hasattr(cls, "allowed_domains") and isinstance(cls.allowed_domains, str):
                issues.append("'allowed_domains' 是字符串；应为列表或元组")

            # 实例化并检查 parse 方法
            try:
                spider = cls.create_instance(None)
                if not callable(getattr(spider, "parse", None)):
                    issues.append("未定义 'parse' 方法（推荐）")
            except Exception as e:
                issues.append(f"实例化爬虫失败: {e}")

            # 自动修复（如果启用）
            if issues and show_fix:
                try:
                    file_path = Path(cls.__file__)
                    fixed, msg = auto_fix_spider_file(cls, file_path)
                    if fixed:
                        if not show_ci and not show_json:
                            console.print(f"[green]已自动修复 {name} → {msg}[/green]")
                        issues = []  # 认为已修复
                    else:
                        if not show_ci and not show_json:
                            console.print(f"[yellow]无法自动修复 {name}: {msg}[/yellow]")
                except Exception as e:
                    if not show_ci and not show_json:
                        console.print(f"[yellow]找不到 {name} 的源文件: {e}[/yellow]")

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
                console.print("合规性检查失败。")
                for r in results:
                    if r["issues"]:
                        console.print(f"  • {r['name']}: {', '.join(r['issues'])}")
            else:
                console.print("所有爬虫合规。")
            return 1 if issues_found else 0

        # 9. 默认 rich 输出
        table = Table(
            title="爬虫合规性检查结果",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold magenta",
            title_style="bold green"
        )
        table.add_column("状态", style="bold", width=4)
        table.add_column("名称", style="cyan")
        table.add_column("类名", style="green")
        table.add_column("问题", style="yellow", overflow="fold")

        for res in results:
            if res["issues"]:
                status = "[red]X[/red]"
                issues_text = "\n".join(f"• {issue}" for issue in res["issues"])
            else:
                status = "[green]√[/green]"
                issues_text = "—"

            table.add_row(status, res["name"], res["class"], issues_text)

        console.print(table)
        console.print()

        if issues_found:
            console.print(Panel(
                "[bold red]一些爬虫存在问题。[/bold red]\n请在运行前修复这些问题。",
                title="合规性检查失败",
                border_style="red",
                padding=(1, 2)
            ))
            return 1
        else:
            console.print(Panel(
                "[bold green]所有爬虫都合规且定义良好！[/bold green]\n准备开始爬取！ ",
                title="检查通过",
                border_style="green",
                padding=(1, 2)
            ))
            return 0

    except Exception as e:
        logger.exception("执行 'crawlo check' 时发生异常")
        if show_json:
            console.print_json(data={"success": False, "error": str(e)})
        elif show_ci:
            console.print(f"意外错误: {e}")
        else:
            console.print(f"[bold red]检查过程中发生意外错误:[/bold red] {e}")
        return 1


if __name__ == "__main__":
    """
    支持直接运行：
        python -m crawlo.commands.check
    """
    sys.exit(main(sys.argv[1:]))