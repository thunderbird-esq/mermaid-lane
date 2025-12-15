"""
Background Health Worker Service

Continuously tests stream health in the background and updates the database.
Prioritizes unchecked streams, then cycles through all streams over time.
Saves snapshots after completing a full pass for faster startup.
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import httpx

from app.services.cache import get_cache
from app.config import get_settings

logger = logging.getLogger(__name__)


class HealthWorker:
    """Background worker that continuously tests stream health."""
    
    # Configuration
    BATCH_SIZE = 30  # Streams per batch
    BATCH_DELAY = 5  # Seconds between batches
    TEST_TIMEOUT = 8.0  # Per-stream timeout
    CONCURRENT_TESTS = 10  # Parallel tests per batch
    SNAPSHOT_FILENAME = "health_snapshot.json"
    
    def __init__(self):
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._full_pass_complete = False
        self._stats = {
            "total_tested": 0,
            "working": 0,
            "failed": 0,
            "started_at": None,
            "last_full_pass": None,
            "snapshot_loaded": False,
        }
        
        # Data directory for snapshots
        settings = get_settings()
        self._data_dir = Path(settings.database_path).parent
    
    async def start(self):
        """Start the background worker."""
        if self._running:
            logger.warning("Health worker already running")
            return
        
        # Try to load previous snapshot
        await self._load_snapshot()
        
        self._running = True
        self._stats["started_at"] = time.time()
        self._task = asyncio.create_task(self._worker_loop())
        logger.info("🏥 Health worker started")
    
    async def stop(self):
        """Stop the background worker."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        # Save snapshot on shutdown
        await self._save_snapshot()
        logger.info("Health worker stopped (snapshot saved)")
    
    def get_stats(self) -> dict:
        """Get worker statistics."""
        return {
            **self._stats,
            "running": self._running,
            "full_pass_complete": self._full_pass_complete,
            "uptime": time.time() - self._stats["started_at"] if self._stats["started_at"] else 0
        }
    
    async def _worker_loop(self):
        """Main worker loop."""
        logger.info("Health worker loop starting...")
        
        # Wait for initial data load
        await asyncio.sleep(10)
        
        while self._running:
            try:
                batch_processed = await self._process_batch()
                
                # If no streams needed checking, we've completed a full pass
                if not batch_processed and not self._full_pass_complete:
                    self._full_pass_complete = True
                    self._stats["last_full_pass"] = datetime.now().isoformat()
                    logger.info("✅ Full health pass complete - saving snapshot")
                    await self._save_snapshot()
                
                await asyncio.sleep(self.BATCH_DELAY)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health worker error: {e}")
                await asyncio.sleep(30)  # Back off on error
    
    async def _process_batch(self) -> bool:
        """Process a batch of streams. Returns True if streams were processed."""
        cache = await get_cache()
        
        # Get unchecked streams (prioritized)
        streams = await cache.get_unchecked_streams(limit=self.BATCH_SIZE)
        
        if not streams:
            # All streams checked recently
            return False
        
        logger.debug(f"Testing batch of {len(streams)} streams")
        
        # Test streams with concurrency limit
        semaphore = asyncio.Semaphore(self.CONCURRENT_TESTS)
        
        async def test_with_sem(stream):
            async with semaphore:
                return await self._test_stream(stream)
        
        results = await asyncio.gather(*[test_with_sem(s) for s in streams])
        
        # Update database
        for stream, result in zip(streams, results):
            # Calculate next check time based on status/error
            now = datetime.now()
            status = result["status"]
            error = result.get("error", "") or ""
            
            if status == "working":
                # Re-check working streams every 6 hours
                next_check = now + timedelta(hours=6)
            elif status == "warning":
                # Geo-blocked (403): Re-check weekly
                next_check = now + timedelta(days=7)
            elif "404" in error or "Not Found" in error:
                # Dead link: Re-check weekly
                next_check = now + timedelta(days=7)
            elif "Timeout" in error:
                # Timeout: Re-check in 1 hour
                next_check = now + timedelta(hours=1)
            elif "Connection refused" in error:
                # Offline: Re-check daily
                next_check = now + timedelta(days=1)
            else:
                # Default failure: Re-check in 1 hour
                next_check = now + timedelta(hours=1)

            await cache.update_stream_health(
                stream_id=stream["id"],
                status=result["status"],
                response_ms=result.get("response_ms"),
                error=result.get("error"),
                next_check_due=next_check.isoformat() if next_check else None
            )
            
            self._stats["total_tested"] += 1
            if result["status"] == "working":
                self._stats["working"] += 1
            elif result["status"] == "failed":
                self._stats["failed"] += 1
        
        working = sum(1 for r in results if r["status"] == "working")
        logger.info(f"Batch complete: {working}/{len(streams)} working")
        return True
    
    async def _save_snapshot(self):
        """Save current health data to a snapshot file."""
        try:
            cache = await get_cache()
            health_stats = await cache.get_health_stats()
            
            # Get all streams with health data
            streams = await cache.get_streams_by_health()
            
            snapshot = {
                "timestamp": datetime.now().isoformat(),
                "stats": self._stats.copy(),
                "health_summary": health_stats,
                "streams": [
                    {
                        "id": s["id"],
                        "channel_id": s["channel_id"],
                        "health_status": s["health_status"],
                        "health_response_ms": s["health_response_ms"],
                    }
                    for s in streams
                    if s.get("health_status") and s["health_status"] != "unknown"
                ]
            }
            
            snapshot_path = self._data_dir / self.SNAPSHOT_FILENAME
            with open(snapshot_path, "w") as f:
                json.dump(snapshot, f, indent=2, default=str)
            
            logger.info(f"📸 Health snapshot saved: {len(snapshot['streams'])} streams to {snapshot_path}")
            
        except Exception as e:
            logger.error(f"Failed to save health snapshot: {e}")
    
    async def _load_snapshot(self):
        """Load health data from a previous snapshot."""
        snapshot_path = self._data_dir / self.SNAPSHOT_FILENAME
        
        if not snapshot_path.exists():
            logger.info("No health snapshot found - will test all streams")
            return
        
        try:
            with open(snapshot_path, "r") as f:
                snapshot = json.load(f)
            
            cache = await get_cache()
            loaded_count = 0
            
            for stream_data in snapshot.get("streams", []):
                await cache.update_stream_health(
                    stream_id=stream_data["id"],
                    status=stream_data["health_status"],
                    response_ms=stream_data.get("health_response_ms")
                )
                loaded_count += 1
            
            self._stats["snapshot_loaded"] = True
            logger.info(f"📥 Loaded health snapshot: {loaded_count} streams from {snapshot.get('timestamp', 'unknown')}")
            
        except Exception as e:
            logger.warning(f"Failed to load health snapshot: {e}")
    
    async def _test_stream(self, stream: dict) -> dict:
        """Test a single stream and return result."""
        url = stream["url"]
        start_time = time.time()
        
        headers = {
            "User-Agent": stream.get("user_agent") or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        if stream.get("referrer"):
            headers["Referer"] = stream["referrer"]
        
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(self.TEST_TIMEOUT),
                follow_redirects=True,
                verify=False
            ) as client:
                # Try HEAD first
                response = await client.head(url, headers=headers)
                
                # Some servers don't support HEAD
                if response.status_code == 405:
                    response = await client.get(
                        url, 
                        headers={**headers, "Range": "bytes=0-0"}
                    )
                
                elapsed_ms = int((time.time() - start_time) * 1000)
                
                if response.status_code in [200, 206]:
                    return {
                        "status": "working",
                        "response_ms": elapsed_ms
                    }
                elif response.status_code == 403:
                    return {
                        "status": "warning",  # May be geo-blocked, but server is alive
                        "response_ms": elapsed_ms,
                        "error": "403 Forbidden (possible geo-block)"
                    }
                elif response.status_code == 404:
                    return {
                        "status": "failed",
                        "error": "404 Not Found"
                    }
                else:
                    return {
                        "status": "failed",
                        "error": f"HTTP {response.status_code}"
                    }
                    
        except httpx.TimeoutException:
            return {
                "status": "failed",
                "error": "Timeout"
            }
        except httpx.ConnectError:
            return {
                "status": "failed",
                "error": "Connection refused"
            }
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e)[:100]
            }


# Singleton
_health_worker: Optional[HealthWorker] = None


def get_health_worker() -> HealthWorker:
    """Get or create health worker singleton."""
    global _health_worker
    if _health_worker is None:
        _health_worker = HealthWorker()
    return _health_worker

