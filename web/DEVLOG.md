# IPTV Web Application - Development Log

## 2025-12-12

### Session 3: v1.0.0 Release

**Goal**: Complete remaining tasks with TDD approach.

**Test Infrastructure**:
- Created pytest test suite with 11 tests
- Tests for M3U parser, EPG parser, and EPG mapping
- All tests passing in 0.02s

**EPG Channel Mapping**:
- Built `epg_mapping.py` with direct + fuzzy matching
- Note: Pluto TV uses internal IDs (MongoDB-style), not iptv-org format
- Future: Need EPG sources with compatible IDs

**Provider Filtering (Complete)**:
- Added `?provider=pluto` to `/api/channels`
- Frontend now shows 249 Pluto channels when filtering
- 31 total providers: Pluto, Tubi, BBC, XUMO, Roku, Samsung, etc.

**Performance & Security**:
- Added PWA manifest.json
- Added Content-Security-Policy
- Mobile responsive complete

---

### Session 2: Elevation & Feature Expansion

**Goal**: Elevate the app from prototype to fully usable by leveraging all available iptv-org resources.

**Analysis Performed**:
- Deep-dive into `iptv/` folder structure
- Discovered 307 M3U files with verified stream URLs
- Found 233 EPG site grabbers in `iptv/epg/sites/`
- Identified 11 CSV files in `iptv/database/data/` with rich metadata

**Key Insight**: We were using only the remote API and ignoring local M3U files which contain actual, tested HLS URLs.

**Implemented**:
1. **M3U Parser** (`app/services/m3u_parser.py`)
   - Parses EXTINF format with tvg-id extraction
   - Maps channel IDs from `ChannelName.country@Feed` format
   - Detects provider from filename (us_pluto.m3u → provider=pluto)
   - Extracts quality hints (720p, 1080p, 4K)

2. **EPG Parser** (`app/services/epg_parser.py`)
   - Parses XMLTV format from iptv-org/epg tool
   - Imports programs with title, description, category, times
   - Generates unique program IDs

3. **Favorites Module** (`frontend/js/favorites.js`)
   - Toggle buttons on cards and player
   - Sidebar filter for favorites-only view
   - Watch history tracking (last 20 channels)
   - Continue Watching sidebar filter

**Validation**:
```bash
curl http://localhost:8000/api/streams/stats
# {"total_streams": 16247, "channels_with_streams": 8614}

curl http://localhost:8000/api/epg/stats
# {"total_programs": 99918, "channels_with_epg": 2350}
```

---

## 2025-12-11

### Session 1: Initial Build

**Goal**: Build a functional IPTV streaming web application.

**Stack Chosen**:
- Backend: Python/FastAPI (rapid development, async support)
- Frontend: Vanilla JS (full control, no framework overhead)
- Database: SQLite (simple, embedded, sufficient for local data)
- Player: HLS.js (industry standard for HLS streaming)

**Implemented**:
1. Backend API with channels, streams, categories, countries
2. Stream proxy to hide original URLs
3. SQLite caching layer for API data
4. Frontend channel browser with filters
5. HLS.js video player with custom controls
6. Dark glassmorphism theme

**Data Synced**:
- 38,546 channels
- 12,966 streams (from API)
- 42,434 logos
- 30 categories
- 250 countries

---

## Architecture Notes

```
mermaid-lane/
├── iptv/                    # iptv-org repositories (submodules)
│   ├── epg/                 # EPG grabber tool
│   ├── database/            # Channel metadata CSVs
│   └── streams/             # M3U playlist files (307 files)
│
└── web/                     # Our application
    ├── backend/             # FastAPI server
    │   ├── app/
    │   │   ├── routers/     # API endpoints
    │   │   ├── services/    # Business logic
    │   │   └── models/      # Pydantic models
    │   └── data/            # SQLite DB, EPG files
    │
    └── frontend/            # Vanilla JS SPA
        ├── js/              # Modules (api, player, channels, etc.)
        └── css/             # Styles (main, player, epg)
```

## Performance Observations

- Initial page load: ~500ms (38K channels pre-cached)
- Channel click → player open: ~200ms
- Stream start: Depends on source (1-5s typical)
- EPG import (100K programs): ~30s
