"""tests/arch 专用 conftest。

签名守护测试共用本目录下的 ``_sig_normalize``，但 pytest 以包形式导入
（tests.arch.*）时不会把本目录加入 sys.path，这里显式插入，保证
``from _sig_normalize import ...`` 在 pytest 与直接运行脚本两种方式下都可用。
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
