"""
Channel discovery API endpoints.
"""
from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from app.services.cache import get_cache
from app.services.data_sync import get_sync_service

router = APIRouter(prefix="/api", tags=["channels"])


@router.get("/channels")
async def list_channels(
    country: Optional[str] = Query(None, description="Filter by country code (e.g., US, UK)"),
    category: Optional[str] = Query(None, description="Filter by category (e.g., news, sports)"),
    provider: Optional[str] = Query(None, description="Filter by stream provider (e.g., pluto, roku)"),
    search: Optional[str] = Query(None, description="Search in channel names"),
    playable_only: bool = Query(True, description="Only show channels with available streams"),
    include_epg: bool = Query(False, description="Include now playing info from EPG"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(50, ge=1, le=100, description="Results per page"),
):
    """
    List channels with filtering and pagination.
    
    - **country**: ISO 3166-1 alpha-2 country code
    - **category**: Category ID from /api/categories
    - **provider**: Stream provider (pluto, roku, samsung, etc.)
    - **search**: Search term for channel name
    - **playable_only**: Only show channels with streams (default: true)
    - **include_epg**: Include "now playing" info from EPG
    """
    cache = await get_cache()
    channels, total = await cache.get_channels(
        country=country,
        category=category,
        provider=provider,
        search=search,
        playable_only=playable_only,
        page=page,
        per_page=per_page
    )
    
    # Optionally fetch "now playing" for each channel
    now_playing = {}
    if include_epg and channels:
        channel_ids = [ch['id'] for ch in channels]
        now_playing = await cache.get_now_playing_for_channels(channel_ids)
        
        # Attach to channels
        for ch in channels:
            if ch['id'] in now_playing:
                ch['now_playing'] = now_playing[ch['id']]
    
    return {
        "channels": channels,
        "total": total,
        "page": page,
        "per_page": per_page,
        "has_more": (page * per_page) < total,
        "epg_count": len(now_playing)
    }


@router.get("/channels/{channel_id}")
async def get_channel(channel_id: str):
    """
    Get channel details with available streams and logos.
    """
    cache = await get_cache()
    channel = await cache.get_channel_by_id(channel_id)
    
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    # Attach streams and logos
    streams = await cache.get_streams_for_channel(channel_id)
    logos = await cache.get_logos_for_channel(channel_id)
    
    return {
        **channel,
        "streams": streams,
        "logos": logos
    }


@router.get("/categories")
async def list_categories():
    """
    List all channel categories with counts.
    """
    cache = await get_cache()
    categories = await cache.get_categories()
    return {"categories": categories}


@router.get("/countries")
async def list_countries():
    """
    List all countries with channel counts.
    """
    cache = await get_cache()
    countries = await cache.get_countries()
    return {"countries": countries}


@router.get("/languages")
async def list_languages():
    """
    List all available languages.
    """
    sync_service = get_sync_service()
    languages = await sync_service.get_languages()
    return {"languages": languages}


@router.get("/regions")
async def list_regions():
    """
    List all geographic regions.
    """
    sync_service = get_sync_service()
    regions = await sync_service.get_regions()
    return {"regions": regions}


@router.get("/providers")
async def list_providers():
    """
    List all stream providers (e.g., pluto, roku, samsung).
    Extracted from M3U filenames.
    """
    cache = await get_cache()
    providers = await cache.get_providers()
    return {"providers": providers}


@router.post("/sync")
async def trigger_sync(x_admin_key: Optional[str] = Query(None, alias="X-Admin-Key")):
    """
    Trigger data sync from iptv-org API.
    Requires X-Admin-Key header or query parameter.
    Set IPTV_ADMIN_API_KEY environment variable to configure.
    """
    from app.config import get_settings
    settings = get_settings()
    
    if x_admin_key != settings.admin_api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing admin API key")
    
    sync_service = get_sync_service()
    results = await sync_service.sync_all()
    return {"status": "completed", "synced": results}


