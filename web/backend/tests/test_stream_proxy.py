"""
Tests for Stream Proxy Service logic.
"""
import pytest
import base64
from app.services.stream_proxy import StreamProxyService

@pytest.mark.asyncio
async def test_rewrite_manifest_absolute():
    """Test rewriting of master manifest with absolute URLs."""
    service = StreamProxyService()
    
    original_manifest = """#EXTM3U
#EXT-X-STREAM-INF:BANDWIDTH=1280000,RESOLUTION=720x480
http://example.com/stream/mid.m3u8"""
    
    rewritten = service._rewrite_manifest(
        original_manifest, 
        "http://example.com/master.m3u8",
        "test_stream_1",
        "http://api.local"
    )
    
    # Check that URLs are proxied
    assert "http://api.local/api/streams/test_stream_1/segment/" in rewritten
    assert "http://example.com/stream/mid.m3u8" not in rewritten
    
    # Decode to verify correctness
    import re
    match = re.search(r'segment/([a-zA-Z0-9_-]+={0,2})', rewritten)
    assert match
    encoded = match.group(1)
    decoded = base64.urlsafe_b64decode(encoded).decode()
    assert decoded == "http://example.com/stream/mid.m3u8"

@pytest.mark.asyncio
async def test_rewrite_nested_manifest_relative():
    """Test rewriting of nested playlist with relative segments."""
    service = StreamProxyService()
    
    original_manifest = """#EXTM3U
#EXTINF:10,
segment0.ts"""
    
    # We simulate fetching a nested playlist from: http://example.com/stream/mid.m3u8
    # The segment "segment0.ts" resolves to: http://example.com/stream/segment0.ts
    
    rewritten = service._rewrite_nested_manifest(
        original_manifest,
        "http://example.com/stream/mid.m3u8"
    )
    
    # Logic verification:
    # 1. Provide encoded filename only
    # 2. Browser appends this to current path (.../segment/)
    # 3. Resulting request goes to .../segment/{encoded_segment_url}
    
    expected_url = "http://example.com/stream/segment0.ts"
    expected_b64 = base64.urlsafe_b64encode(expected_url.encode()).decode()
    
    assert expected_b64 in rewritten
    assert "segment0.ts" not in rewritten
    assert "/" not in rewritten.split('\n')[2] # Should be just the filename (encoded string)

@pytest.mark.asyncio
async def test_rewrite_uri_attribute():
    """Test rewriting of URI attributes in tags."""
    service = StreamProxyService()
    
    line = '#EXT-X-KEY:METHOD=AES-128,URI="key.php"'
    url_base = "http://example.com/"
    
    rewritten = service._rewrite_uri_attribute(
        line,
        url_base,
        "stream1",
        "http://api.local"
    )
    
    assert 'URI="http://api.local/api/streams/stream1/segment/' in rewritten
    assert "key.php" not in rewritten
