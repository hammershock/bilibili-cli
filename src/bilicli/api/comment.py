"""Video comments and replies."""

from typing import Any, Dict

from bilicli.client import BiliClient

_REPLY_URL = "https://api.bilibili.com/x/v2/reply"
_REPLY_DETAIL_URL = "https://api.bilibili.com/x/v2/reply/reply"


def _get_aid(client: BiliClient, bvid: str) -> int:
    from bilicli.api.video import get_video_info
    info = get_video_info(client, bvid)
    return info["aid"]


def get_comments(
    client: BiliClient,
    bvid: str,
    page: int = 1,
    page_size: int = 20,
    sort: int = 2,  # 0=time, 2=hot
) -> Dict[str, Any]:
    """
    Get top-level comments for a video.
    sort: 0 = by time, 2 = by hot/likes
    """
    aid = _get_aid(client, bvid)
    params: Dict[str, Any] = {
        "oid": aid,
        "type": 1,
        "pn": page,
        "ps": page_size,
        "sort": sort,
    }
    data = client.get(_REPLY_URL, params=params)
    page_info = data.get("page", {})
    replies = data.get("replies", []) or []
    return {
        "count": page_info.get("count", 0),
        "page": page,
        "page_size": page_size,
        "replies": replies,
    }


def get_replies(
    client: BiliClient,
    bvid: str,
    rpid: int,
    page: int = 1,
    page_size: int = 20,
) -> Dict[str, Any]:
    """Get replies (sub-comments) under a specific comment."""
    aid = _get_aid(client, bvid)
    params: Dict[str, Any] = {
        "oid": aid,
        "type": 1,
        "root": rpid,
        "pn": page,
        "ps": page_size,
    }
    data = client.get(_REPLY_DETAIL_URL, params=params)
    page_info = data.get("page", {})
    root = data.get("root", {})
    replies = data.get("replies", []) or []
    return {
        "count": page_info.get("count", 0),
        "page": page,
        "page_size": page_size,
        "root": root,
        "replies": replies,
    }
