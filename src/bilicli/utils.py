"""Formatting helpers for terminal output."""

import json
from typing import Any, Dict, List, Optional


def fmt_num(n: Optional[int]) -> str:
    """Format large numbers: 12345 → '1.2万', 123456789 → '1.2亿'."""
    if n is None:
        return "-"
    n = int(n)
    if n >= 100_000_000:
        return f"{n / 100_000_000:.1f}亿"
    if n >= 10_000:
        return f"{n / 10_000:.1f}万"
    return str(n)


def fmt_dur(seconds) -> str:
    """Format duration to mm:ss or hh:mm:ss. Accepts seconds (int) or 'mm:ss' string."""
    if seconds is None:
        return "-"
    if isinstance(seconds, str):
        # Already formatted like "12:19" or "1:02:30"
        if ":" in seconds:
            return seconds
        try:
            seconds = int(seconds)
        except ValueError:
            return seconds
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def print_table(rows: List[List[str]], headers: List[str]) -> None:
    """Print a simple aligned text table."""
    all_rows = [headers] + rows
    widths = [max(len(str(r[i])) for r in all_rows) for i in range(len(headers))]
    sep = "  "
    header_line = sep.join(str(h).ljust(widths[i]) for i, h in enumerate(headers))
    print(header_line)
    print("-" * len(header_line))
    for row in rows:
        print(sep.join(str(v).ljust(widths[i]) for i, v in enumerate(row)))


def print_json(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def truncate(s: str, max_len: int = 40) -> str:
    if len(s) <= max_len:
        return s
    return s[: max_len - 1] + "…"


def video_rows(videos: List[Dict]) -> List[List[str]]:
    """Convert a list of video dicts to table rows."""
    rows = []
    for v in videos:
        bvid = v.get("bvid") or v.get("bv_id") or "-"
        title = truncate(v.get("title", "-"), 45)
        author = v.get("author") or v.get("owner", {}).get("name", "-")
        play = fmt_num(v.get("play") or v.get("stat", {}).get("view"))
        dur = fmt_dur(v.get("duration") or v.get("length"))
        rows.append([bvid, title, author, play, dur])
    return rows


VIDEO_HEADERS = ["BVID", "Title", "Author", "Views", "Duration"]


def print_video_list(videos: List[Dict], as_json: bool = False) -> None:
    if as_json:
        print_json(videos)
        return
    if not videos:
        print("No results.")
        return
    print_table(video_rows(videos), VIDEO_HEADERS)
