#!/usr/bin/env python3
"""
Stream Health Audit Script

Tests a sample of streams from the database and categorizes them by:
- Working (200)
- Geo-blocked (403)
- Dead/Removed (404)
- Server Error (5xx)
- Timeout (unreachable)
- SSL Error

Usage:
    cd web/backend
    source venv/bin/activate
    python -m app.scripts.stream_audit --sample 100

Output:
    data/stream_audit_YYYYMMDD_HHMMSS.json
"""

import asyncio
import argparse
import json
import logging
import ssl
from datetime import datetime
from pathlib import Path
import sys

import httpx

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.cache import get_cache

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Failure categories
CATEGORIES = {
    "working": "✅ Working",
    "geo_blocked": "🔒 Geo-blocked (403)",
    "not_found": "❌ Dead link (404)",
    "server_error": "⚠️ Server error (5xx)",
    "timeout": "⏱️ Timeout",
    "ssl_error": "🔐 SSL/TLS error",
    "connection_error": "🔌 Connection refused",
    "redirect_loop": "🔄 Redirect loop",
    "unknown": "❓ Unknown error",
}


async def test_stream(url: str, timeout: float = 10.0) -> dict:
    """
    Test a single stream URL and return diagnostic info.
    """
    result = {
        "url": url,
        "status_code": None,
        "category": "unknown",
        "response_time_ms": None,
        "content_type": None,
        "error": None,
        "headers": {},
    }
    
    start_time = asyncio.get_event_loop().time()
    
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            follow_redirects=True,
            verify=False,  # Some streams have bad certs
        ) as client:
            # HEAD request is faster than GET for testing
            response = await client.head(url)
            
            elapsed = (asyncio.get_event_loop().time() - start_time) * 1000
            result["response_time_ms"] = round(elapsed, 2)
            result["status_code"] = response.status_code
            result["content_type"] = response.headers.get("content-type", "")
            result["headers"] = dict(response.headers)
            
            # Categorize by status code
            if response.status_code == 200:
                result["category"] = "working"
            elif response.status_code == 403:
                result["category"] = "geo_blocked"
            elif response.status_code == 404:
                result["category"] = "not_found"
            elif response.status_code == 451:
                # Unavailable For Legal Reasons
                result["category"] = "geo_blocked"
            elif 500 <= response.status_code < 600:
                result["category"] = "server_error"
            elif 300 <= response.status_code < 400:
                result["category"] = "redirect_loop"
            else:
                result["category"] = "unknown"
                result["error"] = f"Unexpected status: {response.status_code}"
                
    except httpx.TimeoutException:
        result["category"] = "timeout"
        result["error"] = "Request timed out"
        
    except ssl.SSLError as e:
        result["category"] = "ssl_error"
        result["error"] = str(e)
        
    except httpx.ConnectError as e:
        result["category"] = "connection_error"
        result["error"] = str(e)
        
    except Exception as e:
        result["category"] = "unknown"
        result["error"] = f"{type(e).__name__}: {str(e)}"
    
    return result


async def get_sample_streams(sample_size: int) -> list:
    """
    Get a random sample of streams from the database.
    """
    import aiosqlite
    from app.config import get_settings
    
    settings = get_settings()
    db_path = settings.database_path
    
    streams = []
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute(
            "SELECT id, url, channel_id FROM streams ORDER BY RANDOM() LIMIT ?",
            (sample_size,)
        )
        rows = await cursor.fetchall()
        
        for row in rows:
            streams.append({
                "id": row[0],
                "url": row[1],
                "channel": row[2],
            })
    
    return streams


async def run_audit(sample_size: int, concurrency: int = 10) -> dict:
    """
    Run the stream health audit.
    """
    logger.info(f"Starting audit with sample size: {sample_size}")
    
    # Get sample streams
    streams = await get_sample_streams(sample_size)
    logger.info(f"Retrieved {len(streams)} streams for testing")
    
    if not streams:
        logger.error("No streams found in database!")
        return {}
    
    # Test streams with concurrency limit
    semaphore = asyncio.Semaphore(concurrency)
    
    async def test_with_semaphore(stream):
        async with semaphore:
            result = await test_stream(stream["url"])
            result["stream_id"] = stream["id"]
            result["channel"] = stream["channel"]
            return result
    
    # Run all tests
    logger.info(f"Testing {len(streams)} streams (concurrency: {concurrency})...")
    tasks = [test_with_semaphore(s) for s in streams]
    results = await asyncio.gather(*tasks)
    
    # Summarize results
    summary = {cat: 0 for cat in CATEGORIES.keys()}
    for r in results:
        summary[r["category"]] = summary.get(r["category"], 0) + 1
    
    # Build report
    report = {
        "timestamp": datetime.now().isoformat(),
        "sample_size": len(streams),
        "concurrency": concurrency,
        "summary": summary,
        "summary_labels": {k: f"{CATEGORIES[k]}: {v}" for k, v in summary.items()},
        "percentages": {k: round(v / len(streams) * 100, 1) for k, v in summary.items()},
        "results": results,
    }
    
    return report


def print_summary(report: dict):
    """
    Print a human-readable summary of the audit.
    """
    print("\n" + "=" * 60)
    print("STREAM HEALTH AUDIT RESULTS")
    print("=" * 60)
    print(f"Tested: {report['sample_size']} streams")
    print(f"Time: {report['timestamp']}")
    print("-" * 60)
    
    for category, count in report["summary"].items():
        pct = report["percentages"][category]
        label = CATEGORIES[category]
        bar = "█" * int(pct / 2)
        print(f"{label:30} {count:5} ({pct:5.1f}%) {bar}")
    
    print("-" * 60)
    
    # Top issues
    if report["summary"].get("geo_blocked", 0) > 0:
        print("\n🔒 GEO-BLOCKED STREAMS (sample):")
        geo_blocked = [r for r in report["results"] if r["category"] == "geo_blocked"][:5]
        for r in geo_blocked:
            print(f"   - {r['channel']}: {r['url'][:60]}...")
    
    if report["summary"].get("timeout", 0) > 0:
        print("\n⏱️ TIMEOUT STREAMS (sample):")
        timeouts = [r for r in report["results"] if r["category"] == "timeout"][:5]
        for r in timeouts:
            print(f"   - {r['channel']}: {r['url'][:60]}...")
    
    print("\n" + "=" * 60)


async def main():
    parser = argparse.ArgumentParser(description="Stream Health Audit")
    parser.add_argument(
        "--sample", "-s",
        type=int,
        default=100,
        help="Number of streams to test (default: 100)"
    )
    parser.add_argument(
        "--concurrency", "-c",
        type=int,
        default=10,
        help="Concurrent requests (default: 10)"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="Output file path (default: data/stream_audit_TIMESTAMP.json)"
    )
    
    args = parser.parse_args()
    
    # Run audit
    report = await run_audit(args.sample, args.concurrency)
    
    if not report:
        print("Audit failed - no results")
        return
    
    # Print summary
    print_summary(report)
    
    # Save report
    output_path = args.output or f"data/stream_audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    
    print(f"\n📄 Full report saved to: {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
