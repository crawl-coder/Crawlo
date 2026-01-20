import random
import hashlib
import urllib.parse
from datetime import datetime
from typing import Dict, Optional
from decimal import Decimal, ROUND_HALF_UP


def round_if_numeric(value, decimal_places=4):
    """
    如果 value 是数值（int/float/Decimal），则保留指定小数位；
    否则原样返回（用于字符串、日期等）。
    """
    if value is None:
        return None

    # 排除布尔值
    if isinstance(value, bool):
        return value

    if isinstance(value, (int, float, Decimal)):
        try:
            # 转为 Decimal 并四舍五入，然后转为 float
            d = Decimal(str(value))
            quantize_exp = Decimal('0.1') ** decimal_places
            rounded = d.quantize(quantize_exp, rounding=ROUND_HALF_UP)
            return float(rounded)  # 转换为 float
        except Exception:
            return float(value) if isinstance(value, (int, float, Decimal)) else value
    else:
        return value


def parse_tenure_dates(date_string: str) -> Dict[str, Optional[str]]:
    """
    解析任期日期字符串，返回开始日期和结束日期

    Args:
        date_string: 日期字符串，格式为"YYYY-MM-DD至今"或"YYYY-MM-DD至YYYY-MM-DD"

    Returns:
        Dict: 包含Tenure_Start_Date和Tenure_End_Date的字典，如果结束日期是"至今"则设为None
    """
    try:
        if "至今" in date_string:
            # 处理"YYYY-MM-DD至今"格式
            start_date = date_string.replace("至今", "").strip()

            # 验证日期格式
            datetime.strptime(start_date, "%Y-%m-%d")

            return {
                "tenure_start_date": start_date,
                "tenure_end_date": None
            }
        elif "至" in date_string:
            # 处理"YYYY-MM-DD至YYYY-MM-DD"格式
            dates = date_string.split("至")
            if len(dates) == 2:
                start_date = dates[0].strip()
                end_date = dates[1].strip()

                # 验证日期格式
                datetime.strptime(start_date, "%Y-%m-%d")
                datetime.strptime(end_date, "%Y-%m-%d")

                return {
                    "tenure_start_date": start_date,
                    "tenure_end_date": end_date
                }

        raise ValueError("无效的日期格式")

    except ValueError as e:
        raise ValueError(f"日期格式错误: {e}")


def get_v_params(data):
    """
    格式化参数，生成v值

    :param data: 参数字典
    :return: 格式化后的参数字符串
    """
    e = []
    # 遍历字典，模拟 for...in
    for key in data:
        encoded_key = urllib.parse.quote(str(key), safe='')
        encoded_value = urllib.parse.quote(str(data[key]), safe='')
        e.append(f"{encoded_key}={encoded_value}")

    # 生成 v=随机数，去掉小数点（保留前导零）
    rand = random.random()  # 0.123456789...
    v_str = f"v={rand}".replace(".", "")
    e.append(v_str)

    # 用 & 连接返回
    return "&".join(e)


def generate_pmid(stock_code: str, report_date: str, default: str = "0" * 32) -> str:
    """
    安全生成 32 位唯一标识 pmid（MD5 哈希值）

    Args:
        stock_code (str): 股票代码
        report_date (str): 报告日期，格式如 '2025-06-30'
        default (str): 当输入无效时返回的默认 32 位字符串，默认为 32 个 '0'

    Returns:
        str: 严格 32 位小写 MD5 哈希值，异常时返回 default
    """
    # 校验输入是否为非空字符串
    if not isinstance(stock_code, str) or not stock_code.strip():
        return default
    if not isinstance(report_date, str) or not report_date.strip():
        return default

    try:
        raw_str = f"{stock_code.strip()}{report_date.strip()}"
        md5_hash = hashlib.md5(raw_str.encode('utf-8')).hexdigest()

        # 双保险：确保返回 32 位
        if len(md5_hash) == 32:
            return md5_hash
        else:
            return default
    except Exception:
        return default


def add_exchange_suffix(code):
    """
    为单个股票代码添加交易所后缀：

    - 上交所（.SH）：60xxxx, 68xxxx
    - 深交所（.SZ）：00xxxx, 01xxxx, 02xxxx, 30xxxx
    - 北交所（.BJ）：
        * 43xxxx（老三板，按用户要求暂归入）
        * 82xxxx（优先股）
        * 83xxxx, 87xxxx（普通股）
        * 88xxxx（公开发行等）
        * 920000–920999（2024年新增独立号段）

    参数:
        code (str or int): 单个股票代码，如 300436 或 '002314'

    返回:
        str: 带后缀的代码，如 '300436.SZ'

    异常:
        ValueError: 代码格式无效或前缀无法识别
    """
    s = str(code).strip()
    if not s:
        raise ValueError("Empty stock code")

    s = s.zfill(6)
    if len(s) != 6 or not s.isdigit():
        raise ValueError(f"Invalid stock code format: '{code}'")

    if s.startswith(('60', '68')):
        return s + '.SH'
    elif s.startswith(('00', '01', '02', '30')):
        return s + '.SZ'
    elif (
            s.startswith(('43', '82', '83', '87', '88')) or
            (s.startswith('920') and s <= '920999')
    ):
        return s + '.BJ'
    else:
        raise ValueError(f"Unrecognized stock code prefix: {s}")


