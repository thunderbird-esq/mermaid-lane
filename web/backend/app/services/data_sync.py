"""
Data synchronization service.
Fetches data from iptv-org GitHub API and stores locally.
"""
import httpx
import logging
from typing import Optional
from app.config import get_settings
from app.services.cache import get_cache

logger = logging.getLogger(__name__)


class DataSyncService:
    """Service to sync data from iptv-org API endpoints."""
    
    ENDPOINTS = {
        "channels": "/channels.json",
        "streams": "/streams.json",
        "categories": "/categories.json",
        "countries": "/countries.json",
        "languages": "/languages.json",
        "regions": "/regions.json",
        "logos": "/logos.json",
        "guides": "/guides.json",
        "feeds": "/feeds.json",
    }
    
    def __init__(self):
        self.settings = get_settings()
        self.base_url = self.settings.iptv_api_base
    
    async def fetch_endpoint(self, endpoint: str) -> Optional[list]:
        """Fetch data from a single API endpoint."""
        url = f"{self.base_url}{endpoint}"
        logger.info(f"Fetching data from {url}")
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
                logger.info(f"Fetched {len(data)} items from {endpoint}")
                return data
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch {endpoint}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching {endpoint}: {e}")
            return None
    
    async def sync_all(self) -> dict:
        """Sync all data from iptv-org API."""
        cache = await get_cache()
        results = {}
        
        # Fetch channels first (required for counts)
        channels = await self.fetch_endpoint(self.ENDPOINTS["channels"])
        if channels:
            await cache.store_channels(channels)
            results["channels"] = len(channels)
            logger.info(f"Synced {len(channels)} channels")
        
        # Fetch streams
        streams = await self.fetch_endpoint(self.ENDPOINTS["streams"])
        if streams:
            await cache.store_streams(streams)
            results["streams"] = len(streams)
            logger.info(f"Synced {len(streams)} streams")
            
            # Update has_streams and stream_count for all channels
            counts = await cache.update_channel_stream_counts()
            results["playable_channels"] = counts["playable"]
            results["total_channels"] = counts["total"]
            logger.info(f"📺 Playable channels: {counts['playable']} / {counts['total']} total")
        
        # Fetch logos
        logos = await self.fetch_endpoint(self.ENDPOINTS["logos"])
        if logos:
            await cache.store_logos(logos)
            results["logos"] = len(logos)
            logger.info(f"Synced {len(logos)} logos")
        
        # Fetch categories (after channels for counts)
        categories = await self.fetch_endpoint(self.ENDPOINTS["categories"])
        if categories:
            await cache.store_categories(categories)
            results["categories"] = len(categories)
            logger.info(f"Synced {len(categories)} categories")
        
        # Fetch countries (after channels for counts)
        countries = await self.fetch_endpoint(self.ENDPOINTS["countries"])
        if countries:
            await cache.store_countries(countries)
            results["countries"] = len(countries)
            logger.info(f"Synced {len(countries)} countries")
        
        # Store other data in cache
        for key in ["languages", "regions", "guides", "feeds"]:
            data = await self.fetch_endpoint(self.ENDPOINTS[key])
            if data:
                await cache.set(key, data, ttl_seconds=self.settings.cache_ttl_seconds)
                results[key] = len(data)
                logger.info(f"Cached {len(data)} {key}")
        
        # Import M3U streams if available (Docker bundled or local)
        m3u_imported = await self._import_m3u_streams(cache)
        if m3u_imported > 0:
            results["m3u_streams"] = m3u_imported
            # Recalculate playable channels after M3U import
            counts = await cache.update_channel_stream_counts()
            results["playable_channels"] = counts["playable"]
            results["total_channels"] = counts["total"]
            logger.info(f"📺 Updated playable: {counts['playable']} / {counts['total']}")
        
        return results
    
    async def _import_m3u_streams(self, cache) -> int:
        """Import streams from bundled M3U files."""
        from pathlib import Path
        from app.services.m3u_parser import import_m3u_directory
        
        # Check Docker path first, then local development path
        m3u_paths = [
            Path("/app/iptv_streams"),  # Docker
            Path(__file__).parent.parent.parent.parent / "iptv_streams",  # web/iptv_streams
            Path(__file__).parent.parent.parent.parent.parent / "iptv" / "streams",  # iptv/streams
        ]
        
        m3u_dir = None
        for path in m3u_paths:
            if path.exists() and path.is_dir():
                m3u_dir = path
                break
        
        if not m3u_dir:
            logger.info("No M3U directory found, skipping M3U import")
            return 0
        
        m3u_files = list(m3u_dir.glob("*.m3u"))
        if not m3u_files:
            logger.info(f"No M3U files found in {m3u_dir}")
            return 0
        
        logger.info(f"Importing streams from {len(m3u_files)} M3U files in {m3u_dir}")
        
        try:
            result = await import_m3u_directory(cache, m3u_dir)
            total_imported = result.get('total_streams', 0)
            logger.info(f"✅ Imported {total_imported} streams from M3U files")
            return total_imported
        except Exception as e:
            logger.error(f"Failed to import M3U directory: {e}")
            return 0
    
    async def get_languages(self) -> list[dict]:
        """Get cached languages."""
        cache = await get_cache()
        data = await cache.get("languages")
        if not data:
            data = await self.fetch_endpoint(self.ENDPOINTS["languages"])
            if data:
                await cache.set("languages", data)
        return data or []
    
    async def get_regions(self) -> list[dict]:
        """Get cached regions."""
        cache = await get_cache()
        data = await cache.get("regions")
        if not data:
            data = await self.fetch_endpoint(self.ENDPOINTS["regions"])
            if data:
                await cache.set("regions", data)
        return data or []


# Singleton
_sync_service: Optional[DataSyncService] = None


def get_sync_service() -> DataSyncService:
    """Get or create sync service singleton."""
    global _sync_service
    if _sync_service is None:
        _sync_service = DataSyncService()
    return _sync_service
