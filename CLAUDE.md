# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a monorepo containing IPTV playlist management tools, part of the iptv-org ecosystem.

## Project Structure

### Root Directory
- Minimal Python 3.14 project (placeholder/utilities)
- Configuration files for Claude Code (.claude/)
- Project documentation

### iptv/ Directory (Main Project)
- **TypeScript/Node.js IPTV playlist management system**
- Part of the iptv-org open source ecosystem
- Handles playlist generation, validation, formatting, and testing
- Contains multiple subprojects:
  - **api/**: API documentation and specifications
  - **database/**: Channel database management
  - **epg/**: Electronic Program Guide utilities
  - **scripts/**: Core playlist processing scripts
  - **streams/**: Stream management utilities
  - **tests/**: Comprehensive test suite

## Technology Stack

### iptv/ (TypeScript/Node.js) - Primary Project
- **Runtime**: Node.js with tsx for TypeScript execution
- **Language**: TypeScript (strict mode, ES2022 target)
- **Testing**: Jest with @swc/jest for fast compilation
- **Linting**: ESLint with TypeScript and Stylistic plugins
- **Module System**: NodeNext (ESM)

### Key Dependencies
- **@iptv-org/sdk**: Core IPTV operations and utilities
- **iptv-playlist-parser**: M3U playlist parsing
- **m3u-linter**: Playlist format validation
- **axios**: HTTP client for API requests
- **commander**: CLI command framework
- **chalk**: Terminal output formatting
- **cli-progress**: Progress bars for long operations

### Root (Python) - Minimal
- **Python**: >= 3.14
- **Purpose**: Placeholder for future utilities
- Currently contains only a "Hello World" example

## Common Development Tasks

### Working with Playlists (iptv/)

```bash
cd iptv

# Validation
npm run playlist:validate    # Validate playlist structure
npm run playlist:lint        # Run m3u-linter checks

# Formatting
npm run playlist:format      # Format all playlists

# Testing
npm run playlist:test        # Run playlist-specific tests
npm test                     # Run full test suite

# Generation and Updates
npm run playlist:generate    # Generate new playlists
npm run playlist:update      # Update existing playlists

# Editing and Export
npm run playlist:edit        # Interactive playlist editor
npm run playlist:export      # Export playlists
```

### API Operations (iptv/)

```bash
cd iptv
npm run api:load            # Load API data (runs on postinstall)
```

### Testing and Quality (iptv/)

```bash
cd iptv
npm test                    # Run Jest tests (runInBand mode)
npm run lint                # Run ESLint on scripts and tests
```

### Documentation (iptv/)

```bash
cd iptv
npm run readme:update       # Update README files
npm run report:create       # Generate reports
```

### GitHub Actions Simulation (iptv/)

```bash
cd iptv
npm run act:check           # Simulate check workflow
npm run act:format          # Simulate format workflow
npm run act:update          # Simulate update workflow
```

## Code Standards

### TypeScript (iptv/)
- **Strict mode**: Enabled - all type safety features active
- **Target**: ES2022 - modern JavaScript features
- **Module resolution**: NodeNext - native ESM support
- **Type roots**: Custom types in scripts/types/ + @types
- **Naming conventions**:
  - PascalCase for classes and types
  - camelCase for functions and variables
  - UPPER_CASE for constants
- **File organization**: Follow existing patterns in scripts/
- **Imports**: Use ESM import/export syntax
- **Error handling**: Use try-catch with meaningful error messages

### Python (Root)
- **Version**: Python >= 3.14 required
- **Status**: Currently minimal - placeholder for future utilities
- **Standards**: Follow PEP 8 if/when expanded

## Git Workflow

### Commit Messages
- Follow conventional commits format: `type(scope): description`
- Types: feat, fix, docs, style, refactor, test, chore
- Keep first line under 72 characters
- Include body for complex changes

### Branching
- Create feature branches from main
- Use descriptive branch names: `feature/add-validation`, `fix/parsing-error`
- Keep commits atomic and focused

### Related Repositories
This project is part of the iptv-org ecosystem:
- **iptv-org/database**: Channel data source
- **iptv-org/api**: API specifications
- **iptv-org/epg**: Electronic Program Guide data
- See iptv/CONTRIBUTING.md for ecosystem-wide guidelines

## Testing Requirements

### Before Committing
1. **Change to iptv directory**: `cd iptv`
2. **Run tests**: `npm test` - all must pass
3. **Run linter**: `npm run lint` - no errors
4. **Validate playlists**: `npm run playlist:validate`
5. **Check M3U format**: `npm run playlist:lint`

### Test Organization (iptv/)
- Tests located in `tests/` directory
- Pattern: `tests/(.*?/)?.*test.ts$`
- Use jest-expect-message for descriptive assertions
- Run in band mode (--runInBand) for consistency

## Configuration Files

### iptv/ Configuration
- **tsconfig.json**: TypeScript compiler settings
- **eslint.config.mjs**: Linting rules (TypeScript + Stylistic)
- **m3u-linter.json**: M3U playlist validation rules
- **package.json**: Dependencies and scripts

### Root Configuration
- **pyproject.toml**: Python project metadata
- **.python-version**: Python version specification (3.14)
- **.claude/**: Claude Code configuration

## Important Notes

### Working Directory
- **Primary workspace**: `iptv/` directory
- Most development tasks occur in iptv/
- Root level is for project-wide configuration

### Before Making Changes
1. Understand the iptv-org ecosystem structure
2. Review iptv/CONTRIBUTING.md for guidelines
3. Check existing patterns in scripts/
4. Ensure changes maintain playlist compatibility

### Playlist Integrity
- **Critical**: Always validate playlists after modifications
- Use m3u-linter configuration for consistency
- M3U format errors can break downstream consumers
- Test with actual video players when possible

### Performance Considerations
- Playlists can be very large (100k+ entries)
- Use streaming/chunking for large file operations
- Progress bars (cli-progress) for long operations
- Consider memory usage with large datasets

## Review Checklist

Before marking any task as complete:
- [ ] Code follows TypeScript strict mode standards
- [ ] All tests pass (`npm test` in iptv/)
- [ ] Linter passes (`npm run lint` in iptv/)
- [ ] Playlists validated (`npm run playlist:validate`)
- [ ] M3U format checked (`npm run playlist:lint`)
- [ ] Documentation updated if needed
- [ ] Commit message follows conventional format
- [ ] Changes maintain backward compatibility
- [ ] No sensitive information committed

## Quick Reference

### Main Working Directory
```bash
cd iptv  # Most tasks happen here
```

### Pre-Commit Checklist
```bash
cd iptv
npm test && npm run lint && npm run playlist:validate && npm run playlist:lint
```

### Get Help
- See iptv/README.md for project overview
- See iptv/CONTRIBUTING.md for contribution guidelines
- See iptv/FAQ.md for common questions
- Check iptv/PLAYLISTS.md for playlist documentation

---

## CURRENT PRIORITY: IPTV Web Application

### web/ Directory (Active Development)
The `web/` directory contains a full-stack IPTV streaming web application:

**Backend (Python/FastAPI):**
- `web/backend/app/main.py` - FastAPI application entry point
- `web/backend/app/routers/` - API endpoints (channels, streams, epg)
- `web/backend/app/services/` - Business logic (cache, proxy, transcoder)
- `web/backend/tests/` - Pytest test suite (17 tests)

**Frontend (Vanilla JS + Video.js):**
- `web/frontend/index.html` - Main SPA entry point
- `web/frontend/js/` - Application modules (player, channels, epg, api)
- `web/frontend/js/vendor/` - Video.js core + plugins (local, no CDN)
- `web/frontend/css/` - Styling

### Running the Web Application
```bash
cd web/backend
venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
# Open http://localhost:8000 in browser
```

### Testing the Backend
```bash
cd web/backend
venv/bin/pytest tests/ -v
```

### Phase 1 Priority (Critical Playback Fixes)
- [ ] Fix HLS stream loading freeze
- [ ] Add 15s loading timeout
- [ ] Improve error messaging
- [ ] Add integration tests

### Data Sources
- `tv-garden-channel-list/` - Curated channel database
- `iptv-org API` - Channel metadata and streams
