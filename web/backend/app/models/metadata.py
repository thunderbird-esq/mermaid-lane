"""
Metadata models for categories, countries, languages, regions.
"""
from pydantic import BaseModel, Field
from typing import Optional


class Category(BaseModel):
    """Channel category model."""
    id: str
    name: str
    description: str
    channel_count: int = 0  # Computed field


class Country(BaseModel):
    """Country model with channel count."""
    name: str
    code: str
    languages: list[str] = Field(default_factory=list)
    flag: str = ""
    channel_count: int = 0  # Computed field


class Language(BaseModel):
    """Language model."""
    name: str
    code: str


class Region(BaseModel):
    """Geographic region model."""
    code: str
    name: str
    countries: list[str] = Field(default_factory=list)


class Timezone(BaseModel):
    """Timezone model."""
    id: str
    utc_offset: str
    countries: list[str] = Field(default_factory=list)


class Subdivision(BaseModel):
    """Country subdivision (state/province) model."""
    country: str
    name: str
    code: str
    parent: Optional[str] = None
