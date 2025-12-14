
import asyncio
import logging
import os
import shutil
import signal
from pathlib import Path
from typing import Optional, Dict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class TranscoderService:
    """
    Manages FFmpeg processes to transcode/remux non-HLS streams (e.g., DASH) 
    into local HLS playlists.
    """
    
    # Directory to store HLS segments
    TRANSCODE_DIR = Path("data/hls_transcodes")
    
    def __init__(self):
        # Maps stream_id -> subprocess object
        self._processes: Dict[str, asyncio.subprocess.Process] = {}
        # Maps stream_id -> last access timestamp
        self._last_access: Dict[str, datetime] = {}
        
        # Ensure base directory exists
        if not self.TRANSCODE_DIR.exists():
            self.TRANSCODE_DIR.mkdir(parents=True, exist_ok=True)
            
    async def start_transcode(self, stream_id: str, input_url: str) -> bool:
        """
        Start FFmpeg transcoding for a stream.
        Returns True if started (or already running), False on failure.
        """
        if stream_id in self._processes:
            process = self._processes[stream_id]
            if process.returncode is None:
                self._last_access[stream_id] = datetime.now()
                return True
            else:
                # Process died, cleanup and restart
                await self.stop_transcode(stream_id)
        
        # Create stream specific directory
        stream_dir = self.TRANSCODE_DIR / stream_id
        if stream_dir.exists():
            shutil.rmtree(stream_dir)
        stream_dir.mkdir(parents=True, exist_ok=True)
        
        playlist_path = stream_dir / "index.m3u8"
        segment_pattern = stream_dir / "segment_%03d.ts"
        
        # Build FFmpeg command
        # -c copy: Remux only (low CPU), assumes codecs are compatible (usually true for DASH->HLS)
        # -hls_time 4: 4 second segments
        # -hls_list_size 5: Keep 5 segments in playlist
        # -hls_flags delete_segments: Cleanup old segments
        cmd = [
            "ffmpeg",
            "-i", input_url,
            "-c:v", "copy",
            "-c:a", "copy",
            "-f", "hls",
            "-hls_time", "4",
            "-hls_list_size", "5",
            "-hls_flags", "delete_segments",
            "-hls_segment_filename", str(segment_pattern),
            str(playlist_path)
        ]
        
        logger.info(f"Starting transcoder for {stream_id}: {' '.join(cmd)}")
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            self._processes[stream_id] = process
            self._last_access[stream_id] = datetime.now()
            return True
        except Exception as e:
            logger.error(f"Failed to start transcoder: {e}")
            return False

    async def stop_transcode(self, stream_id: str):
        """Stop and cleanup transcode process."""
        if stream_id in self._processes:
            proc = self._processes[stream_id]
            if proc.returncode is None:
                try:
                    proc.send_signal(signal.SIGTERM)
                    try:
                        await asyncio.wait_for(proc.wait(), timeout=2.0)
                    except asyncio.TimeoutError:
                        proc.kill()
                except Exception as e:
                    logger.error(f"Error stopping process {stream_id}: {e}")
            
            del self._processes[stream_id]
            
        if stream_id in self._last_access:
            del self._last_access[stream_id]
            
        # Cleanup files
        stream_dir = self.TRANSCODE_DIR / stream_id
        if stream_dir.exists():
            try:
                shutil.rmtree(stream_dir)
            except Exception as e:
                logger.error(f"Error cleaning up dir {stream_dir}: {e}")

    async def get_manifest_path(self, stream_id: str) -> Optional[Path]:
        """Get path to the manifest if it exists."""
        self._last_access[stream_id] = datetime.now()
        path = self.TRANSCODE_DIR / stream_id / "index.m3u8"
        return path if path.exists() else None

    async def is_ready(self, stream_id: str) -> bool:
        """Check if playlist is generated."""
        path = await self.get_manifest_path(stream_id)
        return path is not None and path.exists()
    
    async def cleanup_stale_transcodes(self, max_age_minutes: int = 5) -> int:
        """
        Clean up transcodes that haven't been accessed recently.
        Returns number of transcodes cleaned up.
        """
        cleaned = 0
        cutoff = datetime.now() - timedelta(minutes=max_age_minutes)
        
        # Check all tracked transcodes
        stale_ids = [
            stream_id for stream_id, last_access in self._last_access.items()
            if last_access < cutoff
        ]
        
        for stream_id in stale_ids:
            logger.info(f"Cleaning up stale transcode: {stream_id}")
            await self.stop_transcode(stream_id)
            cleaned += 1
        
        # Also clean up orphaned directories (not in our tracking)
        if self.TRANSCODE_DIR.exists():
            for stream_dir in self.TRANSCODE_DIR.iterdir():
                if stream_dir.is_dir() and stream_dir.name not in self._processes:
                    try:
                        shutil.rmtree(stream_dir)
                        cleaned += 1
                        logger.info(f"Cleaned orphaned transcode dir: {stream_dir.name}")
                    except Exception as e:
                        logger.error(f"Error cleaning orphaned dir {stream_dir}: {e}")
        
        return cleaned

# Singleton
_transocoder_service: Optional[TranscoderService] = None

def get_transcoder_service() -> TranscoderService:
    global _transocoder_service
    if _transocoder_service is None:
        _transocoder_service = TranscoderService()
    return _transocoder_service
