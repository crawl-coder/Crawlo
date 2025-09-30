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
from typing import Optional, List

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

# 可选的模块组件
OPTIONAL_MODULES = {
    'mysql': 'MySQL数据库支持',
    'mongodb': 'MongoDB数据库支持',
    'redis': 'Redis支持（分布式队列和去重）',
    'proxy': '代理支持',
    'monitoring': '监控和性能分析',
    'dedup': '去重功能',
    'httpx': 'HttpX下载器',
    'aiohttp': 'AioHttp下载器',
    'curl': 'CurlCffi下载器'
}


def show_error_panel(title, content):
    """显示错误面板的简单实现"""
    if RICH_AVAILABLE:
        from rich.panel import Panel
        console.print(Panel(content, title=title, border_style="red"))
    else:
        print(f"{title}")
        print(content)

def show_success_panel(title, content):
    """显示成功面板的简单实现"""
    if RICH_AVAILABLE:
        from rich.panel import Panel
        console.print(Panel(content, title=title, border_style="green"))
    else:
        print(f"{title}")
        print(content)

def _render_template(tmpl_path, context):
    """读取模板文件，替换 {{key}} 为 context 中的值"""
    with open(tmpl_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 处理简单的过滤器语法 {{key|filter}}
    import re
    
    def apply_filter(value, filter_name):
        if filter_name == 'title':
            # 将 snake_case 转换为 TitleCase
            words = value.replace('_', ' ').split()
            return ''.join(word.capitalize() for word in words)
        return value
    
    # 查找并替换 {{key|filter}} 格式的占位符
    pattern = r'\{\{([^}|]+)\|([^}]+)\}\}'
    def replace_filter_match(match):
        key = match.group(1).strip()
        filter_name = match.group(2).strip()
        if key in context:
            return str(apply_filter(context[key], filter_name))
        return match.group(0)  # 如果找不到key，保持原样
    
    content = re.sub(pattern, replace_filter_match, content)
    
    # 处理普通的 {{key}} 占位符
    for key, value in context.items():
        content = content.replace(f'{{{{{key}}}}}', str(value))
    
    return content


def _copytree_with_templates(src, dst, context, template_type='default', modules: List[str] = None):
    """
    递归复制目录，将 .tmpl 文件渲染后复制（去除 .tmpl 后缀），其他文件直接复制。
    支持选择性模块复制。
    """
    src_path = Path(src)
    dst_path = Path(dst)
    dst_path.mkdir(parents=True, exist_ok=True)

    for item in src_path.rglob('*'):
        rel_path = item.relative_to(src_path)
        # 对于run.py.tmpl文件，需要特殊处理，将其放到项目根目录
        if item.name == 'run.py.tmpl':
            dst_item = dst_path.parent / rel_path  # 放到项目根目录
        else:
            dst_item = dst_path / rel_path

        # 检查是否应该包含此文件
        path_str = str(rel_path).replace('\\', '/')
        
        # 所有文件根据模块选择决定是否包含
        if not _should_include_file(rel_path, modules):
            continue

        if item.is_dir():
            dst_item.mkdir(parents=True, exist_ok=True)
        else:
            if item.suffix == '.tmpl':
                rendered_content = None
                # 处理特定模板类型的设置文件
                if item.name == 'settings.py.tmpl':
                    # 对于设置文件，根据模板类型选择相应的内容模板
                    if template_type != 'default':
                        # 使用特定模板类型的设置文件
                        template_file_name = f'settings_{template_type}.py.tmpl'
                        template_file_path = src_path / template_file_name
                        if template_file_path.exists():
                            rendered_content = _render_template(template_file_path, context)
                        else:
                            # 如果特定模板不存在，使用默认模板
                            rendered_content = _render_template(item, context)
                    else:
                        # 使用默认模板
                        rendered_content = _render_template(item, context)
                # 跳过其他以 settings_ 开头的模板文件，避免重复处理
                elif item.name.startswith('settings_') and item.name.endswith('.py.tmpl'):
                    continue
                else:
                    rendered_content = _render_template(item, context)
                
                # 确保设置文件始终命名为 settings.py
                if item.name == 'settings.py.tmpl':
                    # 特殊处理设置模板文件，统一生成为 settings.py
                    final_dst = dst_item.parent / 'settings.py'
                # 特殊处理run.py.tmpl文件
                elif item.name == 'run.py.tmpl':
                    final_dst = dst_item.with_suffix('')  # 去掉.tmpl后缀
                else:
                    final_dst = dst_item.with_suffix('')
                    
                final_dst.parent.mkdir(parents=True, exist_ok=True)
                with open(final_dst, 'w', encoding='utf-8') as f:
                    f.write(rendered_content)
            else:
                shutil.copy2(item, dst_item)


def _should_include_file(rel_path, modules: List[str]) -> bool:
    """
    根据选择的模块决定是否包含文件
    """
    if modules is None:
        # 如果没有指定模块，则包含所有文件
        return True
    
    # 基础文件始终包含
    basic_files = [
        '__init__.py.tmpl',
        'settings.py.tmpl',
        'spiders/__init__.py.tmpl',
        'items.py.tmpl',
        'middlewares.py.tmpl'
        # 移除了'run.py.tmpl'，因为它现在在模板根目录
    ]
    
    path_str = str(rel_path).replace('\\', '/')
    
    # 始终包含基础文件
    if path_str in basic_files:
        return True
    
    # 根据模块选择包含特定文件
    if 'mysql' in modules and 'mysql' in path_str:
        return True
    if 'mongodb' in modules and 'mongo' in path_str:
        return True
    if 'redis' in modules and 'redis' in path_str:
        return True
    if 'proxy' in modules and 'proxy' in path_str:
        return True
    if 'monitoring' in modules and ('monitor' in path_str or 'stats' in path_str):
        return True
    if 'dedup' in modules and 'dedup' in path_str:
        return True
    if 'httpx' in modules and 'httpx' in path_str:
        return True
    if 'aiohttp' in modules and 'aiohttp' in path_str:
        return True
    if 'curl' in modules and 'cffi' in path_str:
        return True
    
    # 默认不包含特定模块文件
    return False


def validate_project_name(project_name: str) -> tuple[bool, str]:
    """
    验证项目名称是否有效
    
    Returns:
        tuple[bool, str]: (是否有效, 错误信息)
    """
    # 检查是否为空
    if not project_name or not project_name.strip():
        return False, "项目名称不能为空"
    
    project_name = project_name.strip()
    
    # 检查长度
    if len(project_name) > 50:
        return False, "项目名称太长（最多50个字符）"
    
    # 检查是否为Python关键字
    python_keywords = {
        'False', 'None', 'True', 'and', 'as', 'assert', 'break', 'class', 
        'continue', 'def', 'del', 'elif', 'else', 'except', 'finally', 
        'for', 'from', 'global', 'if', 'import', 'in', 'is', 'lambda', 
        'nonlocal', 'not', 'or', 'pass', 'raise', 'return', 'try', 
        'while', 'with', 'yield'
    }
    if project_name in python_keywords:
        return False, f"'{project_name}' 是Python关键字，不能用作项目名称"
    
    # 检查是否为有效的Python标识符
    if not project_name.isidentifier():
        return False, "项目名称必须是有效的Python标识符"
    
    # 检查格式（建议使用snake_case）
    if not re.match(r'^[a-z][a-z0-9_]*$', project_name):
        return False, (
            "项目名称应以小写字母开头，只能包含小写字母、数字和下划线"
        )
    
    # 检查是否以数字结尾（不推荐）
    if project_name[-1].isdigit():
        return False, "项目名称不应以数字结尾"
    
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


def show_module_options():
    """显示可用的模块选项"""
    if RICH_AVAILABLE:
        table = Table(title="可选模块组件", show_header=True, header_style="bold magenta")
        table.add_column("模块", style="cyan", no_wrap=True)
        table.add_column("描述", style="green")
        
        for module, description in OPTIONAL_MODULES.items():
            table.add_row(module, description)
        
        console.print(table)
    else:
        print("可选模块组件:")
        for module, description in OPTIONAL_MODULES.items():
            print(f"  {module}: {description}")


def main(args):
    if len(args) < 1:
        console.print("[bold red]错误:[/bold red] 用法: [blue]crawlo startproject[/blue] <项目名称> [模板类型] [--modules 模块1,模块2]")
        console.print("示例:")
        console.print("   [blue]crawlo startproject[/blue] my_spider_project")
        console.print("   [blue]crawlo startproject[/blue] news_crawler simple")
        console.print("   [blue]crawlo startproject[/blue] ecommerce_spider distributed --modules mysql,proxy")
        show_template_options()
        show_module_options()
        return 1

    # 解析参数
    project_name = args[0]
    template_type = 'default'
    modules = None
    
    # 解析可选参数
    if len(args) > 1:
        for i, arg in enumerate(args[1:], 1):
            if arg.startswith('--modules='):
                modules_str = arg.split('=', 1)[1]
                modules = [m.strip() for m in modules_str.split(',') if m.strip()]
            elif arg.startswith('--modules'):
                # 处理 --modules module1,module2 格式
                if i + 1 < len(args):
                    modules_str = args[i + 1]
                    modules = [m.strip() for m in modules_str.split(',') if m.strip()]
            elif not arg.startswith('--') and arg in TEMPLATE_TYPES:
                template_type = arg
    
    # 验证模板类型
    if template_type not in TEMPLATE_TYPES:
        show_error_panel(
            "无效的模板类型",
            f"不支持模板类型 '[cyan]{template_type}[/cyan]'。\n"
        )
        show_template_options()
        return 1
    
    # 验证项目名称
    is_valid, error_msg = validate_project_name(project_name)
    if not is_valid:
        show_error_panel(
            "无效的项目名称", 
            f"[cyan]{project_name}[/cyan] 不是有效的项目名称。\n"
            f"{error_msg}\n\n"
            "项目名称应:\n"
            "  • 以小写字母开头\n"
            "  • 只能包含小写字母、数字和下划线\n"
            "  • 是有效的Python标识符\n"
            "  • 不能是Python关键字"
        )
        return 1
    
    project_dir = Path(project_name)

    if project_dir.exists():
        show_error_panel(
            "目录已存在",
            f"目录 '[cyan]{project_dir}[/cyan]' 已存在。\n"
            "请选择不同的项目名称或删除现有目录。"
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
            console.print(f"已创建 [green]{project_dir / 'crawlo.cfg'}[/green]")
        else:
            console.print("[yellow]警告:[/yellow] 找不到模板 'crawlo.cfg.tmpl'。")

        # 3. 渲染 run.py.tmpl (放在项目根目录)
        run_template = TEMPLATES_DIR / 'run.py.tmpl'
        if run_template.exists():
            run_content = _render_template(run_template, context)
            (project_dir / 'run.py').write_text(run_content, encoding='utf-8')
            console.print(f"已创建 [green]{project_dir / 'run.py'}[/green]")
        else:
            console.print("[yellow]警告:[/yellow] 找不到模板 'run.py.tmpl'。")

        # 4. 复制并渲染项目包内容
        package_dir = project_dir / project_name
        _copytree_with_templates(template_dir, package_dir, context, template_type, modules)
        console.print(f"已创建项目包: [green]{package_dir}[/green]")

        # 5. 创建 logs 目录
        (project_dir / 'logs').mkdir(exist_ok=True)
        console.print("已创建 logs 目录")
        
        # 6. 创建 output 目录（用于数据输出）
        (project_dir / 'output').mkdir(exist_ok=True)
        console.print("已创建 output 目录")

        # 成功面板
        success_text = Text.from_markup(f"项目 '[bold cyan]{project_name}[/bold cyan]' 创建成功！")
        console.print(Panel(success_text, title="成功", border_style="green", padding=(1, 2)))
        
        # 显示使用的模板类型
        if template_type != 'default':
            console.print(f"使用模板类型: [bold blue]{template_type}[/bold blue] - {TEMPLATE_TYPES[template_type]}")
        
        # 显示选择的模块
        if modules:
            console.print(f"选择的模块: [bold blue]{', '.join(modules)}[/bold blue]")

        # 下一步操作提示（对齐美观 + 语法高亮）
        next_steps = f"""
        [bold]下一步操作:[/bold]
        [blue]cd[/blue] {project_name}
        [blue]crawlo genspider[/blue] example example.com
        [blue]crawlo run[/blue] example
        
        [bold]了解更多:[/bold]
        [blue]crawlo list[/blue]                    # 列出所有爬虫
        [blue]crawlo check[/blue] example          # 检查爬虫有效性
        [blue]crawlo stats[/blue]                  # 查看统计信息
        """.strip()
        console.print(next_steps)

        return 0

    except Exception as e:
        show_error_panel(
            "创建失败",
            f"创建项目失败: {e}"
        )
        if project_dir.exists():
            shutil.rmtree(project_dir, ignore_errors=True)
            console.print("[red]已清理部分创建的项目。[/red]")
        return 1

if __name__ == "__main__":
    import sys
    exit_code = main(sys.argv[1:])
    sys.exit(exit_code)