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
                    data TEXT NOT NULL,
                    health_status TEXT DEFAULT 'unknown',
                    health_checked_at TIMESTAMP,
                    health_response_ms INTEGER,
                    health_error TEXT
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
            
            # Migration: Add health columns to existing streams table (run BEFORE indexes)
            try:
                await db.execute("ALTER TABLE streams ADD COLUMN health_status TEXT DEFAULT 'unknown'")
            except Exception:
                pass  # Column already exists
            try:
                await db.execute("ALTER TABLE streams ADD COLUMN health_checked_at TIMESTAMP")
            except Exception:
                pass
            try:
                await db.execute("ALTER TABLE streams ADD COLUMN health_response_ms INTEGER")
            except Exception:
                pass
            
            try:
                await db.execute("ALTER TABLE streams ADD COLUMN health_error TEXT")
            except Exception:
                pass
            
            # Migration: Add next_check_due for smart scheduling
            try:
                await db.execute("ALTER TABLE streams ADD COLUMN next_check_due TIMESTAMP")
            except Exception:
                pass
            
            # Migration: Add has_streams and stream_count to channels for playable filtering
            try:
                await db.execute("ALTER TABLE channels ADD COLUMN has_streams INTEGER DEFAULT 0")
            except Exception:
                pass
            try:
                await db.execute("ALTER TABLE channels ADD COLUMN stream_count INTEGER DEFAULT 0")
            except Exception:
                pass
            
            # Indexes for common queries (after migration so columns exist)
            await db.execute("CREATE INDEX IF NOT EXISTS idx_channels_country ON channels(country)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_channels_categories ON channels(categories)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_channels_has_streams ON channels(has_streams)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_streams_channel ON streams(channel_id)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_streams_health ON streams(health_status)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_logos_channel ON logos(channel_id)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_programs_channel ON programs(channel_id)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_programs_time ON programs(start_time, stop_time)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_streams_next_check ON streams(next_check_due)")
            
            await db.commit()
    
    @staticmethod
    def _is_epg_cache_valid() -> bool:
        # Implementation in main EPG method
        pass

    # ... (other methods unchanged) ...

    # ==================== STREAM HEALTH TRACKING ====================
    
    async def update_stream_health(
        self, 
        stream_id: str, 
        status: str, 
        response_ms: int = None, 
        error: str = None,
        next_check_due: str = None  # New: scheduling parameter
    ):
        """Update health status for a stream."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE streams 
                SET health_status = ?,
                    health_checked_at = datetime('now'),
                    health_response_ms = ?,
                    health_error = ?,
                    next_check_due = ?
                WHERE id = ?
            """, (status, response_ms, error, next_check_due, stream_id))
            await db.commit()
    
    async def get_unchecked_streams(self, limit: int = 50) -> list[dict]:
        """Get streams due for a check (or never checked)."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT id, url, referrer, user_agent, channel_id, health_status
                FROM streams
                WHERE health_checked_at IS NULL
                   OR health_checked_at < datetime('now', '-10 minutes')
                ORDER BY health_checked_at ASC NULLS FIRST
                LIMIT ?
            """, (limit,))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
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
        """Bulk store/update channels using upsert pattern."""
        async with aiosqlite.connect(self.db_path) as db:
            # Use INSERT OR REPLACE instead of DELETE + INSERT
            # This preserves existing data and only updates/adds new entries
            for ch in channels:
                await db.execute(
                    """INSERT OR REPLACE INTO channels 
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
        playable_only: bool = True,  # New: filter to channels with streams
        page: int = 1,
        per_page: int = 50
    ) -> tuple[list[dict], int]:
        """Query channels with filters and pagination."""
        async with aiosqlite.connect(self.db_path) as db:
            conditions = ["closed IS NULL"]  # Only active channels
            params = []
            
            # Default: only show channels with streams
            if playable_only:
                conditions.append("has_streams = 1")
            
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
            
            # Augment with health data for immediate UI feedback
            if channels:
                channel_ids = [c['id'] for c in channels]
                placeholders = ','.join(['?'] * len(channel_ids))
                
                health_cursor = await db.execute(f"""
                    SELECT channel_id, url, health_status, health_error 
                    FROM streams 
                    WHERE channel_id IN ({placeholders})
                """, channel_ids)
                health_rows = await health_cursor.fetchall()
                
                # Build lookup: (channel_id, url) -> {status, error}
                health_map = {} 
                for hr in health_rows:
                    # distinct streams by channel_id + url
                    health_map[(hr[0], hr[1])] = {'status': hr[2], 'error': hr[3]}
                
                # Inject directly into channel stream objects
                for channel in channels:
                    for stream in channel.get('streams', []):
                        key = (channel['id'], stream['url'])
                        if key in health_map:
                            stream['health_status'] = health_map[key]['status']
                            stream['health_error'] = health_map[key]['error']
            
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
        """Bulk store/update streams using upsert pattern."""
        async with aiosqlite.connect(self.db_path) as db:
            # Use INSERT OR REPLACE instead of DELETE + INSERT
            # This preserves existing data and only updates/adds new entries
            for stream in streams:
                # Generate stable ID from URL and channel (not index-dependent)
                # This ensures same stream always gets same ID
                unique_str = f"{stream.get('url', '')}{stream.get('channel', '')}"
                stream_id = hashlib.md5(unique_str.encode()).hexdigest()[:12]
                await db.execute(
                    """INSERT OR REPLACE INTO streams 
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
    
    async def update_channel_stream_counts(self):
        """Update has_streams and stream_count for all channels based on streams table."""
        async with aiosqlite.connect(self.db_path) as db:
            # Reset all channels to 0
            await db.execute("UPDATE channels SET has_streams = 0, stream_count = 0")
            
            # Update channels that have streams
            await db.execute("""
                UPDATE channels SET 
                    has_streams = 1,
                    stream_count = (
                        SELECT COUNT(*) FROM streams 
                        WHERE streams.channel_id = channels.id
                    )
                WHERE id IN (SELECT DISTINCT channel_id FROM streams WHERE channel_id IS NOT NULL)
            """)
            
            await db.commit()
            
            # Return stats for logging
            cursor = await db.execute("SELECT COUNT(*) FROM channels WHERE has_streams = 1")
            playable = (await cursor.fetchone())[0]
            cursor = await db.execute("SELECT COUNT(*) FROM channels")
            total = (await cursor.fetchone())[0]
            
            return {"playable": playable, "total": total}
    
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
        """Get EPG programs for a channel within a time window.
        
        Uses reverse mapping to find EPG data stored under XMLTV IDs.
        """
        from datetime import datetime, timedelta
        
        now = datetime.utcnow()
        end_time = now + timedelta(hours=hours)
        
        # Build list of EPG channel IDs to search for
        # Include the channel_id itself + any EPG IDs that map to it
        epg_channel_ids = [channel_id]
        
        # Get all mappings and build reverse lookup
        mappings = await self.get_epg_mappings()
        for epg_id, iptv_id in mappings.items():
            if iptv_id == channel_id:
                epg_channel_ids.append(epg_id)
        
        async with aiosqlite.connect(self.db_path) as db:
            # Query for any matching EPG channel ID
            placeholders = ','.join('?' * len(epg_channel_ids))
            cursor = await db.execute(
                f"""SELECT id, channel_id, title, description, start_time, stop_time, category, icon
                   FROM programs 
                   WHERE channel_id IN ({placeholders}) AND stop_time > ? AND start_time < ?
                   ORDER BY start_time""",
                (*epg_channel_ids, now.isoformat(), end_time.isoformat())
            )
            rows = await cursor.fetchall()
            return [
                {
                    "id": r[0],
                    "channel_id": channel_id,  # Return the iptv-org ID, not the EPG ID
                    "title": r[2],
                    "description": r[3],
                    "start_time": r[4],
                    "stop_time": r[5],
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
    
    async def get_now_playing_for_channels(self, channel_ids: list[str]) -> dict[str, dict]:
        """Get currently playing program for multiple channels.
        
        Args:
            channel_ids: List of iptv-org channel IDs
        
        Returns:
            Dict mapping channel_id to current program (or None)
        """
        from datetime import datetime, timezone
        
        if not channel_ids:
            return {}
        
        # Use ISO format with T separator to match DB text storage
        now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S')
        
        # Get EPG mappings for reverse lookup
        mappings = await self.get_epg_mappings()
        
        # Build all possible EPG IDs to query
        epg_ids_to_check = set()
        channel_to_epg = {}  # iptv_id -> list of epg_ids
        
        for ch_id in channel_ids:
            epg_ids_to_check.add(ch_id)
            channel_to_epg[ch_id] = [ch_id]
            
            # Find all EPG IDs that map to this channel
            for epg_id, iptv_id in mappings.items():
                if iptv_id == ch_id:
                    epg_ids_to_check.add(epg_id)
                    channel_to_epg[ch_id].append(epg_id)
        
        # Query all at once
        async with aiosqlite.connect(self.db_path) as db:
            placeholders = ','.join('?' * len(epg_ids_to_check))
            cursor = await db.execute(
                f"""SELECT channel_id, title, start_time, stop_time
                   FROM programs 
                   WHERE channel_id IN ({placeholders}) AND start_time <= ? AND stop_time > ?
                   ORDER BY start_time""",
                (*epg_ids_to_check, now, now)
            )
            rows = await cursor.fetchall()
        
        # Build result - map EPG results back to iptv-org IDs
        epg_results = {r[0]: {"title": r[1], "start": r[2], "stop": r[3]} for r in rows}
        
        result = {}
        for ch_id in channel_ids:
            for epg_id in channel_to_epg.get(ch_id, []):
                if epg_id in epg_results:
                    result[ch_id] = epg_results[epg_id]
                    break
        
        return result
    
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
    
    # ==================== STREAM HEALTH TRACKING ====================
    
    async def update_stream_health(
        self, 
        stream_id: str, 
        status: str, 
        response_ms: int = None, 
        error: str = None
    ):
        """Update health status for a stream."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE streams 
                SET health_status = ?,
                    health_checked_at = datetime('now'),
                    health_response_ms = ?,
                    health_error = ?
                WHERE id = ?
            """, (status, response_ms, error, stream_id))
            await db.commit()
    
    async def get_unchecked_streams(self, limit: int = 50) -> list[dict]:
        """Get streams that haven't been health-checked yet or were checked long ago."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT id, url, referrer, user_agent, channel_id
                FROM streams
                WHERE health_checked_at IS NULL
                   OR health_checked_at < datetime('now', '-1 hour')
                ORDER BY health_checked_at ASC NULLS FIRST
                LIMIT ?
            """, (limit,))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    async def get_streams_by_health(self, channel_id: str = None) -> list[dict]:
        """Get streams sorted by health status (working first)."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            
            query = """
                SELECT id, url, channel_id, quality, health_status, 
                       health_checked_at, health_response_ms
                FROM streams
            """
            params = []
            
            if channel_id:
                query += " WHERE channel_id = ?"
                params.append(channel_id)
            
            query += """
                ORDER BY 
                    CASE health_status
                        WHEN 'working' THEN 1
                        WHEN 'unknown' THEN 2
                        WHEN 'warning' THEN 3
                        WHEN 'failed' THEN 4
                    END,
                    health_response_ms ASC NULLS LAST
            """
            
            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    async def get_recent_health_updates(self, since_seconds: int = 60) -> list[dict]:
        """Get streams that were health-checked recently (for real-time updates)."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT id, channel_id, health_status, health_error, health_checked_at, health_response_ms
                FROM streams
                WHERE health_checked_at > datetime('now', ?)
                ORDER BY health_checked_at DESC
            """, (f'-{since_seconds} seconds',))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    async def get_health_stats(self) -> dict:
        """Get overall health statistics."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT 
                    health_status,
                    COUNT(*) as count
                FROM streams
                GROUP BY health_status
            """)
            rows = await cursor.fetchall()
            return {row[0] or 'unknown': row[1] for row in rows}



# Singleton instance
_cache_service: Optional[CacheService] = None


async def get_cache() -> CacheService:
    """Get or create cache service singleton."""
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService()
        await _cache_service.initialize()
    return _cache_service

