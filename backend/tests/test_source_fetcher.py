from unittest.mock import patch

import pytest

from app.services.source_fetcher import SourceFetchError, fetch_text_source


class FakeResponse:
    def __init__(self, data: bytes):
        self.data = data

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, size: int) -> bytes:
        return self.data[:size]


def test_fetch_text_source_decodes_utf8():
    with patch("app.services.source_fetcher.urlopen", return_value=FakeResponse("vless://example.com:443".encode())):
        assert fetch_text_source("https://example.com/source") == "vless://example.com:443"


def test_fetch_text_source_rejects_non_http_url():
    with pytest.raises(SourceFetchError):
        fetch_text_source("file:///tmp/source")


def test_fetch_text_source_enforces_size_limit():
    with patch("app.services.source_fetcher.urlopen", return_value=FakeResponse(b"123456")):
        with pytest.raises(SourceFetchError):
            fetch_text_source("https://example.com/source", max_bytes=5)
