"""
EPG Channel Mapping Service.
Maps XMLTV channel IDs to iptv-org channel IDs.
"""
import re
from typing import Optional
from difflib import SequenceMatcher
import logging

logger = logging.getLogger(__name__)


class EPGMapper:
    """Maps EPG channel IDs to iptv-org channel IDs."""
    
    def __init__(self, cache):
        self.cache = cache
        self._channel_cache = {}
    
    async def load_channels(self):
        """Load all channels into memory for fast matching."""
        channels = await self.cache.get_all_channels()
        self._channel_cache = {
            ch['id']: ch for ch in channels
        }
        # Build name index for fuzzy matching
        self._name_index = {}
        for ch in channels:
            name_key = self._normalize_name(ch.get('name', ''))
            if name_key:
                self._name_index[name_key] = ch['id']
    
    def _normalize_name(self, name: str) -> str:
        """Normalize channel name for matching."""
        if not name:
            return ''
        # Remove common suffixes, lowercase, remove special chars
        name = name.lower()
        name = re.sub(r'\s*(hd|sd|4k|fhd|\d+p)\s*$', '', name, flags=re.IGNORECASE)
        name = re.sub(r'[^a-z0-9]', '', name)
        return name
    
    def map_channel_id(self, epg_channel_id: str) -> Optional[str]:
        """
        Map an EPG channel ID to an iptv-org channel ID.
        
        EPG IDs are typically in format: "ChannelName.country" or "ChannelName.country@Feed"
        iptv-org IDs are in format: "ChannelName.country"
        """
        if not epg_channel_id:
            return None
        
        # Direct match
        if epg_channel_id in self._channel_cache:
            return epg_channel_id
        
        # Remove feed suffix (@East, @West, etc.)
        base_id = epg_channel_id.split('@')[0]
        if base_id in self._channel_cache:
            return base_id
        
        return None
    
    def fuzzy_match_channel(self, epg_channel_name: str, threshold: float = 0.8) -> Optional[str]:
        """
        Fuzzy match channel by name.
        Returns channel ID if match found above threshold.
        """
        if not epg_channel_name or not self._name_index:
            return None
        
        normalized = self._normalize_name(epg_channel_name)
        if not normalized:
            return None
        
        # Direct normalized match
        if normalized in self._name_index:
            return self._name_index[normalized]
        
        # Fuzzy match
        best_match = None
        best_score = 0
        
        for name_key, channel_id in self._name_index.items():
            score = SequenceMatcher(None, normalized, name_key).ratio()
            if score > best_score and score >= threshold:
                best_score = score
                best_match = channel_id
        
        return best_match
    
    async def batch_map_epg_channels(self) -> dict:
        """
        Map all EPG channels to iptv-org channels.
        Returns statistics about the mapping.
        """
        await self.load_channels()
        
        # Get unique EPG channel IDs from programs table
        epg_channels = await self.cache.get_unique_epg_channels()
        
        mapped = 0
        unmapped = 0
        mappings = {}
        
        for epg_id in epg_channels:
            iptv_id = self.map_channel_id(epg_id)
            if iptv_id:
                mappings[epg_id] = iptv_id
                mapped += 1
            else:
                unmapped += 1
        
        # Store mappings
        await self.cache.store_epg_mappings(mappings)
        
        return {
            'total_epg_channels': len(epg_channels),
            'mapped': mapped,
            'unmapped': unmapped,
            'mapping_rate': f"{(mapped / len(epg_channels) * 100):.1f}%" if epg_channels else '0%'
        }
