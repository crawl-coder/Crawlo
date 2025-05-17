#!/usr/bin/python
# -*- coding:UTF-8 -*-
from typing import Optional
from httpx import AsyncClient, Timeout

from crawlo import Response
from crawlo.downloader import DownloaderBase


class HttpXDownloader(DownloaderBase):
    def __init__(self, crawler):
        super().__init__(crawler)
        self._client: Optional[AsyncClient] = None
        self._timeout: Optional[Timeout] = None

    def open(self):
        super().open()
        self._timeout = Timeout(timeout=self.crawler.settings.get_int("DOWNLOAD_TIMEOUT"))

    async def fetch(self, request) -> Optional[Response]:
        async with self._active(request):
            response = await self.download(request)
            return response

    async def download(self, request) -> Optional[Response]:
        try:
            proxies = None
            async with AsyncClient(timeout=self._timeout, proxies=proxies) as client:
                self.logger.debug(f"request downloading: {request.url}，method: {request.method}")
                response = await client.request(
                    url=request.url,
                    method=request.method,
                    headers=request.headers,
                    cookies=request.cookies,
                    data=request.body
                )
                body = await response.aread()
        except Exception as e:
            self.logger.error(f"Error downloading {request}: {e}")
            return None
        else:
            self.crawler.stats.inc_value('response_received_count')

        return self.structure_response(request=request, response=response, body=body)

    @staticmethod
    def structure_response(request, response, body) -> Response:
        return Response(
            url=response.url,
            headers=dict(response.headers),
            status_code=response.status_code,
            body=body,
            request=request
        )