#!/usr/bin/python
# -*- coding:UTF-8 -*-

_commands = {
    'startproject': 'crawlo.commands.startproject',
    'genspider': 'crawlo.commands.genspider',
    'run': 'crawlo.commands.run',
    'check': 'crawlo.commands.check',
    'list': 'crawlo.commands.list',
    'stats': 'crawlo.commands.stats'
}

def get_commands():
    return _commands