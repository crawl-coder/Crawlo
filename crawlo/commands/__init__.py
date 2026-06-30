#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""Crawlo CLI commands module

Provides command-line interface commands for Crawlo framework:
- startproject: Create new Crawlo project
- genspider: Generate spider template
- run: Execute spider
- check: Validate spider definitions
- list: List available spiders
- stats: Show crawling statistics
- help: Display help information
- schedule: Schedule spider execution
- shell: Interactive crawling shell
"""

_commands = {
    'startproject': 'crawlo.commands.startproject',
    'genspider': 'crawlo.commands.genspider',
    'run': 'crawlo.commands.run',
    'check': 'crawlo.commands.check',
    'list': 'crawlo.commands.list',
    'stats': 'crawlo.commands.stats',
    'help': 'crawlo.commands.help',
    'schedule': 'crawlo.commands.schedule',
    'shell': 'crawlo.commands.shell',
    'dead-letter': 'crawlo.commands.dead_letter',
}

def get_commands():
    return _commands