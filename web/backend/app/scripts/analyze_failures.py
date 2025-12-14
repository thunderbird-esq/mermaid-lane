"""
Failure Analysis Script

Analyzes failed and warning streams from the health check,
categorizes them by error type, and generates a detailed report.

Usage:
    python -m app.scripts.analyze_failures
    python -m app.scripts.analyze_failures --export
"""

import asyncio
import json
import argparse
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import aiosqlite

from app.config import get_settings


async def get_failed_streams() -> list[dict]:
    """Get all failed and warning streams from database."""
    settings = get_settings()
    
    async with aiosqlite.connect(settings.database_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT 
                s.id, s.channel_id, s.url, s.quality,
                s.health_status, s.health_error, s.health_response_ms,
                c.name as channel_name, c.country
            FROM streams s
            LEFT JOIN channels c ON s.channel_id = c.id
            WHERE s.health_status IN ('failed', 'warning')
            ORDER BY s.health_status, s.health_error
        """)
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


def categorize_by_error(streams: list[dict]) -> dict:
    """Categorize streams by error type."""
    categories = defaultdict(list)
    
    for stream in streams:
        error = stream.get('health_error') or 'Unknown'
        
        # Normalize error types
        if '404' in error:
            category = 'dead_404'
        elif '403' in error or 'Forbidden' in error:
            category = 'geo_blocked_403'
        elif 'Timeout' in error:
            category = 'timeout'
        elif 'Connection refused' in error:
            category = 'connection_refused'
        elif '5' in error[:1] if error else False:  # 5xx errors
            category = 'server_error_5xx'
        elif '400' in error or 'Bad Request' in error:
            category = 'bad_request_400'
        elif '302' in error or '307' in error:
            category = 'redirect_not_followed'
        else:
            category = 'other'
        
        categories[category].append(stream)
    
    return dict(categories)


def categorize_by_country(streams: list[dict]) -> dict:
    """Categorize streams by country."""
    countries = defaultdict(list)
    
    for stream in streams:
        country = stream.get('country') or 'Unknown'
        countries[country].append(stream)
    
    # Sort by count
    return dict(sorted(countries.items(), key=lambda x: -len(x[1])))


def categorize_by_domain(streams: list[dict]) -> dict:
    """Categorize streams by domain/CDN."""
    domains = defaultdict(list)
    
    for stream in streams:
        url = stream.get('url', '')
        try:
            parsed = urlparse(url)
            domain = parsed.netloc
            # Simplify to base domain
            parts = domain.split('.')
            if len(parts) >= 2:
                domain = '.'.join(parts[-2:])
        except:
            domain = 'Unknown'
        
        domains[domain].append(stream)
    
    # Sort by count, filter to domains with 3+ failures
    filtered = {k: v for k, v in domains.items() if len(v) >= 3}
    return dict(sorted(filtered.items(), key=lambda x: -len(x[1])))


def generate_report(streams: list[dict], by_error: dict, by_country: dict, by_domain: dict) -> str:
    """Generate human-readable report."""
    lines = []
    lines.append("=" * 60)
    lines.append("STREAM FAILURE ANALYSIS REPORT")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 60)
    lines.append("")
    
    # Summary
    failed = sum(1 for s in streams if s['health_status'] == 'failed')
    warning = sum(1 for s in streams if s['health_status'] == 'warning')
    lines.append(f"Total problematic streams: {len(streams)}")
    lines.append(f"  - Failed: {failed}")
    lines.append(f"  - Warning (geo-blocked): {warning}")
    lines.append("")
    
    # By Error Type
    lines.append("-" * 60)
    lines.append("BY ERROR TYPE")
    lines.append("-" * 60)
    for category, items in sorted(by_error.items(), key=lambda x: -len(x[1])):
        pct = len(items) / len(streams) * 100
        lines.append(f"  {category}: {len(items)} ({pct:.1f}%)")
    lines.append("")
    
    # By Country (top 15)
    lines.append("-" * 60)
    lines.append("BY COUNTRY (top 15)")
    lines.append("-" * 60)
    for i, (country, items) in enumerate(list(by_country.items())[:15]):
        lines.append(f"  {country}: {len(items)} streams")
    lines.append("")
    
    # By Domain (3+ failures)
    lines.append("-" * 60)
    lines.append("BY DOMAIN/CDN (3+ failures)")
    lines.append("-" * 60)
    for domain, items in list(by_domain.items())[:20]:
        lines.append(f"  {domain}: {len(items)} streams")
    lines.append("")
    
    # Sample failures per category
    lines.append("-" * 60)
    lines.append("SAMPLE FAILURES PER CATEGORY")
    lines.append("-" * 60)
    for category, items in sorted(by_error.items(), key=lambda x: -len(x[1])):
        lines.append(f"\n{category.upper()} ({len(items)} total):")
        for item in items[:5]:
            name = item.get('channel_name') or 'Unknown'
            url = item.get('url', '')[:60] + '...' if len(item.get('url', '')) > 60 else item.get('url', '')
            lines.append(f"  - {name}: {url}")
    
    lines.append("")
    lines.append("=" * 60)
    
    return "\n".join(lines)


async def main():
    parser = argparse.ArgumentParser(description='Analyze failed streams')
    parser.add_argument('--export', action='store_true', help='Export to JSON files')
    args = parser.parse_args()
    
    print("Fetching failed streams from database...")
    streams = await get_failed_streams()
    
    if not streams:
        print("No failed or warning streams found!")
        return
    
    print(f"Found {len(streams)} problematic streams")
    
    # Categorize
    by_error = categorize_by_error(streams)
    by_country = categorize_by_country(streams)
    by_domain = categorize_by_domain(streams)
    
    # Generate report
    report = generate_report(streams, by_error, by_country, by_domain)
    print(report)
    
    # Export if requested
    if args.export:
        settings = get_settings()
        data_dir = Path(settings.database_path).parent
        
        # Export full data
        export_path = data_dir / "failed_streams.json"
        export_data = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total": len(streams),
                "failed": sum(1 for s in streams if s['health_status'] == 'failed'),
                "warning": sum(1 for s in streams if s['health_status'] == 'warning'),
            },
            "by_error_type": {k: len(v) for k, v in by_error.items()},
            "by_country": {k: len(v) for k, v in list(by_country.items())[:20]},
            "by_domain": {k: len(v) for k, v in list(by_domain.items())[:20]},
            "streams": streams
        }
        
        with open(export_path, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        print(f"\n📄 Exported to: {export_path}")
        
        # Export report
        report_path = data_dir / "failure_report.txt"
        with open(report_path, 'w') as f:
            f.write(report)
        
        print(f"📄 Report saved to: {report_path}")


if __name__ == "__main__":
    asyncio.run(main())
