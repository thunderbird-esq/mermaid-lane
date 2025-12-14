# CLAUDE.md - AI Development Context

> Development context for AI assistants working on IPTV Web.

## Project Overview

IPTV Web is a streaming application that aggregates 43,000+ channels from iptv-org with 14,000+ playable streams. It features a secure stream proxy, EPG integration, health monitoring, and user persistence.

## Architecture

```
web/
├── backend/          # FastAPI Python backend (v0.3.0)
│   ├── app/
│   │   ├── routers/  # API endpoints (channels, streams, epg, user)
│   │   ├── services/ # Business logic (cache, stream_proxy, health_worker)
│   │   └── models/   # Pydantic models
│   └── tests/        # pytest test suite (33 tests, 39% coverage)
├── frontend/         # Vanilla JS SPA
│   ├── js/           # Modules (api, player, channels, favorites, epg)
│   └── css/          # Responsive styles
└── docker-compose.yml
```

## Key Services

| Service | Description |
|---------|-------------|
| `CacheService` | SQLite caching with 12+ tables, user data methods |
| `StreamProxyService` | HLS manifest rewriting and URL obfuscation |
| `HealthWorker` | Background stream health checking |
| `TranscoderService` | FFmpeg transcoding for non-HLS streams |
| `GeoBypassService` | Header spoofing for geo-blocked content |

## API Routes

- `/api/channels` - Channel browsing with filters
- `/api/streams/{id}/play.m3u8` - Proxied HLS streams
- `/api/epg/{channel_id}` - Electronic Program Guide
- `/api/user/favorites` - User favorites (device fingerprint)
- `/api/user/history` - Watch history
- `/api/user/popular` - Popular channels by view count

## Development Commands

```bash
# Start dev server
cd web/backend && uvicorn app.main:app --reload --port 8000

# Run tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=app --cov-report=term
```

## Current Version: 0.3.0 (Phase 1 Complete)

### Recent Additions
- User persistence (favorites, history, popularity)
- Responsive mobile design (5 breakpoints)
- 12 new API methods in frontend

### Roadmap (Next Phases)
- Phase 2 (v0.4): Stream fallback, geo-bypass Level 2
- Phase 3 (v0.5): EPG automation, personalization
- Phase 4 (v1.0): Redis caching, horizontal scale

## Testing Notes

- All tests are async using `pytest-asyncio`
- Tests use temp SQLite databases
- Coverage: 39% overall (services best covered)
- CI: GitHub Actions on push/PR
