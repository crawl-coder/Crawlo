# crawlo/commands/__init__.py
# 定义可用的命令
_commands = {
    'startproject': 'crawlo.commands.startproject',
    'genspider': 'crawlo.commands.genspider',
    'run': 'crawlo.commands.run',
}

def get_commands():
    return _commands