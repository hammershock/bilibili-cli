"""User info and video list."""

from typing import Any, Dict

from bilicli.client import BiliClient
from bilicli.wbi import wbi_get

_CARD = "https://api.bilibili.com/x/web-interface/card"
_SPACE_VIDEOS = "https://api.bilibili.com/x/space/wbi/arc/search"
_SPACE_INFO = "https://api.bilibili.com/x/space/wbi/acc/info"


def get_user_info(client: BiliClient, mid: int) -> Dict[str, Any]:
    """Get UP主 profile card by UID."""
    data = client.get(_CARD, params={"mid": mid, "photo": "true"})
    card = data.get("card", {})
    stat = data.get("follower", 0)
    return {
        "mid": card.get("mid"),
        "name": card.get("name"),
        "sign": card.get("sign"),
        "sex": card.get("sex"),
        "level": card.get("level_info", {}).get("current_level"),
        "fans": stat,
        "following": card.get("attention", 0),
        "official": card.get("official_verify", {}).get("desc", ""),
        "vip": card.get("vip", {}).get("status", 0) == 1,
        "face": card.get("face"),
    }


def get_user_videos(
    client: BiliClient,
    mid: int,
    page: int = 1,
    page_size: int = 30,
    keyword: str = "",
    order: str = "pubdate",  # pubdate | click | scores
) -> Dict[str, Any]:
    """
    Get UP主's uploaded videos (paginated, WBI signed).
    order: pubdate (newest), click (most viewed), scores (most commented)
    """
    params: Dict[str, Any] = {
        "mid": mid,
        "pn": page,
        "ps": page_size,
        "order": order,
    }
    if keyword:
        params["keyword"] = keyword

    data = wbi_get(client, _SPACE_VIDEOS, params)
    vlist = data.get("list", {}).get("vlist", [])
    page_info = data.get("page", {})
    return {
        "count": page_info.get("count", 0),
        "page": page,
        "page_size": page_size,
        "videos": vlist,
    }
