# Mermaid Lane

Development workspace for IPTV-related tools and utilities.

## Overview

This is a monorepo containing IPTV (Internet Protocol Television) playlist management tools, part of the open source **iptv-org** ecosystem.

## Project Structure

### =ú iptv/
**Main TypeScript/Node.js IPTV Project**

The primary project for managing publicly available IPTV channels from around the world.

- **Language**: TypeScript (ES2022, strict mode)
- **Testing**: Jest with @swc/jest
- **Features**:
  - Playlist generation, validation, and formatting
  - M3U playlist parsing and linting
  - API integration with iptv-org services
  - Database management for channel data
  - EPG (Electronic Program Guide) utilities

=I **See [iptv/README.md](iptv/README.md) for detailed documentation**

#### Subprojects
- `api/` - API documentation and specifications
- `database/` - Channel database management
- `epg/` - Electronic Program Guide utilities
- `scripts/` - Core playlist processing scripts
- `streams/` - Stream management utilities
- `tests/` - Comprehensive test suite

### = Root (Python)
**Minimal Python utilities** (Python >= 3.14)

Currently contains only a placeholder for future Python-based utilities.

## Quick Start

### Working with IPTV Playlists

```bash
# Navigate to the main project
cd iptv

# Install dependencies
npm install

# Run tests
npm test

# Validate playlists
npm run playlist:validate

# Lint M3U format
npm run playlist:lint

# See all available commands
npm run
```

### Common Commands

```bash
cd iptv

# Testing and Quality
npm test                     # Run full test suite
npm run lint                 # Run ESLint

# Playlist Operations
npm run playlist:validate    # Validate structure
npm run playlist:format      # Format playlists
npm run playlist:generate    # Generate new playlists
npm run playlist:update      # Update existing playlists

# Documentation
npm run readme:update        # Update README files
npm run report:create        # Generate reports
```

## Development with Claude Code

This project is configured for use with [Claude Code](https://claude.ai/code).

### Custom Slash Commands
- `/validate-playlist` - Run playlist validation and linting
- `/run-iptv-tests` - Execute full test suite and quality checks
- `/iptv-help` - Display all available npm scripts

### Configuration Files
- `.claude/settings.json` - Claude Code project settings
- `CLAUDE.md` - Detailed development guidelines for AI assistance
- `.claude/commands/` - Custom slash command definitions

## Technology Stack

### IPTV Project (TypeScript)
- **Runtime**: Node.js with tsx
- **Package Manager**: npm
- **Testing**: Jest
- **Linting**: ESLint with TypeScript plugin
- **Key Libraries**: @iptv-org/sdk, iptv-playlist-parser, m3u-linter

### Root (Python)
- **Python**: 3.14+
- **Purpose**: Future utilities (currently minimal)

## Related Projects

This project is part of the **iptv-org** ecosystem:

- [iptv-org/iptv](https://github.com/iptv-org/iptv) - Main playlist repository
- [iptv-org/database](https://github.com/iptv-org/database) - Channel database
- [iptv-org/api](https://github.com/iptv-org/api) - API specifications
- [iptv-org/epg](https://github.com/iptv-org/epg) - EPG utilities
- [iptv-org/awesome-iptv](https://github.com/iptv-org/awesome-iptv) - Resources

## Documentation

- **IPTV Project**: See [iptv/README.md](iptv/README.md)
- **Contributing**: See [iptv/CONTRIBUTING.md](iptv/CONTRIBUTING.md)
- **FAQ**: See [iptv/FAQ.md](iptv/FAQ.md)
- **Playlists**: See [iptv/PLAYLISTS.md](iptv/PLAYLISTS.md)
- **Development Guidelines**: See [CLAUDE.md](CLAUDE.md)

## License

- **IPTV Project**: See [iptv/LICENSE](iptv/LICENSE)
- **Root Project**: See [LICENSE](LICENSE)

## Getting Help

For questions or issues:
- Check the [FAQ](iptv/FAQ.md)
- Review [CONTRIBUTING.md](iptv/CONTRIBUTING.md) guidelines
- Join [Discussions](https://github.com/orgs/iptv-org/discussions)

---

**Main Development Focus**: The `iptv/` directory contains the active TypeScript project. Most development work happens there.
