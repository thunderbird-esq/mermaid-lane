"""
EPG Parser Service.
Parses XMLTV format EPG files and stores programs in the cache.
"""
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
import logging
from typing import Optional
import hashlib

logger = logging.getLogger(__name__)


class EPGParser:
    """Parse XMLTV format EPG data."""
    
    def __init__(self, cache):
        self.cache = cache
    
    async def parse_file(self, filepath: str | Path) -> dict:
        """
        Parse an XMLTV file and store programs in cache.
        
        Args:
            filepath: Path to the XMLTV file
            
        Returns:
            Stats about the parsed data
        """
        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"EPG file not found: {filepath}")
        
        logger.info(f"Parsing EPG file: {filepath}")
        
        # Parse XML
        tree = ET.parse(filepath)
        root = tree.getroot()
        
        # Extract channels and programs
        channels = {}
        programs = []
        
        # Parse channel definitions
        for channel_elem in root.findall('channel'):
            channel_id = channel_elem.get('id')
            display_name = channel_elem.find('display-name')
            
            if channel_id and display_name is not None:
                channels[channel_id] = {
                    'id': channel_id,
                    'name': display_name.text,
                    'url': channel_elem.find('url').text if channel_elem.find('url') is not None else None
                }
        
        # Parse programs
        for programme in root.findall('programme'):
            channel_id = programme.get('channel')
            start = programme.get('start')
            stop = programme.get('stop')
            
            if not all([channel_id, start, stop]):
                continue
            
            # Parse title and description
            title_elem = programme.find('title')
            desc_elem = programme.find('desc')
            sub_title_elem = programme.find('sub-title')
            category_elem = programme.find('category')
            icon_elem = programme.find('icon')
            
            title = title_elem.text if title_elem is not None else 'Unknown'
            description = desc_elem.text if desc_elem is not None else None
            sub_title = sub_title_elem.text if sub_title_elem is not None else None
            category = category_elem.text if category_elem is not None else None
            icon = icon_elem.get('src') if icon_elem is not None else None
            
            # Parse dates (XMLTV format: 20251212040000 +0000)
            try:
                start_dt = self._parse_xmltv_date(start)
                stop_dt = self._parse_xmltv_date(stop)
            except ValueError as e:
                logger.warning(f"Failed to parse date: {e}")
                continue
            
            # Generate unique program ID
            program_id = hashlib.md5(
                f"{channel_id}{start}{title}".encode()
            ).hexdigest()[:16]
            
            programs.append({
                'id': program_id,
                'channel_id': channel_id,
                'title': title,
                'description': description,
                'sub_title': sub_title,
                'category': category,
                'start': start_dt.isoformat(),
                'stop': stop_dt.isoformat(),
                'icon': icon
            })
        
        logger.info(f"Parsed {len(channels)} channels and {len(programs)} programs")
        
        # Store in cache
        await self.cache.store_epg_programs(programs)
        
        return {
            'channels': len(channels),
            'programs': len(programs),
            'file': str(filepath)
        }
    
    def _parse_xmltv_date(self, date_str: str) -> datetime:
        """
        Parse XMLTV date format.
        Format: 20251212040000 +0000 or 20251212040000
        """
        # Remove timezone part for simplicity
        date_str = date_str.split()[0]
        
        # Parse the date
        return datetime.strptime(date_str, '%Y%m%d%H%M%S')


async def import_epg_files(cache, data_dir: str | Path) -> dict:
    """
    Import all EPG files from a directory.
    
    Args:
        cache: Cache service instance
        data_dir: Directory containing XMLTV files
        
    Returns:
        Combined stats from all files
    """
    data_dir = Path(data_dir)
    parser = EPGParser(cache)
    
    total_channels = 0
    total_programs = 0
    files_processed = 0
    
    # Find all XML files
    for xml_file in data_dir.glob('*_guide.xml'):
        try:
            stats = await parser.parse_file(xml_file)
            total_channels += stats['channels']
            total_programs += stats['programs']
            files_processed += 1
        except Exception as e:
            logger.error(f"Failed to parse {xml_file}: {e}")
    
    return {
        'files_processed': files_processed,
        'total_channels': total_channels,
        'total_programs': total_programs
    }
