import shutil
from pathlib import Path

TEMPLATES_DIR = Path(__file__).parent.parent / 'templates'


def _render_template(tmpl_path, context):
    """读取模板文件，替换 {{key}} 为 context 中的值"""
    with open(tmpl_path, 'r', encoding='utf-8') as f:
        content = f.read()
    for key, value in context.items():
        content = content.replace(f'{{{{{key}}}}}', str(value))
    return content


def _copytree_with_templates(src, dst, context):
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
            # 创建目标目录
            dst_item.mkdir(parents=True, exist_ok=True)
        else:
            if item.suffix == '.tmpl':
                # 渲染模板文件，并去掉 .tmpl 后缀
                rendered_content = _render_template(item, context)
                final_dst = dst_item.with_suffix('') # 去掉 .tmpl
                final_dst.parent.mkdir(parents=True, exist_ok=True) # 确保父目录存在
                with open(final_dst, 'w', encoding='utf-8') as f:
                    f.write(rendered_content)
            else:
                # 普通文件，直接复制
                shutil.copy2(item, dst_item)


def main(args):
    if len(args) != 1:
        print("Usage: crawlo startproject <project_name>")
        return 1

    project_name = args[0]
    project_dir = Path(project_name)

    if project_dir.exists():
        print(f"Error: Directory '{project_dir}' already exists.")
        return 1

    context = {'project_name': project_name}
    template_dir = TEMPLATES_DIR / 'project'

    try:
        # 1. 创建项目根目录
        project_dir.mkdir()

        # 2. 处理 crawlo.cfg.tmpl：单独渲染并写入项目根目录
        cfg_template = TEMPLATES_DIR / 'crawlo.cfg.tmpl'  # ✅ 使用 templates/ 目录下的模板
        if cfg_template.exists():
            cfg_content = _render_template(cfg_template, context)
            (project_dir / 'crawlo.cfg').write_text(cfg_content, encoding='utf-8')
        else:
            print("Warning: crawlo.cfg.tmpl not found in templates.")

        # 3. 复制所有其他模板文件到项目包内 (project_dir / project_name)
        package_dir = project_dir / project_name
        # 这会复制 __init__.py.tmpl, items.py.tmpl, settings.py.tmpl, spiders/ 等
        # 并将它们渲染为 .py 文件
        _copytree_with_templates(template_dir, package_dir, context)

        # 4. 创建 logs 目录
        (project_dir / 'logs').mkdir(exist_ok=True)

        print(f"""
        ✔ 项目 '{project_name}' 创建成功！

        进入项目目录:
            cd {project_name}

        创建一个爬虫:
            crawlo genspider example example.com

        运行爬虫:
            crawlo run example
        """)
        return 0

    except Exception as e:
        print(f"Error creating project: {e}")
        # 如果出错，尝试清理已创建的目录
        if project_dir.exists():
            shutil.rmtree(project_dir, ignore_errors=True)
        return 1