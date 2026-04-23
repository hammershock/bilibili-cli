"""Video and user search (WBI signed)."""

import re
from typing import Any, Dict, List

from bilicli.client import BiliClient
from bilicli.wbi import wbi_get

_EM_RE = re.compile(r"<em class=\"keyword\">|</em>")

_SEARCH_TYPE = "https://api.bilibili.com/x/web-interface/wbi/search/type"


def search_videos(
    client: BiliClient,
    keyword: str,
    page: int = 1,
    page_size: int = 20,
) -> Dict[str, Any]:
    """
    Search videos by keyword.
    Returns dict with keys: numResults, numPages, result (list of video dicts).
    """
    params = {
        "search_type": "video",
        "keyword": keyword,
        "pn": page,
        "ps": page_size,
    }
    data = wbi_get(client, _SEARCH_TYPE, params)
    results = data.get("result", [])
    # Strip HTML highlight tags from titles
    for v in results:
        if "title" in v and isinstance(v["title"], str):
            v["title"] = _EM_RE.sub("", v["title"])
    return {
        "numResults": data.get("numResults", 0),
        "numPages": data.get("numPages", 0),
        "page": page,
        "result": results,
    }


def search_users(
    client: BiliClient,
    keyword: str,
    page: int = 1,
    page_size: int = 20,
) -> Dict[str, Any]:
    """
    Search UP主 (users) by keyword.
    Returns dict with keys: numResults, numPages, result (list of user dicts).
    """
    params = {
        "search_type": "bili_user",
        "keyword": keyword,
        "pn": page,
        "ps": page_size,
    }
    data = wbi_get(client, _SEARCH_TYPE, params)
    return {
        "numResults": data.get("numResults", 0),
        "numPages": data.get("numPages", 0),
        "page": page,
        "result": data.get("result", []),
    }
