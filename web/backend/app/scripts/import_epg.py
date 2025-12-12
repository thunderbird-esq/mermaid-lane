"""
Batch EPG Import Script.
Imports all EPG XML files and runs channel mapping.
"""
import asyncio
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.cache import get_cache
from app.services.epg_parser import EPGParser
from app.services.epg_mapping import EPGMapper


async def import_all_epg():
    """Import all EPG files in the data directory and run mapping."""
    data_dir = Path(__file__).parent.parent / "data"
    
    cache = await get_cache()
    parser = EPGParser(cache)
    
    epg_files = list(data_dir.glob("*_guide.xml"))
    
    if not epg_files:
        print(f"No EPG files found in {data_dir}")
        return
    
    print(f"Found {len(epg_files)} EPG files:")
    for f in epg_files:
        print(f"  - {f.name}")
    
    total_programs = 0
    total_channels = 0
    
    for epg_file in epg_files:
        print(f"\n📺 Importing {epg_file.name}...")
        try:
            stats = await parser.parse_file(epg_file)
            print(f"   ✅ Imported {stats['programs']} programs from {stats['channels']} channels")
            total_programs += stats['programs']
            total_channels += stats['channels']
        except Exception as e:
            print(f"   ❌ Failed: {e}")
    
    print(f"\n📊 Total: {total_programs} programs from {total_channels} channels")
    
    # Run mapping
    print("\n🔗 Running EPG channel mapping...")
    mapper = EPGMapper(cache)
    try:
        mapping_stats = await mapper.batch_map_epg_channels()
        print(f"   Mapped: {mapping_stats['mapped']}/{mapping_stats['total_epg_channels']} ({mapping_stats['mapping_rate']})")
    except Exception as e:
        print(f"   ❌ Mapping failed: {e}")
    
    # Final stats
    epg_stats = await cache.get_epg_stats()
    print(f"\n✅ Final: {epg_stats['total_programs']} programs for {epg_stats['channels_with_epg']} channels")


if __name__ == "__main__":
    asyncio.run(import_all_epg())
