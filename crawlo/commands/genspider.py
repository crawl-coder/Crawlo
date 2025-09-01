import sys
from pathlib import Path
import configparser
import importlib

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
        print("Usage: crawlo genspider <spider_name> <domain>")
        return 1

    spider_name = args[0]
    domain = args[1]

    # 查找项目根目录
    project_root = None
    current = Path.cwd()
    while True:
        cfg_file = current / 'crawlo.cfg'
        if cfg_file.exists():
            project_root = current
            break
        parent = current.parent
        if parent == current:
            break
        current = parent

    if not project_root:
        print("Error: Not a crawlo project. crawlo.cfg not found.")
        return 1

    # 将项目根目录加入 sys.path
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    # 从 crawlo.cfg 读取 settings 模块，获取项目包名
    config = configparser.ConfigParser()
    try:
        config.read(cfg_file, encoding='utf-8')
        settings_module = config.get('settings', 'default')
        project_package = settings_module.split('.')[0]  # e.g., myproject.settings -> myproject
    except Exception as e:
        print(f"Error reading crawlo.cfg: {e}")
        return 1

    # 确定 items 模块的路径
    items_module_path = f"{project_package}.items"

    # 尝试导入 items 模块
    try:
        items_module = importlib.import_module(items_module_path)
        # 获取模块中所有大写开头的类
        item_classes = [cls for cls in items_module.__dict__.values()
                        if isinstance(cls, type) and cls.__name__.isupper()]

        # 如果找到了类，使用第一个作为默认
        if item_classes:
            default_item_class = item_classes[0].__name__
        else:
            default_item_class = "ExampleItem"  # 回退到示例
    except ImportError as e:
        print(f"Error importing items module '{items_module_path}': {e}")
        default_item_class = "ExampleItem"

    # 创建爬虫文件
    spiders_dir = project_root / project_package / 'spiders'
    if not spiders_dir.exists():
        spiders_dir.mkdir(parents=True)

    spider_file = spiders_dir / f'{spider_name}.py'
    if spider_file.exists():
        print(f"Error: Spider '{spider_name}' already exists.")
        return 1

    # ✅ 修正模板路径
    tmpl_path = TEMPLATES_DIR / 'spider' / 'spider.py.tmpl'

    if not tmpl_path.exists():
        print(f"Error: Template file not found at {tmpl_path}")
        return 1

    # ✅ 生成正确的类名
    class_name = f"{spider_name.capitalize()}Spider"

    context = {
        'spider_name': spider_name,
        'domain': domain,
        'project_name': project_package,
        'item_class': default_item_class,
        'class_name': class_name  # ✅ 添加处理好的类名
    }

    content = _render_template(tmpl_path, context)

    with open(spider_file, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"Spider '{spider_name}' created in {spider_file}")
    return 0