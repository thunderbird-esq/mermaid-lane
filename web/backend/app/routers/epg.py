"""
EPG (Electronic Program Guide) API endpoints.
"""
from fastapi import APIRouter, Query, HTTPException
from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path

from app.services.cache import get_cache
from app.services.epg_parser import EPGParser
from app.config import get_settings

router = APIRouter(prefix="/api/epg", tags=["epg"])


@router.get("/stats")
async def get_epg_stats():
    """
    Get EPG statistics.
    """
    cache = await get_cache()
    stats = await cache.get_epg_stats()
    return stats


@router.get("/channel/{channel_id}")
async def get_channel_epg(
    channel_id: str,
    hours: int = Query(24, ge=1, le=168, description="Hours of EPG data to return")
):
    """
    Get EPG data for a specific channel.
    
    Note: EPG data depends on available guide sources from iptv-org/epg.
    Not all channels have EPG data.
    """
    cache = await get_cache()
    programs = await cache.get_epg_for_channel(channel_id, hours)
    
    return {
        "channel_id": channel_id,
        "programs": programs,
        "count": len(programs)
    }


@router.get("/now/playing")
async def get_now_playing(
    limit: int = Query(50, ge=1, le=200, description="Max results")
):
    """
    Get currently playing programs across channels.
    """
    cache = await get_cache()
    programs = await cache.get_now_playing(limit)
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "programs": programs,
        "count": len(programs)
    }


@router.get("/timeline")
async def get_epg_timeline(
    channels: str = Query(..., description="Comma-separated channel IDs"),
    start: Optional[str] = Query(None, description="Start time (ISO format)"),
    hours: int = Query(6, ge=1, le=24, description="Hours to show")
):
    """
    Get EPG timeline for multiple channels.
    Used for TV guide grid view.
    """
    channel_ids = [c.strip() for c in channels.split(",") if c.strip()]
    
    if not channel_ids:
        raise HTTPException(status_code=400, detail="At least one channel ID required")
    
    if len(channel_ids) > 50:
        raise HTTPException(status_code=400, detail="Maximum 50 channels per request")
    
    # Parse start time or use now
    if start:
        try:
            start_time = datetime.fromisoformat(start.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start time format")
    else:
        start_time = datetime.utcnow()
    
    end_time = start_time + timedelta(hours=hours)
    
    cache = await get_cache()
    result_channels = []
    
    for cid in channel_ids:
        programs = await cache.get_epg_for_channel(cid, hours)
        # Get channel name from channel data if available
        channel_data = await cache.get_channel_by_id(cid)
        channel_name = channel_data.get("name", cid) if channel_data else cid
        
        result_channels.append({
            "channel_id": cid,
            "channel_name": channel_name,
            "programs": programs
        })
    
    return {
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "channels": result_channels
    }


@router.get("/search")
async def search_epg(
    q: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(50, ge=1, le=200, description="Max results")
):
    """
    Search EPG program titles and descriptions.
    """
    # TODO: Implement full-text search
    return {
        "query": q,
        "results": [],
        "message": "EPG search coming soon"
    }



@router.post("/import")
async def import_epg_file(
    filename: str = Query("pluto_guide.xml", description="EPG file name in data directory")
):
    """
    Import EPG data from an XMLTV file.
    File must be in the data directory.
    """
    settings = get_settings()
    data_dir = Path(settings.database_path).parent
    filepath = data_dir / filename
    
    if not filepath.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {filename}")
    
    if not filepath.suffix == '.xml':
        raise HTTPException(status_code=400, detail="Only XML files supported")
    
    cache = await get_cache()
    parser = EPGParser(cache)
    
    try:
        stats = await parser.parse_file(filepath)
        return {
            "success": True,
            "message": f"Imported {stats['programs']} programs from {stats['channels']} channels",
            **stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


@router.delete("/clear")
async def clear_epg():
    """
    Clear all EPG data.
    """
    cache = await get_cache()
    await cache.clear_epg()
    return {"success": True, "message": "EPG data cleared"}
