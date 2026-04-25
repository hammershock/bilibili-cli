"""CLI entry point — all bilicli commands."""

import sys
from typing import Optional

import click
import httpx

from bilicli.client import get_client, BiliError
from bilicli.utils import (
    print_json, print_video_list, print_table, fmt_num, fmt_dur, truncate
)


def _err(msg: str) -> None:
    click.echo(f"Error: {msg}", err=True)
    sys.exit(1)


def _footer(items: list, start: int, total: int, hint: str) -> None:
    """Print pagination footer, or 'No results.' if empty."""
    if not items:
        click.echo("No results.")
        return
    click.echo(f"\n[{start + 1}-{start + len(items)} of {total}] {hint}")


CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}

POSITIVE_INT = click.IntRange(min=0)
POSITIVE_INT_NONZERO = click.IntRange(min=1)


class BiliGroup(click.Group):
    def invoke(self, ctx):
        try:
            return super().invoke(ctx)
        except httpx.TransportError as e:
            _err(f"Network error: {e}")
        except httpx.HTTPStatusError as e:
            _err(f"HTTP {e.response.status_code}: {e.request.url}")


@click.group(cls=BiliGroup, context_settings=CONTEXT_SETTINGS)
@click.version_option(package_name="bilicli")
def main():
    """bilicli — read-only Bilibili CLI tool."""


# ─── Auth ──────────────────────────────────────────────────────────────────

@main.command()
def login():
    """Login via QR code (scan with Bilibili app)."""
    from bilicli.auth import login as do_login
    client = get_client()
    if client.is_logged_in():
        click.echo("Already logged in. Use `bilicli logout` first to switch accounts.")
        return
    success = do_login(client)
    if not success:
        sys.exit(1)


@main.command()
def logout():
    """Clear saved credentials."""
    get_client().clear_cookies()
    click.echo("Logged out.")


@main.command()
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def whoami(as_json: bool):
    """Show current logged-in user."""
    from bilicli.auth import whoami as do_whoami
    client = get_client()
    if not client.is_logged_in():
        _err("Not logged in. Run `bilicli login` first.")
    info = do_whoami(client)
    if not info:
        _err("Failed to fetch user info.")
    if as_json:
        print_json(info)
    else:
        click.echo(f"UID   : {info['uid']}")
        click.echo(f"Name  : {info['name']}")
        click.echo(f"Level : {info['level']}")
        click.echo(f"VIP   : {'Yes' if info['vip'] else 'No'}")


# ─── Feed ──────────────────────────────────────────────────────────────────

@main.command()
@click.option("-n", "--limit", default=10, show_default=True, type=POSITIVE_INT_NONZERO, help="Number of recommendations")
@click.option("--detail", is_flag=True, help="Show author, views, duration")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def feed(limit: int, detail: bool, as_json: bool):
    """Show recommended video feed (each run returns fresh recommendations)."""
    from bilicli.api.feed import get_feed
    client = get_client()
    try:
        data = get_feed(client, page_size=limit)
    except BiliError as e:
        _err(str(e))
    items = data.get("items") or []
    if as_json:
        print_json(items)
        return
    if not items:
        click.echo("No recommendations returned.")
        return
    for v in items:
        bvid = v.get("bvid", "-")
        dur = fmt_dur(v.get("duration"))
        title = truncate(v.get("title", "-"), 50)
        click.echo(f"  {bvid}  {dur:>8s}  {title}")
        if detail:
            author = (v.get("owner") or {}).get("name", "-")
            play = fmt_num((v.get("stat") or {}).get("view"))
            click.echo(f"    by {author}  views={play}")
    click.echo(f"\n[{len(items)} items] each run returns fresh recommendations, use -n to adjust count")


# ─── Search ────────────────────────────────────────────────────────────────

@main.command()
@click.argument("keyword")
@click.option("-n", "--limit", default=10, show_default=True, type=POSITIVE_INT_NONZERO, help="Max results to show")
@click.option("--offset", default=0, show_default=True, type=POSITIVE_INT, help="Skip first N results")
@click.option("--all", "show_all", is_flag=True, help="Return all results")
@click.option("--detail", is_flag=True, help="Show author, views, duration")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def search(keyword: str, limit: int, offset: int, show_all: bool, detail: bool, as_json: bool):
    """Search videos by keyword."""
    from bilicli.api.search import search_videos
    client = get_client()
    page_size = 20
    all_results = []
    page = 1
    target = None if show_all else offset + limit
    total_results = 0
    try:
        while True:
            data = search_videos(client, keyword, page=page, page_size=page_size)
            batch = data.get("result", [])
            total_results = data.get("numResults", 0)
            if not batch:
                break
            all_results.extend(batch)
            if target and len(all_results) >= target:
                break
            if len(all_results) >= total_results:
                break
            page += 1
    except BiliError as e:
        _err(str(e))
    if show_all:
        items = all_results
        start = 0
    else:
        items = all_results[offset:offset + limit]
        start = offset
    if as_json:
        print_json(items)
        return
    for v in items:
        bvid = v.get("bvid", "-")
        dur = fmt_dur(v.get("duration"))
        title = v.get("title", "-")
        click.echo(f"  {bvid}  {dur:>8s}  {truncate(title, 50)}")
        if detail:
            import time as _time
            author = v.get("author", "-")
            play = fmt_num(v.get("play"))
            pubdate = v.get("pubdate", 0)
            ts = _time.strftime("%Y-%m-%d", _time.localtime(pubdate)) if pubdate else "-"
            click.echo(f"    by {author}  views={play}  date={ts}")
    _footer(items, start, total_results, "use --offset/-n to paginate, --detail to expand")


@main.command("search-user")
@click.argument("keyword")
@click.option("-n", "--limit", default=10, show_default=True, type=POSITIVE_INT_NONZERO, help="Max results to show")
@click.option("--offset", default=0, show_default=True, type=POSITIVE_INT, help="Skip first N results")
@click.option("--all", "show_all", is_flag=True, help="Show all results")
@click.option("--detail", is_flag=True, help="Show fans, videos, signature")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def search_user(keyword: str, limit: int, offset: int, show_all: bool, detail: bool, as_json: bool):
    """Search UP主 (users) by keyword."""
    from bilicli.api.search import search_users
    client = get_client()
    page_size = 20
    all_results = []
    page = 1
    target = None if show_all else offset + limit
    total_results = 0
    try:
        while True:
            data = search_users(client, keyword, page=page, page_size=page_size)
            batch = data.get("result", [])
            total_results = data.get("numResults", 0)
            if not batch:
                break
            all_results.extend(batch)
            if target and len(all_results) >= target:
                break
            if len(all_results) >= total_results:
                break
            page += 1
    except BiliError as e:
        _err(str(e))
    if show_all:
        items = all_results
        start = 0
    else:
        items = all_results[offset:offset + limit]
        start = offset
    if as_json:
        print_json(items)
        return
    for u in items:
        mid = u.get("mid", "-")
        uname = truncate(u.get("uname", "-"), 20)
        click.echo(f"  {mid}  {uname}")
        if detail:
            fans = fmt_num(u.get("fans", 0))
            videos = fmt_num(u.get("videos", 0))
            sign = truncate(u.get("usign", "-"), 40)
            click.echo(f"    fans={fans}  videos={videos}  {sign}")
    _footer(items, start, total_results, "use --offset/-n to paginate, --detail to expand")


# ─── User ──────────────────────────────────────────────────────────────────

@main.command()
@click.argument("mid", type=int)
@click.option("-w", "--width", default=80, show_default=True, help="Max chars for bio (0=full)")
@click.option("--json", "as_json", is_flag=True)
def user(mid: int, width: int, as_json: bool):
    """Show UP主 profile by UID."""
    from bilicli.api.user import get_user_info
    client = get_client()
    try:
        info = get_user_info(client, mid)
    except BiliError as e:
        _err(str(e))
    if as_json:
        print_json(info)
        return
    if not info:
        _err("No user info returned.")
    click.echo(f"UID     : {info.get('mid', '-')}")
    click.echo(f"Name    : {info.get('name', '-')}")
    click.echo(f"Level   : {info.get('level', '-')}")
    click.echo(f"Fans    : {fmt_num(info.get('fans'))}")
    click.echo(f"VIP     : {'Yes' if info.get('vip') else 'No'}")
    if info.get("official"):
        click.echo(f"Official: {info['official']}")
    bio = info.get("sign", "")
    click.echo(f"Bio     : {bio if width <= 0 else truncate(bio, width)}")


@main.command("user-videos")
@click.argument("mid", type=int)
@click.option("-n", "--limit", default=10, show_default=True, type=POSITIVE_INT_NONZERO, help="Max videos to show")
@click.option("--offset", default=0, show_default=True, type=POSITIVE_INT, help="Skip first N videos")
@click.option("--all", "show_all", is_flag=True, help="Show all videos")
@click.option("--order", default="pubdate", show_default=True,
              type=click.Choice(["pubdate", "click", "scores"]))
@click.option("--detail", is_flag=True, help="Show views, duration, date")
@click.option("--json", "as_json", is_flag=True)
def user_videos(mid: int, limit: int, offset: int, show_all: bool, order: str, detail: bool, as_json: bool):
    """List an UP主's uploaded videos."""
    from bilicli.api.user import get_user_videos
    import time as _time
    client = get_client()
    page_size = 30
    all_videos = []
    page = 1
    target = None if show_all else offset + limit
    total_count = 0
    try:
        while True:
            data = get_user_videos(client, mid, page=page, page_size=page_size, order=order)
            batch = data.get("videos") or []
            total_count = data.get("count", 0)
            if not batch:
                break
            all_videos.extend(batch)
            if target and len(all_videos) >= target:
                break
            if len(all_videos) >= total_count:
                break
            page += 1
    except BiliError as e:
        _err(str(e))
    if show_all:
        items = all_videos
        start = 0
    else:
        items = all_videos[offset:offset + limit]
        start = offset
    if as_json:
        print_json(items)
        return
    for v in items:
        bvid = v.get("bvid", "-")
        dur = fmt_dur(v.get("length") or v.get("duration"))
        title = truncate(v.get("title", "-"), 50)
        click.echo(f"  {bvid}  {dur:>8s}  {title}")
        if detail:
            play = fmt_num(v.get("play"))
            created = v.get("created", 0)
            ts = _time.strftime("%Y-%m-%d", _time.localtime(created)) if created else "-"
            click.echo(f"    views={play}  date={ts}")
    _footer(items, start, total_count, f"order={order}, use --offset/-n to paginate, --order to sort, --detail to expand")


# ─── Video ─────────────────────────────────────────────────────────────────

@main.command()
@click.argument("bvid")
@click.option("-w", "--width", default=120, show_default=True, help="Max chars for desc (0=full)")
@click.option("--json", "as_json", is_flag=True)
def video(bvid: str, width: int, as_json: bool):
    """Show detailed video info."""
    from bilicli.api.video import get_video_info
    client = get_client()
    try:
        info = get_video_info(client, bvid)
    except BiliError as e:
        _err(str(e))
    if as_json:
        print_json(info)
        return
    stat = info.get("stat") or {}
    pages = info.get("pages") or []
    click.echo(f"BVID    : {info.get('bvid')}")
    click.echo(f"Title   : {info.get('title')}")
    click.echo(f"Author  : {(info.get('owner') or {}).get('name')}")
    click.echo(f"Duration: {fmt_dur(info.get('duration'))}")
    if len(pages) > 1:
        click.echo(f"Pages   : {len(pages)}")
    click.echo(f"Views   : {fmt_num(stat.get('view'))}")
    click.echo(f"Likes   : {fmt_num(stat.get('like'))}")
    click.echo(f"Coins   : {fmt_num(stat.get('coin'))}")
    click.echo(f"Favs    : {fmt_num(stat.get('favorite'))}")
    click.echo(f"Danmaku : {fmt_num(stat.get('danmaku'))}")
    click.echo(f"Replies : {fmt_num(stat.get('reply'))}")
    desc = info.get("desc", "")
    click.echo(f"Desc    : {desc if width <= 0 else truncate(desc, width)}")
    if len(pages) > 1:
        click.echo(f"\nMulti-part video: use `bilicli pages {bvid}` to list parts")


@main.command()
@click.argument("bvid")
@click.option("--json", "as_json", is_flag=True)
def pages(bvid: str, as_json: bool):
    """List video parts (分P) for a multi-part video."""
    from bilicli.api.video import get_video_pages
    client = get_client()
    try:
        parts = get_video_pages(client, bvid)
    except BiliError as e:
        _err(str(e))
    if as_json:
        print_json(parts)
        return
    if not parts:
        click.echo("No pages found.")
        return
    for p in parts:
        dur = fmt_dur(p.get("duration", 0))
        click.echo(f"  P{p['page']}  cid={p['cid']}  {dur}  {p.get('part', '')}")
    click.echo(f"\n[{len(parts)} parts] use --page N with download/download-audio/subtitle/danmaku")


@main.command()
@click.argument("bvid")
@click.option("--page", "page_num", type=int, default=None, help="Part number (1-indexed, for multi-part videos)")
@click.option("--cid", type=int, default=None, help="Content ID (advanced, overrides --page)")
@click.option("--lang", default=None, help="Language code (e.g. ai-zh, en). Default: zh* or first available")
@click.option("-n", "--limit", default=20, show_default=True, type=POSITIVE_INT_NONZERO, help="Max lines to show")
@click.option("--offset", default=0, show_default=True, type=POSITIVE_INT, help="Skip first N lines")
@click.option("--all", "show_all", is_flag=True, help="Show all lines")
@click.option("--json", "as_json", is_flag=True)
def subtitle(bvid: str, page_num: Optional[int], cid: Optional[int], lang: Optional[str],
             limit: int, offset: int, show_all: bool, as_json: bool):
    """Show subtitle content for a video."""
    from bilicli.api.video import list_subtitles, get_subtitle_content, resolve_cid
    client = get_client()
    try:
        resolved_cid = resolve_cid(client, bvid, page=page_num, cid=cid)
        tracks = list_subtitles(client, bvid, cid=resolved_cid)
    except BiliError as e:
        _err(str(e))
    except ValueError as e:
        _err(str(e))
    if not tracks:
        click.echo("No subtitles available for this video. Use `bilicli subtitle-langs <bvid>` to verify.")
        return
    track = None
    if lang:
        track = next((t for t in tracks if t["lan"] == lang), None)
        if not track:
            avail = ", ".join(f"{t['lan']}({t['lan_doc']})" for t in tracks)
            _err(f"Language '{lang}' not found. Available: {avail}")
    else:
        track = next((t for t in tracks if t["lan"].startswith("zh") or t["lan"].startswith("ai-zh")), None)
        if not track:
            track = tracks[0]
    body = get_subtitle_content(client, track["url"])
    total = len(body)
    if total == 0:
        click.echo(f"[{track['lan']}] {track['lan_doc']}: empty subtitle track.")
        return
    if show_all:
        items = body
        start = 0
    else:
        items = body[offset:offset + limit]
        start = offset
    if as_json:
        print_json({"lan": track["lan"], "lan_doc": track["lan_doc"], "body": items})
        return
    click.echo(f"[{track['lan']}] {track['lan_doc']}")
    for item in items:
        ts = fmt_dur(int(item.get("from", 0)))
        click.echo(f"  {ts}  {item.get('content', '')}")
    _footer(items, start, total, "use --lang to switch, --offset/-n to paginate, `bilicli subtitle-langs <bvid>` to list")


@main.command("subtitle-langs")
@click.argument("bvid")
@click.option("--page", "page_num", type=int, default=None, help="Part number (1-indexed)")
@click.option("--cid", type=int, default=None)
@click.option("--json", "as_json", is_flag=True)
def subtitle_langs(bvid: str, page_num: Optional[int], cid: Optional[int], as_json: bool):
    """List available subtitle languages for a video."""
    from bilicli.api.video import list_subtitles, resolve_cid
    client = get_client()
    try:
        resolved_cid = resolve_cid(client, bvid, page=page_num, cid=cid)
        tracks = list_subtitles(client, bvid, cid=resolved_cid)
    except BiliError as e:
        _err(str(e))
    except ValueError as e:
        _err(str(e))
    if as_json:
        print_json(tracks)
        return
    if not tracks:
        click.echo("No subtitles available for this video.")
        return
    for t in tracks:
        click.echo(f"  {t['lan']:10s} {t['lan_doc']}")


@main.command()
@click.argument("bvid")
@click.option("--page", "page_num", type=int, default=None, help="Part number (1-indexed)")
@click.option("--cid", type=int, default=None)
@click.option("--json", "as_json", is_flag=True)
@click.option("-n", "--limit", default=10, show_default=True, type=POSITIVE_INT_NONZERO, help="Max danmaku to show")
@click.option("--offset", default=0, show_default=True, type=POSITIVE_INT, help="Skip first N danmaku")
@click.option("--all", "show_all", is_flag=True, help="Show all danmaku")
def danmaku(bvid: str, page_num: Optional[int], cid: Optional[int], as_json: bool,
            limit: int, offset: int, show_all: bool):
    """Fetch danmaku (bullet comments) for a video."""
    from bilicli.api.video import get_video_info, get_danmaku
    client = get_client()
    try:
        info = get_video_info(client, bvid)
        if cid is not None:
            resolved_cid = cid
        elif page_num is not None:
            pages = info.get("pages", [])
            if page_num < 1 or page_num > len(pages):
                raise ValueError(f"Page {page_num} out of range (1-{len(pages)})")
            resolved_cid = pages[page_num - 1]["cid"]
        else:
            resolved_cid = info["cid"]
        all_items = get_danmaku(client, bvid, cid=resolved_cid)
    except (BiliError, ValueError) as e:
        _err(str(e))
    all_items = sorted(all_items, key=lambda x: x["time"])
    total = len(all_items)
    # Use part duration if targeting a specific page
    duration = info.get("duration", 0)
    pages_list = info.get("pages", [])
    page_match = next((p for p in pages_list if p["cid"] == resolved_cid), None)
    if page_match:
        duration = page_match.get("duration", duration)

    if show_all:
        items = all_items
        start = 0
    else:
        items = all_items[offset:offset + limit]
        start = offset

    if as_json:
        print_json(items)
        return
    for d in items:
        click.echo(f"  {fmt_dur(int(d['time']))}  {d['content']}")
    _footer(items, start, total, f"duration={fmt_dur(duration)}, use --offset/-n to paginate")


def _format_comment_pictures(content: dict) -> list:
    """Extract picture URLs from comment content."""
    pics = content.get("pictures")
    if not pics:
        return []
    urls = []
    for p in pics:
        src = p.get("img_src", "")
        if src.startswith("//"):
            src = "https:" + src
        elif src.startswith("http://"):
            src = "https" + src[4:]
        if src:
            urls.append(src)
    return urls


@main.command()
@click.argument("bvid")
@click.option("-n", "--limit", default=10, show_default=True, type=POSITIVE_INT_NONZERO, help="Max comments to show")
@click.option("--offset", default=0, show_default=True, type=POSITIVE_INT, help="Skip first N comments")
@click.option("--all", "show_all", is_flag=True, help="Show all comments")
@click.option("--sort", default="hot", type=click.Choice(["hot", "time"]))
@click.option("--detail", is_flag=True, help="Show author, likes, time")
@click.option("-w", "--width", default=70, show_default=True, help="Max chars per comment (0=full)")
@click.option("--json", "as_json", is_flag=True)
def comments(bvid: str, limit: int, offset: int, show_all: bool, sort: str, detail: bool, width: int, as_json: bool):
    """List top-level comments for a video."""
    from bilicli.api.comment import get_comments
    import time as _time
    sort_code = 2 if sort == "hot" else 0
    client = get_client()
    page_size = 20
    all_replies = []
    page = 1
    total_count = 0
    target = None if show_all else offset + limit
    try:
        while True:
            data = get_comments(client, bvid, page=page, page_size=page_size, sort=sort_code)
            batch = data.get("replies") or []
            total_count = data.get("count", 0)
            if not batch:
                break
            all_replies.extend(batch)
            if target and len(all_replies) >= target:
                break
            if len(all_replies) >= total_count:
                break
            page += 1
    except BiliError as e:
        _err(str(e))
    total = len(all_replies)
    if show_all:
        items = all_replies
        start = 0
    else:
        items = all_replies[offset:offset + limit]
        start = offset
    if as_json:
        print_json(items)
        return
    for r in items:
        rpid = r.get("rpid", "-")
        content = r.get("content", {})
        msg = content.get("message", "")
        rcount = r.get("rcount", 0)
        display_msg = msg if width <= 0 else truncate(msg, width)
        line = f"  [{rpid}] {display_msg}  ({rcount} replies)"
        click.echo(line)
        pics = _format_comment_pictures(content)
        for url in pics:
            click.echo(f"    [img] {url}")
        if detail:
            uname = (r.get("member") or {}).get("uname", "-")
            likes = fmt_num(r.get("like", 0))
            ctime = r.get("ctime", 0)
            ts = _time.strftime("%Y-%m-%d %H:%M", _time.localtime(ctime)) if ctime else "-"
            click.echo(f"    by {uname}  likes={likes}  time={ts}")
    _footer(items, start, total_count, "use --offset/-n to paginate, --detail to expand, bilicli replies <bvid> <rpid> for sub-replies")


@main.command()
@click.argument("bvid")
@click.argument("rpid", type=int)
@click.option("-n", "--limit", default=10, show_default=True, type=POSITIVE_INT_NONZERO, help="Max replies to show")
@click.option("--offset", default=0, show_default=True, type=POSITIVE_INT, help="Skip first N replies")
@click.option("--all", "show_all", is_flag=True, help="Show all replies")
@click.option("-w", "--width", default=70, show_default=True, help="Max chars per reply (0=full)")
@click.option("--json", "as_json", is_flag=True)
def replies(bvid: str, rpid: int, limit: int, offset: int, show_all: bool, width: int, as_json: bool):
    """Show replies under a specific comment (by rpid)."""
    from bilicli.api.comment import get_replies
    import time as _time
    client = get_client()
    all_replies = []
    page = 1
    page_size = 20
    total_count = 0
    target = None if show_all else offset + limit
    try:
        while True:
            data = get_replies(client, bvid, rpid, page=page, page_size=page_size)
            batch = data.get("replies") or []
            total_count = data.get("count", 0)
            if not batch:
                break
            all_replies.extend(batch)
            if target and len(all_replies) >= target:
                break
            if len(all_replies) >= total_count:
                break
            page += 1
    except BiliError as e:
        _err(str(e))

    total = len(all_replies)
    if show_all:
        items = all_replies
        start = 0
    else:
        items = all_replies[offset:offset + limit]
        start = offset

    if as_json:
        print_json(items)
        return
    for r in items:
        uname = (r.get("member") or {}).get("uname", "-")
        content = r.get("content", {})
        msg = content.get("message", "")
        likes = fmt_num(r.get("like", 0))
        ctime = r.get("ctime", 0)
        ts = _time.strftime("%Y-%m-%d %H:%M", _time.localtime(ctime)) if ctime else "-"
        display_msg = msg if width <= 0 else truncate(msg, width)
        click.echo(f"  {uname} ({likes} likes, {ts}): {display_msg}")
        pics = _format_comment_pictures(content)
        for url in pics:
            click.echo(f"    [img] {url}")
    _footer(items, start, total_count, "use --offset/-n to paginate")


# ─── Download ──────────────────────────────────────────────────────────────

_QUALITY_CHOICES = {
    "360p": 16, "480p": 32, "720p": 64, "1080p": 80,
    "1080p+": 112, "4k": 120,
}


@main.command()
@click.argument("bvid")
@click.option("-q", "--quality", default="1080p", show_default=True,
              type=click.Choice(list(_QUALITY_CHOICES.keys())))
@click.option("-o", "--output", default=".", show_default=True, help="Output directory")
@click.option("--page", "page_num", type=int, default=None, help="Part number (1-indexed, for multi-part videos)")
@click.option("--cid", type=int, default=None, help="Content ID (advanced, overrides --page)")
@click.option("--quiet", is_flag=True, help="Suppress progress, only print final path (for agent use)")
def download(bvid: str, quality: str, output: str, page_num: Optional[int], cid: Optional[int], quiet: bool):
    """Download a video as MP4 (requires ffmpeg)."""
    from bilicli.download import download_video
    client = get_client()
    qn = _QUALITY_CHOICES[quality]
    try:
        download_video(client, bvid, quality=qn, output_dir=output, cid=cid, page=page_num, quiet=quiet)
    except (BiliError, RuntimeError, ValueError) as e:
        _err(str(e))


@main.command("download-audio")
@click.argument("bvid")
@click.option("-o", "--output", default=".", show_default=True, help="Output directory")
@click.option("--page", "page_num", type=int, default=None, help="Part number (1-indexed, for multi-part videos)")
@click.option("--cid", type=int, default=None, help="Content ID (advanced, overrides --page)")
@click.option("--quiet", is_flag=True, help="Suppress progress, only print final path (for agent use)")
def download_audio_cmd(bvid: str, output: str, page_num: Optional[int], cid: Optional[int], quiet: bool):
    """Download audio only as M4A (requires ffmpeg). Saves bandwidth."""
    from bilicli.download import download_audio
    client = get_client()
    try:
        download_audio(client, bvid, output_dir=output, cid=cid, page=page_num, quiet=quiet)
    except (BiliError, RuntimeError, ValueError) as e:
        _err(str(e))


@main.command("download-cover")
@click.argument("bvid")
@click.option("-o", "--output", default=".", show_default=True, help="Output directory")
@click.option("--quiet", is_flag=True, help="Only print final path (for agent use)")
def download_cover(bvid: str, output: str, quiet: bool):
    """Download a video's cover image."""
    from bilicli.api.video import get_video_info
    from pathlib import Path
    client = get_client()
    try:
        info = get_video_info(client, bvid)
    except BiliError as e:
        _err(str(e))
    pic_url = info.get("pic", "")
    if not pic_url:
        _err("No cover image found.")
    if pic_url.startswith("//"):
        pic_url = "https:" + pic_url
    ext = pic_url.rsplit(".", 1)[-1].split("?")[0] if "." in pic_url else "jpg"
    title = info.get("title", bvid)
    safe_title = "".join(c if c.isalnum() or c in " -_." else "_" for c in title)[:80]
    out_dir = Path(output)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{safe_title}.{ext}"
    resp = client.get_raw(pic_url)
    out_path.write_bytes(resp.content)
    click.echo(str(out_path) if quiet else f"Saved: {out_path}")


@main.command()
@click.argument("bvid")
@click.option("--page", "page_num", type=int, default=None, help="Part number (1-indexed)")
@click.option("--cid", type=int, default=None, help="Content ID (advanced, overrides --page)")
@click.option("--model", default="mlx-community/whisper-turbo", show_default=True, help="Whisper model")
@click.option("--lang", default="zh", show_default=True, help="Language code for transcription")
@click.option("-n", "--limit", default=0, type=POSITIVE_INT, help="Max segments to show (0=all)")
@click.option("--offset", default=0, type=POSITIVE_INT, help="Skip first N segments")
@click.option("--quiet", is_flag=True, help="Suppress download progress")
@click.option("--json", "as_json", is_flag=True)
def transcribe(bvid: str, page_num: Optional[int], cid: Optional[int], model: str,
               lang: str, limit: int, offset: int, quiet: bool, as_json: bool):
    """Transcribe video audio using mlx-whisper (macOS Apple Silicon).

    Downloads audio, then runs local speech-to-text. Requires: pip install mlx-whisper
    """
    from bilicli.download import download_audio
    from bilicli.stt import transcribe_audio
    import tempfile
    client = get_client()

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            if not quiet:
                click.echo("Downloading audio...")
            audio_path = download_audio(client, bvid, output_dir=tmpdir, cid=cid, page=page_num, quiet=True)

            if not quiet:
                click.echo("Transcribing with mlx-whisper...")
            segments = transcribe_audio(str(audio_path), model=model, language=lang)
    except (BiliError, RuntimeError, ValueError) as e:
        _err(str(e))

    total = len(segments)
    if limit > 0:
        items = segments[offset:offset + limit]
    else:
        items = segments[offset:] if offset else segments
    start = offset

    if as_json:
        print_json(items)
        return
    if not items:
        click.echo("No speech segments found.")
        return
    for seg in items:
        ts = fmt_dur(int(seg["start"]))
        click.echo(f"  {ts}  {seg['text']}")
    if limit > 0:
        _footer(items, start, total, "use --offset/-n to paginate")
    else:
        click.echo(f"\n[{len(items)} segments]")
