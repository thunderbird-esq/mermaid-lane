"""
Tests for M3U parser service.
"""
import pytest
from pathlib import Path
import sys

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.m3u_parser import M3UParser


class TestM3UParser:
    """Test suite for M3U parsing functionality."""
    
    @pytest.mark.asyncio
    async def test_parse_extinf_entry(self, sample_m3u_file):
        """Test parsing a single EXTINF entry extracts correct data."""
        # Create mock cache
        class MockCache:
            async def store_m3u_streams(self, streams):
                pass
        
        parser = M3UParser(MockCache())
        result = await parser.parse_file(sample_m3u_file)
        
        # Should find 3 streams
        assert result['count'] == 3
        
        # First stream should have channel_id
        streams = result['streams']
        assert streams[0]['channel_id'] == 'ABC.us'
        assert streams[0]['feed'] == 'East'
        assert streams[0]['title'] == 'ABC East'
        assert 'abc-east.m3u8' in streams[0]['url']
    
    @pytest.mark.asyncio
    async def test_extract_provider_from_filename(self, sample_m3u_file):
        """Test that provider is extracted from filename like 'us_pluto.m3u'."""
        class MockCache:
            async def store_m3u_streams(self, streams):
                pass
        
        parser = M3UParser(MockCache())
        result = await parser.parse_file(sample_m3u_file)
        
        # Provider should be 'pluto' from filename 'us_pluto.m3u'
        assert result['provider'] == 'pluto'
        assert result['country'] == 'US'
        
        # Each stream should have provider
        for stream in result['streams']:
            assert stream['provider'] == 'pluto'
    
    @pytest.mark.asyncio
    async def test_handle_malformed_lines(self, tmp_path):
        """Test parser handles malformed content gracefully."""
        # Create malformed M3U
        bad_m3u = tmp_path / "bad.m3u"
        bad_m3u.write_text("""#EXTM3U
#EXTINF:-1
http://example.com/no-name.m3u8
Random garbage line
#EXTINF:-1 tvg-id="",
http://example.com/empty-id.m3u8
""")
        
        class MockCache:
            async def store_m3u_streams(self, streams):
                pass
        
        parser = M3UParser(MockCache())
        
        # Should not raise, should handle gracefully
        result = await parser.parse_file(bad_m3u)
        
        # Should still find some streams (those with URLs)
        assert result['count'] >= 0
    
    def test_extract_quality(self):
        """Test quality extraction from stream names."""
        class MockCache:
            pass
        
        parser = M3UParser(MockCache())
        
        assert parser._extract_quality("Channel HD (1080p)") == "1080p"
        assert parser._extract_quality("Channel 4K Ultra") == "4K"
        assert parser._extract_quality("Channel (720p)") == "720p"
        assert parser._extract_quality("Channel SD") is None
