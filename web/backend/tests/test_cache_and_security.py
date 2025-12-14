"""
Tests for cache service upsert behavior and data sync.
"""
import pytest
import tempfile
import os
from pathlib import Path


class TestCacheUpsert:
    """Test that cache uses INSERT OR REPLACE (upsert) pattern."""

    @pytest.mark.asyncio
    async def test_store_channels_upsert_preserves_data(self):
        """Verify store_channels uses upsert, not delete-all."""
        from app.services.cache import CacheService
        
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_cache.db")
            cache = CacheService(db_path)
            await cache.initialize()
            
            # First insert
            channels_batch1 = [
                {"id": "ch1", "name": "Channel One", "country": "US"},
                {"id": "ch2", "name": "Channel Two", "country": "UK"},
            ]
            await cache.store_channels(channels_batch1)
            
            # Second insert with partial overlap
            channels_batch2 = [
                {"id": "ch2", "name": "Channel Two Updated", "country": "UK"},
                {"id": "ch3", "name": "Channel Three", "country": "CA"},
            ]
            await cache.store_channels(channels_batch2)
            
            # Verify all 3 channels exist (upsert behavior)
            all_channels, total = await cache.get_channels(page=1, per_page=100)
            channel_ids = {ch["id"] for ch in all_channels}
            
            assert total == 3, f"Expected 3 channels, got {total}"
            assert "ch1" in channel_ids, "ch1 should still exist (not deleted)"
            assert "ch2" in channel_ids, "ch2 should exist (updated)"
            assert "ch3" in channel_ids, "ch3 should exist (new)"
            
            # Check ch2 was updated - use channel_id filter
            ch2_list = [ch for ch in all_channels if ch["id"] == "ch2"]
            assert len(ch2_list) == 1
            assert ch2_list[0]["name"] == "Channel Two Updated"

    @pytest.mark.asyncio
    async def test_store_streams_stable_ids(self):
        """Verify stream IDs are stable across imports (no index dependency)."""
        from app.services.cache import CacheService
        import hashlib
        
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_cache.db")
            cache = CacheService(db_path)
            await cache.initialize()
            
            streams = [
                {"url": "https://example.com/stream1.m3u8", "channel": "ch1"},
                {"url": "https://example.com/stream2.m3u8", "channel": "ch2"},
            ]
            
            await cache.store_streams(streams)
            
            # Calculate expected IDs
            expected_id1 = hashlib.md5(f"{streams[0]['url']}{streams[0]['channel']}".encode()).hexdigest()[:12]
            expected_id2 = hashlib.md5(f"{streams[1]['url']}{streams[1]['channel']}".encode()).hexdigest()[:12]
            
            # Verify streams exist with expected IDs
            stream1 = await cache.get_stream_by_id(expected_id1)
            stream2 = await cache.get_stream_by_id(expected_id2)
            
            assert stream1 is not None, f"Stream with ID {expected_id1} should exist"
            assert stream2 is not None, f"Stream with ID {expected_id2} should exist"

    @pytest.mark.asyncio
    async def test_store_streams_upsert_preserves_data(self):
        """Verify store_streams uses upsert, not delete-all."""
        from app.services.cache import CacheService
        
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_cache.db")
            cache = CacheService(db_path)
            await cache.initialize()
            
            # First batch
            streams1 = [{"url": "https://a.com/1.m3u8", "channel": "ch1"}]
            await cache.store_streams(streams1)
            
            # Second batch (different stream)
            streams2 = [{"url": "https://b.com/2.m3u8", "channel": "ch2"}]
            await cache.store_streams(streams2)
            
            # Both should exist
            ch1_streams = await cache.get_streams_for_channel("ch1")
            ch2_streams = await cache.get_streams_for_channel("ch2")
            
            assert len(ch1_streams) >= 1, "ch1 streams should still exist"
            assert len(ch2_streams) >= 1, "ch2 streams should exist"


class TestAdminEndpointSecurity:
    """Test that admin endpoints require authentication."""

    @pytest.mark.asyncio
    async def test_sync_requires_api_key(self):
        """Verify /sync endpoint rejects requests without API key."""
        from fastapi.testclient import TestClient
        from app.main import app
        
        with TestClient(app) as client:
            # Without API key should fail
            response = client.post("/api/sync")
            assert response.status_code == 401
            assert "admin api key" in response.json()["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_sync_accepts_valid_api_key(self):
        """Verify /sync endpoint accepts valid API key."""
        import os
        os.environ["IPTV_ADMIN_API_KEY"] = "test-key"
        
        from fastapi.testclient import TestClient
        from app.main import app
        
        with TestClient(app) as client:
            # With valid API key should work (or timeout on actual sync)
            response = client.post("/api/sync?X-Admin-Key=test-key")
            # 200 means success, 504 means timeout (both mean auth passed)
            assert response.status_code in [200, 504]
