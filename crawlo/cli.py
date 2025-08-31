# crawlo/cli.py
# !/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import argparse
from crawlo.commands import get_commands


def main():
    # 获取所有可用命令
    commands = get_commands()

    parser = argparse.ArgumentParser(
        description="Crawlo: A lightweight web crawler framework.",
        usage="crawlo <command> [options]"
    )
    parser.add_argument('command', help='Available commands: ' + ', '.join(commands.keys()))
    # 注意：这里不添加具体参数，由子命令解析

    # 只解析命令
    args, unknown = parser.parse_known_args()

    if args.command not in commands:
        print(f"Unknown command: {args.command}")
        print(f"Available commands: {', '.join(commands.keys())}")
        sys.exit(1)

    # 动态导入并执行命令
    try:
        module = __import__(commands[args.command], fromlist=['main'])
        sys.exit(module.main(unknown))
    except ImportError as e:
        print(f"Failed to load command '{args.command}': {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Command '{args.command}' failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()