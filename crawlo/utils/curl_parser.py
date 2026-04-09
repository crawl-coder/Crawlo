#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
curl 命令解析器
将浏览器 DevTools 复制的 curl 命令转换为 Crawlo Request 对象。
"""
import json
import shlex
from typing import Any, Dict, Optional, Tuple
from urllib.parse import parse_qs, unquote_plus

from crawlo.logging import get_logger


class CurlParser:
    """将 curl 命令解析为 Crawlo Request 构造参数"""

    # 需要 1 个值的选项
    _VALUE_OPTIONS = {
        '-X', '--request',
        '-H', '--header',
        '-d', '--data', '--data-raw', '--data-binary',
        '-b', '--cookie',
        '-u', '--user',
        '-A', '--user-agent',
        '--proxy', '--proxy-http', '--proxy-https',
        '--connect-timeout',
        '--url',
        '--max-redirs',
        '-e', '--referer',
        '--output',
        '-o', '--output-doc',
    }

    # 布尔标志（不需要值）
    _FLAG_OPTIONS = {
        '-k', '--insecure',
        '-L', '--location',
        '--compressed',
        '-v', '--verbose',
        '-s', '--silent',
        '-S', '--show-error',
        '-i', '--include',
        '-I', '--head',
        '-N', '--no-buffer',
        '-g', '--globoff',
    }

    @staticmethod
    def parse(curl_cmd: str) -> Dict[str, Any]:
        """解析 curl 命令，返回 Request 构造参数字典

        Args:
            curl_cmd: 完整的 curl 命令字符串

        Returns:
            dict: 可直接传给 Request() 的参数

        Raises:
            ValueError: curl 命令格式无效或缺少 URL
        """
        logger = get_logger('CurlParser')

        # 1. 清理命令
        cmd = curl_cmd.strip()
        if not cmd:
            raise ValueError("Empty curl command")

        # 处理多行续行符
        cmd = cmd.replace('\\\n', ' ').replace('\\\r\n', ' ')
        # 合并多余空白
        while '  ' in cmd:
            cmd = cmd.replace('  ', ' ')

        # 2. 安全拆分
        try:
            parts = shlex.split(cmd, posix=True)
        except ValueError as e:
            # Windows 下可能引号不匹配，尝试宽容模式
            try:
                parts = shlex.split(cmd, posix=False)
            except ValueError:
                raise ValueError(f"Invalid curl command syntax: {e}")

        # 3. 去掉开头的 'curl'
        if parts and parts[0] == 'curl':
            parts = parts[1:]

        if not parts:
            raise ValueError("No arguments after 'curl'")

        # 4. 遍历参数
        result = {
            'method': 'GET',
            'headers': {},
            'url': '',
        }
        i = 0
        has_data = False

        while i < len(parts):
            part = parts[i]

            # -X / --request
            if part in ('-X', '--request'):
                _ensure_value(parts, i, part)
                result['method'] = parts[i + 1].upper()
                i += 2

            # -H / --header
            elif part in ('-H', '--header'):
                _ensure_value(parts, i, part)
                header_line = parts[i + 1]
                if ':' in header_line:
                    k, v = header_line.split(':', 1)
                    result['headers'][k.strip()] = v.strip()
                i += 2

            # -d / --data / --data-raw / --data-binary
            elif part in ('-d', '--data', '--data-raw', '--data-binary'):
                _ensure_value(parts, i, part)
                data = parts[i + 1]
                has_data = True
                content_type = result['headers'].get('Content-Type', '')

                if 'application/json' in content_type:
                    try:
                        result['json_body'] = json.loads(data)
                    except json.JSONDecodeError:
                        result['body'] = data
                elif 'application/x-www-form-urlencoded' in content_type:
                    result['form_data'] = _parse_form_data(data)
                else:
                    result['body'] = data

                i += 2

            # -b / --cookie
            elif part in ('-b', '--cookie'):
                _ensure_value(parts, i, part)
                result['cookies'] = _parse_cookies(parts[i + 1])
                i += 2

            # -u / --user
            elif part in ('-u', '--user'):
                _ensure_value(parts, i, part)
                user_info = parts[i + 1]
                if ':' in user_info:
                    u, p = user_info.split(':', 1)
                    result['auth'] = (u, p)
                else:
                    result['auth'] = (user_info, '')
                i += 2

            # -k / --insecure
            elif part in ('-k', '--insecure'):
                result['verify'] = False
                i += 1

            # -L / --location
            elif part in ('-L', '--location'):
                result['allow_redirects'] = True
                i += 1

            # --max-redirs
            elif part == '--max-redirs':
                _ensure_value(parts, i, part)
                if parts[i + 1] == '0':
                    result['allow_redirects'] = False
                i += 2

            # --proxy / --proxy-http / --proxy-https
            elif part in ('--proxy', '--proxy-http', '--proxy-https', '-x'):
                _ensure_value(parts, i, part)
                result['proxy'] = parts[i + 1]
                i += 2

            # --connect-timeout
            elif part == '--connect-timeout':
                _ensure_value(parts, i, part)
                try:
                    result['timeout'] = float(parts[i + 1])
                except ValueError:
                    pass
                i += 2

            # -A / --user-agent
            elif part in ('-A', '--user-agent'):
                _ensure_value(parts, i, part)
                result['headers']['User-Agent'] = parts[i + 1]
                i += 2

            # -e / --referer
            elif part in ('-e', '--referer'):
                _ensure_value(parts, i, part)
                result['headers']['Referer'] = parts[i + 1]
                i += 2

            # --url
            elif part == '--url':
                _ensure_value(parts, i, part)
                result['url'] = parts[i + 1]
                i += 2

            # -I / --head
            elif part in ('-I', '--head'):
                result['method'] = 'HEAD'
                i += 1

            # 布尔标志：忽略
            elif part in CurlParser._FLAG_OPTIONS:
                i += 1

            # 其他 --option（跳过其值）
            elif part.startswith('--'):
                if i + 1 < len(parts) and not parts[i + 1].startswith('-'):
                    i += 2
                else:
                    i += 1

            # 其他 -o 单字母选项（跳过其值）
            elif part.startswith('-') and len(part) == 2 and part not in CurlParser._FLAG_OPTIONS:
                if i + 1 < len(parts):
                    i += 2
                else:
                    i += 1

            # URL（第一个非选项参数）
            elif not part.startswith('-') and not result['url']:
                result['url'] = part
                i += 1

            else:
                i += 1

        # 5. 验证 URL
        if not result['url']:
            raise ValueError("No URL found in curl command")

        # 6. 有数据时默认方法为 POST
        if has_data and result['method'] == 'GET':
            result['method'] = 'POST'

        # 7. 清理：移除 Crawlo Request 不需要的字段
        result.pop('output', None)
        result.pop('output_doc', None)

        # 8. 移除空 headers
        if not result['headers']:
            del result['headers']

        logger.debug(f"Parsed curl command: method={result['method']}, url={result['url']}")
        return result

    @staticmethod
    def to_request(curl_cmd: str, **kwargs) -> Any:
        """将 curl 命令直接转换为 Request 对象

        Args:
            curl_cmd: curl 命令字符串
            **kwargs: 额外覆盖参数（如 meta, callback 等）

        Returns:
            Request: Crawlo Request 对象
        """
        from crawlo.network.request import Request

        params = CurlParser.parse(curl_cmd)
        params.update(kwargs)
        return Request(**params)


def _ensure_value(parts: list, i: int, option: str) -> None:
    """确保选项后面有值"""
    if i + 1 >= len(parts):
        raise ValueError(f"Option '{option}' requires a value")


def _parse_form_data(data: str) -> Dict[str, Any]:
    """解析 URL 编码的表单数据

    Args:
        data: application/x-www-form-urlencoded 格式字符串

    Returns:
        dict: 表单字段字典
    """
    result = {}
    for pair in data.split('&'):
        if '=' in pair:
            k, v = pair.split('=', 1)
            result[unquote_plus(k)] = unquote_plus(v)
        else:
            result[unquote_plus(pair)] = ''
    return result


def _parse_cookies(cookie_str: str) -> Dict[str, str]:
    """解析 Cookie 字符串

    支持两种格式：
    - "key1=val1; key2=val2"（标准格式）
    - "key1=val1&key2=val2"（少数情况）

    Args:
        cookie_str: Cookie 字符串

    Returns:
        dict: Cookie 字典
    """
    cookies = {}
    # 优先按 ; 分割
    separator = ';' if ';' in cookie_str else '&'
    for pair in cookie_str.split(separator):
        pair = pair.strip()
        if '=' in pair:
            k, v = pair.split('=', 1)
            cookies[k.strip()] = v.strip()
    return cookies
