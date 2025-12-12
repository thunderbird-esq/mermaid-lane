# IPTV Web

A modern, secure IPTV streaming web application built on top of the [iptv-org](https://github.com/iptv-org) ecosystem.

![IPTV Web](https://img.shields.io/badge/Status-Development-blue)

## Features

- 📺 **38,000+ Channels** from iptv-org database
- 🌍 **200+ Countries** with filtering and search
- 🎯 **30 Categories** (News, Sports, Movies, etc.)
- 🔒 **Secure Streaming** - All streams proxied (no URL exposure)
- 📅 **EPG Support** - Electronic Program Guide
- 📱 **Responsive Design** - Works on desktop and mobile
- 🌙 **Dark Theme** - Modern glassmorphism UI

## Quick Start

### Prerequisites

- Python 3.10+
- pip

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

### Access

Open [http://localhost:8000](http://localhost:8000) in your browser.

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
│   └── requirements.txt
└── frontend/          # Static frontend
    ├── index.html
    ├── css/           # Stylesheets
    └── js/            # JavaScript modules
```

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/channels` | List channels (filterable) |
| `GET /api/channels/{id}` | Get channel with streams |
| `GET /api/categories` | List categories |
| `GET /api/countries` | List countries |
| `GET /api/streams/{id}/play.m3u8` | Proxied HLS stream |
| `GET /api/epg/{channel_id}` | EPG for channel |

## Data Source

Channel data is fetched from [iptv-org API](https://github.com/iptv-org/api):
- Channels: ~38,000
- Streams: Variable availability
- EPG: From iptv-org/epg sources

## License

This project is for educational purposes. Respect the licenses of upstream data sources.
