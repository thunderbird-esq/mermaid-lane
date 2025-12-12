"""
Channel, Feed, and Stream data models.
Maps to iptv-org API schema.
"""
from pydantic import BaseModel, Field
from typing import Optional


class Channel(BaseModel):
    """TV Channel model matching iptv-org channels.json schema."""
    id: str
    name: str
    alt_names: list[str] = Field(default_factory=list)
    network: Optional[str] = None
    owners: list[str] = Field(default_factory=list)
    country: str
    categories: list[str] = Field(default_factory=list)
    is_nsfw: bool = False
    launched: Optional[str] = None
    closed: Optional[str] = None
    replaced_by: Optional[str] = None
    website: Optional[str] = None


class Feed(BaseModel):
    """Channel feed model for regional/quality variants."""
    channel: str
    id: str
    name: str
    alt_names: list[str] = Field(default_factory=list)
    is_main: bool = False
    broadcast_area: list[str] = Field(default_factory=list)
    timezones: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    format: Optional[str] = None


class Stream(BaseModel):
    """Stream URL model matching iptv-org streams.json schema."""
    channel: Optional[str] = None
    feed: Optional[str] = None
    title: str
    url: str
    referrer: Optional[str] = None
    user_agent: Optional[str] = None
    quality: Optional[str] = None
    
    # Internal fields (not from API)
    stream_id: Optional[str] = None  # Generated unique ID for proxying


class Logo(BaseModel):
    """Channel logo model."""
    channel: str
    feed: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    width: int = 0
    height: int = 0
    format: Optional[str] = None
    url: str


class Guide(BaseModel):
    """EPG guide source model."""
    channel: Optional[str] = None
    feed: Optional[str] = None
    site: str
    site_id: str
    site_name: str
    lang: str


# Response models for API
class ChannelWithStreams(Channel):
    """Channel with available streams attached."""
    streams: list[Stream] = Field(default_factory=list)
    logos: list[Logo] = Field(default_factory=list)
    current_program: Optional[str] = None  # From EPG if available


class ChannelListResponse(BaseModel):
    """Paginated channel list response."""
    channels: list[Channel]
    total: int
    page: int
    per_page: int
    has_more: bool
