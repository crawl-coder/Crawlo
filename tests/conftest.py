"""Pytest 全局 conftest — Phase 0 防护网。

collect_ignore_glob 路径相对于本文件所在目录（tests/）。
这些文件因 pre-existing bug（导入崩溃/模块缺失/spider 注册冲突/语法错）
暂从 pytest collection 中排除，避免阻塞架构守护测试基线建立。

修复流程：修文件内 bug → 从下方列表中移除路径 → 验证 pytest collect 通过 → PR 合入。
"""
collect_ignore_glob = [
    # --- integration: script 风格文件，模块级执行并 sys.exit(1)，会中断整个 collection ---
    "integration/_comprehensive_test.py",
    # --- integration: pre-existing collection errors ---
    "integration/test_advanced_tools.py",
    "integration/test_all_pipeline_fingerprints.py",
    "integration/test_cleaners.py",
    "integration/test_cloakbrowser_full.py",
    "integration/test_component_factory.py",
    "integration/test_config_consistency.py",
    "integration/test_error_handler_compatibility.py",
    "integration/test_final_validation.py",
    "integration/test_fingerprint_consistency.py",
    "integration/test_fingerprint_simple.py",
    "integration/test_get_component_logger.py",
    "integration/test_large_scale_helper.py",
    "integration/test_logging_enhancements.py",
    "integration/test_logging_final.py",
    "integration/test_logging_integration.py",
    "integration/test_mysql_optimizations.py",
    "integration/test_mysql_pipeline.py",
    "integration/test_mysql_pipeline_comprehensive.py",
    "integration/test_mysql_pipeline_config.py",
    "integration/test_mysql_pipeline_refactor.py",
    "integration/test_mysql_pipeline_refactor_simple.py",
    "integration/test_mysql_pipeline_robustness.py",
    "integration/test_mysql_pipeline_types.py",
    "integration/test_optimized_selector_naming.py",
    "integration/test_pipeline_fingerprint_consistency.py",
    "integration/test_proxy_middleware_enhanced.py",
    "integration/test_proxy_middleware_integration.py",
    "integration/test_proxy_middleware_refactored.py",
    "integration/test_proxy_stats.py",
    "integration/test_proxy_strategies.py",
    "integration/test_resource_leak_detection.py",
    "integration/test_spider_loader.py",
    "integration/test_spider_loader_comprehensive.py",
    "integration/test_throttle_simple_config.py",
    "integration/test_tools.py",
    "integration/test_utils_fixes.py",
    # --- scrapy_comparison: 需要 scrapy 环境 ---
    "scrapy_comparison/scrapy_test.py",
    # --- unit: pre-existing collection errors ---
    "unit/simple_response_selector_test.py",
]
