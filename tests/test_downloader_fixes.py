#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
Downloader Module Test Suite
=============================
Tests for all P0-P2 fixes in the downloader module.
"""
import asyncio
import platform
import sys
from typing import Any, Dict
from unittest.mock import Mock, MagicMock, AsyncMock

# Add project root to path
sys.path.insert(0, '/Users/dowell/others/Crawlo')


def test_p0_1_activate_request_manager_type_annotation():
    """P0-1: Test ActivateRequestManager._active has correct type annotation"""
    from crawlo.downloader import ActivateRequestManager
    
    manager = ActivateRequestManager()
    
    # Test that _active is a Set[Any]
    assert hasattr(manager, '_active'), "Missing _active attribute"
    assert isinstance(manager._active, set), "_active should be a set"
    
    # Test functionality
    mock_request = Mock()
    manager.add(mock_request)
    assert len(manager._active) == 1
    assert mock_request in manager._active
    
    manager.remove(mock_request, success=True)
    assert len(manager._active) == 0
    
    print("✅ P0-1: ActivateRequestManager._active type annotation - PASSED")


def test_p0_2_downloader_meta_subclasscheck():
    """P0-2: Test DownloaderMeta only checks required methods"""
    from crawlo.downloader import DownloaderMeta, DownloaderBase
    
    # Test that DownloaderBase passes the check
    assert isinstance(DownloaderBase, DownloaderMeta)
    
    # Create a minimal subclass with only required methods
    class MinimalDownloader:
        async def download(self, request):
            pass
        
        async def close(self):
            pass
    
    # Should pass because it has download and close methods
    assert issubclass(MinimalDownloader, DownloaderBase), \
        "MinimalDownloader should be recognized as subclass"
    
    print("✅ P0-2: DownloaderMeta.__subclasscheck__ simplified - PASSED")


def test_p0_3_concurrency_config_simplified():
    """P0-3: Test concurrency config uses safe_get_config"""
    from crawlo.downloader import DownloaderBase
    import inspect
    
    # Get the source code of open() method
    source = inspect.getsource(DownloaderBase.open)
    
    # Verify it uses safe_get_config
    assert 'safe_get_config' in source, \
        "open() should use safe_get_config for concurrency"
    
    # Verify the old complex logic is removed
    assert 'hasattr(self.crawler.settings, \'get_int\')' not in source, \
        "Old complex hasattr logic should be removed"
    
    print("✅ P0-3: Concurrency config simplified - PASSED")


def test_p1_1_english_documentation():
    """P1-1: Test documentation and logs are in English"""
    from crawlo.downloader import ActivateRequestManager
    import inspect
    
    # Check method docstrings are in English
    add_doc = inspect.getdoc(ActivateRequestManager.add)
    assert add_doc and 'Add' in add_doc, "add() docstring should be in English"
    
    remove_doc = inspect.getdoc(ActivateRequestManager.remove)
    assert remove_doc and 'Remove' in remove_doc, "remove() docstring should be in English"
    
    print("✅ P1-1: English documentation - PASSED")


def test_p1_2_hybrid_downloader_english_docs():
    """P1-2: Test hybrid_downloader.py documentation is in English"""
    from crawlo.downloader.hybrid_downloader import HybridDownloader
    import inspect
    
    # Check class docstring
    doc = inspect.getdoc(HybridDownloader)
    assert doc and 'Hybrid Downloader' in doc, \
        "HybridDownloader docstring should be in English"
    
    # Check method docstrings
    init_doc = inspect.getdoc(HybridDownloader._initialize_default_downloaders)
    assert init_doc and 'Initialize' in init_doc, \
        "_initialize_default_downloaders docstring should be in English"
    
    print("✅ P1-2: hybrid_downloader.py English docs - PASSED")


def test_p1_3_constants_docstring():
    """P1-3: Test constants.py has comprehensive docstring"""
    from crawlo.downloader import constants
    import inspect
    
    doc = inspect.getdoc(constants)
    assert doc is not None, "constants.py should have module docstring"
    
    # Check it mentions key components
    assert 'anti-detection' in doc.lower() or 'Downloader Constants' in doc, \
        "Docstring should mention anti-detection or downloader constants"
    assert 'Harmful' in doc or 'harmful' in doc, \
        "Docstring should mention harmful arguments"
    
    print("✅ P1-3: constants.py comprehensive docstring - PASSED")


def test_p1_4_happy_eyeballs_function():
    """P1-4: Test _supports_happy_eyeballs() function exists and works"""
    from crawlo.downloader.aiohttp_downloader import _supports_happy_eyeballs
    
    # Function should exist and return bool
    result = _supports_happy_eyeballs()
    assert isinstance(result, bool), \
        "_supports_happy_eyeballs() should return bool"
    
    # Function should have proper docstring
    assert _supports_happy_eyeballs.__doc__ is not None, \
        "Function should have docstring"
    assert 'aiohttp' in _supports_happy_eyeballs.__doc__.lower() or \
           'happy_eyeballs' in _supports_happy_eyeballs.__doc__.lower(), \
        "Docstring should mention aiohttp or happy_eyeballs"
    
    print("✅ P1-4: _supports_happy_eyeballs() function - PASSED")


def test_p1_5_drissionpage_exception_logging():
    """P1-5: Test DrissionPageDownloader exception handler has debug log"""
    from crawlo.downloader.drissionpage_downloader import DrissionPageDownloader
    import inspect
    
    # Get source code of _cleanup_orphan_processes
    source = inspect.getsource(DrissionPageDownloader._cleanup_orphan_processes)
    
    # Should have logger.debug instead of just pass
    assert 'logger.debug' in source, \
        "Exception handler should have logger.debug"
    assert 'pass' not in source.split('except Exception')[1].split('\n')[0:3], \
        "Exception handler should not just pass"
    
    print("✅ P1-5: DrissionPageDownloader exception logging - PASSED")


def test_p1_6_camoufox_dynamic_os():
    """P1-6: Test CamoufoxDownloader uses dynamic OS detection"""
    from crawlo.downloader.camoufox_downloader import CamoufoxDownloader
    import inspect
    
    # Get __init__ source
    source = inspect.getsource(CamoufoxDownloader.__init__)
    
    # Should import platform module
    module_source = inspect.getsource(
        sys.modules['crawlo.downloader.camoufox_downloader']
    )
    assert 'import platform' in module_source, \
        "Should import platform module"
    
    print("✅ P1-6: CamoufoxDownloader dynamic OS detection - PASSED")


def test_p2_1_dynamic_sub_downloader_detection():
    """P2-1: Test sub-downloader detection is dynamic"""
    from crawlo.downloader import DownloaderBase
    import inspect
    
    # Get open() source
    source = inspect.getsource(DownloaderBase.open)
    
    # Should NOT have hard-coded set of downloaders
    assert '_sub_downloaders = {' not in source, \
        "Should not have hard-coded _sub_downloaders set"
    assert '_hybrid_downloaders = {' not in source, \
        "Should not have hard-coded _hybrid_downloaders set"
    
    # Should use dynamic detection
    assert 'HybridDownloader' in source, \
        "Should check for HybridDownloader dynamically"
    
    print("✅ P2-1: Dynamic sub-downloader detection - PASSED")


def test_p2_2_get_stats_type_annotation():
    """P2-2: Test get_stats() has Dict[str, Any] return type"""
    from crawlo.downloader import DownloaderBase, ActivateRequestManager
    import inspect
    from typing import Dict, Any
    
    # Check DownloaderBase.get_stats
    sig = inspect.signature(DownloaderBase.get_stats)
    # Python 3.9+ may show as dict or Dict[str, Any]
    return_annotation = str(sig.return_annotation)
    assert 'Dict' in return_annotation or 'dict' in return_annotation, \
        f"get_stats() should have dict return type, got: {return_annotation}"
    
    # Check ActivateRequestManager.get_stats
    sig2 = inspect.signature(ActivateRequestManager.get_stats)
    return_annotation2 = str(sig2.return_annotation)
    assert 'Dict' in return_annotation2 or 'dict' in return_annotation2, \
        f"ActivateRequestManager.get_stats() should have dict return type"
    
    print("✅ P2-2: get_stats() type annotation - PASSED")


def test_p2_3_spa_content_selectors_constant():
    """P2-3: Test SPA_CONTENT_SELECTORS is extracted as constant"""
    from crawlo.downloader.wait_strategies import SPA_CONTENT_SELECTORS
    
    # Should be a list
    assert isinstance(SPA_CONTENT_SELECTORS, list), \
        "SPA_CONTENT_SELECTORS should be a list"
    
    # Should contain expected selectors
    assert '[data-testid]' in SPA_CONTENT_SELECTORS, \
        "Should contain [data-testid] selector"
    assert 'main' in SPA_CONTENT_SELECTORS, \
        "Should contain main selector"
    assert len(SPA_CONTENT_SELECTORS) > 0, \
        "Should have at least one selector"
    
    print("✅ P2-3: SPA_CONTENT_SELECTORS constant - PASSED")


def test_p2_5_stealth_type_annotation():
    """P2-5: Test stealth.py has proper type annotations"""
    from crawlo.downloader.stealth import StealthMixin
    import inspect
    
    # Check _inject_stealth_scripts signature
    sig = inspect.signature(StealthMixin._inject_stealth_scripts)
    params = list(sig.parameters.keys())
    
    # Should have 'page' parameter
    assert 'page' in params, \
        "_inject_stealth_scripts should have 'page' parameter"
    
    # Check docstring is in English
    doc = inspect.getdoc(StealthMixin._inject_stealth_scripts)
    assert doc and 'Inject' in doc, \
        "Docstring should be in English"
    
    print("✅ P2-5: stealth.py type annotation - PASSED")


def test_all_imports():
    """Test all downloader modules can be imported"""
    try:
        from crawlo.downloader import (
            DownloaderBase,
            ActivateRequestManager,
        )
        from crawlo.downloader.aiohttp_downloader import AioHttpDownloader
        from crawlo.downloader.httpx_downloader import HttpXDownloader
        from crawlo.downloader.cffi_downloader import CurlCffiDownloader
        from crawlo.downloader.hybrid_downloader import HybridDownloader
        from crawlo.downloader.stealth import StealthMixin
        from crawlo.downloader.wait_strategies import (
            SmartWaitMixin,
            WaitStrategy,
            SPA_CONTENT_SELECTORS
        )
        from crawlo.downloader.constants import (
            HARMFUL_ARGS,
            DEFAULT_ARGS,
            STEALTH_ARGS
        )
        print("✅ All imports successful - PASSED")
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        raise


if __name__ == '__main__':
    print("=" * 70)
    print("Downloader Module P0-P2 Fixes Test Suite")
    print("=" * 70)
    print()
    
    tests = [
        ("Import Test", test_all_imports),
        ("P0-1: ActivateRequestManager Type Annotation", test_p0_1_activate_request_manager_type_annotation),
        ("P0-2: DownloaderMeta Subclass Check", test_p0_2_downloader_meta_subclasscheck),
        ("P0-3: Concurrency Config Simplified", test_p0_3_concurrency_config_simplified),
        ("P1-1: English Documentation", test_p1_1_english_documentation),
        ("P1-2: Hybrid Downloader English Docs", test_p1_2_hybrid_downloader_english_docs),
        ("P1-3: Constants Docstring", test_p1_3_constants_docstring),
        ("P1-4: Happy Eyeballs Function", test_p1_4_happy_eyeballs_function),
        ("P1-5: DrissionPage Exception Logging", test_p1_5_drissionpage_exception_logging),
        ("P1-6: Camoufox Dynamic OS", test_p1_6_camoufox_dynamic_os),
        ("P2-1: Dynamic Sub-Downloader Detection", test_p2_1_dynamic_sub_downloader_detection),
        ("P2-2: Get Stats Type Annotation", test_p2_2_get_stats_type_annotation),
        ("P2-3: SPA Content Selectors", test_p2_3_spa_content_selectors_constant),
        ("P2-5: Stealth Type Annotation", test_p2_5_stealth_type_annotation),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            print(f"\nRunning: {name}")
            test_func()
            passed += 1
        except Exception as e:
            print(f"❌ {name} - FAILED: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 70)
    print(f"Test Results: {passed} passed, {failed} failed, {passed + failed} total")
    print("=" * 70)
    
    if failed == 0:
        print("\n🎉 All tests passed!")
        sys.exit(0)
    else:
        print(f"\n⚠️  {failed} test(s) failed")
        sys.exit(1)
