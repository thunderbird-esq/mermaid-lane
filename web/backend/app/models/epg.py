"""
EPG (Electronic Program Guide) data models.
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class Program(BaseModel):
    """TV program/show model from EPG data."""
    id: str  # Generated unique ID
    channel_id: str
    title: str
    description: Optional[str] = None
    start: datetime
    stop: datetime
    category: Optional[str] = None
    icon: Optional[str] = None
    rating: Optional[str] = None
    
    @property
    def duration_minutes(self) -> int:
        """Calculate program duration in minutes."""
        return int((self.stop - self.start).total_seconds() / 60)
    
    @property
    def is_live(self) -> bool:
        """Check if program is currently airing."""
        now = datetime.utcnow()
        return self.start <= now <= self.stop
    
    @property
    def progress_percent(self) -> float:
        """Get playback progress as percentage (0-100)."""
        if not self.is_live:
            return 0.0 if datetime.utcnow() < self.start else 100.0
        total = (self.stop - self.start).total_seconds()
        elapsed = (datetime.utcnow() - self.start).total_seconds()
        return min(100.0, (elapsed / total) * 100)


class EPGChannel(BaseModel):
    """Channel info from EPG data."""
    id: str
    display_name: str
    icon: Optional[str] = None


class ChannelEPG(BaseModel):
    """EPG data for a specific channel."""
    channel_id: str
    channel_name: str
    programs: list[Program] = Field(default_factory=list)


class NowPlaying(BaseModel):
    """Currently playing program across channels."""
    channel_id: str
    channel_name: str
    program: Program
    progress_percent: float


class EPGTimelineResponse(BaseModel):
    """EPG timeline response with multiple channels."""
    start_time: datetime
    end_time: datetime
    channels: list[ChannelEPG]
