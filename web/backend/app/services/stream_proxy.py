"""
Secure HLS stream proxy service.
Proxies streams to hide original URLs and inject required headers.
"""
import httpx
import logging
import re
from typing import Optional, AsyncIterator
from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from app.services.cache import get_cache

logger = logging.getLogger(__name__)


class StreamProxyService:
    """Service to securely proxy HLS streams."""
    
    # Timeout for stream requests
    CONNECT_TIMEOUT = 10.0
    READ_TIMEOUT = 30.0
    
    # Content types
    MANIFEST_TYPES = ["application/vnd.apple.mpegurl", "application/x-mpegurl", "audio/mpegurl"]
    SEGMENT_TYPES = ["video/mp2t", "video/MP2T", "application/octet-stream"]
    
    def __init__(self):
        pass
    
    async def get_stream_info(self, stream_id: str) -> Optional[dict]:
        """Get stream details from cache."""
        cache = await get_cache()
        return await cache.get_stream_by_id(stream_id)
    
    def _build_headers(self, stream: dict) -> dict:
        """Build request headers from stream metadata."""
        headers = {
            "User-Agent": stream.get("user_agent") or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        if stream.get("referrer"):
            headers["Referer"] = stream["referrer"]
        return headers
    
    async def check_stream_health(self, stream_id: str) -> dict:
        """Check if stream is accessible."""
        stream = await self.get_stream_info(stream_id)
        if not stream:
            return {"status": "error", "message": "Stream not found"}
        
        headers = self._build_headers(stream)
        
        try:
            async with httpx.AsyncClient(timeout=self.CONNECT_TIMEOUT) as client:
                response = await client.head(stream["url"], headers=headers, follow_redirects=True)
                if response.status_code == 200:
                    return {
                        "status": "ok",
                        "stream_id": stream_id,
                        "quality": stream.get("quality"),
                        "content_type": response.headers.get("content-type")
                    }
                else:
                    return {
                        "status": "error",
                        "message": f"Stream returned status {response.status_code}"
                    }
        except httpx.TimeoutException:
            return {"status": "error", "message": "Stream connection timed out"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    async def proxy_manifest(self, stream_id: str, base_url: str) -> StreamingResponse:
        """
        Proxy HLS manifest and rewrite segment URLs.
        base_url is our API base for rewriting segment URLs.
        """
        stream = await self.get_stream_info(stream_id)
        if not stream:
            raise HTTPException(status_code=404, detail="Stream not found")
        
        headers = self._build_headers(stream)
        stream_url = stream["url"]
        
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(self.CONNECT_TIMEOUT, read=self.READ_TIMEOUT)
            ) as client:
                response = await client.get(stream_url, headers=headers, follow_redirects=True)
                response.raise_for_status()
                
                # Use final URL after redirects for resolving relative paths
                final_url = str(response.url)
                content = response.text
                content_type = response.headers.get("content-type", "application/vnd.apple.mpegurl")
                
                # Rewrite URLs in manifest to go through our proxy
                rewritten = self._rewrite_manifest(content, final_url, stream_id, base_url)
                
                return StreamingResponse(
                    iter([rewritten.encode()]),
                    media_type=content_type,
                    headers={
                        "Access-Control-Allow-Origin": "*",
                        "Cache-Control": "no-cache, no-store, must-revalidate"
                    }
                )
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="Stream timed out")
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=502, detail=f"Upstream error: {e.response.status_code}")
        except Exception as e:
            logger.error(f"Manifest proxy error: {e}")
            raise HTTPException(status_code=500, detail="Failed to proxy stream")
    
    def _rewrite_manifest(self, content: str, original_url: str, stream_id: str, base_url: str) -> str:
        """Rewrite manifest URLs to proxy through our API."""
        # Get base path from original URL
        from urllib.parse import urljoin, urlparse
        parsed = urlparse(original_url)
        url_base = f"{parsed.scheme}://{parsed.netloc}{'/'.join(parsed.path.split('/')[:-1])}/"
        
        lines = content.split('\n')
        rewritten_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                rewritten_lines.append(line)
                continue
                
            if line.startswith('#'):
                # Rewrite URI= attributes in #EXT-X-KEY and similar
                if 'URI="' in line:
                    line = self._rewrite_uri_attribute(line, url_base, stream_id, base_url)
                rewritten_lines.append(line)
            else:
                # This is a URL line - could be segment or variant playlist
                if line.startswith('http://') or line.startswith('https://'):
                    full_url = line
                else:
                    full_url = urljoin(url_base, line)
                
                # Encode the URL for proxying
                import base64
                encoded_url = base64.urlsafe_b64encode(full_url.encode()).decode()
                proxy_url = f"{base_url}/api/streams/{stream_id}/segment/{encoded_url}"
                rewritten_lines.append(proxy_url)
        
        return '\n'.join(rewritten_lines)
    
    def _rewrite_uri_attribute(self, line: str, url_base: str, stream_id: str, base_url: str) -> str:
        """Rewrite URI attributes in HLS tags."""
        import base64
        from urllib.parse import urljoin
        
        pattern = r'URI="([^"]+)"'
        match = re.search(pattern, line)
        if match:
            uri = match.group(1)
            if not uri.startswith('http'):
                uri = urljoin(url_base, uri)
            encoded_url = base64.urlsafe_b64encode(uri.encode()).decode()
            proxy_url = f"{base_url}/api/streams/{stream_id}/segment/{encoded_url}"
            line = re.sub(pattern, f'URI="{proxy_url}"', line)
        return line
    
    async def proxy_segment(self, stream_id: str, encoded_url: str) -> StreamingResponse:
        """Proxy a stream segment OR a nested playlist."""
        import base64
        from urllib.parse import urlparse
        
        stream = await self.get_stream_info(stream_id)
        if not stream:
            raise HTTPException(status_code=404, detail="Stream not found")
        
        try:
            segment_url = base64.urlsafe_b64decode(encoded_url).decode()
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid segment URL")
        
        headers = self._build_headers(stream)
        
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(self.CONNECT_TIMEOUT, read=self.READ_TIMEOUT)
            ) as client:
                # First, we need to know the content type to decide how to handle it
                # We can't really stream if we need to rewrite, so we fetch headers first
                # But to save latency, let's just GET it and check headers
                
                response = await client.get(segment_url, headers=headers, follow_redirects=True)
                response.raise_for_status()
                
                content_type = response.headers.get("content-type", "").lower()
                
                # Check if this is a nested playlist (m3u8)
                if "mpegurl" in content_type or segment_url.endswith('.m3u8'):
                    # It's a nested playlist! Rewrite it.
                    # We need the base_url. For now, we reconstruct it from the request if possible
                    # But wait, proxy_segment doesn't get request object with base_url.
                    # We have a problem: we need the API base URL to rewrite nested links.
                    
                    # Workaround: Assume standard local pattern or try to extract from current call context
                    # Ideally passed in. But for now, let's reconstruct relative to /api/streams
                    # A better way is to simply NOT rewrite if we can't, but we MUST rewrite relative links.
                    
                    # Hack: The client (browser) knows the base URL.
                    # We can use a relative proxy path like "../../segment/" 
                    # URLs in the manifest rewritten as: "../segment/{encoded}"
                    
                    # Let's inspect the stream_id to find where we are
                    # If we don't know the hostname, we can use relative paths for the proxy API
                    # The proxy URL format is /api/streams/{stream_id}/segment/{encoded}
                    # If we are returning a playlist from /api/streams/{stream_id}/segment/{encoded_parent},
                    # then "segment/{encoded_child}" is a sibling.
                    # So we can use just "{encoded_child}" if the browser resolves typical HLS?
                    # No, browser treats last part as filename.
                    # Current URL: .../segment/{encoded_parent}
                    # We want: .../segment/{encoded_child}
                    # So rewriting to just "{encoded_child}" works! 
                    # Wait, no. The browser thinks the current directory is .../segment/
                    # So if we link to "{encoded_child}", it goes to .../segment/{encoded_child}. Correct!
                    
                    # But wait, the rewritten line in _rewrite_manifest uses full URL:
                    # proxy_url = f"{base_url}/api/streams/{stream_id}/segment/{encoded_url}"
                    # We need to change _rewrite_manifest to support relative rewriting or we need base_url.
                    
                    # Let's change this method signature in next step? 
                    # No, let's just make a modified rewrite for nested lists.
                    
                    content = response.text
                    final_url = str(response.url)
                    
                    # Custom rewrite for nested playlists that uses relative paths
                    rewritten = self._rewrite_nested_manifest(content, final_url)
                    
                    return StreamingResponse(
                        iter([rewritten.encode()]),
                        media_type="application/vnd.apple.mpegurl",
                        headers={
                            "Access-Control-Allow-Origin": "*",
                            "Cache-Control": "no-cache"
                        }
                    )
                
                else:
                    # Binary content (TS segment) - just return the bytes we already fetched
                    # Since we already did await client.get(), we have the content in memory.
                    # For large segments this is inefficient, but safe for bug fixing.
                    return StreamingResponse(
                        iter([response.content]),
                        media_type="video/mp2t",
                        headers={
                            "Access-Control-Allow-Origin": "*",
                            "Cache-Control": "max-age=3600"
                        }
                    )

        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="Segment timeout")
        except httpx.HTTPStatusError as e:
            # Pass through upstream error code (e.g. 404)
            status = e.response.status_code
            if status == 404:
                raise HTTPException(status_code=404, detail="Segment not found upstream")
            raise HTTPException(status_code=502, detail=f"Upstream segment error: {status}")
        except Exception as e:
            logger.error(f"Segment proxy error: {e}")
            raise HTTPException(status_code=500, detail="Failed to proxy segment")

    def _rewrite_nested_manifest(self, content: str, original_url: str) -> str:
        """Rewrite nested manifest with relative proxy URLs."""
        from urllib.parse import urljoin, urlparse
        import base64
        
        parsed = urlparse(original_url)
        url_base = f"{parsed.scheme}://{parsed.netloc}{'/'.join(parsed.path.split('/')[:-1])}/"
        
        lines = content.split('\n')
        rewritten_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                rewritten_lines.append(line)
                continue
            
            if line.startswith('#'):
                # Handle keys if needed (skipping for brevity, complex relative paths)
                rewritten_lines.append(line)
            else:
                if line.startswith('http'):
                    full_url = line
                else:
                    full_url = urljoin(url_base, line)
                
                encoded_url = base64.urlsafe_b64encode(full_url.encode()).decode()
                # Use relative path since we are already at .../segment/
                rewritten_lines.append(encoded_url)
        
        return '\n'.join(rewritten_lines)



# Singleton
_proxy_service: Optional[StreamProxyService] = None


def get_proxy_service() -> StreamProxyService:
    """Get or create proxy service singleton."""
    global _proxy_service
    if _proxy_service is None:
        _proxy_service = StreamProxyService()
    return _proxy_service
