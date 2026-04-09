#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
命令行入口：crawlo shell [url]
交互式终端，用于调试选择器、测试动态渲染和验证逻辑。

用法：
    crawlo shell                    # 启动空 Shell
    crawlo shell https://example.com # 启动并预抓取 URL
"""
import asyncio
import os
import sys

from crawlo.logging import get_logger
from crawlo.shell.core import CrawloShell

_logger = None


def logger():
    """延迟获取 logger 实例"""
    global _logger
    if _logger is None:
        _logger = get_logger(__name__)
    return _logger


def _load_project_settings():
    """尝试加载项目配置"""
    try:
        from crawlo.project import _find_project_root
        from crawlo.initialization import initialize_framework
        
        project_root = _find_project_root()
        if not project_root:
            return None
        
        # 将项目根目录加入 sys.path
        project_root_str = str(project_root)
        if project_root_str not in sys.path:
            sys.path.insert(0, project_root_str)
        
        # 初始化框架并加载 settings
        settings = initialize_framework()
        return settings
        
    except Exception as e:
        logger().debug(f"Failed to load project settings: {e}")
        return None


def main(args):
    """
    主函数：启动交互式终端
    
    用法:
        crawlo shell [url]
    """
    # 解析 URL 参数
    url = None
    if args and not args[0].startswith('-'):
        url = args[0]
    
    print("\n" + "=" * 50)
    print("  Crawlo Shell - Interactive Console")
    print("=" * 50)
    
    # 尝试加载项目配置
    settings = _load_project_settings()
    
    if settings:
        print(f"  Settings loaded: {settings.get('PROJECT_NAME', 'unknown')}")
    else:
        print("  No project settings found (running in standalone mode)")
    
    if url:
        print(f"  Pre-fetch URL: {url}")
    
    print("=" * 50 + "\n")
    
    # 创建 Shell 实例
    shell = CrawloShell(settings=settings)
    
    try:
        # 启动 Shell
        asyncio.run(shell.start(url=url))
    except KeyboardInterrupt:
        print("\nShell interrupted by user")
    except SystemExit:
        pass
    except Exception as e:
        logger().error(f"Shell error: {type(e).__name__}: {e}")
    finally:
        # 清理资源
        try:
            asyncio.run(shell.close())
        except Exception:
            pass
    
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
