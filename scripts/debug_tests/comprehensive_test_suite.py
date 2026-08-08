#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
Crawlo 框架完整测试套件

作为高级爬虫框架测试工程师，执行系统性测试：
1. 核心组件测试
2. 集成测试
3. 端到端测试
4. 性能测试
5. 异常测试
"""
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple


class CrawloTestSuite:
    """Crawlo 框架测试套件"""
    
    def __init__(self):
        self.test_root = Path(__file__).parent
        self.results: Dict[str, Dict] = {}
    
    def run_test_group(self, name: str, test_files: List[str], timeout: int = 60) -> Dict:
        """运行一组测试"""
        print(f"\n{'='*80}")
        print(f"📋 运行测试组: {name}")
        print(f"{'='*80}")
        
        cmd = [
            sys.executable, '-m', 'pytest',
            *test_files,
            '-v', '--tb=short', '-q'
        ]
        
        start_time = time.time()
        try:
            result = subprocess.run(
                cmd,
                cwd=self.test_root.parent,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            elapsed = time.time() - start_time
            
            # 解析结果
            output = result.stdout + result.stderr
            passed = output.count(' PASSED')
            failed = output.count(' FAILED')
            errors = output.count(' ERROR')
            warnings = output.count(' warning')
            
            stats = {
                'passed': passed,
                'failed': failed,
                'errors': errors,
                'warnings': warnings,
                'elapsed': elapsed,
                'success': result.returncode == 0
            }
            
            self.results[name] = stats
            
            # 打印摘要
            status = "✅ 通过" if stats['success'] else "❌ 失败"
            print(f"\n{status} - 通过: {passed}, 失败: {failed}, 错误: {errors}, 警告: {warnings}")
            print(f"⏱️  耗时: {elapsed:.2f}s")
            
            return stats
            
        except subprocess.TimeoutExpired:
            print(f"⏰ 超时 ({timeout}s)")
            self.results[name] = {'success': False, 'timeout': True}
            return {'success': False, 'timeout': True}
    
    def run_core_tests(self):
        """核心组件测试"""
        print("\n" + "="*80)
        print("🔬 第一阶段：核心组件测试")
        print("="*80)
        
        test_files = [
            'tests/test_error_handling.py',
            'tests/test_middleware_lifecycle.py',
            'tests/test_concurrency_control.py',
            'tests/test_scheduler.py',
            'tests/test_factories.py',
            'tests/test_storage_backends.py',
        ]
        
        return self.run_test_group("核心组件", test_files, timeout=90)
    
    def run_integration_tests(self):
        """集成测试"""
        print("\n" + "="*80)
        print("🔗 第二阶段：集成测试")
        print("="*80)
        
        test_files = [
            'tests/test_integration.py',
            'tests/test_scheduling.py',
            'tests/test_scheduling_integration.py',
        ]
        
        return self.run_test_group("集成测试", test_files, timeout=120)
    
    def run_downloader_tests(self):
        """下载器测试"""
        print("\n" + "="*80)
        print("🌐 第三阶段：下载器测试")
        print("="*80)
        
        test_files = [
            'tests/test_dynamic_downloader.py',
            'tests/test_downloader_proxy_compatibility.py',
            'tests/test_hybrid_downloader_optimization.py',
        ]
        
        return self.run_test_group("下载器", test_files, timeout=90)
    
    def run_middleware_tests(self):
        """中间件测试"""
        print("\n" + "="*80)
        print("🛡️  第四阶段：中间件测试")
        print("="*80)
        
        test_files = [
            'tests/test_proxy_middleware.py',
            'tests/test_retry_middleware.py',
            'tests/test_offsite_middleware.py',
            'tests/test_default_header_middleware.py',
            'tests/test_response_filter_middleware.py',
        ]
        
        return self.run_test_group("中间件", test_files, timeout=90)
    
    def run_queue_tests(self):
        """队列测试"""
        print("\n" + "="*80)
        print("📦 第五阶段：队列测试")
        print("="*80)
        
        test_files = [
            'tests/test_queue_type.py',
            'tests/test_redis_queue.py',
            'tests/test_queue_naming.py',
        ]
        
        return self.run_test_group("队列", test_files, timeout=90)
    
    def run_e2e_test(self):
        """端到端测试（实际爬虫）"""
        print("\n" + "="*80)
        print("🚀 第六阶段：端到端测试")
        print("="*80)
        
        # 运行示例爬虫
        cmd = [
            sys.executable,
            'examples/ofweek_standalone/run.py'
        ]
        
        start_time = time.time()
        try:
            result = subprocess.run(
                cmd,
                cwd=self.test_root.parent,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            elapsed = time.time() - start_time
            output = result.stdout + result.stderr
            
            # 检查是否成功
            success = 'stats:' in output and result.returncode == 0
            
            # 提取统计信息
            stats_extracted = False
            if 'stats:' in output:
                stats_start = output.find('stats:')
                stats_end = output.find('}', stats_start) + 1
                if stats_end > 0:
                    print("\n📊 爬虫统计:")
                    print(output[stats_start:stats_end])
                    stats_extracted = True
            
            stats = {
                'success': success,
                'elapsed': elapsed,
                'stats_extracted': stats_extracted
            }
            
            self.results['端到端测试'] = stats
            
            status = "✅ 通过" if success else "❌ 失败"
            print(f"\n{status} - 耗时: {elapsed:.2f}s")
            
            return stats
            
        except subprocess.TimeoutExpired:
            print("⏰ 超时 (60s)")
            self.results['端到端测试'] = {'success': False, 'timeout': True}
            return {'success': False, 'timeout': True}
    
    def run_performance_tests(self):
        """性能测试"""
        print("\n" + "="*80)
        print("⚡ 第七阶段：性能测试")
        print("="*80)
        
        test_files = [
            'tests/test_fingerprint_performance.py',
            'tests/test_hash_performance.py',
        ]
        
        return self.run_test_group("性能", test_files, timeout=60)
    
    def generate_report(self):
        """生成测试报告"""
        print("\n" + "="*80)
        print("📊 测试报告")
        print("="*80)
        
        total_passed = sum(r.get('passed', 0) for r in self.results.values())
        total_failed = sum(r.get('failed', 0) for r in self.results.values())
        total_errors = sum(r.get('errors', 0) for r in self.results.values())
        total_elapsed = sum(r.get('elapsed', 0) for r in self.results.values())
        
        success_count = sum(1 for r in self.results.values() if r.get('success'))
        total_count = len(self.results)
        
        print(f"\n{'测试组':<20} {'状态':<8} {'通过':<6} {'失败':<6} {'错误':<6} {'耗时(s)':<10}")
        print("-" * 80)
        
        for name, stats in self.results.items():
            status = "✅" if stats.get('success') else "❌"
            passed = stats.get('passed', 0)
            failed = stats.get('failed', 0)
            errors = stats.get('errors', 0)
            elapsed = stats.get('elapsed', 0)
            print(f"{name:<20} {status:<8} {passed:<6} {failed:<6} {errors:<6} {elapsed:<10.2f}")
        
        print("-" * 80)
        print(f"{'总计':<20} {'':<8} {total_passed:<6} {total_failed:<6} {total_errors:<6} {total_elapsed:<10.2f}")
        print(f"\n测试组通过率: {success_count}/{total_count} ({success_count/total_count*100:.1f}%)")
        
        if total_failed == 0 and total_errors == 0:
            print("\n🎉 所有测试通过！框架质量优秀！")
        else:
            print(f"\n⚠️  发现 {total_failed} 个失败，{total_errors} 个错误，需要修复")
        
        return {
            'total_passed': total_passed,
            'total_failed': total_failed,
            'total_errors': total_errors,
            'success_rate': success_count / total_count if total_count > 0 else 0
        }


def main():
    """主测试流程"""
    print("="*80)
    print("🔍 Crawlo 框架完整测试套件")
    print("="*80)
    print("测试工程师: AI Assistant")
    print("测试时间:", time.strftime('%Y-%m-%d %H:%M:%S'))
    
    suite = CrawloTestSuite()
    
    # 执行各阶段测试
    suite.run_core_tests()
    suite.run_integration_tests()
    suite.run_downloader_tests()
    suite.run_middleware_tests()
    suite.run_queue_tests()
    suite.run_e2e_test()
    suite.run_performance_tests()
    
    # 生成报告
    report = suite.generate_report()
    
    # 返回退出码
    sys.exit(0 if report['total_failed'] == 0 and report['total_errors'] == 0 else 1)


if __name__ == '__main__':
    main()
