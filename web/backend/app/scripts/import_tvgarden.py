"""
Script to import channels and streams from the local 'tv-garden-channel-list' directory.
"""
import json
import asyncio
import os
import sys
from pathlib import Path

# Add backend directory to path to import app modules
backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(backend_dir))

from app.services.cache import get_cache


DATA_DIR = Path("/Users/edsaga/claudes-world/mermaid-lane/tv-garden-channel-list/channels/raw/countries")

async def import_tv_garden_data():
    print(f"Importing data from {DATA_DIR}...")
    
    if not DATA_DIR.exists():
        print(f"Error: Directory {DATA_DIR} not found.")
        return

    cache = await get_cache()
    
    total_channels = 0
    total_streams = 0
    
    files = list(DATA_DIR.glob("*.json"))
    print(f"Found {len(files)} country files.")

    all_channels = []
    all_streams = []

    for file_path in files:
        try:
            content = file_path.read_text(encoding='utf-8')
            channels = json.loads(content)
            
            for item in channels:
                # Map Channel
                channel_id = item.get("nanoid")
                if not channel_id:
                    continue

                channel = {
                    "id": channel_id,
                    "name": item.get("name"),
                    "country": item.get("country", "").upper(),
                    "is_nsfw": False, # tv.garden seems safe
                    "languages": [item.get("language")] if item.get("language") else [],
                    "categories": [] # We don't have categories in this file, maybe load from metadata later
                }
                all_channels.append(channel)
                total_channels += 1

                # Map Streams (IPTV)
                for i, url in enumerate(item.get("iptv_urls", [])):
                    if not url: continue
                    stream = {
                        "channel": channel_id,
                        "title": "Stream (HLS)",
                        "url": url,
                        "stream_id": f"{channel_id}_hls_{i}"
                    }
                    all_streams.append(stream)
                    total_streams += 1

                # Map Streams (YouTube)
                for i, url in enumerate(item.get("youtube_urls", [])):
                    if not url: continue
                    # Convert embed URL to watch URL if needed, or keep as is?
                    # Player.js detects 'youtube.com' and sets type='video/youtube'.
                    # Video.js YouTube tech handles standard watch URLs best.
                    # Embed: https://www.youtube-nocookie.com/embed/VIDEO_ID
                    # Watch: https://www.youtube.com/watch?v=VIDEO_ID
                    
                    if "embed/" in url:
                        vid_id = url.split("embed/")[-1].split("?")[0]
                        watch_url = f"https://www.youtube.com/watch?v={vid_id}"
                    else:
                        watch_url = url

                    stream = {
                        "channel": channel_id,
                        "title": "Stream (YouTube)",
                        "url": watch_url,
                        "stream_id": f"{channel_id}_yt_{i}"
                    }
                    all_streams.append(stream)
                    total_streams += 1

        except Exception as e:
            print(f"Error processing {file_path.name}: {e}")

    print(f"Processed {total_channels} channels and {total_streams} streams.")
    
    # Deduplicate channels
    unique_channels = []
    seen_ids = set()
    for ch in all_channels:
        if ch['id'] not in seen_ids:
            unique_channels.append(ch)
            seen_ids.add(ch['id'])
    
    # Batch Store
    print(f"Storing {len(unique_channels)} unique channels and {len(all_streams)} streams in database...")
    await cache.store_channels(unique_channels)
    await cache.store_streams(all_streams)
    
    # Store logo metadata if available?
    # tv.garden data doesn't seem to have logos in the country files?
    # Checked `us.json` output above - no "logo" field.
    # We might lose logos if we overwrite. 
    # But user wants parity with tv.garden reliability.
    
    print("Import complete.")

if __name__ == "__main__":
    asyncio.run(import_tv_garden_data())
