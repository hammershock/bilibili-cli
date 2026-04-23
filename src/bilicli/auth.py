"""QR code login flow and credential management."""

import sys
import time
from typing import Dict, Optional

from bilicli.client import BiliClient, BiliError

_QR_GENERATE = "https://passport.bilibili.com/x/passport-login/web/qrcode/generate"
_QR_POLL = "https://passport.bilibili.com/x/passport-login/web/qrcode/poll"

# Poll status codes
_STATUS_SUCCESS = 0
_STATUS_EXPIRED = 86038
_STATUS_SCANNED = 86090   # scanned but not confirmed
_STATUS_WAITING = 86101   # not yet scanned


def _print_qr(url: str) -> None:
    """Print QR code to terminal using qrcode library (ASCII output)."""
    try:
        import qrcode
        qr = qrcode.QRCode(border=1)
        qr.add_data(url)
        qr.make(fit=True)
        qr.print_ascii(invert=True)
    except ImportError:
        print(f"QR URL (install qrcode for visual): {url}")


def login(client: BiliClient) -> bool:
    """Run QR code login flow. Returns True on success."""
    data = client.get(_QR_GENERATE)
    qr_url: str = data["url"]
    qrcode_key: str = data["qrcode_key"]

    print("Scan this QR code with the Bilibili app:\n")
    _print_qr(qr_url)
    print("\nWaiting for scan...")

    deadline = time.time() + 180
    last_status = None

    while time.time() < deadline:
        time.sleep(2)
        result = client.get_json(_QR_POLL, params={"qrcode_key": qrcode_key})
        status_data = result.get("data", {})
        code = status_data.get("code", -1)

        if code == _STATUS_SUCCESS:
            # Extract cookies from the response (Set-Cookie headers are handled by httpx)
            # bilibili also returns them in the response body URL
            cookies = _extract_cookies_from_poll(client, qrcode_key)
            client.save_cookies(cookies)
            print("\nLogin successful!")
            return True
        elif code == _STATUS_EXPIRED:
            print("\nQR code expired. Please run `bilicli login` again.")
            return False
        elif code == _STATUS_SCANNED and last_status != _STATUS_SCANNED:
            print("QR code scanned, please confirm on your phone...")
        elif code == _STATUS_WAITING and last_status != _STATUS_WAITING:
            pass  # still waiting, no need to print again

        last_status = code

    print("\nLogin timed out.")
    return False


def _extract_cookies_from_poll(client: BiliClient, qrcode_key: str) -> Dict[str, str]:
    """
    After a successful poll, extract cookies from the HTTP client's cookie jar.
    httpx automatically handles Set-Cookie headers during the poll request.
    """
    # Re-issue the poll to capture cookies via httpx cookie jar
    resp = client.get_raw(_QR_POLL, params={"qrcode_key": qrcode_key})
    jar = resp.cookies

    cookies: Dict[str, str] = {}
    for name in ("SESSDATA", "bili_jct", "DedeUserID", "DedeUserID__ckMd5", "sid"):
        val = jar.get(name)
        if val:
            cookies[name] = val

    # Also pull from the client's existing cookie jar (accumulated)
    for name in ("SESSDATA", "bili_jct", "DedeUserID", "DedeUserID__ckMd5", "sid", "buvid3"):
        if name not in cookies:
            val = client.http.cookies.get(name)
            if val:
                cookies[name] = val

    return cookies


def whoami(client: BiliClient) -> Optional[Dict]:
    """Return current user info, or None if not logged in."""
    if not client.is_logged_in():
        return None
    try:
        data = client.get("https://api.bilibili.com/x/web-interface/nav")
        return {
            "uid": data.get("mid"),
            "name": data.get("uname"),
            "level": data.get("level_info", {}).get("current_level"),
            "vip": data.get("vipStatus", 0) == 1,
            "face": data.get("face"),
        }
    except BiliError:
        return None
