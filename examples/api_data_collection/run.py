#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from crawlo.commands.run import execute

if __name__ == '__main__':
    execute()