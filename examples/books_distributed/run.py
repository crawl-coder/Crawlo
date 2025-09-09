#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Run the distributed books spider
"""
import sys
import os

# Add the project root to sys.path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from crawlo.commands.run import main

if __name__ == '__main__':
    # Run the spider
    sys.argv = ['crawlo', 'run', 'books']
    main()