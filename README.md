# Media Extractor — Windows

A minimalistic app for downloading media from YouTube, TikTok, Instagram, Twitter, SoundCloud, Spotify, Reddit, and Facebook.

## Install

### Option 1 — Portable EXE (Recommended)
Download `MediaExtractor.exe` from [Releases](https://github.com/wfrae/MediaExtractorWin/releases/latest). No installation needed — just double-click.

### Option 2 — Installer
Download `MediaExtractor-Setup-v2.0.exe` from [Releases](https://github.com/wfrae/MediaExtractorWin/releases/latest). Run it, follow the prompts, and launch from your Start Menu or Desktop.

### Option 3 — Build from Source
```
git clone https://github.com/wfrae/MediaExtractorWin.git
cd MediaExtractorWin
pip install -r requirements.txt
python media_extractor.py
```

To build the standalone EXE:
```
build.bat
```

To build the installer (requires [Inno Setup](https://jrsoftware.org/isinfo.php)):
```
build_installer.bat
```

## Requirements

- Windows 10 or later (64-bit)
- [yt-dlp](https://github.com/yt-dlp/yt-dlp/releases/latest) — download `yt-dlp.exe` and add it to your PATH (the app will guide you if it's missing)

## Features

- **Multi-platform downloads** — YouTube, TikTok, Instagram, Twitter/X, SoundCloud, Spotify, Reddit, Facebook
- **8 themes** — Midnight, Dracula, Catppuccin, One Dark, Nord, Ayu, Light, Rosé Pine
- **Format selection** — MP4, WebM, MKV video / MP3, M4A, WAV, Opus audio
- **Quality control** — Best, 1080p, 720p, 4K
- **CSV batch extractor** — Drop a CSV file and download all media URLs at once
- **Download history** — Track every download with status, size, and timestamps
- **AES-256-GCM encryption** — Protect downloaded files with a password
- **ZIP export** — Bundle downloads into a single archive
- **Activity logs** — Full log of all operations

## License

MIT
