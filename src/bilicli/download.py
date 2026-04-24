"""DASH video/audio download with ffmpeg merge."""

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

from bilicli.client import BiliClient, BASE_HEADERS
from bilicli.api.video import get_video_info, resolve_cid

_PLAYURL = "https://api.bilibili.com/x/player/playurl"

# fnval: DASH=16, HDR=64, 4K=128, DOLBY=256, DOLBY_AUDIO=512, AV1=1024
_FNVAL_DASH = 16 | 64 | 128 | 256 | 512 | 1024


def get_playurl(
    client: BiliClient,
    bvid: str,
    cid: Optional[int] = None,
    quality: int = 80,  # 80=1080p
) -> Dict[str, Any]:
    """Fetch DASH playurl data."""
    if cid is None:
        cid = resolve_cid(client, bvid)

    params = {
        "bvid": bvid,
        "cid": cid,
        "qn": quality,
        "fnval": _FNVAL_DASH,
        "fnver": 0,
        "fourk": 1,
    }
    return client.get(_PLAYURL, params=params)


def _best_stream(streams: list, preferred_quality: int) -> Optional[Dict]:
    """Pick the best available stream at or below preferred quality."""
    if not streams:
        return None
    streams_sorted = sorted(streams, key=lambda s: s.get("id", 0), reverse=True)
    # try to find exact or nearest below
    for s in streams_sorted:
        if s.get("id", 0) <= preferred_quality:
            return s
    return streams_sorted[-1]  # fallback: lowest


def _download_stream(client: BiliClient, url: str, dest: Path, quiet: bool = False) -> None:
    """Stream download with optional progress indicator."""
    headers = dict(BASE_HEADERS)
    headers["Referer"] = "https://www.bilibili.com/"

    with client.http.stream("GET", url, headers=headers) as resp:
        resp.raise_for_status()
        total = int(resp.headers.get("content-length", 0))
        downloaded = 0
        with open(dest, "wb") as f:
            for chunk in resp.iter_bytes(chunk_size=1024 * 256):
                f.write(chunk)
                downloaded += len(chunk)
                if not quiet and total:
                    pct = downloaded * 100 // total
                    print(f"\r  {pct:3d}%  {downloaded // 1024 // 1024}MB / {total // 1024 // 1024}MB", end="", flush=True)
    if not quiet:
        print()


def _make_safe_filename(title: str, page_info: Optional[Dict] = None) -> str:
    """Build a safe filename from title and optional page info."""
    safe = "".join(c if c.isalnum() or c in " -_." else "_" for c in title)[:80]
    if page_info and page_info.get("page", 1) > 0:
        page_num = page_info["page"]
        part_name = page_info.get("part", "")
        safe_part = "".join(c if c.isalnum() or c in " -_." else "_" for c in part_name)[:40]
        safe = f"{safe}_P{page_num}_{safe_part}" if safe_part else f"{safe}_P{page_num}"
    return safe


def download_video(
    client: BiliClient,
    bvid: str,
    quality: int = 80,
    output_dir: str = ".",
    cid: Optional[int] = None,
    page: Optional[int] = None,
    quiet: bool = False,
) -> Path:
    """
    Download a bilibili video as MP4.
    Returns the path to the output file.
    Requires ffmpeg in PATH.
    """
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg not found in PATH. Install ffmpeg to download videos.")

    info = get_video_info(client, bvid)
    title = info.get("title", bvid)
    cid = resolve_cid(client, bvid, page=page, cid=cid)

    # Get page info for filename
    page_info = None
    pages = info.get("pages", [])
    if len(pages) > 1:
        page_info = next((p for p in pages if p["cid"] == cid), None)

    if not quiet:
        part_label = f" (P{page_info['page']}: {page_info.get('part', '')})" if page_info else ""
        print(f"Fetching stream URLs for: {title}{part_label}")
    playurl_data = get_playurl(client, bvid, cid=cid, quality=quality)

    dash = playurl_data.get("dash")
    if not dash:
        raise RuntimeError("No DASH stream available for this video.")

    video_streams = dash.get("video", [])
    audio_streams = dash.get("audio", [])

    best_video = _best_stream(video_streams, quality)
    best_audio = _best_stream(audio_streams, 30280)  # 30280=320kbps

    if not best_video or not best_audio:
        raise RuntimeError("Could not find suitable video/audio streams.")

    video_url = best_video.get("base_url") or best_video.get("baseUrl")
    audio_url = best_audio.get("base_url") or best_audio.get("baseUrl")

    safe_title = _make_safe_filename(title, page_info)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{safe_title}.mp4"

    with tempfile.TemporaryDirectory() as tmpdir:
        video_tmp = Path(tmpdir) / "video.m4s"
        audio_tmp = Path(tmpdir) / "audio.m4s"

        if not quiet:
            print(f"Downloading video stream (quality={best_video.get('id')})...")
        _download_stream(client, video_url, video_tmp, quiet=quiet)

        if not quiet:
            print(f"Downloading audio stream (quality={best_audio.get('id')})...")
        _download_stream(client, audio_url, audio_tmp, quiet=quiet)

        if not quiet:
            print(f"Merging to {out_path} ...")
        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_tmp),
            "-i", str(audio_tmp),
            "-c", "copy",
            str(out_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg failed:\n{result.stderr}")

    print(out_path if quiet else f"Done: {out_path}")
    return out_path


def download_audio(
    client: BiliClient,
    bvid: str,
    output_dir: str = ".",
    cid: Optional[int] = None,
    page: Optional[int] = None,
    quiet: bool = False,
) -> Path:
    """
    Download audio-only from a bilibili video as M4A.
    Returns the path to the output file.
    Requires ffmpeg in PATH.
    """
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg not found in PATH. Install ffmpeg to download audio.")

    info = get_video_info(client, bvid)
    title = info.get("title", bvid)
    cid = resolve_cid(client, bvid, page=page, cid=cid)

    page_info = None
    pages = info.get("pages", [])
    if len(pages) > 1:
        page_info = next((p for p in pages if p["cid"] == cid), None)

    if not quiet:
        part_label = f" (P{page_info['page']}: {page_info.get('part', '')})" if page_info else ""
        print(f"Fetching audio for: {title}{part_label}")

    playurl_data = get_playurl(client, bvid, cid=cid, quality=80)

    dash = playurl_data.get("dash")
    if not dash:
        raise RuntimeError("No DASH stream available for this video.")

    audio_streams = dash.get("audio", [])
    best_audio = _best_stream(audio_streams, 30280)
    if not best_audio:
        raise RuntimeError("Could not find suitable audio stream.")

    audio_url = best_audio.get("base_url") or best_audio.get("baseUrl")

    safe_title = _make_safe_filename(title, page_info)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{safe_title}.m4a"

    with tempfile.TemporaryDirectory() as tmpdir:
        audio_tmp = Path(tmpdir) / "audio.m4s"

        if not quiet:
            print(f"Downloading audio stream (quality={best_audio.get('id')})...")
        _download_stream(client, audio_url, audio_tmp, quiet=quiet)

        if not quiet:
            print(f"Converting to {out_path} ...")
        cmd = [
            "ffmpeg", "-y",
            "-i", str(audio_tmp),
            "-c", "copy",
            str(out_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg failed:\n{result.stderr}")

    print(out_path if quiet else f"Done: {out_path}")
    return out_path
