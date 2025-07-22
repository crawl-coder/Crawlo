#!/usr/bin/python
# -*- coding:UTF-8 -*-
from typing import Optional, Dict, Any
from playwright.async_api import Browser, Page, Response as PlaywrightResponse
from crawlo import Response, Request
from crawlo.downloader import DownloaderBase


class PlaywrightDownloader(DownloaderBase):
    def __init__(self, crawler):
        super().__init__(crawler)
        # Playwright 核心对象
        self.browser: Optional[Browser] = None  # 浏览器实例
        self.context: Optional[Any] = None  # 浏览器上下文（隔离cookies等）

        # 可配置参数（通过crawler.settings覆盖默认值）
        self._browser_type: str = "chromium"  # 浏览器类型（chromium/firefox/webkit）
        self._headless: bool = True  # 是否无头模式
        self._timeout: int = 30000  # 操作超时（毫秒）
        self._viewport: Dict[str, int] = {"width": 1280, "height": 720}  # 视口大小
        self._extra_launch_args: Dict[str, Any] = {}  # 浏览器启动额外参数

    async def _init_browser(self):
        """初始化Playwright浏览器实例"""
        from playwright.async_api import async_playwright

        # 启动Playwright引擎
        playwright = await async_playwright().start()

        # 根据配置选择浏览器类型
        browser_launcher = {
            "chromium": playwright.chromium,
            "firefox": playwright.firefox,
            "webkit": playwright.webkit
        }.get(self._browser_type, playwright.chromium)  # 默认chromium

        # 启动浏览器（含启动参数）
        self.browser = await browser_launcher.launch(
            headless=self._headless,  # 无头模式开关
            timeout=self._timeout,  # 启动超时
            **self._extra_launch_args  # 透传额外参数（如代理配置）
        )

        # 创建浏览器上下文（隔离环境）
        self.context = await self.browser.new_context(
            viewport=self._viewport,  # 设置窗口大小
            user_agent=self.crawler.settings.get("USER_AGENT")  # 自定义UA
        )

    def open(self):
        """从crawler配置加载参数"""
        super().open()  # 调用父类初始化

        # 读取配置（支持在settings.py中覆盖）
        self._browser_type = self.crawler.settings.get("PLAYWRIGHT_BROWSER", "chromium")
        self._headless = self.crawler.settings.get_bool("HEADLESS", True)
        self._timeout = self.crawler.settings.get_int("PLAYWRIGHT_TIMEOUT", 30000)
        self._viewport = self.crawler.settings.get_dict("VIEWPORT", {"width": 1280, "height": 720})
        self._extra_launch_args = self.crawler.settings.get_dict("PLAYWRIGHT_LAUNCH_ARGS", {})

    async def download(self, request: Request) -> Response:
        """
        核心下载方法：
        1. 创建新页面Tab
        2. 加载目标URL
        3. 获取渲染后的内容
        """
        if not self.browser:
            await self._init_browser()  # 懒加载浏览器

        page = await self.context.new_page()  # 每个请求独立Page（自动隔离）

        try:
            # 设置请求头（模拟浏览器）
            if request.headers:
                await page.set_extra_http_headers(request.headers)

            # 导航到目标URL（支持等待策略配置）
            response = await page.goto(
                request.url,
                timeout=self._timeout,
                wait_until="domcontentloaded"  # 等待策略：domcontentloaded/networkidle/load
            )

            # 特殊处理POST请求（Playwright限制需用API方式）
            if request.method.lower() == "post":
                return await self._handle_post_request(request, page)

            # 执行自定义JavaScript（用于提取动态数据）
            if request.meta.get("execute_js"):
                result = await page.evaluate(request.meta["execute_js"])
                request.meta["js_result"] = result  # 存储JS执行结果

            # 获取渲染后的完整HTML（含动态生成内容）
            body = await page.content()

            # 调试模式下截图（用于排查页面问题）
            if self.crawler.settings.get_bool("DEBUG"):
                screenshot = await page.screenshot(type="png")
                request.meta["screenshot"] = screenshot  # 截图存入request.meta

            # 构造统一响应对象
            return self._structure_response(request, response, body)

        except Exception as e:
            self.logger.error(f"页面下载失败: {str(e)}")
            raise
        finally:
            await page.close()  # 确保页面关闭，避免资源泄漏

    async def _handle_post_request(self, request: Request, page: Page) -> Response:
        """
        处理POST请求的特殊方法：
        通过页面内fetch API发送POST请求，并监听响应
        """
        async with page.expect_response(request.url) as response_info:
            # 在页面上下文中执行fetch
            await page.evaluate(
                """async ({url, headers, body}) => {
                    await fetch(url, {
                        method: 'POST',
                        headers: headers,
                        body: body
                    });
                }""",
                {
                    "url": request.url,
                    "headers": request.headers or {},
                    "body": request.body or ""
                }
            )

        response = await response_info.value  # 获取API响应
        body = await response.text()  # 读取响应体
        return self._structure_response(request, response, body)

    @staticmethod
    def _structure_response(
            request: Request,
            response: PlaywrightResponse,
            body: str
    ) -> Response:
        """
        标准化响应格式：
        将Playwright的响应转换为crawlo的统一Response对象
        """
        return Response(
            url=str(response.url),  # 最终URL（含重定向）
            headers=response.headers,  # 响应头
            status_code=response.status,  # HTTP状态码
            body=body.encode('utf-8'),  # 响应体（转bytes）
            request=request  # 关联的请求对象
        )

    async def close(self) -> None:
        """资源清理：关闭浏览器实例和上下文"""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        await super().close()  # 调用父类清理逻辑