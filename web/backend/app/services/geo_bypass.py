"""
Geo-bypass service for circumventing geo-restrictions.

Level 1: Header Spoofing (X-Forwarded-For, Client-IP)
Level 2: Proxy Scavenging (free proxy lists for target countries)

Based on the "Scavenger Relay" architecture.
"""

import httpx
import random
import logging
from typing import Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


# Country-specific fake IP ranges (first octet patterns common in each region)
# These are for X-Forwarded-For header spoofing
COUNTRY_IP_RANGES = {
    "uk": [(2, 255), (5, 255), (31, 255), (51, 255), (82, 255), (86, 255)],
    "us": [(3, 255), (8, 255), (12, 255), (15, 255), (23, 255), (24, 255)],
    "de": [(5, 255), (46, 255), (77, 255), (78, 255), (79, 255), (80, 255)],
    "es": [(2, 255), (5, 255), (31, 255), (37, 255), (77, 255), (79, 255)],
    "br": [(138, 255), (143, 255), (152, 255), (177, 255), (179, 255), (186, 255)],
    "co": [(138, 255), (152, 255), (181, 255), (186, 255), (190, 255), (200, 255)],
    "fr": [(2, 255), (5, 255), (31, 255), (37, 255), (77, 255), (78, 255)],
}

# URL patterns that indicate specific geo-restrictions
GEO_PATTERNS = {
    "uk": [
        "bbc.co.uk", ".bbc.", "akamaized.net/x=4/i=urn:bbc",
        "ve-cmaf-push-uk", "vs-cmaf-push-uk"
    ],
    "es": [
        ".3catdirectes.cat", "rtve.es"
    ],
    "br": [
        "brasilstream", "playplus", "akamaihd.net/i/pp_"
    ],
    "co": [
        "cdnmedia.tv/canal", "cdnmedia.tv/cristo"
    ],
}


class GeoBypassService:
    """Service to bypass geo-restrictions using header spoofing and proxies."""
    
    CONNECT_TIMEOUT = 15.0
    READ_TIMEOUT = 30.0
    
    def __init__(self):
        self._proxy_cache = {}  # Country -> list of working proxies
        self._proxy_cache_time = {}
    
    def detect_country_from_url(self, url: str) -> Optional[str]:
        """
        Detect the likely target country from URL patterns.
        Returns country code (uk, us, etc.) or None.
        """
        url_lower = url.lower()
        
        for country, patterns in GEO_PATTERNS.items():
            for pattern in patterns:
                if pattern in url_lower:
                    logger.info(f"Detected geo-target: {country} for URL pattern {pattern}")
                    return country
        
        return None
    
    def generate_fake_ip(self, country: str) -> str:
        """
        Generate a plausible IP address for the target country.
        Used for X-Forwarded-For header spoofing.
        """
        ranges = COUNTRY_IP_RANGES.get(country.lower(), [(1, 200)])
        first_octet_range = random.choice(ranges)
        
        return f"{random.randint(*first_octet_range)}.{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}"
    
    def build_spoofed_headers(self, url: str, country: Optional[str] = None) -> dict:
        """
        Build headers with geo-spoofing for Level 1 bypass.
        """
        # Auto-detect country if not provided
        if not country:
            country = self.detect_country_from_url(url)
        
        fake_ip = self.generate_fake_ip(country or "us")
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "X-Forwarded-For": fake_ip,
            "Client-IP": fake_ip,
            "X-Real-IP": fake_ip,
            "Referer": url,
            "Origin": f"https://{urlparse(url).netloc}",
        }
        
        logger.debug(f"Built spoofed headers with IP {fake_ip} for country {country}")
        return headers
    
    async def fetch_with_bypass(
        self, 
        url: str, 
        original_headers: dict,
        target_country: Optional[str] = None,
        try_spoof: bool = True,
        try_proxy: bool = False  # Reserved for future proxy implementation
    ) -> httpx.Response:
        """
        Fetch a URL with geo-bypass techniques.
        
        Level 1: Try with spoofed headers first
        Level 2: (Future) Try with proxy if spoofing fails
        """
        # Detect country from URL if not specified
        if not target_country:
            target_country = self.detect_country_from_url(url)
        
        # Merge original headers with spoofed headers
        headers = {**original_headers}
        
        if try_spoof and target_country:
            spoofed = self.build_spoofed_headers(url, target_country)
            # Add spoofed headers but keep original User-Agent if specified
            headers.update({
                "X-Forwarded-For": spoofed["X-Forwarded-For"],
                "Client-IP": spoofed["Client-IP"],
                "X-Real-IP": spoofed["X-Real-IP"],
            })
            if not headers.get("Referer"):
                headers["Referer"] = spoofed["Referer"]
            if not headers.get("Origin"):
                headers["Origin"] = spoofed["Origin"]
        
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(self.CONNECT_TIMEOUT, read=self.READ_TIMEOUT),
            follow_redirects=True,
            verify=False  # Some streams have bad certs
        ) as client:
            response = await client.get(url, headers=headers)
            
            # Log bypass attempt result
            if response.status_code == 403:
                logger.warning(f"Geo-bypass Level 1 failed for {url[:50]}... (still 403)")
            elif response.status_code == 200:
                logger.info(f"Geo-bypass Level 1 success for {url[:50]}...")
            
            return response
    
    def is_geo_blocked_error(self, status_code: int, response_text: str = "") -> bool:
        """
        Check if an error response indicates geo-blocking.
        """
        if status_code == 403:
            return True
        if status_code == 451:  # Unavailable For Legal Reasons
            return True
        
        # Check for common geo-block messages in response
        geo_keywords = ["geo", "country", "region", "available in your", "not available"]
        for keyword in geo_keywords:
            if keyword.lower() in response_text.lower():
                return True
        
        return False


# Singleton
_geo_bypass_service = None


async def get_geo_bypass_service() -> GeoBypassService:
    """Get or create the geo-bypass service singleton."""
    global _geo_bypass_service
    if _geo_bypass_service is None:
        _geo_bypass_service = GeoBypassService()
    return _geo_bypass_service
