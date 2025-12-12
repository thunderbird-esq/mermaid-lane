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
        
        return results
    
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
