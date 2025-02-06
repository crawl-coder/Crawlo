#!/usr/bin/python
# -*- coding:UTF-8 -*-
import random
import asyncio


class Downloader:
    def __init__(self):
        self._active = set()

    async def fetch(self, request):
        self._active.add(request)
        response = await self.download(request)
        self._active.remove(request)
        return response

    async def download(self, url):
        # response = requests.get(url)
        # print(response)
        await asyncio.sleep(random.uniform(0, 1))
        return 'result'

    def idle(self) -> bool:
        return len(self) == 0

    def __len__(self):
        return len(self._active)
