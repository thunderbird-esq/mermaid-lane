"""
M3U Parser Service.
Parses local M3U playlist files from iptv/streams/ folder.
"""
import re
from pathlib import Path
from typing import Optional
import logging
import hashlib

logger = logging.getLogger(__name__)

# Regex to parse EXTINF line
EXTINF_PATTERN = re.compile(
    r'#EXTINF:-?\d+\s*(?:tvg-id="([^"]*)")?[^,]*,(.+)'
)


class M3UParser:
    """Parse M3U playlist files."""
    
    def __init__(self, cache):
        self.cache = cache
    
    async def parse_file(self, filepath: str | Path) -> dict:
        """
        Parse a single M3U file and return stream entries.
        
        Args:
            filepath: Path to the M3U file
            
        Returns:
            Stats about the parsed data
        """
        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"M3U file not found: {filepath}")
        
        logger.info(f"Parsing M3U file: {filepath}")
        
        streams = []
        current_info = None
        
        # Determine country and provider from filename
        # e.g., "us.m3u" -> country=US, provider=None
        # e.g., "us_pluto.m3u" -> country=US, provider=pluto
        filename = filepath.stem
        parts = filename.split('_', 1)
        country = parts[0].upper() if parts else None
        provider = parts[1] if len(parts) > 1 else None
        
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                
                if line.startswith('#EXTINF:'):
                    # Parse the EXTINF line
                    match = EXTINF_PATTERN.match(line)
                    if match:
                        tvg_id = match.group(1) or ''
                        name = match.group(2).strip()
                        current_info = {
                            'tvg_id': tvg_id,
                            'name': name
                        }
                
                elif line and not line.startswith('#') and current_info:
                    # This is the URL line
                    url = line
                    
                    # Parse channel ID from tvg-id (format: ChannelName.country@Feed)
                    tvg_id = current_info['tvg_id']
                    channel_id = None
                    feed = None
                    
                    if tvg_id:
                        # Extract channel ID and feed from tvg_id
                        # Format: "ABC.us@East" or "ABC.us"
                        if '@' in tvg_id:
                            channel_id, feed = tvg_id.rsplit('@', 1)
                        else:
                            channel_id = tvg_id
                    
                    # Generate unique stream ID
                    unique_str = f"{url}{country}{provider or ''}"
                    stream_id = hashlib.md5(unique_str.encode()).hexdigest()[:12]
                    
                    # Extract quality hint from name
                    quality = self._extract_quality(current_info['name'])
                    
                    streams.append({
                        'id': stream_id,
                        'channel_id': channel_id,
                        'feed': feed,
                        'title': current_info['name'],
                        'url': url,
                        'quality': quality,
                        'country': country,
                        'provider': provider,
                        'source_file': filepath.name
                    })
                    
                    current_info = None
        
        logger.info(f"Parsed {len(streams)} streams from {filepath.name}")
        
        return {
            'streams': streams,
            'count': len(streams),
            'country': country,
            'provider': provider,
            'file': str(filepath)
        }
    
    def _extract_quality(self, name: str) -> Optional[str]:
        """Extract quality from stream name."""
        name_lower = name.lower()
        
        if '4k' in name_lower or '2160' in name_lower:
            return '4K'
        elif '1080' in name_lower:
            return '1080p'
        elif '720' in name_lower:
            return '720p'
        elif '480' in name_lower:
            return '480p'
        elif '360' in name_lower:
            return '360p'
        
        return None
    
    async def import_streams(self, streams: list[dict]):
        """Import parsed streams into the cache."""
        await self.cache.store_m3u_streams(streams)


async def import_m3u_directory(cache, streams_dir: str | Path, countries: list[str] = None) -> dict:
    """
    Import all M3U files from a directory.
    
    Args:
        cache: Cache service instance
        streams_dir: Directory containing M3U files
        countries: Optional list of country codes to import (e.g., ['us', 'uk'])
        
    Returns:
        Combined stats from all files
    """
    streams_dir = Path(streams_dir)
    parser = M3UParser(cache)
    
    total_streams = 0
    files_processed = 0
    all_streams = []
    
    # Find all M3U files
    m3u_files = sorted(streams_dir.glob('*.m3u'))
    
    for m3u_file in m3u_files:
        # Filter by country if specified
        if countries:
            country = m3u_file.stem.split('_')[0].lower()
            if country not in [c.lower() for c in countries]:
                continue
        
        try:
            result = await parser.parse_file(m3u_file)
            all_streams.extend(result['streams'])
            total_streams += result['count']
            files_processed += 1
        except Exception as e:
            logger.error(f"Failed to parse {m3u_file}: {e}")
    
    # Store all streams
    if all_streams:
        await parser.import_streams(all_streams)
    
    return {
        'files_processed': files_processed,
        'total_streams': total_streams
    }
