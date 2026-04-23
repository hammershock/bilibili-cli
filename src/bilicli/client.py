"""HTTP client with cookie management and proper headers."""

import json
import time
from pathlib import Path
from typing import Any, Dict, Optional

import httpx

CONFIG_DIR = Path.home() / ".config" / "bilicli"
COOKIES_FILE = CONFIG_DIR / "cookies.json"

BASE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.bilibili.com/",
    "Origin": "https://www.bilibili.com",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


class BiliError(Exception):
    """Bilibili API returned a non-zero code."""

    def __init__(self, code: int, message: str) -> None:
        super().__init__(f"[{code}] {message}")
        self.code = code
        self.message = message


class BiliClient:
    def __init__(self) -> None:
        self._cookies: Dict[str, str] = {}
        self._http: Optional[httpx.Client] = None
        self._load_cookies()

    def _load_cookies(self) -> None:
        if COOKIES_FILE.exists():
            try:
                self._cookies = json.loads(COOKIES_FILE.read_text())
            except Exception:
                self._cookies = {}

    def save_cookies(self, cookies: Dict[str, str]) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_DIR.chmod(0o700)
        self._cookies = cookies
        COOKIES_FILE.write_text(json.dumps(cookies, indent=2, ensure_ascii=False))
        COOKIES_FILE.chmod(0o600)
        # rebuild client with new cookies
        if self._http:
            self._http.close()
            self._http = None

    def clear_cookies(self) -> None:
        self._cookies = {}
        if COOKIES_FILE.exists():
            COOKIES_FILE.unlink()
        if self._http:
            self._http.close()
            self._http = None

    def is_logged_in(self) -> bool:
        return bool(self._cookies.get("SESSDATA"))

    @property
    def http(self) -> httpx.Client:
        if self._http is None:
            self._http = httpx.Client(
                headers=BASE_HEADERS,
                cookies=self._cookies,
                timeout=30,
                follow_redirects=True,
            )
        return self._http

    def get(self, url: str, params: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
        resp = self.http.get(url, params=params, **kwargs)
        resp.raise_for_status()
        data = resp.json()
        code = data.get("code", 0)
        if code != 0:
            raise BiliError(code, data.get("message", "unknown error"))
        return data.get("data")

    def get_raw(self, url: str, params: Optional[Dict[str, Any]] = None, **kwargs) -> httpx.Response:
        """Return raw response without parsing (for binary or non-standard responses)."""
        resp = self.http.get(url, params=params, **kwargs)
        resp.raise_for_status()
        return resp

    def get_json(self, url: str, params: Optional[Dict[str, Any]] = None, **kwargs) -> Dict:
        """Return full JSON response without raising on non-zero code."""
        resp = self.http.get(url, params=params, **kwargs)
        resp.raise_for_status()
        return resp.json()

    def post(self, url: str, data: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
        resp = self.http.post(url, data=data, **kwargs)
        resp.raise_for_status()
        result = resp.json()
        code = result.get("code", 0)
        if code != 0:
            raise BiliError(code, result.get("message", "unknown error"))
        return result.get("data")

    def close(self) -> None:
        if self._http:
            self._http.close()
            self._http = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


# Module-level singleton
_client: Optional[BiliClient] = None


def get_client() -> BiliClient:
    global _client
    if _client is None:
        _client = BiliClient()
    return _client
