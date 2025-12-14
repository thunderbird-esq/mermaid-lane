"""
Background Health Worker Service

Continuously tests stream health in the background and updates the database.
Prioritizes unchecked streams, then cycles through all streams over time.
"""

import asyncio
import logging
import time
from typing import Optional

import httpx

from app.services.cache import get_cache

logger = logging.getLogger(__name__)


class HealthWorker:
    """Background worker that continuously tests stream health."""
    
    # Configuration
    BATCH_SIZE = 30  # Streams per batch
    BATCH_DELAY = 5  # Seconds between batches
    TEST_TIMEOUT = 8.0  # Per-stream timeout
    CONCURRENT_TESTS = 10  # Parallel tests per batch
    
    def __init__(self):
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._stats = {
            "total_tested": 0,
            "working": 0,
            "failed": 0,
            "started_at": None,
        }
    
    async def start(self):
        """Start the background worker."""
        if self._running:
            logger.warning("Health worker already running")
            return
        
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
        logger.info("Health worker stopped")
    
    def get_stats(self) -> dict:
        """Get worker statistics."""
        return {
            **self._stats,
            "running": self._running,
            "uptime": time.time() - self._stats["started_at"] if self._stats["started_at"] else 0
        }
    
    async def _worker_loop(self):
        """Main worker loop."""
        logger.info("Health worker loop starting...")
        
        # Wait for initial data load
        await asyncio.sleep(10)
        
        while self._running:
            try:
                await self._process_batch()
                await asyncio.sleep(self.BATCH_DELAY)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health worker error: {e}")
                await asyncio.sleep(30)  # Back off on error
    
    async def _process_batch(self):
        """Process a batch of streams."""
        cache = await get_cache()
        
        # Get unchecked streams (prioritized)
        streams = await cache.get_unchecked_streams(limit=self.BATCH_SIZE)
        
        if not streams:
            # All streams checked recently, wait longer
            await asyncio.sleep(60)
            return
        
        logger.debug(f"Testing batch of {len(streams)} streams")
        
        # Test streams with concurrency limit
        semaphore = asyncio.Semaphore(self.CONCURRENT_TESTS)
        
        async def test_with_sem(stream):
            async with semaphore:
                return await self._test_stream(stream)
        
        results = await asyncio.gather(*[test_with_sem(s) for s in streams])
        
        # Update database
        for stream, result in zip(streams, results):
            await cache.update_stream_health(
                stream_id=stream["id"],
                status=result["status"],
                response_ms=result.get("response_ms"),
                error=result.get("error")
            )
            
            self._stats["total_tested"] += 1
            if result["status"] == "working":
                self._stats["working"] += 1
            elif result["status"] == "failed":
                self._stats["failed"] += 1
        
        working = sum(1 for r in results if r["status"] == "working")
        logger.info(f"Batch complete: {working}/{len(streams)} working")
    
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
