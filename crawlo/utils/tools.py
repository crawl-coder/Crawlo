def custom_extractor_proxy(data: dict, key: str='proxy') -> dict | str | None:
    """只负责从 API 返回数据中提取代理部分"""
    if data.get("status") == 0:
        return data.get(key)  # 返回 {"http": "...", "https": "..."} 整个字典
    return None