"""
User data API endpoints.
Handles favorites, watch history, and user data export/import.
"""
from fastapi import APIRouter, Header, Query, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.services.cache import get_cache

router = APIRouter(prefix="/api/user", tags=["user"])


class FavoriteRequest(BaseModel):
    channel_id: str


class WatchRequest(BaseModel):
    channel_id: str
    stream_id: Optional[str] = None
    duration_seconds: Optional[int] = 0


class ImportRequest(BaseModel):
    favorites: list[str] = []


# Favorites endpoints
@router.get("/favorites")
async def get_favorites(
    x_device_id: str = Header(..., description="Device fingerprint for user identification")
):
    """Get user's favorite channels."""
    cache = await get_cache()
    channel_ids = await cache.get_favorites(x_device_id)
    
    # Optionally fetch full channel data
    channels = []
    for channel_id in channel_ids:
        channel = await cache.get_channel_by_id(channel_id)
        if channel:
            channels.append(channel)
    
    return {
        "favorites": channel_ids,
        "channels": channels,
        "count": len(channel_ids)
    }


@router.post("/favorites")
async def add_favorite(
    request: FavoriteRequest,
    x_device_id: str = Header(..., description="Device fingerprint")
):
    """Add a channel to favorites."""
    cache = await get_cache()
    success = await cache.add_favorite(x_device_id, request.channel_id)
    return {"success": success, "channel_id": request.channel_id}


@router.delete("/favorites/{channel_id}")
async def remove_favorite(
    channel_id: str,
    x_device_id: str = Header(..., description="Device fingerprint")
):
    """Remove a channel from favorites."""
    cache = await get_cache()
    success = await cache.remove_favorite(x_device_id, channel_id)
    return {"success": success, "channel_id": channel_id}


@router.get("/favorites/{channel_id}/check")
async def check_favorite(
    channel_id: str,
    x_device_id: str = Header(..., description="Device fingerprint")
):
    """Check if a channel is in favorites."""
    cache = await get_cache()
    is_fav = await cache.is_favorite(x_device_id, channel_id)
    return {"is_favorite": is_fav, "channel_id": channel_id}


# Watch history endpoints
@router.post("/watch")
async def record_watch(
    request: WatchRequest,
    x_device_id: str = Header(..., description="Device fingerprint")
):
    """Record a channel watch event."""
    cache = await get_cache()
    await cache.record_watch(
        x_device_id, 
        request.channel_id, 
        request.stream_id, 
        request.duration_seconds
    )
    return {"recorded": True}


@router.get("/history")
async def get_history(
    x_device_id: str = Header(..., description="Device fingerprint"),
    limit: int = Query(20, ge=1, le=100)
):
    """Get user's watch history."""
    cache = await get_cache()
    history = await cache.get_watch_history(x_device_id, limit)
    return {"history": history, "count": len(history)}


# Discovery endpoints (don't require device ID)
@router.get("/popular")
async def get_popular(limit: int = Query(20, ge=1, le=100)):
    """Get most popular channels by view count."""
    cache = await get_cache()
    popular = await cache.get_popular_channels(limit)
    
    # Optionally fetch full channel data
    channels = []
    for item in popular:
        channel = await cache.get_channel_by_id(item["channel_id"])
        if channel:
            channel["view_count"] = item["view_count"]
            channels.append(channel)
    
    return {"channels": channels, "count": len(channels)}


@router.get("/recent")
async def get_recently_added(hours: int = Query(168, ge=1, le=720)):
    """Get recently added channels (default: last week)."""
    cache = await get_cache()
    channel_ids = await cache.get_recently_added_channels(hours)
    return {"channel_ids": channel_ids, "count": len(channel_ids)}


# Export/Import endpoints
@router.get("/export")
async def export_data(
    x_device_id: str = Header(..., description="Device fingerprint")
):
    """Export user data for backup."""
    cache = await get_cache()
    data = await cache.export_user_data(x_device_id)
    return data


@router.post("/import")
async def import_data(
    request: ImportRequest,
    x_device_id: str = Header(..., description="Device fingerprint")
):
    """Import user data from backup."""
    cache = await get_cache()
    result = await cache.import_user_data(x_device_id, {"favorites": request.favorites})
    return {"imported": result}
