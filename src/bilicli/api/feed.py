"""Recommended video feed (requires login)."""

from typing import Any, Dict

from bilicli.client import BiliClient
from bilicli.wbi import wbi_get

_FEED_URL = "https://api.bilibili.com/x/web-interface/wbi/index/top/feed/rcmd"


def get_feed(
    client: BiliClient,
    page_size: int = 10,
    fresh_type: int = 3,
) -> Dict[str, Any]:
    """
    Get personalized recommended video feed (login required for personalization).
    This is a recommendation stream — each call returns a fresh batch, not a fixed page.
    fresh_type: 3 = normal refresh, 4 = fewer duplicates
    """
    params: Dict[str, Any] = {
        "ps": page_size,
        "fresh_type": fresh_type,
        "feed_version": "V8",
    }
    data = wbi_get(client, _FEED_URL, params)
    items = data.get("item", [])
    # Filter out placeholder entries (ads/promotions with empty bvid)
    items = [v for v in items if v.get("bvid")]
    return {
        "items": items,
    }
