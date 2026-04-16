#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
股票加载器
提供A股股票列表加载功能（从数据库获取 - 同步版本）
"""
import warnings
import pymysql
from crawlo.logging import get_logger

logger = get_logger(__name__)

# 禁用警告
warnings.filterwarnings('ignore', category=Warning)


def get_db_config():
    """
    获取数据库配置
    
    Returns:
        dict: 数据库连接配置
    """
    # 动态导入以避免循环导入
    import importlib
    try:
        settings_module = importlib.import_module('listed_company_executive_crawler.settings')
    except ModuleNotFoundError:
        raise ImportError("Settings module not found. Please create a settings.py file in the project root directory.")
    
    return {
        'host': settings_module.MYSQL_HOST,
        'port': settings_module.MYSQL_PORT,
        'user': settings_module.MYSQL_USER,
        'password': settings_module.MYSQL_PASSWORD,
        'database': settings_module.MYSQL_DB,
        'charset': 'utf8mb4',
        'cursorclass': pymysql.cursors.DictCursor
    }


def load_a_stocks():
    """
    从数据库加载A股股票列表（同步版本）
    
    Returns:
        list: 股票代码和名称的列表，格式为 [(stock_code, stock_name), ...]
              代码格式保持数据库中存储的格式
    
    Example:
        >>> stocks = load_a_stocks()
        >>> print(stocks[:3])
        [('600285.SH', '羚锐制药'), ('000001.SZ', '平安银行'), ...]
    """
    db_config = get_db_config()
    conn = None
    cursor = None
    
    try:
        logger.info("开始从数据库加载股票列表...")
        
        # 创建数据库连接
        conn = pymysql.connect(**db_config)
        cursor = conn.cursor()
        
        # 查询股票列表
        sql = """
            SELECT stock_code, stock_name 
            FROM listed_stock_list 
            WHERE stock_type IN ('A股', '科创板', '创业板')
        """
        
        cursor.execute(sql)
        rows = cursor.fetchall()
        
        if not rows:
            logger.warning("未查询到股票数据")
            return []
        
        # 转换为列表格式
        stocks = [(row['stock_code'], row['stock_name']) for row in rows]
        
        logger.info(f"✓ 成功加载 {len(stocks)} 只股票（A股/科创板/创业板）")
        
        return stocks
        
    except Exception as e:
        logger.error(f"加载股票列表失败: {e}")
        return []
    finally:
        # 确保资源被正确释放
        if cursor:
            try:
                cursor.close()
            except Exception as e:
                logger.warning(f"关闭游标时出现异常: {e}")
        if conn:
            try:
                conn.close()
            except Exception as e:
                logger.warning(f"关闭连接时出现异常: {e}")
