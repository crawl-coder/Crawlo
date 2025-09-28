#!/usr/bin/python
# -*- coding:UTF-8 -*-
import platform

system_name = platform.system().lower()
if system_name == 'windows':
    import asyncio
    asyncio.set_event_loop_policy(
        asyncio.WindowsSelectorEventLoopPolicy()
    )

