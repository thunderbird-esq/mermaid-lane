"""
Secure streaming API endpoints.
All streams are proxied to hide original URLs.
"""
from fastapi import APIRouter, Request, Query, HTTPException
from pathlib import Path
from typing import Optional, List

from app.services.stream_proxy import get_proxy_service
from app.services.cache import get_cache
from app.services.m3u_parser import import_m3u_directory

router = APIRouter(prefix="/api/streams", tags=["streams"])


@router.get("/{stream_id}/play.m3u8")
async def get_stream_manifest(stream_id: str, request: Request):
    """
    Get proxied HLS manifest for a stream.
    All segment URLs in the manifest are rewritten to proxy through our API.
    """
    proxy = get_proxy_service()
    
    # Build our base URL for rewriting segment URLs
    base_url = str(request.base_url).rstrip('/')
    
    return await proxy.proxy_manifest(stream_id, base_url)


@router.get("/{stream_id}/segment/{encoded_url:path}")
async def get_stream_segment(stream_id: str, encoded_url: str):
    """
    Proxy an HLS segment.
    The encoded_url is a base64-encoded original segment URL.
    """
    proxy = get_proxy_service()
    return await proxy.proxy_segment(stream_id, encoded_url)


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

