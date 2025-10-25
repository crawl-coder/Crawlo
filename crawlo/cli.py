# crawlo/cli.py
# !/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import argparse
from crawlo.commands import get_commands
from crawlo.utils.config_manager import EnvConfigManager


def main():
    # 获取框架版本号
    VERSION = EnvConfigManager.get_version()

    # 获取所有可用命令
    commands = get_commands()

    # 创建主解析器
    parser = argparse.ArgumentParser(
        description="Crawlo: A lightweight web crawler framework.",
        usage="crawlo <command> [options]",
        add_help=False  # 禁用默认帮助，我们自己处理
    )
    
    # 添加帮助参数
    parser.add_argument('-h', '--help', action='store_true', help='显示帮助信息')
    parser.add_argument('-v', '--version', action='store_true', help='显示版本信息')
    parser.add_argument('command', nargs='?', help='可用命令: ' + ', '.join(commands.keys()))
    
    # 解析已知参数
    args, unknown = parser.parse_known_args()

    # 处理版本参数
    if args.version:
        print(f"Crawlo {VERSION}")
        sys.exit(0)

    # 处理帮助参数
    if args.help or (args.command is None and not unknown):
        # 导入并运行帮助命令
        try:
            module = __import__(commands['help'], fromlist=['main'])
            sys.exit(module.main([]))
        except ImportError as e:
            print(f"Failed to load help command: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"Help command failed: {e}")
            sys.exit(1)

    # 检查命令是否存在
    if args.command not in commands:
        print(f"Unknown command: {args.command}")
        print(f"Available commands: {', '.join(commands.keys())}")
        # 显示帮助信息
        try:
            module = __import__(commands['help'], fromlist=['main'])
            module.main([])
        except:
            pass
        sys.exit(1)

    # 动态导入并执行命令
    try:
        module = __import__(commands[args.command], fromlist=['main'])
        # 将未知参数传递给子命令
        sys.exit(module.main(unknown))
    except ImportError as e:
        print(f"Failed to load command '{args.command}': {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Command '{args.command}' failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()