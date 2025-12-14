# IPTV Web

A modern, secure IPTV streaming web application built on top of the [iptv-org](https://github.com/iptv-org) ecosystem.

![IPTV Web](https://img.shields.io/badge/Status-Development-blue)

## Features

- 📺 **14,000+ Playable Channels** (43k total in catalog) from iptv-org database
- 🌍 **200+ Countries** with filtering and search
- 🎯 **30 Categories** (News, Sports, Movies, etc.)
- 🏢 **Provider Filter** - Browse by Pluto TV, Tubi, Samsung TV Plus, etc.
- 🔒 **Secure Streaming** - All streams proxied (no URL exposure)
- 📅 **EPG Integration** - Now Playing info & channel guides
- ❤️ **Favorites** - Save and organize your favorite channels
- 🏥 **Stream Health Monitoring** - Background health checks with status badges
- 📱 **PWA Support** - Installable on mobile & desktop
- 🌙 **Dark Theme** - Modern glassmorphism UI

## Quick Start

### Prerequisites

- Python 3.10+
- pip
- **ffmpeg** (required for transcoding non-HLS streams)

### Installation

```bash
# Navigate to backend
cd web/backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the server
uvicorn app.main:app --reload --port 8000
```

### Docker Deployment

```bash
cd web

# Set admin API key (required for production)
export IPTV_ADMIN_API_KEY=your-secure-key-here

# Start with Docker Compose
docker compose up -d

# View logs
docker compose logs -f
```

### Access

Open [http://localhost:8000](http://localhost:8000) in your browser.

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `IPTV_HOST` | Server bind address | `0.0.0.0` |
| `IPTV_PORT` | Server port | `8000` |
| `IPTV_DEBUG` | Enable debug mode | `false` |
| `IPTV_ADMIN_API_KEY` | API key for admin endpoints | `dev-admin-key` |
| `IPTV_DATABASE_PATH` | SQLite database location | `data/iptv_cache.db` |
| `IPTV_CACHE_TTL_SECONDS` | Cache TTL for API responses | `3600` |

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/health` | Health check |
| `GET /api/stats` | Database statistics (playable/total channels) |
| `GET /api/channels` | List channels (filterable, `playable_only=true` by default) |
| `GET /api/channels/{id}` | Get channel with streams |
| `GET /api/categories` | List categories |
| `GET /api/countries` | List countries |
| `GET /api/streams/{id}/play.m3u8` | Proxied HLS stream |
| `GET /api/streams/health-stats` | Stream health statistics |
| `GET /api/epg/{channel_id}` | EPG for channel |
| `GET /api/user/favorites` | Get user favorites (X-Device-Id header) |
| `POST /api/user/favorites` | Add favorite |
| `GET /api/user/history` | Get watch history |
| `GET /api/user/popular` | Popular channels by views |
| `POST /api/sync?X-Admin-Key=KEY` | Trigger data sync (protected) |

## Troubleshooting

### Streams not loading?
1. Check browser console for errors
2. Try a different stream - some upstream sources may be offline
3. For YouTube streams: "Playback on other websites disabled" = video owner restriction

### Video stuck loading?
- HLS streams timeout after 15 seconds
- YouTube streams timeout after 30 seconds
- Try refreshing and selecting a different stream

### CORS errors?
- The server allows all origins by default
- For production, set `IPTV_CORS_ORIGINS` to your domain

## Architecture

```
web/
├── backend/           # FastAPI Python backend
│   ├── app/
│   │   ├── main.py    # Application entry point
│   │   ├── config.py  # Configuration
│   │   ├── models/    # Pydantic data models
│   │   ├── routers/   # API endpoints
│   │   └── services/  # Business logic
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/          # Static frontend
│   ├── index.html
│   ├── css/           # Stylesheets
│   └── js/            # JavaScript modules
└── docker-compose.yml
```

## Data Source

Channel data is fetched from [iptv-org API](https://github.com/iptv-org/api):
- **Channels in catalog**: ~43,000 (from iptv-org/database)
- **Playable channels**: ~14,000 (with active stream URLs)
- **Streams**: ~19,000 (from iptv-org/iptv)
- **EPG**: From iptv-org/epg sources

> Note: Many channels exist in the catalog without available streams. The UI defaults to showing only playable channels.

## License

This project is for educational purposes. Respect the licenses of upstream data sources.

