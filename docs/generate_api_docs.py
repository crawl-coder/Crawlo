#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
自动生成 API 文档的脚本
"""

import os
import ast
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 定义要生成文档的模块
MODULES = [
    'crawlo/__init__.py',
    'crawlo/crawler.py',
    'crawlo/spider/__init__.py',
    'crawlo/network/request.py',
    'crawlo/network/response.py',
    'crawlo/items/items.py',
    'crawlo/pipelines/__init__.py',
    'crawlo/pipelines/redis_dedup_pipeline.py',
    'crawlo/pipelines/memory_dedup_pipeline.py',
    'crawlo/pipelines/bloom_dedup_pipeline.py',
    'crawlo/pipelines/database_dedup_pipeline.py',
    'crawlo/pipelines/console_pipeline.py',
    'crawlo/pipelines/json_pipeline.py',
    'crawlo/pipelines/csv_pipeline.py',
    'crawlo/pipelines/mysql_pipeline.py',
    'crawlo/pipelines/mongo_pipeline.py',
    'crawlo/middleware/__init__.py',
    'crawlo/extension/__init__.py',
    'crawlo/filters/__init__.py',
    'crawlo/downloader/__init__.py',
    'crawlo/core/scheduler.py',
    'crawlo/queue/__init__.py',
    'crawlo/utils/log.py'
]

def extract_module_info(module_path):
    """提取模块信息"""
    try:
        with open(module_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content)
        
        # 提取模块文档字符串
        docstring = ast.get_docstring(tree)
        
        # 提取类和函数
        classes = []
        functions = []
        
        # 提取导入的类
        imported_classes = []
        for node in tree.body:
            if isinstance(node, ast.ImportFrom):
                # 处理 from ... import ... 语句
                for alias in node.names:
                    if alias.asname:
                        imported_classes.append(alias.asname)
                    else:
                        imported_classes.append(alias.name)
        
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                class_doc = ast.get_docstring(node)
                # 提取方法
                methods = []
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        method_doc = ast.get_docstring(item)
                        methods.append({
                            'name': item.name,
                            'docstring': method_doc,
                            'args': [arg.arg for arg in item.args.args]
                        })
                
                classes.append({
                    'name': node.name,
                    'docstring': class_doc,
                    'methods': methods
                })
            elif isinstance(node, ast.FunctionDef):
                func_doc = ast.get_docstring(node)
                functions.append({
                    'name': node.name,
                    'docstring': func_doc,
                    'args': [arg.arg for arg in node.args.args]
                })
        
        return {
            'docstring': docstring,
            'classes': classes,
            'functions': functions,
            'imported_classes': imported_classes
        }
    except Exception as e:
        print(f"Error processing {module_path}: {e}")
        return None

def generate_module_doc(module_name, module_info):
    """生成模块文档"""
    lines = [f"# {module_name}", ""]
    
    if module_info['docstring']:
        lines.append(module_info['docstring'])
        lines.append("")
    
    # 添加导入的类信息
    if module_info.get('imported_classes'):
        lines.append("## 导入的类")
        lines.append("")
        for cls_name in module_info['imported_classes']:
            lines.append(f"- {cls_name}")
        lines.append("")
    
    if module_info['classes']:
        lines.append("## 类")
        lines.append("")
        for cls in module_info['classes']:
            lines.append(f"### {cls['name']}")
            if cls['docstring']:
                lines.append(cls['docstring'])
            
            if cls['methods']:
                lines.append("\n#### 方法")
                for method in cls['methods']:
                    lines.append(f"\n##### {method['name']}")
                    if method['docstring']:
                        lines.append(method['docstring'])
            lines.append("")
    
    if module_info['functions']:
        lines.append("## 函数")
        lines.append("")
        for func in module_info['functions']:
            lines.append(f"### {func['name']}")
            if func['docstring']:
                lines.append(func['docstring'])
            lines.append("")
    
    return "\n".join(lines)

def main():
    """主函数"""
    # 确保在 docs 目录下运行
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    # 创建 API 文档目录
    api_dir = Path("api")
    api_dir.mkdir(exist_ok=True)
    
    # 为每个模块生成文档
    for module in MODULES:
        full_path = project_root / module
        
        if full_path.exists():
            # 从模块路径生成文档文件名
            module_name = module.replace('/', '.').replace('.py', '')
            module_info = extract_module_info(full_path)
            if module_info:
                doc_content = generate_module_doc(module_name, module_info)
                # 生成文档文件名
                doc_file_name = module.replace('/', '_').replace('.py', '') + '.md'
                doc_file = api_dir / doc_file_name
                with open(doc_file, 'w', encoding='utf-8') as f:
                    f.write(doc_content)
                print(f"Generated API doc for {module_name} at {doc_file}")
        else:
            print(f"Module file not found: {full_path}")

if __name__ == "__main__":
    main()