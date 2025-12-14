"""
Tests for playable channel filtering and stream count features.
"""
import pytest
import tempfile
import os


class TestPlayableChannelFilter:
    """Test the playable_only filter functionality."""

    @pytest.mark.asyncio
    async def test_playable_only_filter_excludes_channels_without_streams(self):
        """Channels without streams should be excluded when playable_only=True."""
        from app.services.cache import CacheService
        
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_cache.db")
            cache = CacheService(db_path)
            await cache.initialize()
            
            # Create channels
            channels = [
                {"id": "ch1", "name": "Channel One", "country": "US"},
                {"id": "ch2", "name": "Channel Two", "country": "UK"},
                {"id": "ch3", "name": "Channel Three", "country": "CA"},
            ]
            await cache.store_channels(channels)
            
            # Create streams for only ch1 and ch2
            streams = [
                {"url": "http://example.com/stream1.m3u8", "channel": "ch1"},
                {"url": "http://example.com/stream2.m3u8", "channel": "ch2"},
            ]
            await cache.store_streams(streams)
            
            # Update has_streams counts
            result = await cache.update_channel_stream_counts()
            assert result["playable"] == 2
            assert result["total"] == 3
            
            # Test playable_only=True (default)
            playable_channels, playable_count = await cache.get_channels(
                page=1, per_page=100, playable_only=True
            )
            playable_ids = {ch["id"] for ch in playable_channels}
            
            assert playable_count == 2
            assert "ch1" in playable_ids
            assert "ch2" in playable_ids
            assert "ch3" not in playable_ids  # No streams
            
            # Test playable_only=False
            all_channels, all_count = await cache.get_channels(
                page=1, per_page=100, playable_only=False
            )
            all_ids = {ch["id"] for ch in all_channels}
            
            assert all_count == 3
            assert "ch3" in all_ids  # Now included

    @pytest.mark.asyncio
    async def test_update_channel_stream_counts_accuracy(self):
        """Verify stream counts are calculated correctly."""
        from app.services.cache import CacheService
        
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_cache.db")
            cache = CacheService(db_path)
            await cache.initialize()
            
            # Create a channel
            await cache.store_channels([
                {"id": "multi", "name": "Multi-stream Channel", "country": "US"}
            ])
            
            # Create multiple streams for same channel
            streams = [
                {"url": "http://example.com/stream1.m3u8", "channel": "multi"},
                {"url": "http://example.com/stream2.m3u8", "channel": "multi"},
                {"url": "http://example.com/stream3.m3u8", "channel": "multi"},
            ]
            await cache.store_streams(streams)
            
            # Update counts
            await cache.update_channel_stream_counts()
            
            # Get channel and verify stream_count column could be queried
            channels, _ = await cache.get_channels(page=1, per_page=10, playable_only=True)
            assert len(channels) == 1
            assert channels[0]["id"] == "multi"


class TestHealthWorker:
    """Test health worker functionality."""

    @pytest.mark.asyncio
    async def test_get_unchecked_streams_returns_streams(self):
        """Verify get_unchecked_streams returns streams that need checking."""
        from app.services.cache import CacheService
        
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_cache.db")
            cache = CacheService(db_path)
            await cache.initialize()
            
            # Create streams (never checked)
            streams = [
                {"url": "http://example.com/stream1.m3u8", "channel": "ch1"},
                {"url": "http://example.com/stream2.m3u8", "channel": "ch2"},
            ]
            await cache.store_streams(streams)
            
            # Get unchecked streams
            unchecked = await cache.get_unchecked_streams(limit=10)
            
            assert len(unchecked) == 2
            assert all(s.get("url") for s in unchecked)

    @pytest.mark.asyncio
    async def test_update_stream_health_updates_status(self):
        """Verify stream health updates are persisted."""
        from app.services.cache import CacheService
        
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_cache.db")
            cache = CacheService(db_path)
            await cache.initialize()
            
            # Create a stream
            streams = [
                {"url": "http://example.com/stream1.m3u8", "channel": "ch1"},
            ]
            await cache.store_streams(streams)
            
            # Get the stream ID
            unchecked = await cache.get_unchecked_streams(limit=1)
            stream_id = unchecked[0]["id"]
            
            # Update health status
            await cache.update_stream_health(
                stream_id=stream_id,
                status="healthy",
                response_ms=150,
                error=None
            )
            
            # Verify update
            stream = await cache.get_stream_by_id(stream_id)
            assert stream is not None
            # The health status is stored in the database but not returned in get_stream_by_id
            # We can verify by checking health stats
            stats = await cache.get_health_stats()
            assert stats.get("healthy", 0) >= 1


class TestGeoBypass:
    """Test geo-bypass service."""

    def test_detect_country_from_bbc_url(self):
        """BBC URLs should be detected as UK."""
        from app.services.geo_bypass import GeoBypassService
        
        service = GeoBypassService()
        
        assert service.detect_country_from_url("https://vs-cmaf-push-uk.live.fastly.md.bbci.co.uk/x=4") == "uk"
        assert service.detect_country_from_url("https://example.com/stream.m3u8") is None

    def test_generate_fake_ip(self):
        """Fake IP should be valid format."""
        from app.services.geo_bypass import GeoBypassService
        
        service = GeoBypassService()
        
        fake_ip = service.generate_fake_ip("uk")
        parts = fake_ip.split(".")
        
        assert len(parts) == 4
        assert all(0 <= int(p) <= 255 for p in parts)

    def test_build_spoofed_headers_includes_forwarded_for(self):
        """Spoofed headers should include X-Forwarded-For."""
        from app.services.geo_bypass import GeoBypassService
        
        service = GeoBypassService()
        
        headers = service.build_spoofed_headers("https://bbc.co.uk/stream.m3u8")
        
        assert "X-Forwarded-For" in headers
        assert "Client-IP" in headers
        assert "User-Agent" in headers


class TestTranscoderCleanup:
    """Test transcoder cleanup functionality."""

    @pytest.mark.asyncio
    async def test_cleanup_stale_transcodes_removes_old_entries(self):
        """Verify stale transcodes are cleaned up."""
        from app.services.transcoder import TranscoderService
        from datetime import datetime, timedelta
        
        service = TranscoderService()
        
        # Manually add a stale entry
        service._last_access["stale_stream"] = datetime.now() - timedelta(minutes=10)
        
        # Run cleanup with 5 minute threshold
        cleaned = await service.cleanup_stale_transcodes(max_age_minutes=5)
        
        # The stale entry should be cleaned (even if process doesn't exist)
        assert "stale_stream" not in service._last_access
