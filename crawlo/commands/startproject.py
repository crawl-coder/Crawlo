#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
# @Time    : 2025-08-31 22:36
# @Author  : crawl-coder
# @Desc    : 命令行入口：crawlo startproject baidu，创建项目。
"""
import shutil
import re
import sys
import os
from pathlib import Path
from typing import Optional

# 添加项目根目录到路径，以便能够导入utils模块
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    from rich.table import Table
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

try:
    from .utils import show_error_panel, show_success_panel
    UTILS_AVAILABLE = True
except ImportError:
    # 如果相对导入失败，尝试绝对导入
    try:
        from crawlo.commands.utils import show_error_panel, show_success_panel
        UTILS_AVAILABLE = True
    except ImportError:
        UTILS_AVAILABLE = False

# 初始化 rich 控制台（如果可用）
if RICH_AVAILABLE:
    console = Console()
else:
    # 简单的控制台输出替代
    class Console:
        def print(self, text):
            print(text)
    console = Console()

TEMPLATES_DIR = Path(__file__).parent.parent / 'templates'

# 可用的模板类型
TEMPLATE_TYPES = {
    'default': '默认模板 - 通用配置，适合大多数项目',
    'simple': '简化模板 - 最小配置，适合快速开始',
    'distributed': '分布式模板 - 针对分布式爬取优化',
    'high-performance': '高性能模板 - 针对大规模高并发优化',
    'gentle': '温和模板 - 低负载配置，对目标网站友好'
}


def show_error_panel(title, content):
    """显示错误面板的简单实现"""
    if RICH_AVAILABLE:
        from rich.panel import Panel
        console.print(Panel(content, title=title, border_style="red"))
    else:
        print(f"❌ {title}")
        print(content)

def show_success_panel(title, content):
    """显示成功面板的简单实现"""
    if RICH_AVAILABLE:
        from rich.panel import Panel
        console.print(Panel(content, title=title, border_style="green"))
    else:
        print(f"✅ {title}")
        print(content)

def _render_template(tmpl_path, context):
    """读取模板文件，替换 {{key}} 为 context 中的值"""
    with open(tmpl_path, 'r', encoding='utf-8') as f:
        content = f.read()
    for key, value in context.items():
        content = content.replace(f'{{{{{key}}}}}', str(value))
    return content


def _copytree_with_templates(src, dst, context, template_type='default'):
    """
    递归复制目录，将 .tmpl 文件渲染后复制（去除 .tmpl 后缀），其他文件直接复制。
    """
    src_path = Path(src)
    dst_path = Path(dst)
    dst_path.mkdir(parents=True, exist_ok=True)

    for item in src_path.rglob('*'):
        rel_path = item.relative_to(src_path)
        dst_item = dst_path / rel_path

        if item.is_dir():
            dst_item.mkdir(parents=True, exist_ok=True)
        else:
            if item.suffix == '.tmpl':
                # 处理特定模板类型的设置文件
                if item.name == 'settings.py.tmpl' and template_type != 'default':
                    # 使用特定模板类型的设置文件
                    template_file_name = f'settings_{template_type}.py.tmpl'
                    template_file_path = src_path / template_file_name
                    if template_file_path.exists():
                        rendered_content = _render_template(template_file_path, context)
                    else:
                        # 如果特定模板不存在，使用默认模板
                        rendered_content = _render_template(item, context)
                else:
                    rendered_content = _render_template(item, context)
                
                final_dst = dst_item.with_suffix('')
                final_dst.parent.mkdir(parents=True, exist_ok=True)
                with open(final_dst, 'w', encoding='utf-8') as f:
                    f.write(rendered_content)
            else:
                shutil.copy2(item, dst_item)


def validate_project_name(project_name: str) -> tuple[bool, str]:
    """
    验证项目名称是否有效
    
    Returns:
        tuple[bool, str]: (是否有效, 错误信息)
    """
    # 检查是否为空
    if not project_name or not project_name.strip():
        return False, "Project name cannot be empty"
    
    project_name = project_name.strip()
    
    # 检查长度
    if len(project_name) > 50:
        return False, "Project name too long (max 50 characters)"
    
    # 检查是否为Python关键字
    python_keywords = {
        'False', 'None', 'True', 'and', 'as', 'assert', 'break', 'class', 
        'continue', 'def', 'del', 'elif', 'else', 'except', 'finally', 
        'for', 'from', 'global', 'if', 'import', 'in', 'is', 'lambda', 
        'nonlocal', 'not', 'or', 'pass', 'raise', 'return', 'try', 
        'while', 'with', 'yield'
    }
    if project_name in python_keywords:
        return False, f"'{project_name}' is a Python keyword and cannot be used as project name"
    
    # 检查是否为有效的Python标识符
    if not project_name.isidentifier():
        return False, "Project name must be a valid Python identifier"
    
    # 检查格式（建议使用snake_case）
    if not re.match(r'^[a-z][a-z0-9_]*$', project_name):
        return False, (
            "Project name should start with lowercase letter and "
            "contain only lowercase letters, numbers, and underscores"
        )
    
    # 检查是否以数字结尾（不推荐）
    if project_name[-1].isdigit():
        return False, "Project name should not end with a number"
    
    return True, ""


def show_template_options():
    """显示可用的模板选项"""
    if RICH_AVAILABLE:
        table = Table(title="可用模板类型", show_header=True, header_style="bold magenta")
        table.add_column("模板类型", style="cyan", no_wrap=True)
        table.add_column("描述", style="green")
        
        for template_type, description in TEMPLATE_TYPES.items():
            table.add_row(template_type, description)
        
        console.print(table)
    else:
        print("可用模板类型:")
        for template_type, description in TEMPLATE_TYPES.items():
            print(f"  {template_type}: {description}")


def main(args):
    if len(args) < 1 or len(args) > 2:
        console.print("[bold red]Error:[/bold red] Usage: [blue]crawlo startproject[/blue] <project_name> [template_type]")
        console.print("💡 Examples:")
        console.print("   [blue]crawlo startproject[/blue] my_spider_project")
        console.print("   [blue]crawlo startproject[/blue] news_crawler simple")
        console.print("   [blue]crawlo startproject[/blue] ecommerce_spider distributed")
        show_template_options()
        return 1

    project_name = args[0]
    template_type = args[1] if len(args) > 1 else 'default'
    
    # 验证模板类型
    if template_type not in TEMPLATE_TYPES:
        show_error_panel(
            "Invalid Template Type",
            f"Template type '[cyan]{template_type}[/cyan]' is not supported.\n"
        )
        show_template_options()
        return 1
    
    # 验证项目名称
    is_valid, error_msg = validate_project_name(project_name)
    if not is_valid:
        show_error_panel(
            "Invalid Project Name", 
            f"[cyan]{project_name}[/cyan] is not a valid project name.\n"
            f"❌ {error_msg}\n\n"
            "💡 Project name should:\n"
            "  • Start with lowercase letter\n"
            "  • Contain only lowercase letters, numbers, and underscores\n"
            "  • Be a valid Python identifier\n"
            "  • Not be a Python keyword"
        )
        return 1
    
    project_dir = Path(project_name)

    if project_dir.exists():
        show_error_panel(
            "Directory Exists",
            f"Directory '[cyan]{project_dir}[/cyan]' already exists.\n"
            "💡 Choose a different project name or remove the existing directory."
        )
        return 1

    context = {'project_name': project_name}
    template_dir = TEMPLATES_DIR / 'project'

    try:
        # 1. 创建项目根目录
        project_dir.mkdir()

        # 2. 渲染 crawlo.cfg.tmpl
        cfg_template = TEMPLATES_DIR / 'crawlo.cfg.tmpl'
        if cfg_template.exists():
            cfg_content = _render_template(cfg_template, context)
            (project_dir / 'crawlo.cfg').write_text(cfg_content, encoding='utf-8')
            console.print(f":white_check_mark: Created [green]{project_dir / 'crawlo.cfg'}[/green]")
        else:
            console.print("[yellow]⚠ Warning:[/yellow] Template 'crawlo.cfg.tmpl' not found.")

        # 3. 复制并渲染项目包内容
        package_dir = project_dir / project_name
        _copytree_with_templates(template_dir, package_dir, context, template_type)
        console.print(f":white_check_mark: Created project package: [green]{package_dir}[/green]")

        # 4. 创建 logs 目录
        (project_dir / 'logs').mkdir(exist_ok=True)
        console.print(":white_check_mark: Created logs directory")
        
        # 5. 创建 output 目录（用于数据输出）
        (project_dir / 'output').mkdir(exist_ok=True)
        console.print(":white_check_mark: Created output directory")

        # 成功面板
        success_text = Text.from_markup(f"Project '[bold cyan]{project_name}[/bold cyan]' created successfully!")
        console.print(Panel(success_text, title=":rocket: Success", border_style="green", padding=(1, 2)))
        
        # 显示使用的模板类型
        if template_type != 'default':
            console.print(f":information: 使用模板类型: [bold blue]{template_type}[/bold blue] - {TEMPLATE_TYPES[template_type]}")

        # 下一步操作提示（对齐美观 + 语法高亮）
        next_steps = f"""
        [bold]🚀 Next steps:[/bold]
        [blue]cd[/blue] {project_name}
        [blue]crawlo genspider[/blue] example example.com
        [blue]crawlo run[/blue] example
        
        [bold]📚 Learn more:[/bold]
        [blue]crawlo list[/blue]                    # List all spiders
        [blue]crawlo check[/blue] example          # Check spider validity
        [blue]crawlo stats[/blue]                  # View statistics
        """.strip()
        console.print(next_steps)

        return 0

    except Exception as e:
        show_error_panel(
            "Creation Failed",
            f"Failed to create project: {e}"
        )
        if project_dir.exists():
            shutil.rmtree(project_dir, ignore_errors=True)
            console.print("[red]:cross_mark: Cleaned up partially created project.[/red]")
        return 1

if __name__ == "__main__":
    import sys
    exit_code = main(sys.argv[1:])
    sys.exit(exit_code)