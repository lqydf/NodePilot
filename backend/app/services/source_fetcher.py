from __future__ import annotations

from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class SourceFetchError(RuntimeError):
    """Raised when a public text source cannot be fetched safely."""


def fetch_text_source(url: str, *, timeout: float = 10.0, max_bytes: int = 2_000_000) -> str:
    """Fetch a bounded UTF-8 text source over HTTP(S).

    This adapter only retrieves public text. It does not execute source content,
    follow arbitrary protocols, or probe the endpoints contained in the text.
    """
    if not (url.startswith("https://") or url.startswith("http://")):
        raise SourceFetchError("only HTTP(S) sources are supported")
    if timeout <= 0:
        raise ValueError("timeout must be positive")
    if max_bytes < 1:
        raise ValueError("max_bytes must be positive")

    request = Request(url, headers={"User-Agent": "NodePilot/0.1 source-fetcher"})
    try:
        with urlopen(request, timeout=timeout) as response:
            data = response.read(max_bytes + 1)
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        raise SourceFetchError(str(exc)) from exc

    if len(data) > max_bytes:
        raise SourceFetchError("source exceeds max_bytes")
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise SourceFetchError("source is not valid UTF-8 text") from exc
