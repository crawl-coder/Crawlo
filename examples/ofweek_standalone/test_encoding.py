#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
测试 ofweek 网页编码识别问题
"""
import asyncio
import httpx
from crawlo.network.response import Response
from crawlo.network.request import Request
from crawlo.utils.encoding_detector import EncodingDetector

URL = "https://ee.ofweek.com/2026-03/ART-8110-2812-30684071.html"

async def test_encoding():
    """测试编码识别"""
    print("=" * 80)
    print(f"测试URL: {URL}")
    print("=" * 80)
    
    # 1. 使用 httpx 下载网页
    print("\n[1] 下载网页...")
    async with httpx.AsyncClient(follow_redirects=True) as client:
        http_response = await client.get(URL, timeout=30.0)
        body_bytes = http_response.content
        headers = dict(http_response.headers)
    
    print(f"   响应状态码: {http_response.status_code}")
    print(f"   响应体大小: {len(body_bytes)} bytes")
    print(f"   Content-Type: {headers.get('content-type', 'N/A')}")
    
    # 2. 检测编码
    print("\n[2] 编码检测...")
    detected_encoding = EncodingDetector.detect(
        body=body_bytes,
        headers=headers,
        declared_encoding=None,
    )
    print(f"   检测到的编码: {detected_encoding}")
    
    # 3. 尝试不同编码解码
    print("\n[3] 尝试不同编码解码...")
    encodings_to_try = ['utf-8', 'gbk', 'gb2312', 'gb18030', 'latin-1']
    
    for enc in encodings_to_try:
        try:
            text = body_bytes.decode(enc, errors='strict')
            # 检查是否包含中文
            has_chinese = any('\u4e00' <= char <= '\u9fff' for char in text[:1000])
            print(f"   ✓ {enc:12s} - 解码成功, 包含中文: {has_chinese}")
            
            # 显示前200个字符
            print(f"   内容预览: {text[:200]}")
            print()
        except UnicodeDecodeError as e:
            print(f"   ✗ {enc:12s} - 解码失败: {e}")
        except Exception as e:
            print(f"   ✗ {enc:12s} - 其他错误: {e}")
    
    # 4. 使用 EncodingDetector.decode_body 解码
    print("\n[4] 使用 EncodingDetector.decode_body 解码...")
    try:
        decoded_text = EncodingDetector.decode_body(
            body=body_bytes,
            encoding=detected_encoding,
            headers=headers,
        )
        print(f"   解码成功")
        print(f"   内容预览（前500字符）:")
        print(f"   {decoded_text[:500]}")
        
        # 检查是否有 U+FFFD 替换字符
        fffd_count = decoded_text.count('\ufffd')
        if fffd_count > 0:
            print(f"\n   ⚠️  发现 {fffd_count} 个 U+FFFD 替换字符（乱码标志）")
        else:
            print(f"\n   ✓ 未发现 U+FFFD 替换字符")
    except Exception as e:
        print(f"   解码失败: {e}")
    
    # 5. 创建 Response 对象测试
    print("\n[5] 创建 Response 对象测试...")
    request = Request(url=URL)
    print(f"   Request.encoding: {getattr(request, 'encoding', None)}")
    
    # 先手动检测编码
    manual_encoding = EncodingDetector.detect(
        body=body_bytes,
        headers=headers,
        declared_encoding=None,
    )
    print(f"   手动检测编码: {manual_encoding}")
    
    response = Response(
        url=URL,
        headers=headers,
        body=body_bytes,
        method='GET',
        request=request,
        status=200,
    )
    
    print(f"   Response.encoding: {response.encoding}")
    print(f"   Response._determine_encoding() 返回值: {response._determine_encoding()}")
    print(f"   Response.text 长度: {len(response.text)}")
    
    # 检查 text 中是否有替换字符
    fffd_in_text = response.text.count('\ufffd')
    if fffd_in_text > 0:
        print(f"   ⚠️  Response.text 包含 {fffd_in_text} 个 U+FFFD 替换字符")
    else:
        print(f"   ✓  Response.text 无替换字符")
    
    # 6. 测试 XPath 提取
    print("\n[6] 测试 XPath 提取内容...")
    try:
        title = response.xpath('//title/text()').get()
        print(f"   页面标题: {title}")
        
        content_elem = response.xpath('//div[@class="TRS_Editor"]|//*[@id="articleC"]')
        if content_elem:
            content_text = content_elem.xpath('.//text()').getall()
            content = '\n'.join([t.strip() for t in content_text if t.strip()])
            
            print(f"   内容长度: {len(content)} 字符")
            print(f"   内容预览（前300字符）:")
            print(f"   {content[:300]}")
            
            # 检查内容中的替换字符
            fffd_in_content = content.count('\ufffd')
            if fffd_in_content > 0:
                print(f"\n   ⚠️  提取的内容包含 {fffd_in_content} 个 U+FFFD 替换字符")
            else:
                print(f"\n   ✓  提取的内容无替换字符")
        else:
            print("   未找到内容区域")
    except Exception as e:
        print(f"   XPath 提取失败: {e}")
    
    # 7. 检查 HTML meta 标签
    print("\n[7] 检查 HTML meta charset 标签...")
    import re
    text_preview = body_bytes[:2000].decode('utf-8', errors='replace')
    
    # HTML5: <meta charset="utf-8">
    meta_charset = re.search(r'<meta\s+charset=["\']?([\w-]+)', text_preview, re.IGNORECASE)
    if meta_charset:
        print(f"   找到 meta charset: {meta_charset.group(1)}")
    
    # HTML4: <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
    meta_http = re.search(r'<meta[^>]+http-equiv=["\']?content-type["\']?[^>]*>', text_preview, re.IGNORECASE)
    if meta_http:
        charset_match = re.search(r'charset=([\w-]+)', meta_http.group(0), re.IGNORECASE)
        if charset_match:
            print(f"   找到 meta http-equiv charset: {charset_match.group(1)}")
    
    if not meta_charset and not meta_http:
        print("   未找到 meta charset 标签")
    
    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_encoding())
