# MP4 Video Downloader

Download videos in the highest available resolution from YouTube, Vimeo, Twitter/X, TikTok, Instagram, and 1000+ sites.

## Requirements

- Python 3.8+
- ffmpeg (for merging video + audio into a single MP4)

## Install ffmpeg

| OS | Command |
|---|---|
| Windows | `winget install ffmpeg` |
| macOS | `brew install ffmpeg` |
| Ubuntu/Debian | `sudo apt install ffmpeg` |

## Setup & Run

```bash
cd mp4-downloader

# Optional: create a virtual environment
python -m venv venv
source venv/bin/activate      # macOS/Linux
venv\Scripts\activate         # Windows

pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000 in your browser.

## How to use

1. Paste any video URL into the input field
2. Click **Fetch** — the app loads available resolutions with file sizes
3. Pick your preferred resolution (highest is selected by default)
4. Click **Download MP4**
5. Watch the progress bar, then click **Download** when done

Downloaded files are saved to the `downloads/` folder and also offered as a browser download.

## Notes

- High-resolution YouTube videos (1080p+) come as separate video+audio streams — ffmpeg merges them automatically
- Files are saved as MP4 with H.264 video where possible
