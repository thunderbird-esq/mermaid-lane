"""
Pytest configuration and fixtures for IPTV backend tests.
"""
import pytest
import asyncio
import tempfile
import os
from pathlib import Path


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_m3u_content():
    """Sample M3U content for testing."""
    return """#EXTM3U
#EXTINF:-1 tvg-id="ABC.us@East",ABC East
http://example.com/abc-east.m3u8
#EXTINF:-1 tvg-id="CNN.us",CNN (1080p)
http://example.com/cnn.m3u8
#EXTINF:-1,Channel Without ID
http://example.com/no-id.m3u8
"""


@pytest.fixture
def sample_m3u_file(sample_m3u_content, tmp_path):
    """Create a temporary M3U file for testing."""
    m3u_file = tmp_path / "us_pluto.m3u"
    m3u_file.write_text(sample_m3u_content)
    return m3u_file


@pytest.fixture
def sample_epg_xml():
    """Sample XMLTV EPG content for testing."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<tv>
    <channel id="ABC.us">
        <display-name>ABC</display-name>
        <icon src="https://example.com/abc.png"/>
    </channel>
    <programme start="20251212010000 +0000" stop="20251212020000 +0000" channel="ABC.us">
        <title>Morning News</title>
        <desc>Daily news broadcast</desc>
        <category>News</category>
    </programme>
    <programme start="20251212020000 +0000" stop="20251212030000 +0000" channel="ABC.us">
        <title>Weather Update</title>
    </programme>
</tv>
"""


@pytest.fixture
def sample_epg_file(sample_epg_xml, tmp_path):
    """Create a temporary EPG XML file for testing."""
    epg_file = tmp_path / "test_guide.xml"
    epg_file.write_text(sample_epg_xml)
    return epg_file
