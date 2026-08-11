"""跨 Python 版本一致的签名归一化（供签名守护测试共用）。

Python 3.14 的 ``inspect.signature`` 会把字符串注解求值后按 PEP 604
渲染：``Optional[X]`` -> ``X | None``、``Union[A, B]`` -> ``A | B``，
而 3.10-3.13 保留 ``from __future__ import annotations`` 的字符串原样。
为保证 frozen 签名哈希与解释器版本无关，哈希前统一归一化。

归一化规则（只影响渲染形式，不影响语义）：
    Optional[X]        -> X | None
    Union[A, B, ...]   -> A | B | ...
    NoneType           -> None
    <object object at 0x...> -> <object>（内存地址跨进程不稳定）
"""

from __future__ import annotations

import re


def _matching_bracket(text: str, start: int) -> int:
    """text[start] == '['，返回配对的 ']' 下标（引号内 '[' ']' 不计数）。"""
    depth = 0
    in_quote = None
    i = start
    while i < len(text):
        ch = text[i]
        if in_quote:
            if ch == in_quote:
                in_quote = None
        elif ch in ("'", '"'):
            in_quote = ch
        elif ch == '[':
            depth += 1
        elif ch == ']':
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def _split_top_level(text: str) -> list[str]:
    """按顶层逗号切分（忽略 []/() 内部与引号内的逗号）。"""
    parts: list[str] = []
    depth = 0
    in_quote = None
    start = 0
    for i, ch in enumerate(text):
        if in_quote:
            if ch == in_quote:
                in_quote = None
            continue
        if ch in ("'", '"'):
            in_quote = ch
        elif ch in '[(':
            depth += 1
        elif ch in '])':
            depth -= 1
        elif ch == ',' and depth == 0:
            parts.append(text[start:i].strip())
            start = i + 1
    parts.append(text[start:].strip())
    return parts


def _rewrite_type_expr(expr: str) -> str:
    """递归把 Optional[X] / Union[A, B, ...] 重写为 PEP 604 形式。"""
    expr = expr.strip()
    out: list[str] = []
    i = 0
    n = len(expr)
    while i < n:
        ch = expr[i]
        if ch.isalnum() or ch == '_':
            j = i
            while j < n and (expr[j].isalnum() or expr[j] in '_.'):
                j += 1
            word = expr[i:j]
            if j < n and expr[j] == '[' and (
                word.endswith('Optional') or word.endswith('Union')
            ):
                end = _matching_bracket(expr, j)
                if end != -1:
                    inner = expr[j + 1:end]
                    if word.endswith('Optional'):
                        out.append(_rewrite_type_expr(inner) + ' | None')
                    else:
                        out.append(
                            ' | '.join(
                                _rewrite_type_expr(p)
                                for p in _split_top_level(inner)
                            )
                        )
                    i = end + 1
                    continue
            out.append(word)
            i = j
        else:
            out.append(ch)
            i += 1
    return ''.join(out)


def normalize_signature_str(sig_str: str) -> str:
    """归一化签名字符串，使哈希跨 Python 版本（3.10-3.14）一致。"""
    s = re.sub(r"<object object at 0x[0-9a-fA-F]+>", "<object>", sig_str)
    s = re.sub(r"\bNoneType\b", "None", s)
    return _rewrite_type_expr(s)


__all__ = ["normalize_signature_str"]
