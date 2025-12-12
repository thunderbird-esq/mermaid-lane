"""
Tests for EPG channel mapping service.
"""
import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.epg_mapping import EPGMapper


class MockCache:
    """Mock cache for testing."""
    
    def __init__(self, channels=None):
        self.channels = channels or []
        self.stored_mappings = {}
        self.epg_channels = []
    
    async def get_all_channels(self):
        return self.channels
    
    async def get_unique_epg_channels(self):
        return self.epg_channels
    
    async def store_epg_mappings(self, mappings):
        self.stored_mappings = mappings


class TestEPGMapper:
    """Test suite for EPG channel mapping."""
    
    @pytest.mark.asyncio
    async def test_map_exact_channel_id(self):
        """Test direct mapping of identical channel ID."""
        cache = MockCache(channels=[
            {'id': 'ABC.us', 'name': 'ABC'},
            {'id': 'CNN.us', 'name': 'CNN'},
        ])
        
        mapper = EPGMapper(cache)
        await mapper.load_channels()
        
        # Exact match
        result = mapper.map_channel_id('ABC.us')
        assert result == 'ABC.us'
        
        # With feed suffix
        result = mapper.map_channel_id('ABC.us@East')
        assert result == 'ABC.us'
    
    @pytest.mark.asyncio
    async def test_fuzzy_match_by_name(self):
        """Test fuzzy matching by channel name."""
        cache = MockCache(channels=[
            {'id': 'ABC.us', 'name': 'ABC'},
            {'id': 'FoxNews.us', 'name': 'Fox News'},
        ])
        
        mapper = EPGMapper(cache)
        await mapper.load_channels()
        
        # Exact normalized match
        result = mapper.fuzzy_match_channel('Fox News')
        assert result == 'FoxNews.us'
        
        # Match with case difference only
        result = mapper.fuzzy_match_channel('abc')
        assert result == 'ABC.us'
    
    @pytest.mark.asyncio
    async def test_return_none_for_unmapped(self):
        """Test that None is returned for unmappable channels."""
        cache = MockCache(channels=[
            {'id': 'ABC.us', 'name': 'ABC'},
        ])
        
        mapper = EPGMapper(cache)
        await mapper.load_channels()
        
        # No match
        result = mapper.map_channel_id('UnknownChannel.zz')
        assert result is None
        
        # Fuzzy with low similarity
        result = mapper.fuzzy_match_channel('XYZ International')
        assert result is None
    
    @pytest.mark.asyncio
    async def test_batch_mapping(self):
        """Test batch mapping of EPG channels."""
        cache = MockCache(channels=[
            {'id': 'ABC.us', 'name': 'ABC'},
            {'id': 'CNN.us', 'name': 'CNN'},
        ])
        cache.epg_channels = ['ABC.us', 'CNN.us', 'Unknown.xx']
        
        mapper = EPGMapper(cache)
        result = await mapper.batch_map_epg_channels()
        
        assert result['total_epg_channels'] == 3
        assert result['mapped'] == 2
        assert result['unmapped'] == 1
        assert cache.stored_mappings == {'ABC.us': 'ABC.us', 'CNN.us': 'CNN.us'}
