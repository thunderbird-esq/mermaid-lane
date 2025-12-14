"""
Secure streaming API endpoints.
All streams are proxied to hide original URLs.
"""
from fastapi import APIRouter, Request, Query, HTTPException
from pathlib import Path
from typing import Optional

from app.services.stream_proxy import get_proxy_service
from app.services.cache import get_cache
from app.services.m3u_parser import import_m3u_directory
from app.services.transcoder import get_transcoder_service

import logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/streams", tags=["streams"])


@router.get("/{stream_id}/play.m3u8")
async def get_stream_manifest(stream_id: str, request: Request):
    """
    Get proxied HLS manifest for a stream.
    If stream is not HLS (e.g. DASH), transparently transcode it.
    """
    proxy = get_proxy_service()
    transcoder = get_transcoder_service()
    stream = await proxy.get_stream_info(stream_id)
    
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")

    # Check content type if not known (simple check, improvement from earlier)
    # We can rely on extension or probe headers. 
    # Logic: Try proxy first if it looks like HLS. If failing or DASH, use transcoder.
    # Given the previous logic was robust-ish but failed on DASH, let's explicit check.
    
    is_hls = True
    url_lower = stream["url"].lower()
    if "youtube.com" in url_lower or "youtu.be" in url_lower:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(stream["url"])

    if ".mpd" in url_lower or ".mp4" in url_lower:
        is_hls = False
    
    if is_hls:
        # Build base URL for rewriting segment URLs
        base_url = str(request.base_url).rstrip('/')
        return await proxy.proxy_manifest(stream_id, base_url)

    # Transcode path
    logger.info(f"Using transcoder for {stream_id}")
    started = await transcoder.start_transcode(stream_id, stream["url"])
    if not started:
        raise HTTPException(status_code=500, detail="Failed to start transcoder")
    
    # Wait for playlist
    import asyncio
    for _ in range(20): # Wait up to 10s (20 * 0.5)
        if await transcoder.is_ready(stream_id):
            break
        await asyncio.sleep(0.5)
    
    path = await transcoder.get_manifest_path(stream_id)
    if not path or not path.exists():
        raise HTTPException(status_code=503, detail="Stream failed to initialize (transcode timeout)")

    # Read and rewrite local manifest to point to local segment route
    content = path.read_text()
    # Rewrite: segment_000.ts -> local/segment_000.ts
    # This assumes ffmpeg output naming convention
    content = content.replace("segment_", f"local/segment_")
    
    from fastapi.responses import Response
    return Response(
        content=content,
        media_type="application/vnd.apple.mpegurl",
        headers={
            "Access-Control-Allow-Origin": "*",
            "Cache-Control": "no-cache"
        }
    )


@router.get("/{stream_id}/local/{filename}")
async def get_local_segment(stream_id: str, filename: str):
    """Serve locally transcoded segments."""
    from fastapi.responses import FileResponse
    transcoder = get_transcoder_service()
    
    # Verify file is valid for this stream
    path = transcoder.TRANSCODE_DIR / stream_id / filename
    
    # Security check: ensure path is within stream dir
    if not path.resolve().is_relative_to(transcoder.TRANSCODE_DIR / stream_id):
        raise HTTPException(status_code=403, detail="Access denied")
        
    if not path.exists():
        raise HTTPException(status_code=404, detail="Segment not found")
        
    media_type = "video/mp2t" if filename.endswith(".ts") else "application/octet-stream"
    return FileResponse(
        path,
        media_type=media_type,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Cache-Control": "no-cache"
        }
    )


@router.get("/{stream_id}/segment/{encoded_url:path}")
async def get_stream_segment(stream_id: str, encoded_url: str, request: Request):
    """
    Proxy an HLS segment or nested playlist.
    The encoded_url is a base64-encoded original segment URL.
    """
    proxy = get_proxy_service()
    base_url = str(request.base_url).rstrip('/')
    return await proxy.proxy_segment(stream_id, encoded_url, base_url)


@router.get("/{stream_id}/status")
async def get_stream_status(stream_id: str):
    """
    Check if a stream is accessible.
    """
    proxy = get_proxy_service()
    return await proxy.check_stream_health(stream_id)


@router.get("/stats")
async def get_stream_stats():
    """
    Get stream statistics.
    """
    cache = await get_cache()
    return await cache.get_stream_stats()


@router.get("/health-updates")
async def get_health_updates(since: int = 60):
    """
    Get recently updated stream health statuses.
    Used for real-time UI updates via polling.
    
    Args:
        since: Seconds to look back (default 60)
    """
    cache = await get_cache()
    updates = await cache.get_recent_health_updates(since_seconds=since)
    return {
        "updates": updates,
        "count": len(updates),
        "since_seconds": since
    }


@router.get("/health-stats")
async def get_health_stats():
    """
    Get overall stream health statistics.
    """
    cache = await get_cache()
    stats = await cache.get_health_stats()
    
    total = sum(stats.values())
    return {
        "stats": stats,
        "total": total,
        "percentages": {k: round(v / total * 100, 1) if total else 0 for k, v in stats.items()}
    }


@router.get("/health-worker")
async def get_health_worker_status():
    """
    Get background health worker status.
    """
    from app.services.health_worker import get_health_worker
    worker = get_health_worker()
    return worker.get_stats()


@router.post("/import/m3u")
async def import_m3u_streams(
    countries: Optional[str] = Query(None, description="Comma-separated country codes (e.g., 'us,uk,ca')")
):
    """
    Import streams from local M3U files.
    Files are located in iptv/streams/ directory.
    """
    # Path to iptv streams directory (relative to project root)
    streams_dir = Path(__file__).parent.parent.parent.parent.parent / "iptv" / "streams"
    
    if not streams_dir.exists():
        raise HTTPException(status_code=404, detail=f"Streams directory not found: {streams_dir}")
    
    # Parse country codes
    country_list = None
    if countries:
        country_list = [c.strip().lower() for c in countries.split(',') if c.strip()]
    
    cache = await get_cache()
    
    try:
        stats = await import_m3u_directory(cache, streams_dir, country_list)
        return {
            "success": True,
            "message": f"Imported {stats['total_streams']} streams from {stats['files_processed']} files",
            **stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")

