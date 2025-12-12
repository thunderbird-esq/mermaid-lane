"""
SQLite-based caching layer for iptv-org API data.
Provides fast local queries and TTL-based invalidation.
"""
import aiosqlite
import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Any
from app.config import get_settings


class CacheService:
    """Async SQLite cache service for API data."""
    
    def __init__(self, db_path: Optional[str] = None):
        settings = get_settings()
        self.db_path = db_path or settings.database_path
        self._ensure_directory()
    
    def _ensure_directory(self):
        """Create data directory if it doesn't exist."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
    
    async def initialize(self):
        """Create database tables if they don't exist."""
        async with aiosqlite.connect(self.db_path) as db:
            # Key-value cache for API responses
            await db.execute("""
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Channels table for efficient querying
            await db.execute("""
                CREATE TABLE IF NOT EXISTS channels (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    alt_names TEXT,
                    network TEXT,
                    owners TEXT,
                    country TEXT NOT NULL,
                    categories TEXT,
                    is_nsfw INTEGER DEFAULT 0,
                    launched TEXT,
                    closed TEXT,
                    replaced_by TEXT,
                    website TEXT,
                    data TEXT NOT NULL
                )
            """)
            
            # Streams table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS streams (
                    id TEXT PRIMARY KEY,
                    channel_id TEXT,
                    feed_id TEXT,
                    title TEXT NOT NULL,
                    url TEXT NOT NULL,
                    referrer TEXT,
                    user_agent TEXT,
                    quality TEXT,
                    data TEXT NOT NULL
                )
            """)
            
            # Categories table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS categories (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    channel_count INTEGER DEFAULT 0
                )
            """)
            
            # Countries table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS countries (
                    code TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    languages TEXT,
                    flag TEXT,
                    channel_count INTEGER DEFAULT 0
                )
            """)
            
            # Logos table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS logos (
                    id TEXT PRIMARY KEY,
                    channel_id TEXT NOT NULL,
                    feed_id TEXT,
                    url TEXT NOT NULL,
                    width INTEGER,
                    height INTEGER,
                    format TEXT,
                    tags TEXT
                )
            """)
            
            # EPG programs table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS programs (
                    id TEXT PRIMARY KEY,
                    channel_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    start_time TIMESTAMP NOT NULL,
                    stop_time TIMESTAMP NOT NULL,
                    category TEXT,
                    icon TEXT,
                    rating TEXT
                )
            """)
            
            # Indexes for common queries
            await db.execute("CREATE INDEX IF NOT EXISTS idx_channels_country ON channels(country)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_channels_categories ON channels(categories)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_streams_channel ON streams(channel_id)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_logos_channel ON logos(channel_id)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_programs_channel ON programs(channel_id)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_programs_time ON programs(start_time, stop_time)")
            
            await db.commit()
    
    @staticmethod
    def _generate_key(prefix: str, params: dict) -> str:
        """Generate cache key from prefix and parameters."""
        param_str = json.dumps(params, sort_keys=True)
        hash_val = hashlib.md5(param_str.encode()).hexdigest()[:8]
        return f"{prefix}:{hash_val}"
    
    async def get(self, key: str) -> Optional[Any]:
        """Get cached value if not expired."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT value FROM cache WHERE key = ? AND expires_at > ?",
                (key, datetime.utcnow().isoformat())
            )
            row = await cursor.fetchone()
            if row:
                return json.loads(row[0])
            return None
    
    async def set(self, key: str, value: Any, ttl_seconds: int = 3600):
        """Set cached value with TTL."""
        expires_at = datetime.utcnow() + timedelta(seconds=ttl_seconds)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """INSERT OR REPLACE INTO cache (key, value, expires_at) 
                   VALUES (?, ?, ?)""",
                (key, json.dumps(value), expires_at.isoformat())
            )
            await db.commit()
    
    async def clear_expired(self):
        """Remove expired cache entries."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "DELETE FROM cache WHERE expires_at < ?",
                (datetime.utcnow().isoformat(),)
            )
            await db.commit()
    
    # Channel-specific methods
    async def store_channels(self, channels: list[dict]):
        """Bulk store channels for efficient querying."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM channels")
            for ch in channels:
                await db.execute(
                    """INSERT INTO channels 
                       (id, name, alt_names, network, owners, country, categories, 
                        is_nsfw, launched, closed, replaced_by, website, data)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        ch.get("id"),
                        ch.get("name"),
                        json.dumps(ch.get("alt_names", [])),
                        ch.get("network"),
                        json.dumps(ch.get("owners", [])),
                        ch.get("country"),
                        json.dumps(ch.get("categories", [])),
                        1 if ch.get("is_nsfw") else 0,
                        ch.get("launched"),
                        ch.get("closed"),
                        ch.get("replaced_by"),
                        ch.get("website"),
                        json.dumps(ch)
                    )
                )
            await db.commit()
    
    async def get_channels(
        self,
        country: Optional[str] = None,
        category: Optional[str] = None,
        provider: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        per_page: int = 50
    ) -> tuple[list[dict], int]:
        """Query channels with filters and pagination."""
        async with aiosqlite.connect(self.db_path) as db:
            conditions = ["closed IS NULL"]  # Only active channels
            params = []
            
            if country:
                conditions.append("country = ?")
                params.append(country.upper())
            
            if category:
                conditions.append("categories LIKE ?")
                params.append(f'%"{category}"%')
            
            if search:
                conditions.append("(name LIKE ? OR alt_names LIKE ?)")
                params.extend([f"%{search}%", f"%{search}%"])
            
            if provider:
                # Filter channels that have streams from this provider
                conditions.append("""id IN (
                    SELECT channel_id FROM streams 
                    WHERE data LIKE ? AND channel_id IS NOT NULL
                )""")
                params.append(f'%"provider": "{provider}"%')
            
            where_clause = " AND ".join(conditions)
            
            # Get total count
            count_cursor = await db.execute(
                f"SELECT COUNT(*) FROM channels WHERE {where_clause}",
                params
            )
            total = (await count_cursor.fetchone())[0]
            
            # Get paginated results
            offset = (page - 1) * per_page
            cursor = await db.execute(
                f"""SELECT data FROM channels 
                    WHERE {where_clause} 
                    ORDER BY name 
                    LIMIT ? OFFSET ?""",
                params + [per_page, offset]
            )
            rows = await cursor.fetchall()
            channels = [json.loads(row[0]) for row in rows]
            
            return channels, total
    
    async def get_channel_by_id(self, channel_id: str) -> Optional[dict]:
        """Get single channel by ID."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT data FROM channels WHERE id = ?",
                (channel_id,)
            )
            row = await cursor.fetchone()
            if row:
                return json.loads(row[0])
            return None
    
    # Stream methods
    async def store_streams(self, streams: list[dict]):
        """Bulk store streams."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM streams")
            for i, stream in enumerate(streams):
                # Generate unique ID from URL, channel, and index
                unique_str = f"{stream.get('url', '')}{stream.get('channel', '')}{i}"
                stream_id = hashlib.md5(unique_str.encode()).hexdigest()[:12]
                await db.execute(
                    """INSERT INTO streams 
                       (id, channel_id, feed_id, title, url, referrer, user_agent, quality, data)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        stream_id,
                        stream.get("channel"),
                        stream.get("feed"),
                        stream.get("title", ""),
                        stream.get("url"),
                        stream.get("referrer"),
                        stream.get("user_agent"),
                        stream.get("quality"),
                        json.dumps({**stream, "stream_id": stream_id})
                    )
                )
            await db.commit()
    
    async def get_streams_for_channel(self, channel_id: str) -> list[dict]:
        """Get all streams for a channel."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT data FROM streams WHERE channel_id = ?",
                (channel_id,)
            )
            rows = await cursor.fetchall()
            return [json.loads(row[0]) for row in rows]
    
    async def get_stream_by_id(self, stream_id: str) -> Optional[dict]:
        """Get stream by its generated ID."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT data FROM streams WHERE id = ?",
                (stream_id,)
            )
            row = await cursor.fetchone()
            if row:
                return json.loads(row[0])
            return None
    
    async def store_m3u_streams(self, streams: list[dict]):
        """Store streams from local M3U files (appends, doesn't clear)."""
        async with aiosqlite.connect(self.db_path) as db:
            for stream in streams:
                stream_id = stream.get('id')
                await db.execute(
                    """INSERT OR REPLACE INTO streams 
                       (id, channel_id, feed_id, title, url, referrer, user_agent, quality, data)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        stream_id,
                        stream.get("channel_id"),
                        stream.get("feed"),
                        stream.get("title", ""),
                        stream.get("url"),
                        stream.get("referrer"),
                        stream.get("user_agent"),
                        stream.get("quality"),
                        json.dumps({**stream, "stream_id": stream_id, "source": "m3u_local"})
                    )
                )
            await db.commit()
    
    async def get_stream_stats(self) -> dict:
        """Get stream statistics."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM streams")
            total = (await cursor.fetchone())[0]
            
            cursor = await db.execute("SELECT COUNT(DISTINCT channel_id) FROM streams WHERE channel_id IS NOT NULL")
            channels_with_streams = (await cursor.fetchone())[0]
            
            return {
                "total_streams": total,
                "channels_with_streams": channels_with_streams
            }
    
    async def get_providers(self) -> list[dict]:
        """Get unique stream providers extracted from M3U data."""
        async with aiosqlite.connect(self.db_path) as db:
            # Provider is stored in the JSON data field from M3U imports
            cursor = await db.execute(
                "SELECT data FROM streams WHERE data LIKE '%m3u_local%'"
            )
            rows = await cursor.fetchall()
            
            providers = {}
            for row in rows:
                try:
                    data = json.loads(row[0])
                    provider = data.get("provider")
                    if provider:
                        if provider not in providers:
                            providers[provider] = {"id": provider, "name": provider.title(), "stream_count": 0}
                        providers[provider]["stream_count"] += 1
                except:
                    pass
            
            # Sort by stream count
            return sorted(providers.values(), key=lambda x: x["stream_count"], reverse=True)
    
    # Categories and countries
    async def store_categories(self, categories: list[dict]):
        """Store categories with channel counts."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM categories")
            for cat in categories:
                # Count channels in this category
                count_cursor = await db.execute(
                    "SELECT COUNT(*) FROM channels WHERE categories LIKE ?",
                    (f'%"{cat.get("id")}"%',)
                )
                count = (await count_cursor.fetchone())[0]
                
                await db.execute(
                    """INSERT INTO categories (id, name, description, channel_count)
                       VALUES (?, ?, ?, ?)""",
                    (cat.get("id"), cat.get("name"), cat.get("description"), count)
                )
            await db.commit()
    
    async def get_categories(self) -> list[dict]:
        """Get all categories with channel counts."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT id, name, description, channel_count FROM categories ORDER BY name"
            )
            rows = await cursor.fetchall()
            return [
                {"id": r[0], "name": r[1], "description": r[2], "channel_count": r[3]}
                for r in rows
            ]
    
    async def store_countries(self, countries: list[dict]):
        """Store countries with channel counts."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM countries")
            for country in countries:
                # Count channels in this country
                count_cursor = await db.execute(
                    "SELECT COUNT(*) FROM channels WHERE country = ?",
                    (country.get("code"),)
                )
                count = (await count_cursor.fetchone())[0]
                
                await db.execute(
                    """INSERT INTO countries (code, name, languages, flag, channel_count)
                       VALUES (?, ?, ?, ?, ?)""",
                    (
                        country.get("code"),
                        country.get("name"),
                        json.dumps(country.get("languages", [])),
                        country.get("flag", ""),
                        count
                    )
                )
            await db.commit()
    
    async def get_countries(self) -> list[dict]:
        """Get all countries with channel counts."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """SELECT code, name, languages, flag, channel_count 
                   FROM countries ORDER BY name"""
            )
            rows = await cursor.fetchall()
            return [
                {
                    "code": r[0],
                    "name": r[1],
                    "languages": json.loads(r[2]),
                    "flag": r[3],
                    "channel_count": r[4]
                }
                for r in rows
            ]
    
    # Logo methods
    async def store_logos(self, logos: list[dict]):
        """Store channel logos."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM logos")
            for i, logo in enumerate(logos):
                # Generate unique ID from URL, channel, and index
                unique_str = f"{logo.get('url', '')}{logo.get('channel', '')}{i}"
                logo_id = hashlib.md5(unique_str.encode()).hexdigest()[:12]
                await db.execute(
                    """INSERT INTO logos 
                       (id, channel_id, feed_id, url, width, height, format, tags)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        logo_id,
                        logo.get("channel"),
                        logo.get("feed"),
                        logo.get("url"),
                        logo.get("width", 0),
                        logo.get("height", 0),
                        logo.get("format"),
                        json.dumps(logo.get("tags", []))
                    )
                )
            await db.commit()
    
    async def get_logos_for_channel(self, channel_id: str) -> list[dict]:
        """Get logos for a channel."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT url, width, height, format, tags FROM logos WHERE channel_id = ?",
                (channel_id,)
            )
            rows = await cursor.fetchall()
            return [
                {
                    "url": r[0],
                    "width": r[1],
                    "height": r[2],
                    "format": r[3],
                    "tags": json.loads(r[4])
                }
                for r in rows
            ]
    
    # EPG Program methods
    async def store_epg_programs(self, programs: list[dict]):
        """Store EPG programs (appends, doesn't clear existing)."""
        async with aiosqlite.connect(self.db_path) as db:
            for prog in programs:
                await db.execute(
                    """INSERT OR REPLACE INTO programs 
                       (id, channel_id, title, description, start_time, stop_time, category, icon, rating)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        prog.get("id"),
                        prog.get("channel_id"),
                        prog.get("title"),
                        prog.get("description"),
                        prog.get("start"),
                        prog.get("stop"),
                        prog.get("category"),
                        prog.get("icon"),
                        prog.get("rating")
                    )
                )
            await db.commit()
    
    async def get_epg_for_channel(self, channel_id: str, hours: int = 24) -> list[dict]:
        """Get EPG programs for a channel within a time window."""
        from datetime import datetime, timedelta
        
        now = datetime.utcnow()
        end_time = now + timedelta(hours=hours)
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """SELECT id, channel_id, title, description, start_time, stop_time, category, icon
                   FROM programs 
                   WHERE channel_id = ? AND stop_time > ? AND start_time < ?
                   ORDER BY start_time""",
                (channel_id, now.isoformat(), end_time.isoformat())
            )
            rows = await cursor.fetchall()
            return [
                {
                    "id": r[0],
                    "channel_id": r[1],
                    "title": r[2],
                    "description": r[3],
                    "start": r[4],
                    "stop": r[5],
                    "category": r[6],
                    "icon": r[7]
                }
                for r in rows
            ]
    
    async def get_now_playing(self, limit: int = 50) -> list[dict]:
        """Get currently playing programs across all channels."""
        from datetime import datetime
        
        now = datetime.utcnow().isoformat()
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """SELECT id, channel_id, title, description, start_time, stop_time, category, icon
                   FROM programs 
                   WHERE start_time <= ? AND stop_time > ?
                   ORDER BY channel_id
                   LIMIT ?""",
                (now, now, limit)
            )
            rows = await cursor.fetchall()
            return [
                {
                    "id": r[0],
                    "channel_id": r[1],
                    "title": r[2],
                    "description": r[3],
                    "start": r[4],
                    "stop": r[5],
                    "category": r[6],
                    "icon": r[7]
                }
                for r in rows
            ]
    
    async def get_epg_stats(self) -> dict:
        """Get EPG statistics."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM programs")
            total_programs = (await cursor.fetchone())[0]
            
            cursor = await db.execute("SELECT COUNT(DISTINCT channel_id) FROM programs")
            channels_with_epg = (await cursor.fetchone())[0]
            
            return {
                "total_programs": total_programs,
                "channels_with_epg": channels_with_epg
            }
    
    async def clear_epg(self):
        """Clear all EPG data."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM programs")
            await db.commit()
    
    async def get_all_channels(self) -> list[dict]:
        """Get all channels for mapping purposes."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT id, name FROM channels")
            rows = await cursor.fetchall()
            return [{"id": r[0], "name": r[1]} for r in rows]
    
    async def get_unique_epg_channels(self) -> list[str]:
        """Get unique channel IDs from EPG programs."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT DISTINCT channel_id FROM programs")
            rows = await cursor.fetchall()
            return [r[0] for r in rows if r[0]]
    
    async def store_epg_mappings(self, mappings: dict):
        """Store EPG channel ID to iptv-org ID mappings."""
        # Store in cache table as JSON
        await self.set('epg_mappings', mappings, ttl_seconds=86400 * 30)  # 30 days
    
    async def get_epg_mappings(self) -> dict:
        """Get stored EPG mappings."""
        result = await self.get('epg_mappings')
        return result or {}



# Singleton instance
_cache_service: Optional[CacheService] = None


async def get_cache() -> CacheService:
    """Get or create cache service singleton."""
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService()
        await _cache_service.initialize()
    return _cache_service

