#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
导入问题检查工具
检查 Crawlo 框架中的导入问题：
1. 重复导入
2. 导入位置不合理
3. 应该延迟导入但未延迟
"""

import os
import re
import ast
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict


class ImportAnalyzer:
    """导入分析器"""

    def __init__(self, root_dir: str):
        self.root_dir = Path(root_dir)
        self.issues = []
        
    def analyze_file(self, file_path: Path) -> List[Dict]:
        """分析单个文件的导入问题"""
        issues = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
            
            # 检查重复导入
            imports = self._extract_imports(content)
            duplicates = self._find_duplicates(imports)
            if duplicates:
                issues.append({
                    'file': str(file_path),
                    'type': 'DUPLICATE_IMPORT',
                    'message': f'重复导入: {", ".join(duplicates)}',
                    'severity': 'WARNING'
                })
            
            # 检查导入位置
            import_positions = self._check_import_positions(lines)
            if import_positions:
                issues.append({
                    'file': str(file_path),
                    'type': 'IMPORT_POSITION',
                    'message': f'导入位置问题: {import_positions}',
                    'severity': 'INFO'
                })
            
            # 检查是否需要延迟导入
            delayed_imports = self._check_delayed_imports(content, file_path)
            if delayed_imports:
                issues.append({
                    'file': str(file_path),
                    'type': 'DELAYED_IMPORT_NEEDED',
                    'message': f'建议延迟导入: {delayed_imports}',
                    'severity': 'SUGGESTION'
                })
                
        except Exception as e:
            issues.append({
                'file': str(file_path),
                'type': 'PARSE_ERROR',
                'message': f'解析失败: {str(e)}',
                'severity': 'ERROR'
            })
        
        return issues
    
    def _extract_imports(self, content: str) -> List[Tuple[str, int]]:
        """提取所有导入语句及其行号"""
        imports = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            line = line.strip()
            if line.startswith('import ') or line.startswith('from '):
                imports.append((line, i))
        
        return imports
    
    def _find_duplicates(self, imports: List[Tuple[str, int]]) -> List[str]:
        """查找重复导入"""
        seen = {}
        duplicates = []
        
        for imp, line_num in imports:
            # 标准化导入语句
            normalized = re.sub(r'\s+', ' ', imp)
            
            if normalized in seen:
                module = normalized.split()[1] if normalized.startswith('import') else normalized.split()[1]
                if module not in duplicates:
                    duplicates.append(module)
            else:
                seen[normalized] = line_num
        
        return duplicates
    
    def _check_import_positions(self, lines: List[str]) -> List[str]:
        """检查导入位置是否合理"""
        issues = []
        import_section_ended = False
        code_started = False
        
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            
            # 跳过注释和空行
            if not stripped or stripped.startswith('#'):
                continue
            
            # 检查是否有代码在导入之前
            if stripped.startswith(('import ', 'from ')):
                if code_started:
                    issues.append(f'行 {i}: 导入语句出现在代码之后')
            else:
                code_started = True
        
        return issues
    
    def _check_delayed_imports(self, content: str, file_path: Path) -> List[str]:
        """检查是否需要延迟导入"""
        delayed_needed = []
        
        # 检查是否有大型库在顶层导入
        heavy_libraries = [
            'numpy', 'pandas', 'sklearn', 'tensorflow', 'torch',
            'playwright', 'selenium', 'camoufox',
        ]
        
        for lib in heavy_libraries:
            if f'import {lib}' in content or f'from {lib}' in content:
                # 检查是否已经在函数内部导入
                if not self._is_delayed_import(content, lib):
                    delayed_needed.append(lib)
        
        # 检查 crawlo 内部模块的循环导入风险
        if 'crawlo' in str(file_path):
            # 检查是否导入了可能导致循环的模块
            circular_risk = ['crawlo.crawler', 'crawlo.framework', 'crawlo.application']
            for mod in circular_risk:
                if f'from {mod}' in content or f'import {mod}' in content:
                    if not self._is_delayed_import(content, mod):
                        delayed_needed.append(mod)
        
        return delayed_needed
    
    def _is_delayed_import(self, content: str, module: str) -> bool:
        """检查是否已经是延迟导入"""
        # 检查是否在函数或方法内部
        patterns = [
            rf'def \w+\(.*?\):\s*\n\s*.*?import {module}',
            rf'if TYPE_CHECKING:.*?import {module}',
            rf'__import__\(.*?{module}.*?\)',
            rf'importlib\.import_module\(.*?{module}.*?\)',
        ]
        
        for pattern in patterns:
            if re.search(pattern, content, re.DOTALL):
                return True
        
        return False
    
    def analyze_directory(self, dir_path: Path = None) -> Dict[str, List[Dict]]:
        """分析目录中的所有 Python 文件"""
        if dir_path is None:
            dir_path = self.root_dir
        
        results = defaultdict(list)
        
        for py_file in dir_path.rglob('*.py'):
            # 跳过测试文件和 __pycache__
            if 'test' in str(py_file) or '__pycache__' in str(py_file):
                continue
            
            file_issues = self.analyze_file(py_file)
            if file_issues:
                results[str(py_file)] = file_issues
        
        return dict(results)
    
    def print_report(self, results: Dict[str, List[Dict]]):
        """打印分析报告"""
        if not results:
            print("✅ 未发现导入问题")
            return
        
        print("\n" + "="*80)
        print("Crawlo 框架导入问题检查报告")
        print("="*80 + "\n")
        
        severity_count = {'ERROR': 0, 'WARNING': 0, 'INFO': 0, 'SUGGESTION': 0}
        
        for file_path, issues in sorted(results.items()):
            rel_path = os.path.relpath(file_path, self.root_dir)
            print(f"📁 {rel_path}")
            
            for issue in issues:
                severity = issue['severity']
                severity_count[severity] = severity_count.get(severity, 0) + 1
                
                icon = {
                    'ERROR': '❌',
                    'WARNING': '⚠️ ',
                    'INFO': 'ℹ️ ',
                    'SUGGESTION': '💡'
                }.get(severity, '•')
                
                print(f"  {icon} [{severity}] {issue['message']}")
            
            print()
        
        print("="*80)
        print("统计汇总:")
        print(f"  ❌ ERROR:      {severity_count.get('ERROR', 0)}")
        print(f"  ⚠️  WARNING:    {severity_count.get('WARNING', 0)}")
        print(f"  ℹ️  INFO:       {severity_count.get('INFO', 0)}")
        print(f"  💡 SUGGESTION:  {severity_count.get('SUGGESTION', 0)}")
        print(f"  {'='*40}")
        total = sum(severity_count.values())
        print(f"  总计: {total} 个问题")
        print("="*80)


def main():
    """主函数"""
    root_dir = '/Users/oscar/projects/Crawlo/crawlo'
    
    print("🔍 开始检查 Crawlo 框架导入问题...")
    print(f"📂 扫描目录: {root_dir}\n")
    
    analyzer = ImportAnalyzer(root_dir)
    results = analyzer.analyze_directory()
    analyzer.print_report(results)
    
    # 返回退出码
    error_count = sum(
        1 for issues in results.values() 
        for issue in issues 
        if issue['severity'] == 'ERROR'
    )
    
    sys.exit(1 if error_count > 0 else 0)


if __name__ == '__main__':
    main()
