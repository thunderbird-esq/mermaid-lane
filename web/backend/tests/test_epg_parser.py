"""
Tests for EPG parser service.
"""
import pytest
from pathlib import Path
import sys

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.epg_parser import EPGParser


class TestEPGParser:
    """Test suite for EPG parsing functionality."""
    
    @pytest.mark.asyncio
    async def test_parse_single_program(self, sample_epg_file):
        """Test parsing extracts program data correctly."""
        # Create mock cache
        class MockCache:
            stored_programs = []
            
            async def store_epg_programs(self, programs):
                self.stored_programs = programs
        
        cache = MockCache()
        parser = EPGParser(cache)
        result = await parser.parse_file(sample_epg_file)
        
        # Should find 2 programs
        assert result['programs'] == 2
        
        # Should have stored them
        assert len(cache.stored_programs) == 2
        
        # Check first program
        prog = cache.stored_programs[0]
        assert prog['title'] == 'Morning News'
        assert prog['channel_id'] == 'ABC.us'
        assert prog['description'] == 'Daily news broadcast'
    
    @pytest.mark.asyncio
    async def test_parse_channel_with_multiple_programs(self, sample_epg_file):
        """Test parsing multiple programs for same channel."""
        class MockCache:
            stored_programs = []
            
            async def store_epg_programs(self, programs):
                self.stored_programs = programs
        
        cache = MockCache()
        parser = EPGParser(cache)
        result = await parser.parse_file(sample_epg_file)
        
        # Both programs should be for ABC.us
        channels = set(p['channel_id'] for p in cache.stored_programs)
        assert channels == {'ABC.us'}
        
        # Programs should be different
        titles = [p['title'] for p in cache.stored_programs]
        assert 'Morning News' in titles
        assert 'Weather Update' in titles
    
    @pytest.mark.asyncio
    async def test_handle_missing_fields(self, tmp_path):
        """Test parser handles programs with missing optional fields."""
        # Create EPG with minimal data
        minimal_epg = tmp_path / "minimal.xml"
        minimal_epg.write_text("""<?xml version="1.0" encoding="UTF-8"?>
<tv>
    <programme start="20251212010000 +0000" stop="20251212020000 +0000" channel="TEST">
        <title>Test Show</title>
    </programme>
</tv>
""")
        
        class MockCache:
            stored_programs = []
            
            async def store_epg_programs(self, programs):
                self.stored_programs = programs
        
        cache = MockCache()
        parser = EPGParser(cache)
        
        # Should not raise
        result = await parser.parse_file(minimal_epg)
        
        assert result['programs'] == 1
        prog = cache.stored_programs[0]
        assert prog['title'] == 'Test Show'
        assert prog['description'] is None or prog['description'] == ''  # Missing field
