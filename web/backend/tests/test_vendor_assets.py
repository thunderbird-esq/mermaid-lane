"""
Tests for serving vendor assets locally.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_vendor_videojs_core():
    """Test that Video.js Core is served correctly."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/js/vendor/video-core.min.js")
    assert response.status_code == 200
    assert len(response.content) > 1000  # Basic size check
    # Check for specific content signature if possible, looking for widely known string
    assert "videojs" in response.text or "vjs" in response.text

@pytest.mark.asyncio
async def test_vendor_videojs_css():
    """Test that Video.js CSS is served correctly."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/css/vendor/video-js.css")
    assert response.status_code == 200
    assert "video-js" in response.text

@pytest.mark.asyncio
async def test_vendor_plugins():
    """Test that manual plugins are served."""
    plugins = [
        "m3u8-parser.min.js",
        "mpd-parser.min.js",
        "videojs-http-streaming.min.js",
        "videojs-contrib-quality-levels.min.js",
        "videojs-http-source-selector.min.js"
    ]
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        for plugin in plugins:
            response = await ac.get(f"/js/vendor/{plugin}")
            assert response.status_code == 200, f"Failed to load {plugin}"
