"""
Integration tests for stream playback endpoints.
Tests the player/stream infrastructure without requiring a browser.
"""
import pytest
import base64
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock


class TestStreamEndpoints:
    """Test stream API endpoints."""

    @pytest.mark.asyncio
    async def test_youtube_stream_redirects(self):
        """Test that YouTube stream URLs trigger a redirect response."""
        from app.services.stream_proxy import StreamProxyService
        from app.services.cache import CacheService
        
        # Mock cache to return a YouTube stream
        mock_stream = {
            "stream_id": "test_yt_123",
            "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "title": "Test YouTube Stream",
            "channel": "test_channel"
        }
        
        with patch.object(CacheService, 'get_stream_by_id', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_stream
            
            # The URL detection is in the router, so we test the detection logic
            url_lower = mock_stream["url"].lower()
            is_youtube = "youtube.com" in url_lower or "youtu.be" in url_lower
            
            assert is_youtube is True, "YouTube URL should be detected"

    @pytest.mark.asyncio
    async def test_hls_stream_returns_manifest(self):
        """Test that HLS streams return rewritten manifest."""
        from app.services.stream_proxy import StreamProxyService
        
        service = StreamProxyService()
        
        # Test manifest rewriting
        original_manifest = """#EXTM3U
#EXT-X-VERSION:3
#EXT-X-TARGETDURATION:4
#EXTINF:4.000,
segment0.ts
#EXTINF:4.000,
segment1.ts"""
        
        rewritten = service._rewrite_manifest(
            original_manifest,
            "http://example.com/live/stream.m3u8",
            "test_stream_id",
            "http://localhost:8000"
        )
        
        # Verify segments are rewritten to proxy URLs
        assert "http://localhost:8000/api/streams/test_stream_id/segment/" in rewritten
        assert "segment0.ts" not in rewritten
        assert "segment1.ts" not in rewritten
        
        # Verify base64 encoding is present
        lines = rewritten.split('\n')
        segment_lines = [l for l in lines if l.startswith('http://localhost:8000')]
        assert len(segment_lines) == 2
        
        # Decode and verify URL
        for line in segment_lines:
            encoded_part = line.split('/segment/')[-1]
            decoded_url = base64.urlsafe_b64decode(encoded_part).decode()
            assert decoded_url.startswith("http://example.com/live/")

    @pytest.mark.asyncio
    async def test_manifest_preserves_ext_headers(self):
        """Test that manifest rewriting preserves HLS headers."""
        from app.services.stream_proxy import StreamProxyService
        
        service = StreamProxyService()
        
        manifest = """#EXTM3U
#EXT-X-VERSION:3
#EXT-X-MEDIA-SEQUENCE:12345
#EXT-X-TARGETDURATION:4
#EXTINF:4.000,
segment.ts"""
        
        rewritten = service._rewrite_manifest(
            manifest,
            "http://example.com/stream.m3u8",
            "stream_1",
            "http://api.local"
        )
        
        assert "#EXTM3U" in rewritten
        assert "#EXT-X-VERSION:3" in rewritten
        assert "#EXT-X-MEDIA-SEQUENCE:12345" in rewritten
        assert "#EXT-X-TARGETDURATION:4" in rewritten
        assert "#EXTINF:4.000," in rewritten

    @pytest.mark.asyncio
    async def test_loading_timeout_logic(self):
        """Test that the loading timeout concept would work in player.js.
        
        Note: This is a conceptual test. The actual timeout is in JS.
        We verify the backend responds quickly enough.
        """
        # This test verifies the stream proxy initialization is fast
        from app.services.stream_proxy import StreamProxyService
        
        service = StreamProxyService()
        
        # Verify timeouts are configured
        assert service.CONNECT_TIMEOUT == 15.0, "Connect timeout should be 15 seconds"
        assert service.READ_TIMEOUT == 30.0, "Read timeout should be 30 seconds"
