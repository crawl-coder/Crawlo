import ast

# 使用绝对路径
with open('d:/dowell/projects/Crawlo/crawlo/pipelines/__init__.py', 'r', encoding='utf-8') as f:
    tree = ast.parse(f.read())
    
print("AST nodes:")
for i, node in enumerate(tree.body):
    print(f"{i}: {type(node).__name__}")
    
print("\nImportFrom nodes:")
for node in tree.body:
    if isinstance(node, ast.ImportFrom):
        print(f"  from {node.module} import {', '.join(alias.name for alias in node.names)}")