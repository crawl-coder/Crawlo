"""P3-2 统一扩展点：register_downloader / unregister_downloader 测试"""

import pytest

from crawlo.downloader import (
    DOWNLOADER_MAP,
    get_downloader_class,
    register_downloader,
    unregister_downloader,
)


class DummyDownloader:
    """测试用下载器（不真正继承 DownloaderBase 以隔离测试）"""

    name = 'dummy'


def test_register_and_resolve():
    register_downloader('dummy', DummyDownloader)
    try:
        assert DOWNLOADER_MAP['dummy'] is DummyDownloader
        assert get_downloader_class('dummy') is DummyDownloader
    finally:
        unregister_downloader('dummy')


def test_unregister_returns_bool():
    register_downloader('dummy', DummyDownloader)
    assert unregister_downloader('dummy') is True
    assert unregister_downloader('dummy') is False
    assert 'dummy' not in DOWNLOADER_MAP


def test_register_invalid_args():
    with pytest.raises(ValueError):
        register_downloader('', DummyDownloader)
    with pytest.raises(ValueError):
        register_downloader('dummy', None)


def test_get_unknown_raises():
    with pytest.raises(ValueError):
        get_downloader_class('definitely_not_a_downloader')
