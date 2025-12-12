"""
EPG Channel Mapping Service.
Maps XMLTV channel IDs to iptv-org channel IDs using multiple strategies.
"""
import re
from typing import Optional, Dict, List, Tuple
from difflib import SequenceMatcher
import logging

logger = logging.getLogger(__name__)


class EPGMapper:
    """Maps EPG channel IDs to iptv-org channel IDs using multiple strategies."""
    
    def __init__(self, cache):
        self.cache = cache
        self._channel_cache: Dict[str, dict] = {}
        self._name_index: Dict[str, str] = {}
        self._alt_name_index: Dict[str, str] = {}
    
    async def load_channels(self):
        """Load all channels into memory for fast matching."""
        channels = await self.cache.get_all_channels()
        self._channel_cache = {
            ch['id']: ch for ch in channels
        }
        
        # Build multiple indexes for matching
        self._name_index = {}
        self._alt_name_index = {}
        
        for ch in channels:
            channel_id = ch['id']
            
            # Primary name
            name_key = self._normalize_name(ch.get('name', ''))
            if name_key:
                self._name_index[name_key] = channel_id
            
            # Also index by the ID prefix (e.g., "ABC" from "ABC.us")
            id_prefix = channel_id.split('.')[0].lower()
            if id_prefix and id_prefix not in self._alt_name_index:
                self._alt_name_index[id_prefix] = channel_id
    
    def _normalize_name(self, name: str) -> str:
        """Normalize channel name for matching."""
        if not name:
            return ''
        name = name.lower()
        # Remove common suffixes
        name = re.sub(r'\s*(hd|sd|4k|fhd|uhd|\d+p)\s*$', '', name, flags=re.IGNORECASE)
        # Remove special chars but keep spaces for now
        name = re.sub(r'[^a-z0-9\s]', '', name)
        # Collapse spaces
        name = re.sub(r'\s+', '', name)
        return name
    
    def _extract_channel_name(self, epg_id: str) -> str:
        """Extract the channel name part from an EPG ID like 'ABC.us@East'."""
        # Remove feed suffix
        base = epg_id.split('@')[0]
        # Remove country suffix
        name_part = base.rsplit('.', 1)[0] if '.' in base else base
        return name_part
    
    def map_channel_id(self, epg_channel_id: str) -> Optional[str]:
        """
        Map an EPG channel ID to an iptv-org channel ID.
        Uses multiple strategies:
        1. Direct match
        2. Remove feed suffix (@East, @West, @SD, etc.)
        3. Match by extracted channel name + country
        """
        if not epg_channel_id:
            return None
        
        # Strategy 1: Direct match
        if epg_channel_id in self._channel_cache:
            return epg_channel_id
        
        # Strategy 2: Remove feed suffix
        base_id = epg_channel_id.split('@')[0]
        if base_id in self._channel_cache:
            return base_id
        
        # Strategy 3: Try common variations
        # e.g., "KACVDT1.us@SD" -> try "KACV.us", "KACVDT.us"
        if '.' in base_id:
            name_part, country = base_id.rsplit('.', 1)
            # Try without DT suffix (digital TV designation)
            simplified = re.sub(r'(DT\d?|HD|SD)$', '', name_part, flags=re.IGNORECASE)
            if simplified != name_part:
                simple_id = f"{simplified}.{country}"
                if simple_id in self._channel_cache:
                    return simple_id
        
        return None
    
    def fuzzy_match_channel(self, epg_channel_name: str, country: str = None, threshold: float = 0.75) -> Optional[str]:
        """
        Fuzzy match channel by name.
        Returns channel ID if match found above threshold.
        """
        if not epg_channel_name or not self._name_index:
            return None
        
        normalized = self._normalize_name(epg_channel_name)
        if not normalized:
            return None
        
        # Strategy 1: Direct normalized match
        if normalized in self._name_index:
            return self._name_index[normalized]
        
        # Strategy 2: Check alt name index
        if normalized in self._alt_name_index:
            return self._alt_name_index[normalized]
        
        # Strategy 3: Fuzzy match with country preference
        best_match = None
        best_score = 0
        
        for name_key, channel_id in self._name_index.items():
            score = SequenceMatcher(None, normalized, name_key).ratio()
            
            # Boost score if country matches
            if country and f".{country.lower()}" in channel_id.lower():
                score += 0.1
            
            if score > best_score and score >= threshold:
                best_score = score
                best_match = channel_id
        
        return best_match
    
    async def batch_map_epg_channels(self, use_fuzzy: bool = True) -> dict:
        """
        Map all EPG channels to iptv-org channels.
        Returns statistics about the mapping.
        """
        await self.load_channels()
        
        # Get unique EPG channel IDs from programs table
        epg_channels = await self.cache.get_unique_epg_channels()
        
        mapped = 0
        unmapped = 0
        fuzzy_matched = 0
        mappings = {}
        unmapped_list = []
        
        for epg_id in epg_channels:
            # Try direct mapping first
            iptv_id = self.map_channel_id(epg_id)
            
            # If no direct match and fuzzy enabled, try fuzzy
            if not iptv_id and use_fuzzy:
                # Extract name from EPG ID for fuzzy matching
                name = self._extract_channel_name(epg_id)
                # Try to get country from EPG ID
                country = None
                if '.' in epg_id:
                    country = epg_id.split('@')[0].rsplit('.', 1)[-1]
                
                iptv_id = self.fuzzy_match_channel(name, country, threshold=0.8)
                if iptv_id:
                    fuzzy_matched += 1
            
            if iptv_id:
                mappings[epg_id] = iptv_id
                mapped += 1
            else:
                unmapped += 1
                if len(unmapped_list) < 20:
                    unmapped_list.append(epg_id)
        
        # Store mappings
        await self.cache.store_epg_mappings(mappings)
        
        return {
            'total_epg_channels': len(epg_channels),
            'mapped': mapped,
            'fuzzy_matched': fuzzy_matched,
            'unmapped': unmapped,
            'mapping_rate': f"{(mapped / len(epg_channels) * 100):.1f}%" if epg_channels else '0%',
            'sample_unmapped': unmapped_list[:10]
        }

