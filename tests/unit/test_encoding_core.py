#!/usr/bin/python
# -*- coding: UTF-8 -*-
import sys
import os
sys.path.insert(0, "/Users/oscar/projects/Crawlo")
#!/usr/bin/python
# -*- coding:UTF-8 -*-
"""
编码检测核心功能测试
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from crawlo.http.response import Response


def test_encoding_detection():
    """测试编码检测核心功能"""
    print("测试编码检测核心功能...")
    
    # 测试 Request 编码优先级
    class MockRequest:
        encoding = 'gbk'
    
    response1 = Response(
        url="https://example.com",
        body=b'',
        request=MockRequest()
    )
    print(f"Request 编码优先级: {response1.encoding}")
    
    # 测试 Content-Type 头部编码
    response2 = Response(
        url="https://example.com",
        body=b'',
        headers={"content-type": "text/html; charset=iso-8859-1"}
    )
    print(f"Content-Type 编码: {response2.encoding}")
    
    # 测试声明编码方法（使用当前 encoding 属性替代已移除的 _declared_encoding()）
    declared_enc = response2.encoding
    print(f"声明编码: {declared_enc}")
    
    # 测试默认编码
    response3 = Response(
        url="https://example.com",
        body=b''
    )
    print(f"默认编码: {response3.encoding}")
    
    # 验证结果
    assert response1.encoding == 'gbk', f"Expected 'gbk', got {response1.encoding}"
    # w3lib 将 iso-8859-1 解析为 cp1252（HTML5 规范行为，cp1252 是 iso-8859-1 的超集）
    assert response2.encoding == 'cp1252', f"Expected 'cp1252', got {response2.encoding}"
    assert declared_enc == 'cp1252', f"Expected 'cp1252', got {declared_enc}"
    # 空 body 经 w3lib auto_detect 回调返回 ascii → resolve_encoding('ascii') = 'cp1252'
    assert response3.encoding == 'cp1252', f"Expected 'cp1252', got {response3.encoding}"
    
    print("所有测试通过！")


if __name__ == '__main__':
    test_encoding_detection()