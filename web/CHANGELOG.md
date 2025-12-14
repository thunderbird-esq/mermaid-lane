# IPTV Web Application - Changelog

All notable changes to this project will be documented in this file.

## [1.2.0] - 2025-12-14

### Added
- **Debug Logging in Player** - Console logs for troubleshooting playback issues
  - Logs stream URL, type, and YouTube detection
  - Logs playback success/failure events
  
- **Loading Timeout** - 15-second timeout prevents infinite loading spinner
  - User-friendly error message when stream fails to load
  - Timeout clears automatically on success or error
  
- **Integration Tests** - 4 new tests for player/stream infrastructure
  - YouTube URL detection test
  - HLS manifest rewriting verification
  - EXT header preservation test
  - Timeout configuration verification
  
### Fixed
- Duplicate "Initialize plugins" comment in player.js
- Added proper `self` parameter to async test methods

### Changed
- Player now uses one-time event listeners for playback attempts
- Test count increased from 17 to 21

## [1.1.0] - 2025-12-12

### Added
- **Now Playing Integration**
  - "Now Playing" info directly on channel cards
  - Live progress bar showing show status
  - `include_epg` parameter in `/api/channels` endpoint
  
- **Enhanced EPG Mapping**
  - Multi-strategy mapping (Direct, Prefix-based, Fuzzy Name Match)
  - Mapping rate improved to ~21% (518 channels mapped)
  - Imported EPG sources: `tvguide.com`, `i.mjh.nz_pbs`, `gatotv.com`
  - Batch import script: `app/scripts/import_epg.py`
  
- **UI Polish**
  - Skeleton loaders for smoother loading states
  - "Now Playing" visual indicators
  - Improved date/time handling in backend SQL queries

### Changed
- `get_now_playing_for_channels` now uses ISO date format with T separator to correctly match DB storage
- `get_epg_for_channel` uses reverse mapping lookup to find data across multiple EPG IDs

### Fixed
- Fixed SQL datetime comparison bug preventing "Now Playing" from showing
- Fixed EPG data visibility for channels with simple ID variations (e.g. `ABC.us@East` -> `ABC.us`)

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
