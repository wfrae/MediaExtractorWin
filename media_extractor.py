"""
Universal Media Extractor — Windows Edition
A minimalistic app for downloading media from YouTube, TikTok, Instagram, Twitter, SoundCloud, Spotify, and more.
"""

import os
import sys
import json
import csv
import re
import shutil
import subprocess
import threading
import time
import uuid
import zipfile
import hashlib
import webbrowser
import urllib.request
import urllib.error
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False

# ── App info ──────────────────────────────────────────────────────

APP_NAME = "Media Extractor"
APP_VERSION = "2.0"
CONFIG_DIR = Path.home() / ".mediaextractor"
CONFIG_FILE = CONFIG_DIR / "config.json"
HISTORY_FILE = CONFIG_DIR / "history.json"
LOG_FILE = CONFIG_DIR / "logs.json"

# ── Themes ────────────────────────────────────────────────────────

THEMES = {
    "Midnight": {
        "bg": "#0a0a0a", "surface": "#141414", "surface_hover": "#1e1e1e",
        "border": "#1a1a1a", "text": "#e8e6e1", "muted": "#666666",
        "accent": "#c4b59a", "success": "#66bf66", "danger": "#d95959",
    },
    "Dracula": {
        "bg": "#282a36", "surface": "#363949", "surface_hover": "#434758",
        "border": "#44475a", "text": "#f8f8f2", "muted": "#9ea3c2",
        "accent": "#bd93f9", "success": "#50fa7b", "danger": "#ff5555",
    },
    "Catppuccin": {
        "bg": "#1e1e2e", "surface": "#29293b", "surface_hover": "#333348",
        "border": "#45475a", "text": "#cdd6f4", "muted": "#6c7086",
        "accent": "#89b4fa", "success": "#a6e3a1", "danger": "#f38ba8",
    },
    "One Dark": {
        "bg": "#282c34", "surface": "#333842", "surface_hover": "#3e434d",
        "border": "#4d535e", "text": "#abb2bf", "muted": "#636a76",
        "accent": "#61afef", "success": "#98c379", "danger": "#e06c75",
    },
    "Nord": {
        "bg": "#2e3440", "surface": "#3b4252", "surface_hover": "#434c5e",
        "border": "#4c566a", "text": "#d8dee9", "muted": "#808a9c",
        "accent": "#88c0d0", "success": "#a3be8c", "danger": "#bf616a",
    },
    "Ayu": {
        "bg": "#0f1419", "surface": "#162029", "surface_hover": "#1e2c36",
        "border": "#2d3d47", "text": "#b3bcc5", "muted": "#5c6773",
        "accent": "#ffb454", "success": "#aad94c", "danger": "#ff7733",
    },
    "Light": {
        "bg": "#f7f7f7", "surface": "#ffffff", "surface_hover": "#f0f0f2",
        "border": "#e0e0e0", "text": "#212125", "muted": "#888888",
        "accent": "#3366e6", "success": "#33a652", "danger": "#d94040",
    },
    "Rosé Pine": {
        "bg": "#232136", "surface": "#2e2b3d", "surface_hover": "#383448",
        "border": "#4a4559", "text": "#e0d9de", "muted": "#857e8f",
        "accent": "#ea9a97", "success": "#9ec699", "danger": "#ea7373",
    },
}

# ── Platforms ─────────────────────────────────────────────────────

PLATFORMS = {
    "YouTube": {"pattern": r"youtube\.com|youtu\.be", "icon": "▶"},
    "TikTok": {"pattern": r"tiktok\.com", "icon": "♫"},
    "Instagram": {"pattern": r"instagram\.com", "icon": "○"},
    "Twitter": {"pattern": r"twitter\.com|x\.com", "icon": "✱"},
    "SoundCloud": {"pattern": r"soundcloud\.com", "icon": "♪"},
    "Spotify": {"pattern": r"spotify\.com", "icon": "●"},
    "Reddit": {"pattern": r"reddit\.com", "icon": "R"},
    "Facebook": {"pattern": r"facebook\.com|fb\.watch", "icon": "f"},
}

def detect_platform(url):
    for name, info in PLATFORMS.items():
        if re.search(info["pattern"], url, re.IGNORECASE):
            return name, info["icon"]
    return None, None

def get_yt_video_id(url):
    m = re.search(r"(?:v=|youtu\.be/)([a-zA-Z0-9_-]{11})", url)
    return m.group(1) if m else None

# ── Config ────────────────────────────────────────────────────────

def load_config():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    defaults = {
        "theme": "Midnight",
        "download_folder": str(Path.home() / "Downloads" / "MediaExtractor"),
        "video_format": "mp4",
        "video_quality": "best",
        "audio_format": "mp3",
        "audio_bitrate": "320k",
        "encrypt": False,
        "encryption_password": "",
        "concurrent_fragments": 8,
        "chunk_size_mb": 10,
        "max_cpu_cores": os.cpu_count() or 4,
        "max_ram_mb": 512,
        "process_priority": "normal",
    }
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r") as f:
                saved = json.load(f)
            defaults.update(saved)
        except Exception:
            pass
    return defaults

def save_config(cfg):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)

# ── History & Logs ────────────────────────────────────────────────

def load_history():
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return []

def save_history(history):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(HISTORY_FILE, "w") as f:
        json.dump(history[-500:], f, indent=2)

def load_logs():
    if LOG_FILE.exists():
        try:
            with open(LOG_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return []

def save_logs(logs):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "w") as f:
        json.dump(logs[-1000:], f, indent=2)

def add_log(logs, level, message):
    logs.append({"date": datetime.now().isoformat(), "level": level, "message": message})

# ── yt-dlp helper ─────────────────────────────────────────────────

def find_ytdlp():
    for name in ["yt-dlp", "yt-dlp.exe"]:
        path = shutil.which(name)
        if path:
            return path
    common = [
        Path.home() / "yt-dlp.exe",
        Path(r"C:\yt-dlp\yt-dlp.exe"),
        Path(r"C:\Program Files\yt-dlp\yt-dlp.exe"),
    ]
    for p in common:
        if p.exists():
            return str(p)
    return ""

def download_url(url, folder, vid_fmt, quality, aud_fmt, aud_bit, fragments=8, chunk_mb=10, priority="normal"):
    ytdlp = find_ytdlp()
    if not ytdlp:
        return {"ok": False, "error": "yt-dlp not found", "ext": "", "bytes": 0, "title": ""}

    os.makedirs(folder, exist_ok=True)
    args = [
        ytdlp, url, "-o", "%(title)s.%(ext)s", "-P", folder,
        "--no-playlist", "--no-overwrites",
        "--concurrent-fragments", str(fragments), "--retries", "5",
        "--fragment-retries", "5", "--buffer-size", "64K",
        "--http-chunk-size", f"{chunk_mb}M",
    ]
    is_audio_url = any(s in url.lower() for s in ["soundcloud.com", "spotify.com"])
    if is_audio_url:
        args += ["-x", "--audio-format", aud_fmt, "--audio-quality", aud_bit.replace("k", "")]
    else:
        if vid_fmt == "mp4":
            args += ["-f", f"bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"]
        elif vid_fmt == "webm":
            args += ["-f", "bestvideo[ext=webm]+bestaudio/best"]
        else:
            args += ["-f", "best"]
        if quality == "720p":
            args += ["-f", "bestvideo[height<=720]+bestaudio/best[height<=720]"]
        elif quality == "1080p":
            args += ["-f", "bestvideo[height<=1080]+bestaudio/best[height<=1080]"]
        elif quality == "4K":
            args += ["-f", "bestvideo[height<=2160]+bestaudio/best[height<=2160]"]

    args += ["--print-json"]
    try:
        creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        if sys.platform == "win32":
            if priority == "low":
                creationflags |= 0x00000040  # IDLE_PRIORITY_CLASS
            elif priority == "high":
                creationflags |= 0x00000080  # HIGH_PRIORITY_CLASS
        result = subprocess.run(args, capture_output=True, text=True, timeout=600,
                                creationflags=creationflags)
        if result.returncode == 0:
            try:
                info = json.loads(result.stdout.strip().split("\n")[-1])
                filepath = info.get("_filename", info.get("filepath", ""))
                fsize = os.path.getsize(filepath) if filepath and os.path.exists(filepath) else info.get("filesize", 0) or 0
                return {"ok": True, "error": None, "ext": os.path.splitext(filepath)[1],
                        "bytes": fsize, "title": info.get("title", "Media"), "path": filepath}
            except (json.JSONDecodeError, IndexError):
                return {"ok": True, "error": None, "ext": "", "bytes": 0, "title": "Media"}
        else:
            return {"ok": False, "error": result.stderr[:300], "ext": "", "bytes": 0, "title": ""}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "Download timed out (10 min)", "ext": "", "bytes": 0, "title": ""}
    except Exception as e:
        return {"ok": False, "error": str(e)[:300], "ext": "", "bytes": 0, "title": ""}

# ── Encryption ────────────────────────────────────────────────────

def encrypt_file(filepath, password):
    if not HAS_CRYPTO or not password:
        return
    key = hashlib.sha256(password.encode()).digest()
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    with open(filepath, "rb") as f:
        data = f.read()
    encrypted = aesgcm.encrypt(nonce, data, None)
    with open(filepath + ".enc", "wb") as f:
        f.write(nonce + encrypted)

# ── Format bytes ──────────────────────────────────────────────────

def fmt_bytes(b):
    if b < 1024: return f"{b} B"
    if b < 1024**2: return f"{b/1024:.1f} KB"
    if b < 1024**3: return f"{b/1024**2:.1f} MB"
    return f"{b/1024**3:.2f} GB"

# ── Long download warning ─────────────────────────────────────────

def get_download_warning(url, quality):
    u = url.lower()
    if quality in ("4K", "best"):
        if "youtube.com" in u or "youtu.be" in u:
            return "YouTube in high quality may take 30s-2min depending on length."
    if "instagram.com" in u and ("/reel" in u or "/tv" in u):
        return "Instagram video downloads may take 10-30s due to format merging."
    if "soundcloud.com" in u or "spotify.com" in u:
        return "Audio downloads require transcoding and may take 10-20s."
    if quality == "4K":
        return "4K downloads are large and may take 1-3 minutes."
    return None

# ── CSV URL extraction ────────────────────────────────────────────

URL_PATTERN = re.compile(r'https?://[^\s,"\'>]+')

def extract_urls_from_csv(filepath):
    urls = set()
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            reader = csv.reader(f)
            for row in reader:
                for cell in row:
                    for m in URL_PATTERN.finditer(cell):
                        urls.add(m.group())
    except Exception:
        pass
    return list(urls)

# ══════════════════════════════════════════════════════════════════
# ──  GUI Application  ────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.config_data = load_config()
        self.history = load_history()
        self.logs = load_logs()
        self.theme_name = self.config_data.get("theme", "Midnight")
        self.t = THEMES[self.theme_name]

        self.title(APP_NAME)
        self.geometry("1100x750")
        self.minsize(800, 600)
        self.configure(bg=self.t["bg"])

        try:
            icon_path = Path(__file__).parent / "icon.ico"
            if icon_path.exists():
                self.iconbitmap(str(icon_path))
        except Exception:
            pass

        self.current_page = "media"
        self.download_thread = None
        self.csv_futures = []

        self._build_ui()
        self._show_page("media")

    # ── Theme switching ───────────────────────────────────────────

    def apply_theme(self, name):
        if name not in THEMES:
            return
        self.theme_name = name
        self.t = THEMES[name]
        self.config_data["theme"] = name
        save_config(self.config_data)
        self.configure(bg=self.t["bg"])
        self._build_ui()
        self._show_page(self.current_page)

    # ── Build main UI ─────────────────────────────────────────────

    def _build_ui(self):
        for w in self.winfo_children():
            w.destroy()

        self.main = tk.Frame(self, bg=self.t["bg"])
        self.main.pack(fill="both", expand=True)

        self.sidebar = tk.Frame(self.main, bg=self.t["surface"], width=200)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        self.content = tk.Frame(self.main, bg=self.t["bg"])
        self.content.pack(side="left", fill="both", expand=True)

        self._build_sidebar()

    def _build_sidebar(self):
        for w in self.sidebar.winfo_children():
            w.destroy()

        pad_top = tk.Frame(self.sidebar, bg=self.t["surface"], height=18)
        pad_top.pack(fill="x")

        buttons = [
            ("Media", "media"),
            ("CSV Extractor", "csv"),
            ("Documents", "documents"),
        ]
        for label, page in buttons:
            self._sidebar_btn(label, page)

        sep1 = tk.Frame(self.sidebar, bg=self.t["border"], height=1)
        sep1.pack(fill="x", padx=20, pady=10)

        self._sidebar_btn("Settings", "settings")
        self._sidebar_btn("Logs", "logs")

        spacer = tk.Frame(self.sidebar, bg=self.t["surface"])
        spacer.pack(fill="both", expand=True)

        brand = tk.Frame(self.sidebar, bg=self.t["surface"])
        brand.pack(fill="x", padx=18, pady=(0, 16))
        tk.Label(brand, text="Media Extractor", font=("Segoe UI", 9),
                 fg=self.t["muted"], bg=self.t["surface"]).pack(anchor="w")
        tk.Label(brand, text=f"v{APP_VERSION}", font=("Consolas", 8),
                 fg=self.t["border"], bg=self.t["surface"]).pack(anchor="w")

    def _sidebar_btn(self, label, page):
        is_sel = self.current_page == page
        bg = self.t["surface_hover"] if is_sel else self.t["surface"]
        fg = self.t["text"] if is_sel else self.t["muted"]
        font = ("Segoe UI", 10, "bold") if is_sel else ("Segoe UI", 10)

        btn = tk.Label(self.sidebar, text=f"  {label}", font=font, fg=fg, bg=bg,
                       anchor="w", padx=10, pady=8, cursor="hand2")
        btn.pack(fill="x", padx=8, pady=1)
        btn.bind("<Button-1>", lambda e, p=page: self._show_page(p))
        btn.bind("<Enter>", lambda e, b=btn: b.configure(bg=self.t["surface_hover"]))
        btn.bind("<Leave>", lambda e, b=btn, s=is_sel: b.configure(bg=self.t["surface_hover"] if s else self.t["surface"]))

    # ── Page routing ──────────────────────────────────────────────

    def _show_page(self, page):
        self.current_page = page
        for w in self.content.winfo_children():
            w.destroy()
        self._build_sidebar()
        {
            "media": self._page_media,
            "csv": self._page_csv,
            "documents": self._page_documents,
            "settings": self._page_settings,
            "logs": self._page_logs,
        }.get(page, self._page_media)()

    # ── Media Page ────────────────────────────────────────────────

    def _page_media(self):
        scroll = self._scrollable(self.content)

        self._heading(scroll, "Media Downloader", "Paste any media link to download")

        url_frame = tk.Frame(scroll, bg=self.t["surface"], highlightthickness=1,
                             highlightbackground=self.t["border"])
        url_frame.pack(fill="x", pady=(0, 8))

        tk.Label(url_frame, text="\U0001f517", font=("Segoe UI", 12), bg=self.t["surface"],
                 fg=self.t["muted"]).pack(side="left", padx=(12, 6))

        self.url_var = tk.StringVar()
        url_entry = tk.Entry(url_frame, textvariable=self.url_var, font=("Consolas", 11),
                             bg=self.t["surface"], fg=self.t["text"], insertbackground=self.t["text"],
                             relief="flat", border=0)
        url_entry.pack(side="left", fill="x", expand=True, ipady=10)
        url_entry.insert(0, "")
        url_entry.bind("<KeyRelease>", self._on_url_change)

        self.platform_label = tk.Label(url_frame, text="", font=("Segoe UI", 9, "bold"),
                                       bg=self.t["surface"], fg=self.t["accent"])
        self.platform_label.pack(side="right", padx=12)

        self.warning_label = tk.Label(scroll, text="", font=("Segoe UI", 9),
                                      fg=self.t["accent"], bg=self.t["bg"], wraplength=600, anchor="w")
        self.warning_label.pack(fill="x", pady=(0, 4))

        self.preview_frame = tk.Frame(scroll, bg=self.t["bg"])
        self.preview_frame.pack(fill="x", pady=(0, 12))

        fmt_row = tk.Frame(scroll, bg=self.t["bg"])
        fmt_row.pack(fill="x", pady=(0, 12))

        vid_card = self._card(fmt_row, "Video")
        vid_card.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.vid_fmt_var = tk.StringVar(value=self.config_data.get("video_format", "mp4"))
        self.vid_qual_var = tk.StringVar(value=self.config_data.get("video_quality", "best"))
        self._dropdown_row(vid_card, "Format", self.vid_fmt_var, ["mp4", "webm", "mkv"])
        self._dropdown_row(vid_card, "Quality", self.vid_qual_var, ["best", "1080p", "720p", "4K"])

        aud_card = self._card(fmt_row, "Audio")
        aud_card.pack(side="left", fill="x", expand=True, padx=(6, 0))
        self.aud_fmt_var = tk.StringVar(value=self.config_data.get("audio_format", "mp3"))
        self.aud_bit_var = tk.StringVar(value=self.config_data.get("audio_bitrate", "320k"))
        self._dropdown_row(aud_card, "Format", self.aud_fmt_var, ["mp3", "m4a", "wav", "opus"])
        self._dropdown_row(aud_card, "Bitrate", self.aud_bit_var, ["320k", "256k", "192k", "128k"])

        self.dl_btn = tk.Label(scroll, text="⬇  Download", font=("Segoe UI", 11, "bold"),
                               fg=self.t["text"], bg=self.t["accent"] if self.theme_name != "Light" else self.t["accent"],
                               cursor="hand2", padx=20, pady=12, anchor="center")
        self.dl_btn.pack(fill="x", pady=(0, 8))
        self.dl_btn.bind("<Button-1>", self._start_download)

        self.status_label = tk.Label(scroll, text="", font=("Segoe UI", 9),
                                     fg=self.t["muted"], bg=self.t["bg"])
        self.status_label.pack(fill="x", pady=(0, 8))

        if self.history:
            self._heading(scroll, "Download History", "")
            for item in reversed(self.history[-20:]):
                self._history_row(scroll, item)

    def _on_url_change(self, event=None):
        url = self.url_var.get().strip()
        name, icon = detect_platform(url)
        if name:
            self.platform_label.config(text=f"{icon} {name}")
        else:
            self.platform_label.config(text="")

        warning = get_download_warning(url, self.vid_qual_var.get()) if url else None
        self.warning_label.config(text=f"⏰ {warning}" if warning else "")

        for w in self.preview_frame.winfo_children():
            w.destroy()
        vid = get_yt_video_id(url)
        if vid:
            pf = tk.Frame(self.preview_frame, bg=self.t["surface"], highlightthickness=1,
                          highlightbackground=self.t["border"])
            pf.pack(fill="x")
            tk.Label(pf, text=f"▶  YouTube Preview — Click to watch ad-free",
                     font=("Segoe UI", 10), fg=self.t["text"], bg=self.t["surface"],
                     pady=16, cursor="hand2").pack(fill="x")
            pf.bind("<Button-1>", lambda e, v=vid: webbrowser.open(f"https://www.youtube.com/watch?v={v}"))
            for child in pf.winfo_children():
                child.bind("<Button-1>", lambda e, v=vid: webbrowser.open(f"https://www.youtube.com/watch?v={v}"))
            badge = tk.Label(pf, text="Ad-Free Preview", font=("Segoe UI", 8),
                             fg=self.t["accent"], bg=self.t["surface"])
            badge.pack(anchor="e", padx=12, pady=(0, 8))

    def _start_download(self, event=None):
        url = self.url_var.get().strip()
        if not url:
            return
        if self.download_thread and self.download_thread.is_alive():
            return

        self.status_label.config(text="Downloading...", fg=self.t["accent"])
        self.dl_btn.config(bg=self.t["muted"])

        folder = self.config_data.get("download_folder", str(Path.home() / "Downloads" / "MediaExtractor"))

        def run():
            result = download_url(url, folder, self.vid_fmt_var.get(), self.vid_qual_var.get(),
                                  self.aud_fmt_var.get(), self.aud_bit_var.get(),
                                  self.config_data.get("concurrent_fragments", 8),
                                  self.config_data.get("chunk_size_mb", 10),
                                  self.config_data.get("process_priority", "normal"))
            entry = {
                "id": str(uuid.uuid4()), "url": url, "date": datetime.now().isoformat(),
                "status": "complete" if result["ok"] else "failed",
                "title": result.get("title", "Media"), "ext": result.get("ext", ""),
                "bytes": result.get("bytes", 0), "error": result.get("error"),
                "path": result.get("path", ""),
            }
            name, _ = detect_platform(url)
            entry["platform"] = name or "Unknown"

            if result["ok"] and self.config_data.get("encrypt") and self.config_data.get("encryption_password"):
                path = result.get("path", "")
                if path and os.path.exists(path):
                    encrypt_file(path, self.config_data["encryption_password"])

            self.history.append(entry)
            save_history(self.history)
            add_log(self.logs, "info" if result["ok"] else "error",
                    f"{'Downloaded' if result['ok'] else 'Failed'}: {url}" + (f" — {result['error']}" if result.get('error') else ""))
            save_logs(self.logs)

            self.after(0, lambda: self._download_done(result))

        self.download_thread = threading.Thread(target=run, daemon=True)
        self.download_thread.start()

    def _download_done(self, result):
        if result["ok"]:
            self.status_label.config(text=f"✅ Downloaded: {result.get('title', 'Media')} ({fmt_bytes(result.get('bytes', 0))})",
                                     fg=self.t["success"])
        else:
            self.status_label.config(text=f"❌ Failed: {result.get('error', 'Unknown error')}", fg=self.t["danger"])
        self.dl_btn.config(bg=self.t["accent"])

    def _history_row(self, parent, item):
        row = tk.Frame(parent, bg=self.t["surface"], highlightthickness=1,
                       highlightbackground=self.t["border"])
        row.pack(fill="x", pady=2)

        left = tk.Frame(row, bg=self.t["surface"])
        left.pack(side="left", fill="x", expand=True, padx=12, pady=8)

        top = tk.Frame(left, bg=self.t["surface"])
        top.pack(fill="x")

        platform = item.get("platform", "")
        if platform:
            tk.Label(top, text=platform, font=("Segoe UI", 8, "bold"),
                     fg=self.t["accent"], bg=self.t["surface"]).pack(side="left", padx=(0, 8))

        title = item.get("title", item.get("url", "")[:50])
        tk.Label(top, text=title, font=("Segoe UI", 9), fg=self.t["text"],
                 bg=self.t["surface"], anchor="w").pack(side="left", fill="x", expand=True)

        status = item.get("status", "unknown")
        status_color = self.t["success"] if status == "complete" else self.t["danger"]
        tk.Label(top, text=status.capitalize(), font=("Segoe UI", 8, "bold"),
                 fg=status_color, bg=self.t["surface"]).pack(side="right")

        bot = tk.Frame(left, bg=self.t["surface"])
        bot.pack(fill="x", pady=(2, 0))

        try:
            dt = datetime.fromisoformat(item.get("date", ""))
            date_str = dt.strftime("%b %d, %Y %I:%M %p")
        except Exception:
            date_str = ""
        tk.Label(bot, text=date_str, font=("Segoe UI", 8), fg=self.t["muted"],
                 bg=self.t["surface"]).pack(side="left")

        if item.get("bytes", 0) > 0:
            tk.Label(bot, text=f"  {fmt_bytes(item['bytes'])}", font=("Segoe UI", 8),
                     fg=self.t["muted"], bg=self.t["surface"]).pack(side="left")

        if item.get("path") and os.path.exists(item["path"]):
            open_btn = tk.Label(bot, text="Open", font=("Segoe UI", 8, "bold"),
                                fg=self.t["accent"], bg=self.t["surface"], cursor="hand2")
            open_btn.pack(side="right", padx=4)
            open_btn.bind("<Button-1>", lambda e, p=item["path"]: os.startfile(os.path.dirname(p)) if sys.platform == "win32" else subprocess.run(["open", os.path.dirname(p)]))

    # ── CSV Page ──────────────────────────────────────────────────

    def _page_csv(self):
        scroll = self._scrollable(self.content)
        self._heading(scroll, "CSV Batch Extractor", "Drop CSV files to extract and download media URLs")

        btn_row = tk.Frame(scroll, bg=self.t["bg"])
        btn_row.pack(fill="x", pady=(0, 12))

        add_btn = tk.Label(btn_row, text="+ Add CSV Files", font=("Segoe UI", 10, "bold"),
                           fg=self.t["accent"], bg=self.t["surface"], padx=16, pady=10, cursor="hand2")
        add_btn.pack(side="left")
        add_btn.bind("<Button-1>", self._add_csv_files)

        self.csv_status = tk.Label(scroll, text="", font=("Segoe UI", 9),
                                   fg=self.t["muted"], bg=self.t["bg"])
        self.csv_status.pack(fill="x", pady=(0, 8))

        self.csv_list_frame = tk.Frame(scroll, bg=self.t["bg"])
        self.csv_list_frame.pack(fill="x")

    def _add_csv_files(self, event=None):
        files = filedialog.askopenfilenames(filetypes=[("CSV files", "*.csv")])
        if not files:
            return

        folder = self.config_data.get("download_folder", str(Path.home() / "Downloads" / "MediaExtractor"))
        total_urls = 0

        for filepath in files:
            urls = extract_urls_from_csv(filepath)
            total_urls += len(urls)
            fname = os.path.basename(filepath)

            row = tk.Frame(self.csv_list_frame, bg=self.t["surface"], highlightthickness=1,
                           highlightbackground=self.t["border"])
            row.pack(fill="x", pady=2)
            tk.Label(row, text=f"\U0001f4c4 {fname}", font=("Segoe UI", 10),
                     fg=self.t["text"], bg=self.t["surface"], padx=12, pady=8).pack(side="left")
            tk.Label(row, text=f"{len(urls)} URLs found", font=("Segoe UI", 9),
                     fg=self.t["muted"], bg=self.t["surface"]).pack(side="left", padx=8)

            if urls:
                dl_label = tk.Label(row, text="Download All", font=("Segoe UI", 9, "bold"),
                                    fg=self.t["accent"], bg=self.t["surface"], cursor="hand2", padx=12)
                dl_label.pack(side="right", padx=8)
                dl_label.bind("<Button-1>", lambda e, u=urls, f=folder, fn=fname: self._csv_download_all(u, f, fn))

        self.csv_status.config(text=f"Found {total_urls} URLs across {len(files)} files")

    def _csv_download_all(self, urls, folder, csv_name):
        stem = Path(csv_name).stem
        target = os.path.join(folder, stem)
        os.makedirs(target, exist_ok=True)

        self.csv_status.config(text=f"Downloading {len(urls)} files from {csv_name}...")
        add_log(self.logs, "info", f"CSV batch: {len(urls)} URLs from {csv_name}")

        def run():
            ok, fail = 0, 0
            with ThreadPoolExecutor(max_workers=8) as pool:
                futures = {}
                for url in urls:
                    fut = pool.submit(self._csv_download_one, url.strip(), target)
                    futures[fut] = url
                for fut in as_completed(futures):
                    if fut.result():
                        ok += 1
                    else:
                        fail += 1
                    self.after(0, lambda o=ok, f=fail: self.csv_status.config(
                        text=f"Progress: {o} OK, {f} failed / {len(urls)} total"))

            add_log(self.logs, "info", f"CSV batch done: {ok} OK, {fail} failed")
            save_logs(self.logs)
            self.after(0, lambda: self.csv_status.config(
                text=f"Done! {ok} downloaded, {fail} failed from {csv_name}"))

        threading.Thread(target=run, daemon=True).start()

    def _csv_download_one(self, url, folder):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                ct = resp.headers.get("Content-Type", "")
                ext = ".jpg" if "image" in ct else ".mp4" if "video" in ct else ".bin"
                fname = str(uuid.uuid4())[:8] + ext
                path = os.path.join(folder, fname)
                with open(path, "wb") as f:
                    f.write(resp.read())
                return True
        except Exception:
            return False

    # ── Documents Page ────────────────────────────────────────────

    def _page_documents(self):
        scroll = self._scrollable(self.content)
        self._heading(scroll, "Documents", "Read PDFs and EPUBs with a fast, minimal viewer")

        btn_row = tk.Frame(scroll, bg=self.t["bg"])
        btn_row.pack(fill="x", pady=(0, 16))

        open_btn = tk.Label(btn_row, text="\U0001f4c4  Open Document", font=("Segoe UI", 11, "bold"),
                            fg=self.t["accent"], bg=self.t["surface"], padx=20, pady=14, cursor="hand2")
        open_btn.pack()
        open_btn.bind("<Button-1>", self._open_document)

        tk.Label(btn_row, text="Supports PDF and EPUB files", font=("Segoe UI", 8),
                 fg=self.t["muted"], bg=self.t["bg"]).pack(pady=(4, 0))

        recent = self.config_data.get("recent_documents", [])
        if recent:
            self._heading(scroll, "Recent Documents", "")
            for path in recent[:10]:
                if os.path.exists(path):
                    row = tk.Frame(scroll, bg=self.t["surface"], highlightthickness=1,
                                   highlightbackground=self.t["border"])
                    row.pack(fill="x", pady=1)
                    fname = os.path.basename(path)
                    icon = "PDF" if fname.lower().endswith(".pdf") else "EPUB"
                    tk.Label(row, text=f"  {icon}  {fname}", font=("Segoe UI", 9),
                             fg=self.t["text"], bg=self.t["surface"], anchor="w",
                             padx=8, pady=8, cursor="hand2").pack(side="left", fill="x", expand=True)
                    row.bind("<Button-1>", lambda e, p=path: self._view_document(p))
                    for child in row.winfo_children():
                        child.bind("<Button-1>", lambda e, p=path: self._view_document(p))

    def _open_document(self, event=None):
        filepath = filedialog.askopenfilename(filetypes=[("Documents", "*.pdf *.epub"), ("PDF files", "*.pdf"), ("EPUB files", "*.epub")])
        if filepath:
            self._view_document(filepath)

    def _view_document(self, filepath):
        recent = self.config_data.get("recent_documents", [])
        if filepath in recent:
            recent.remove(filepath)
        recent.insert(0, filepath)
        self.config_data["recent_documents"] = recent[:10]
        save_config(self.config_data)

        ext = os.path.splitext(filepath)[1].lower()
        if ext == ".pdf":
            self._view_pdf(filepath)
        elif ext == ".epub":
            self._view_epub(filepath)

    def _view_pdf(self, filepath):
        for w in self.content.winfo_children():
            w.destroy()

        toolbar = tk.Frame(self.content, bg=self.t["surface"])
        toolbar.pack(fill="x")

        back_btn = tk.Label(toolbar, text="← Library", font=("Segoe UI", 9, "bold"),
                            fg=self.t["accent"], bg=self.t["surface"], padx=12, pady=6, cursor="hand2")
        back_btn.pack(side="left")
        back_btn.bind("<Button-1>", lambda e: self._show_page("documents"))

        tk.Label(toolbar, text=os.path.basename(filepath), font=("Segoe UI", 9, "bold"),
                 fg=self.t["text"], bg=self.t["surface"]).pack(side="left", padx=12)

        try:
            if sys.platform == "win32":
                os.startfile(filepath)
            else:
                subprocess.run(["open", filepath])
        except Exception:
            pass

        info = tk.Frame(self.content, bg=self.t["bg"])
        info.pack(fill="both", expand=True)

        fsize = os.path.getsize(filepath) if os.path.exists(filepath) else 0

        tk.Label(info, text="\U0001f4c4", font=("Segoe UI", 48), fg=self.t["muted"],
                 bg=self.t["bg"]).pack(pady=(40, 10))
        tk.Label(info, text=os.path.basename(filepath), font=("Segoe UI", 14, "bold"),
                 fg=self.t["text"], bg=self.t["bg"]).pack()
        tk.Label(info, text=f"Size: {fmt_bytes(fsize)}", font=("Segoe UI", 9),
                 fg=self.t["muted"], bg=self.t["bg"]).pack(pady=(4, 0))
        tk.Label(info, text="Opened in your default PDF viewer", font=("Segoe UI", 9),
                 fg=self.t["accent"], bg=self.t["bg"]).pack(pady=(8, 0))

    def _view_epub(self, filepath):
        for w in self.content.winfo_children():
            w.destroy()

        toolbar = tk.Frame(self.content, bg=self.t["surface"])
        toolbar.pack(fill="x")

        back_btn = tk.Label(toolbar, text="← Library", font=("Segoe UI", 9, "bold"),
                            fg=self.t["accent"], bg=self.t["surface"], padx=12, pady=6, cursor="hand2")
        back_btn.pack(side="left")
        back_btn.bind("<Button-1>", lambda e: self._show_page("documents"))

        tk.Label(toolbar, text=os.path.basename(filepath), font=("Segoe UI", 9, "bold"),
                 fg=self.t["text"], bg=self.t["surface"]).pack(side="left", padx=12)

        try:
            if sys.platform == "win32":
                os.startfile(filepath)
            else:
                subprocess.run(["open", filepath])
        except Exception:
            pass

        info = tk.Frame(self.content, bg=self.t["bg"])
        info.pack(fill="both", expand=True)

        fsize = os.path.getsize(filepath) if os.path.exists(filepath) else 0

        tk.Label(info, text="\U0001f4d6", font=("Segoe UI", 48), fg=self.t["muted"],
                 bg=self.t["bg"]).pack(pady=(40, 10))
        tk.Label(info, text=os.path.basename(filepath), font=("Segoe UI", 14, "bold"),
                 fg=self.t["text"], bg=self.t["bg"]).pack()
        tk.Label(info, text=f"Size: {fmt_bytes(fsize)}", font=("Segoe UI", 9),
                 fg=self.t["muted"], bg=self.t["bg"]).pack(pady=(4, 0))
        tk.Label(info, text="Opened in your default EPUB reader", font=("Segoe UI", 9),
                 fg=self.t["accent"], bg=self.t["bg"]).pack(pady=(8, 0))

    # ── Settings Page ─────────────────────────────────────────────

    def _page_settings(self):
        scroll = self._scrollable(self.content)
        self._heading(scroll, "Settings", "")

        profile_card = tk.Frame(scroll, bg=self.t["surface"], highlightthickness=1,
                                highlightbackground=self.t["border"])
        profile_card.pack(fill="x", pady=(0, 12))

        prof_top = tk.Frame(profile_card, bg=self.t["surface"])
        prof_top.pack(fill="x", padx=14, pady=12)

        username = os.environ.get("USERNAME", os.environ.get("USER", "User"))
        avatar = tk.Label(prof_top, text=username[0].upper(), font=("Segoe UI", 18, "bold"),
                          fg=self.t["text"], bg=self.t["accent"], width=3, height=1)
        avatar.pack(side="left", padx=(0, 12))

        info = tk.Frame(prof_top, bg=self.t["surface"])
        info.pack(side="left", fill="x", expand=True)
        tk.Label(info, text=username, font=("Segoe UI", 12, "bold"),
                 fg=self.t["text"], bg=self.t["surface"]).pack(anchor="w")
        tk.Label(info, text=f"Media Extractor v{APP_VERSION}", font=("Segoe UI", 8),
                 fg=self.t["muted"], bg=self.t["surface"]).pack(anchor="w")

        stats = tk.Frame(prof_top, bg=self.t["surface"])
        stats.pack(side="right")
        tk.Label(stats, text=f"{len(self.history)} downloads", font=("Segoe UI", 9),
                 fg=self.t["muted"], bg=self.t["surface"]).pack(anchor="e")
        total_bytes = sum(h.get("bytes", 0) for h in self.history)
        tk.Label(stats, text=f"{fmt_bytes(total_bytes)} total", font=("Segoe UI", 8),
                 fg=self.t["border"], bg=self.t["surface"]).pack(anchor="e")

        sep = tk.Frame(profile_card, bg=self.t["border"], height=1)
        sep.pack(fill="x", padx=14)

        theme_section = tk.Frame(profile_card, bg=self.t["surface"])
        theme_section.pack(fill="x", padx=14, pady=12)

        tk.Label(theme_section, text="\U0001f3a8  Theme", font=("Segoe UI", 9, "bold"),
                 fg=self.t["muted"], bg=self.t["surface"]).pack(anchor="w", pady=(0, 8))

        theme_grid = tk.Frame(theme_section, bg=self.t["surface"])
        theme_grid.pack(fill="x")

        for i, tname in enumerate(THEMES.keys()):
            pal = THEMES[tname]
            is_current = tname == self.theme_name
            col = i % 4
            row = i // 4

            tf = tk.Frame(theme_grid, bg=self.t["surface"], cursor="hand2")
            tf.grid(row=row, column=col, padx=4, pady=4, sticky="ew")
            theme_grid.columnconfigure(col, weight=1)

            swatch = tk.Frame(tf, bg=pal["bg"], height=28, highlightthickness=2,
                              highlightbackground=self.t["accent"] if is_current else self.t["border"],
                              cursor="hand2")
            swatch.pack(fill="x")
            swatch.pack_propagate(False)

            dots = tk.Frame(swatch, bg=pal["bg"], cursor="hand2")
            dots.pack(expand=True)
            for c in [pal["accent"], pal["success"], pal["danger"]]:
                tk.Frame(dots, bg=c, width=6, height=6).pack(side="left", padx=1)

            font_w = "bold" if is_current else "normal"
            color = self.t["accent"] if is_current else self.t["muted"]
            lbl = tk.Label(tf, text=tname, font=("Segoe UI", 8, font_w), fg=color,
                           bg=self.t["surface"], cursor="hand2")
            lbl.pack(pady=(2, 0))

            for widget in [swatch, dots, lbl, tf]:
                widget.bind("<Button-1>", lambda e, n=tname: self.apply_theme(n))

        self._settings_card(scroll, "Download Folder",
                            "Where your downloaded files are saved.",
                            self._build_folder_setting)

        self._settings_card(scroll, "Default Formats",
                            "File type and quality for downloads.",
                            self._build_format_setting)

        ytdlp_path = find_ytdlp()
        self._settings_card(scroll, "yt-dlp",
                            "Download engine for video/audio.",
                            lambda parent: self._build_ytdlp_setting(parent, ytdlp_path))

        self._settings_card(scroll, "Encryption",
                            "Protect downloads with AES-256-GCM encryption.",
                            self._build_encryption_setting)

        self._settings_card(scroll, "Performance",
                            "Fine-tune download speed vs resource usage.",
                            self._build_performance_setting)

        self._settings_card(scroll, "Export as ZIP",
                            "Bundle your downloads into a .zip file.",
                            self._build_zip_setting)

        self._settings_card(scroll, "Data",
                            "Clear logs or download history.",
                            self._build_data_setting)

    def _build_folder_setting(self, parent):
        row = tk.Frame(parent, bg=self.t["surface"])
        row.pack(fill="x")
        folder = self.config_data.get("download_folder", "")
        tk.Label(row, text=folder, font=("Consolas", 9), fg=self.t["muted"],
                 bg=self.t["surface"], anchor="w").pack(side="left", fill="x", expand=True)
        change_btn = tk.Label(row, text="Change", font=("Segoe UI", 9, "bold"),
                              fg=self.t["accent"], bg=self.t["surface"], cursor="hand2")
        change_btn.pack(side="right")
        change_btn.bind("<Button-1>", self._change_folder)

    def _change_folder(self, event=None):
        folder = filedialog.askdirectory()
        if folder:
            self.config_data["download_folder"] = folder
            save_config(self.config_data)
            self._show_page("settings")

    def _build_format_setting(self, parent):
        row1 = tk.Frame(parent, bg=self.t["surface"])
        row1.pack(fill="x", pady=2)
        tk.Label(row1, text="Video Format", font=("Segoe UI", 9), fg=self.t["muted"],
                 bg=self.t["surface"]).pack(side="left")
        vid_fmt = ttk.Combobox(row1, values=["mp4", "webm", "mkv"], width=8, state="readonly")
        vid_fmt.set(self.config_data.get("video_format", "mp4"))
        vid_fmt.pack(side="left", padx=8)
        vid_fmt.bind("<<ComboboxSelected>>", lambda e: self._save_fmt("video_format", vid_fmt.get()))

        tk.Label(row1, text="Quality", font=("Segoe UI", 9), fg=self.t["muted"],
                 bg=self.t["surface"]).pack(side="left", padx=(16, 0))
        vid_qual = ttk.Combobox(row1, values=["best", "1080p", "720p", "4K"], width=8, state="readonly")
        vid_qual.set(self.config_data.get("video_quality", "best"))
        vid_qual.pack(side="left", padx=8)
        vid_qual.bind("<<ComboboxSelected>>", lambda e: self._save_fmt("video_quality", vid_qual.get()))

        row2 = tk.Frame(parent, bg=self.t["surface"])
        row2.pack(fill="x", pady=2)
        tk.Label(row2, text="Audio Format", font=("Segoe UI", 9), fg=self.t["muted"],
                 bg=self.t["surface"]).pack(side="left")
        aud_fmt = ttk.Combobox(row2, values=["mp3", "m4a", "wav", "opus"], width=8, state="readonly")
        aud_fmt.set(self.config_data.get("audio_format", "mp3"))
        aud_fmt.pack(side="left", padx=8)
        aud_fmt.bind("<<ComboboxSelected>>", lambda e: self._save_fmt("audio_format", aud_fmt.get()))

        tk.Label(row2, text="Bitrate", font=("Segoe UI", 9), fg=self.t["muted"],
                 bg=self.t["surface"]).pack(side="left", padx=(16, 0))
        aud_bit = ttk.Combobox(row2, values=["320k", "256k", "192k", "128k"], width=8, state="readonly")
        aud_bit.set(self.config_data.get("audio_bitrate", "320k"))
        aud_bit.pack(side="left", padx=8)
        aud_bit.bind("<<ComboboxSelected>>", lambda e: self._save_fmt("audio_bitrate", aud_bit.get()))

    def _save_fmt(self, key, val):
        self.config_data[key] = val
        save_config(self.config_data)

    def _build_ytdlp_setting(self, parent, path):
        if not path:
            warn = tk.Frame(parent, bg=self.t["surface"])
            warn.pack(fill="x")
            tk.Label(warn, text="⚠", font=("Segoe UI", 14), fg=self.t["danger"],
                     bg=self.t["surface"]).pack(side="left", padx=(0, 8))
            msg = tk.Frame(warn, bg=self.t["surface"])
            msg.pack(side="left", fill="x", expand=True)
            tk.Label(msg, text="yt-dlp is not installed", font=("Segoe UI", 10, "bold"),
                     fg=self.t["danger"], bg=self.t["surface"]).pack(anchor="w")
            tk.Label(msg, text="Required for downloading videos and audio.",
                     font=("Segoe UI", 8), fg=self.t["muted"], bg=self.t["surface"]).pack(anchor="w")

            dl_btn = tk.Label(parent, text="⬇  Download yt-dlp", font=("Segoe UI", 10, "bold"),
                              fg="#ffffff", bg=self.t["accent"], padx=14, pady=8, cursor="hand2")
            dl_btn.pack(anchor="w", pady=(8, 4))
            dl_btn.bind("<Button-1>", lambda e: webbrowser.open("https://github.com/yt-dlp/yt-dlp/releases/latest"))

            tk.Label(parent, text="Download the .exe and place it in your PATH or home folder.",
                     font=("Segoe UI", 8), fg=self.t["muted"], bg=self.t["surface"]).pack(anchor="w")
        else:
            row = tk.Frame(parent, bg=self.t["surface"])
            row.pack(fill="x")
            tk.Label(row, text="✅", font=("Segoe UI", 12), fg=self.t["success"],
                     bg=self.t["surface"]).pack(side="left", padx=(0, 8))
            tk.Label(row, text=path, font=("Consolas", 9), fg=self.t["success"],
                     bg=self.t["surface"]).pack(side="left")

    def _build_encryption_setting(self, parent):
        self.encrypt_var = tk.BooleanVar(value=self.config_data.get("encrypt", False))
        cb = tk.Checkbutton(parent, text="Encrypt downloaded files", variable=self.encrypt_var,
                            font=("Segoe UI", 9), fg=self.t["text"], bg=self.t["surface"],
                            selectcolor=self.t["surface"], activebackground=self.t["surface"],
                            command=self._toggle_encrypt)
        cb.pack(anchor="w")

        self.enc_pw_entry = tk.Entry(parent, show="•", font=("Consolas", 10),
                                     bg=self.t["bg"], fg=self.t["text"], insertbackground=self.t["text"],
                                     relief="flat", border=0)
        if self.config_data.get("encrypt"):
            self.enc_pw_entry.insert(0, self.config_data.get("encryption_password", ""))
            self.enc_pw_entry.pack(fill="x", pady=(6, 0), ipady=6)

        if not HAS_CRYPTO:
            tk.Label(parent, text="Install cryptography package: pip install cryptography",
                     font=("Segoe UI", 8), fg=self.t["danger"], bg=self.t["surface"]).pack(anchor="w", pady=(4, 0))

    def _toggle_encrypt(self):
        on = self.encrypt_var.get()
        self.config_data["encrypt"] = on
        if on:
            self.enc_pw_entry.pack(fill="x", pady=(6, 0), ipady=6)
        else:
            self.enc_pw_entry.pack_forget()
        self.config_data["encryption_password"] = self.enc_pw_entry.get()
        save_config(self.config_data)

    def _build_performance_setting(self, parent):
        row1 = tk.Frame(parent, bg=self.t["surface"])
        row1.pack(fill="x", pady=2)
        tk.Label(row1, text="Threads", font=("Segoe UI", 9), fg=self.t["muted"],
                 bg=self.t["surface"]).pack(side="left")
        threads_cb = ttk.Combobox(row1, values=["1", "2", "4", "8", "12", "16"], width=5, state="readonly")
        threads_cb.set(str(self.config_data.get("concurrent_fragments", 8)))
        threads_cb.pack(side="left", padx=8)
        threads_cb.bind("<<ComboboxSelected>>", lambda e: self._save_perf("concurrent_fragments", int(threads_cb.get())))

        tk.Label(row1, text="Chunk Size", font=("Segoe UI", 9), fg=self.t["muted"],
                 bg=self.t["surface"]).pack(side="left", padx=(16, 0))
        chunk_cb = ttk.Combobox(row1, values=["5 MB", "10 MB", "25 MB", "50 MB", "100 MB"], width=7, state="readonly")
        chunk_cb.set(f"{self.config_data.get('chunk_size_mb', 10)} MB")
        chunk_cb.pack(side="left", padx=8)
        chunk_cb.bind("<<ComboboxSelected>>", lambda e: self._save_perf("chunk_size_mb", int(chunk_cb.get().replace(" MB", ""))))

        row2 = tk.Frame(parent, bg=self.t["surface"])
        row2.pack(fill="x", pady=2)
        cpu_count = os.cpu_count() or 4
        tk.Label(row2, text="CPU Cores", font=("Segoe UI", 9), fg=self.t["muted"],
                 bg=self.t["surface"]).pack(side="left")
        cpu_cb = ttk.Combobox(row2, values=[str(i) for i in range(1, cpu_count + 1)], width=5, state="readonly")
        cpu_cb.set(str(self.config_data.get("max_cpu_cores", cpu_count)))
        cpu_cb.pack(side="left", padx=8)
        cpu_cb.bind("<<ComboboxSelected>>", lambda e: self._save_perf("max_cpu_cores", int(cpu_cb.get())))

        tk.Label(row2, text="RAM Limit", font=("Segoe UI", 9), fg=self.t["muted"],
                 bg=self.t["surface"]).pack(side="left", padx=(16, 0))
        ram_cb = ttk.Combobox(row2, values=["256 MB", "512 MB", "1024 MB", "2048 MB", "4096 MB"], width=8, state="readonly")
        ram_cb.set(f"{self.config_data.get('max_ram_mb', 512)} MB")
        ram_cb.pack(side="left", padx=8)
        ram_cb.bind("<<ComboboxSelected>>", lambda e: self._save_perf("max_ram_mb", int(ram_cb.get().replace(" MB", ""))))

        row3 = tk.Frame(parent, bg=self.t["surface"])
        row3.pack(fill="x", pady=2)
        tk.Label(row3, text="Priority", font=("Segoe UI", 9), fg=self.t["muted"],
                 bg=self.t["surface"]).pack(side="left")
        pri_cb = ttk.Combobox(row3, values=["low", "normal", "high"], width=8, state="readonly")
        pri_cb.set(self.config_data.get("process_priority", "normal"))
        pri_cb.pack(side="left", padx=8)
        pri_cb.bind("<<ComboboxSelected>>", lambda e: self._save_perf("process_priority", pri_cb.get()))

        tk.Label(parent, text="More threads & larger chunks = faster downloads. Lower priority = less system impact.",
                 font=("Segoe UI", 8), fg=self.t["muted"], bg=self.t["surface"], wraplength=500).pack(anchor="w", pady=(4, 0))

    def _save_perf(self, key, val):
        self.config_data[key] = val
        save_config(self.config_data)

    def _build_zip_setting(self, parent):
        tk.Label(parent, text="Package your download folder into a ZIP archive.",
                 font=("Segoe UI", 8), fg=self.t["muted"], bg=self.t["surface"]).pack(anchor="w")
        btn = tk.Label(parent, text="\U0001f4e6  Create ZIP Archive", font=("Segoe UI", 10, "bold"),
                       fg=self.t["accent"], bg=self.t["surface"], cursor="hand2", pady=8)
        btn.pack(anchor="w", pady=(6, 0))
        btn.bind("<Button-1>", self._create_zip)

    def _create_zip(self, event=None):
        src = self.config_data.get("download_folder", "")
        if not os.path.isdir(src):
            messagebox.showwarning("No folder", "Download folder doesn't exist yet.")
            return
        dest = filedialog.asksaveasfilename(defaultextension=".zip",
                                            initialfile=f"MediaExtractor_{datetime.now().strftime('%Y%m%d')}.zip",
                                            filetypes=[("ZIP files", "*.zip")])
        if not dest:
            return
        try:
            shutil.make_archive(dest.replace(".zip", ""), "zip", src)
            add_log(self.logs, "info", f"Exported ZIP: {os.path.basename(dest)}")
            save_logs(self.logs)
            if sys.platform == "win32":
                os.startfile(os.path.dirname(dest))
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _build_data_setting(self, parent):
        row = tk.Frame(parent, bg=self.t["surface"])
        row.pack(fill="x")
        clear_logs_btn = tk.Label(row, text="Clear Logs", font=("Segoe UI", 9, "bold"),
                                  fg=self.t["danger"], bg=self.t["surface"], cursor="hand2")
        clear_logs_btn.pack(side="left", padx=(0, 12))
        clear_logs_btn.bind("<Button-1>", lambda e: (self.logs.clear(), save_logs(self.logs)))

        clear_hist_btn = tk.Label(row, text="Clear Download History", font=("Segoe UI", 9, "bold"),
                                  fg=self.t["danger"], bg=self.t["surface"], cursor="hand2")
        clear_hist_btn.pack(side="left")
        clear_hist_btn.bind("<Button-1>", lambda e: (self.history.clear(), save_history(self.history), self._show_page("settings")))

    # ── Logs Page ─────────────────────────────────────────────────

    def _page_logs(self):
        scroll = self._scrollable(self.content)
        self._heading(scroll, "Activity Log", f"{len(self.logs)} entries")

        for entry in reversed(self.logs[-100:]):
            row = tk.Frame(scroll, bg=self.t["surface"], highlightthickness=1,
                           highlightbackground=self.t["border"])
            row.pack(fill="x", pady=1)

            level = entry.get("level", "info")
            color = self.t["success"] if level == "info" else self.t["danger"] if level == "error" else self.t["accent"]

            tk.Label(row, text=level.upper(), font=("Consolas", 8, "bold"), fg=color,
                     bg=self.t["surface"], width=6).pack(side="left", padx=(8, 4), pady=6)

            try:
                dt = datetime.fromisoformat(entry.get("date", ""))
                time_str = dt.strftime("%H:%M:%S")
            except Exception:
                time_str = ""
            tk.Label(row, text=time_str, font=("Consolas", 8), fg=self.t["muted"],
                     bg=self.t["surface"]).pack(side="left", padx=(0, 8))

            tk.Label(row, text=entry.get("message", ""), font=("Segoe UI", 9),
                     fg=self.t["text"], bg=self.t["surface"], anchor="w",
                     wraplength=700).pack(side="left", fill="x", expand=True, padx=(0, 8), pady=6)

    # ── Shared UI helpers ─────────────────────────────────────────

    def _scrollable(self, parent):
        canvas = tk.Canvas(parent, bg=self.t["bg"], highlightthickness=0)
        scrollbar = tk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        frame = tk.Frame(canvas, bg=self.t["bg"])

        frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))

        inner = tk.Frame(frame, bg=self.t["bg"])
        inner.pack(fill="x", expand=True, padx=32, pady=24)
        return inner

    def _heading(self, parent, title, subtitle):
        tk.Label(parent, text=title, font=("Segoe UI", 16, "bold"),
                 fg=self.t["text"], bg=self.t["bg"], anchor="w").pack(fill="x", pady=(0, 2))
        if subtitle:
            tk.Label(parent, text=subtitle, font=("Segoe UI", 9),
                     fg=self.t["muted"], bg=self.t["bg"], anchor="w").pack(fill="x", pady=(0, 12))

    def _card(self, parent, title):
        frame = tk.Frame(parent, bg=self.t["surface"], highlightthickness=1,
                         highlightbackground=self.t["border"])
        tk.Label(frame, text=title, font=("Segoe UI", 10, "bold"),
                 fg=self.t["muted"], bg=self.t["surface"], anchor="w").pack(fill="x", padx=12, pady=(10, 4))
        return frame

    def _dropdown_row(self, parent, label, var, options):
        row = tk.Frame(parent, bg=self.t["surface"])
        row.pack(fill="x", padx=12, pady=3)
        tk.Label(row, text=label, font=("Segoe UI", 9), fg=self.t["muted"],
                 bg=self.t["surface"]).pack(side="left")
        combo = ttk.Combobox(row, textvariable=var, values=options, width=8, state="readonly")
        combo.pack(side="right")

    def _settings_card(self, parent, title, info, build_fn):
        card = tk.Frame(parent, bg=self.t["surface"], highlightthickness=1,
                        highlightbackground=self.t["border"])
        card.pack(fill="x", pady=(0, 8))

        header = tk.Frame(card, bg=self.t["surface"])
        header.pack(fill="x", padx=14, pady=(10, 4))
        tk.Label(header, text=title, font=("Segoe UI", 10, "bold"),
                 fg=self.t["muted"], bg=self.t["surface"]).pack(side="left")

        if info:
            info_btn = tk.Label(header, text="ⓘ", font=("Segoe UI", 10),
                                fg=self.t["muted"], bg=self.t["surface"], cursor="hand2")
            info_btn.pack(side="left", padx=6)
            info_btn.bind("<Button-1>", lambda e, t=title, i=info: messagebox.showinfo(t, i))

        content = tk.Frame(card, bg=self.t["surface"])
        content.pack(fill="x", padx=14, pady=(0, 10))
        build_fn(content)


# ── Entry point ───────────────────────────────────────────────────

if __name__ == "__main__":
    app = App()
    app.mainloop()
