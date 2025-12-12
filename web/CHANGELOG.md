# IPTV Web Application - Changelog

All notable changes to this project will be documented in this file.

## [0.2.0] - 2025-12-12

### Added
- **Local M3U Stream Import** - Parse and import streams from `iptv/streams/*.m3u` files
  - 16,247 streams imported from 39 files (US, UK, CA)
  - Provider detection from filenames (pluto, roku, samsung, etc.)
  - Quality extraction from stream names (720p, 1080p, 4K)
  
- **EPG Integration** - Full Electronic Program Guide support
  - XMLTV parser for iptv-org/epg output
  - 99,918 programs imported from Pluto TV
  - `/api/epg/import` endpoint for easy imports
  - `/api/epg/now/playing` - Currently airing programs
  - `/api/epg/stats` - EPG statistics
  
- **Favorites System**
  - Star toggle buttons on channel cards
  - Favorite button in player header
  - "My Favorites" sidebar filter
  - localStorage persistence
  - Import/export functionality

- **Watch History**
  - Automatic tracking when channels opened
  - "Continue Watching" sidebar filter
  - Last 20 channels stored
  - localStorage persistence

### Changed
- Stream proxy now supports both API-sourced and M3U-sourced streams
- Enhanced player to show stream count
- Improved error messages for stream failures

## [0.1.0] - 2025-12-11

### Added
- Initial FastAPI backend with SQLite caching
- Channel browser with 38,546 channels from iptv-org API
- Country and category filtering
- HLS.js video player with custom controls
- Secure stream proxy (hides original URLs)
- Dark glassmorphism UI theme
- Responsive layout
