# IPTV Web Application - Changelog

All notable changes to this project will be documented in this file.

## [1.1.0] - 2025-12-12

### Added
- **EPG Reverse Mapping** - iptv-org channels now get EPG data automatically
  - `tvguide.com` EPG imported (153 channels with proper IDs)
  - `i.mjh.nz_pbs` EPG imported (149 PBS stations)
  - 175 channels now mapped to EPG data
  
- **Batch EPG Import Script**
  - `app/scripts/import_epg.py` for importing all EPG files
  
### Changed
- `get_epg_for_channel()` now uses reverse mapping lookup
  - Queries both iptv-org ID and mapped XMLTV IDs
  - Returns unified channel_id for frontend

### Fixed
- EPG data now displays for channels like `FX.us`, `AMC.us`, etc.

## [1.0.0] - 2025-12-12

### Added
- **Test Suite** - 11 pytest tests covering M3U, EPG, and mapping
  - M3U parser: 4 tests (parsing, provider extraction, error handling, quality)
  - EPG parser: 3 tests (program parsing, multi-program, missing fields)
  - EPG mapping: 4 tests (exact match, fuzzy match, unmapped, batch)
  
- **EPG Channel Mapping** - Link EPG data to iptv-org channels
  - Direct ID matching
  - Fuzzy name matching with SequenceMatcher
  - `/api/epg/map` endpoint
  - `/api/epg/coverage` endpoint
  
- **Provider Filtering (Complete)**
  - `/api/channels?provider=pluto` filter
  - Frontend sidebar loads provider channels
  - 249 Pluto channels, 31 providers total
  
- **PWA Support**
  - manifest.json for add-to-home-screen
  - theme-color meta tag
  
- **Security**
  - Content-Security-Policy header
  - Restricts scripts, styles, and connections

## [0.3.0] - 2025-12-12

### Added
- **Providers Section** - 31 stream providers discovered and listed
  - Pluto (492), Tubi (255), BBC (162), XUMO (162), Roku (55), Samsung (39)
  - Provider filter in sidebar with stream counts
  - `/api/providers` endpoint
  
- **Mobile Responsiveness**
  - Hamburger menu toggle for sidebar on tablet/mobile
  - Collapsible sidebar with overlay backdrop
  - Touch-friendly controls (larger tap targets)
  - Responsive navbar that hides search on mobile
  - Single-column channel grid on small screens
  
- **EPG Route Fixes**
  - Fixed routing order so `/api/epg/stats` works correctly
  - Changed channel EPG route to `/api/epg/channel/{id}`

### Changed
- EPG channel endpoint moved from `/{channel_id}` to `/channel/{channel_id}`

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
