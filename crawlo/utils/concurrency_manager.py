import os
import platform
import logging
from typing import Optional

try:
    import psutil  # 用于获取系统资源信息的第三方库
except ImportError:
    psutil = None  # 如果psutil不可用则设为None

logger = logging.getLogger(__name__)


def calculate_optimal_concurrency(user_specified: Optional[int] = None, use_logical_cores: bool = True) -> int:
    """
    基于系统资源计算最优并发数，或使用用户指定值

    参数:
        user_specified: 用户指定的并发数（优先使用）
        use_logical_cores: 是否使用逻辑CPU核心数（超线程），默认为True

    返回:
        计算得出的最优并发数

    说明:
        1. 优先使用用户指定的并发数
        2. 根据操作系统类型采用不同的计算策略：
           - Windows: 保守计算，避免内存压力
           - macOS: 平衡资源使用
           - Linux: 充分利用服务器资源
           - 其他系统: 使用合理默认值
        3. 使用可用内存和CPU核心数进行计算
        4. 提供psutil不可用时的备用方案
    """
    # 优先使用用户指定的并发数
    if user_specified is not None:
        logger.info(f"使用用户指定的并发数: {user_specified}")
        return user_specified

    try:
        current_os = platform.system()  # 获取当前操作系统类型
        logger.debug(f"检测到操作系统: {current_os}")

        # 获取CPU核心数（根据参数决定是否使用逻辑核心）
        cpu_count = psutil.cpu_count(logical=use_logical_cores) or 1 if psutil else os.cpu_count() or 1

        # 根据操作系统类型选择不同的计算方法
        if current_os == "Windows":
            concurrency = _get_concurrency_for_windows(cpu_count, use_logical_cores)
        elif current_os == "Darwin":  # macOS系统
            concurrency = _get_concurrency_for_macos(cpu_count, use_logical_cores)
        elif current_os == "Linux":
            concurrency = _get_concurrency_for_linux(cpu_count, use_logical_cores)
        else:  # 其他操作系统
            concurrency = _get_concurrency_default(cpu_count)

        logger.info(f"计算得到最大并发数: {concurrency}")
        return concurrency

    except Exception as e:
        logger.warning(f"动态计算并发数失败: {str(e)}，使用默认值50")
        return 50  # 计算失败时的安全默认值


def _get_concurrency_for_windows(cpu_count: int, use_logical_cores: bool) -> int:
    """Windows系统专用的并发数计算逻辑"""
    if psutil:
        # 计算可用内存（GB）
        available_memory = psutil.virtual_memory().available / (1024 ** 3)
        # 内存计算：每4GB可用内存分配10个并发
        mem_based = int((available_memory / 4) * 10)
        # CPU计算：使用逻辑核心时乘数较大
        cpu_based = cpu_count * (5 if use_logical_cores else 3)
        # 取5-100之间的值，选择内存和CPU限制中较小的
        return max(5, min(100, mem_based, cpu_based))
    else:
        # 无psutil时的备用方案
        return min(50, cpu_count * 5)


def _get_concurrency_for_macos(cpu_count: int, use_logical_cores: bool) -> int:
    """macOS系统专用的并发数计算逻辑"""
    if psutil:
        available_memory = psutil.virtual_memory().available / (1024 ** 3)
        # 内存计算：每3GB可用内存分配10个并发
        mem_based = int((available_memory / 3) * 10)
        # CPU计算：使用逻辑核心时乘数较大
        cpu_based = cpu_count * (6 if use_logical_cores else 4)
        # 取5-120之间的值
        return max(5, min(120, mem_based, cpu_based))
    else:
        try:
            # macOS备用方案：使用系统命令获取物理CPU核心数
            import subprocess
            output = subprocess.check_output(["sysctl", "hw.physicalcpu"])
            cpu_count = int(output.split()[1])
            return min(60, cpu_count * 5)
        except:
            return 40  # Mac电脑的合理默认值


def _get_concurrency_for_linux(cpu_count: int, use_logical_cores: bool) -> int:
    """Linux系统专用的并发数计算逻辑（更激进）"""
    if psutil:
        available_memory = psutil.virtual_memory().available / (1024 ** 3)
        # 内存计算：每1.5GB可用内存分配10个并发
        mem_based = int((available_memory / 1.5) * 10)
        # CPU计算：服务器环境使用更大的乘数
        cpu_based = cpu_count * (8 if use_logical_cores else 5)
        # 取5-200之间的值
        return max(5, min(200, mem_based, cpu_based))
    else:
        try:
            # Linux备用方案：解析/proc/cpuinfo文件
            with open("/proc/cpuinfo") as f:
                cpu_count = f.read().count("processor\t:")
                if cpu_count > 0:
                    return min(200, cpu_count * 8)
        except:
            return 50  # Linux服务器的合理默认值


def _get_concurrency_default(cpu_count: int) -> int:
    """未知操作系统的默认计算逻辑"""
    return min(50, cpu_count * 5)  # 保守的默认计算方式