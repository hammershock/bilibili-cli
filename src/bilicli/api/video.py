"""Video info, subtitles, danmaku."""

import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional

from bilicli.client import BiliClient

_VIEW = "https://api.bilibili.com/x/web-interface/view"
_PLAYER_V2 = "https://api.bilibili.com/x/player/wbi/v2"
_DANMAKU_XML = "https://comment.bilibili.com/{cid}.xml"
_STAT = "https://api.bilibili.com/x/web-interface/archive/stat"


def get_video_info(client: BiliClient, bvid: str) -> Dict[str, Any]:
    """Full video info by BVID."""
    return client.get(_VIEW, params={"bvid": bvid})


def get_video_stat(client: BiliClient, bvid: str) -> Dict[str, Any]:
    return client.get(_STAT, params={"bvid": bvid})


def list_subtitles(client: BiliClient, bvid: str, cid: Optional[int] = None) -> List[Dict]:
    """
    Return available subtitle tracks (without content).
    Each item: {lan, lan_doc, url}
    """
    from bilicli.wbi import fetch_wbi_keys, sign_params

    if cid is None:
        info = get_video_info(client, bvid)
        cid = info["cid"]

    img_key, sub_key = fetch_wbi_keys(client)
    params = sign_params({"bvid": bvid, "cid": cid}, img_key, sub_key)
    data = client.get(_PLAYER_V2, params=params)

    subtitle_info = data.get("subtitle", {})
    subtitles = subtitle_info.get("subtitles", [])
    result = []
    for sub in subtitles:
        url = sub.get("subtitle_url", "")
        if url.startswith("//"):
            url = "https:" + url
        result.append({
            "lan": sub.get("lan", ""),
            "lan_doc": sub.get("lan_doc", ""),
            "url": url,
        })
    return result


def get_subtitle_content(client: BiliClient, url: str) -> List[Dict]:
    """Fetch subtitle body from a subtitle URL."""
    try:
        resp = client.get_raw(url)
        data = resp.json()
        return data.get("body", [])
    except Exception:
        return []


def get_danmaku(client: BiliClient, bvid: str, cid: Optional[int] = None) -> List[Dict]:
    """
    Fetch danmaku (bullet comments) via legacy XML endpoint.
    Returns list of {time, type, size, color, content}.
    """
    if cid is None:
        info = get_video_info(client, bvid)
        cid = info["cid"]

    url = f"https://comment.bilibili.com/{cid}.xml"
    resp = client.get_raw(url)
    root = ET.fromstring(resp.content)

    items = []
    for d in root.findall("d"):
        p = d.get("p", "")
        text = d.text or ""
        parts = p.split(",")
        if len(parts) < 8:
            continue
        try:
            items.append({
                "time": float(parts[0]),
                "type": int(parts[1]),
                "size": int(parts[2]),
                "color": int(parts[3]),
                "content": text,
            })
        except (ValueError, IndexError):
            continue
    return items
