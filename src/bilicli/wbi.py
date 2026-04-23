"""WBI (Wbi Risk Control) signature implementation.

Reference: https://socialsisteryi.github.io/bilibili-API-collect/docs/misc/sign/wbi.html
"""

import hashlib
import time
import urllib.parse
from typing import Dict, Any, Tuple

# Mixin key reorder table (hardcoded, from bilibili-API-collect)
MIXIN_KEY_ENC_TAB = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35,
    27, 43, 5, 49, 33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13,
    37, 48, 7, 16, 24, 55, 40, 61, 26, 17, 0, 1, 60, 51, 30, 4,
    22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11, 36, 20, 34, 44, 52,
]

# Characters to strip from param values before signing
_STRIP_CHARS = "!'()*"

# Cached keys: (img_key, sub_key, fetched_at)
_wbi_keys_cache: Tuple[str, str, float] = ("", "", 0.0)
_CACHE_TTL = 1800  # 30 minutes


def _get_mixin_key(img_key: str, sub_key: str) -> str:
    raw = img_key + sub_key  # 64 chars
    return "".join(raw[i] for i in MIXIN_KEY_ENC_TAB)[:32]


def _extract_key_from_url(url: str) -> str:
    """Extract key from wbi image URL filename (strip path and extension)."""
    filename = url.split("/")[-1]
    return filename.split(".")[0]


def fetch_wbi_keys(client) -> Tuple[str, str]:
    """Fetch WBI img/sub keys from /x/web-interface/nav. Uses cache."""
    global _wbi_keys_cache
    img_key, sub_key, fetched_at = _wbi_keys_cache
    if img_key and time.time() - fetched_at < _CACHE_TTL:
        return img_key, sub_key

    data = client.get("https://api.bilibili.com/x/web-interface/nav")
    wbi_img = data["wbi_img"]
    img_key = _extract_key_from_url(wbi_img["img_url"])
    sub_key = _extract_key_from_url(wbi_img["sub_url"])
    _wbi_keys_cache = (img_key, sub_key, time.time())
    return img_key, sub_key


def sign_params(params: Dict[str, Any], img_key: str, sub_key: str) -> Dict[str, Any]:
    """Add w_rid and wts to params (returns new dict, does not mutate input)."""
    mixin_key = _get_mixin_key(img_key, sub_key)
    wts = int(time.time())
    signed = dict(params)
    signed["wts"] = wts

    # Sort by key, strip special chars from values
    items = sorted(signed.items(), key=lambda x: x[0])
    query = "&".join(
        f"{k}={''.join(c for c in str(v) if c not in _STRIP_CHARS)}"
        for k, v in items
    )
    w_rid = hashlib.md5((query + mixin_key).encode()).hexdigest()
    signed["w_rid"] = w_rid
    return signed


def wbi_get(client, url: str, params: Dict[str, Any]) -> Any:
    """Convenience: fetch WBI keys, sign params, then GET."""
    img_key, sub_key = fetch_wbi_keys(client)
    signed = sign_params(params, img_key, sub_key)
    return client.get(url, params=signed)
