import os
import re
import shutil
import sys
import threading
import uuid
from flask import Flask, request, jsonify, send_file, render_template

app = Flask(__name__)

DOWNLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads")
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

job_status = {}


def find_ffmpeg():
    if shutil.which("ffmpeg"):
        return None
    win_paths = [
        r"C:\ffmpeg\bin", r"C:\Program Files\ffmpeg\bin",
        os.path.expanduser(r"~\ffmpeg\bin"),
    ]
    for p in win_paths:
        if os.path.isfile(os.path.join(p, "ffmpeg.exe")):
            return p
    unix_paths = ["/usr/local/bin", "/opt/homebrew/bin", "/usr/bin"]
    for p in unix_paths:
        if os.path.isfile(os.path.join(p, "ffmpeg")):
            return p
    return "NOT_FOUND"


FFMPEG_LOCATION = find_ffmpeg()


def sanitize(name):
    return re.sub(r'[\\/*?:"<>|]', "_", name)


def fetch_formats(url):
    import yt_dlp
    ydl_opts = {"quiet": True, "no_warnings": True, "skip_download": True}
    if FFMPEG_LOCATION and FFMPEG_LOCATION != "NOT_FOUND":
        ydl_opts["ffmpeg_location"] = FFMPEG_LOCATION
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        title = info.get("title", "video")
        thumbnail = info.get("thumbnail", "")
        duration = info.get("duration", 0)

        seen = {}
        for f in info.get("formats", []):
            h = f.get("height")
            ext = f.get("ext", "")
            vcodec = f.get("vcodec", "none")
            if not h or vcodec == "none":
                continue
            label = f"{h}p"
            fsize = f.get("filesize") or f.get("filesize_approx") or 0
            if label not in seen or fsize > seen[label].get("filesize", 0):
                seen[label] = {
                    "format_id": f["format_id"],
                    "label": label,
                    "height": h,
                    "ext": ext,
                    "filesize": fsize,
                    "fps": f.get("fps", ""),
                    "vcodec": vcodec,
                }

        formats = sorted(seen.values(), key=lambda x: x["height"], reverse=True)
        return {"title": title, "thumbnail": thumbnail, "duration": duration, "formats": formats}


def download_video(url, format_id, title, job_id):
    import yt_dlp
    try:
        safe_title = sanitize(title)
        out_path = os.path.join(DOWNLOAD_FOLDER, f"{safe_title}.%(ext)s")

        ydl_opts = {
            "format": f"{format_id}+bestaudio/best",
            "outtmpl": out_path,
            "merge_output_format": "mp4",
            "progress_hooks": [lambda d: _hook(d, job_id)],
            "quiet": True,
            "no_warnings": True,
        }
        if FFMPEG_LOCATION and FFMPEG_LOCATION != "NOT_FOUND":
            ydl_opts["ffmpeg_location"] = FFMPEG_LOCATION

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        final = os.path.join(DOWNLOAD_FOLDER, f"{safe_title}.mp4")
        if not os.path.exists(final):
            candidates = [f for f in os.listdir(DOWNLOAD_FOLDER) if f.startswith(safe_title)]
            final = os.path.join(DOWNLOAD_FOLDER, candidates[0]) if candidates else None

        job_status[job_id].update({
            "status": "done",
            "progress": 100,
            "message": "Download complete!",
            "filename": os.path.basename(final),
            "filepath": final,
        })
    except Exception as e:
        job_status[job_id] = {"status": "error", "progress": 0, "message": str(e)}


def _hook(d, job_id):
    if d["status"] == "downloading":
        raw = d.get("_percent_str", "0%").strip().replace("%", "").replace("\x1b[0;94m", "").replace("\x1b[0m", "")
        try:
            pct = float(raw)
        except Exception:
            pct = 0
        job_status[job_id] = {
            "status": "downloading",
            "progress": round(pct),
            "message": f"{d.get('_speed_str','').strip()}  ETA {d.get('_eta_str','').strip()}",
        }
    elif d["status"] == "finished":
        job_status[job_id] = {"status": "merging", "progress": 95, "message": "Merging audio + video..."}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/info", methods=["POST"])
def info():
    url = (request.get_json() or {}).get("url", "").strip()
    if not url:
        return jsonify({"error": "No URL"}), 400
    try:
        data = fetch_formats(url)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/download", methods=["POST"])
def start_download():
    body = request.get_json() or {}
    url = body.get("url", "").strip()
    format_id = body.get("format_id", "bestvideo")
    title = body.get("title", "video")
    if not url:
        return jsonify({"error": "No URL"}), 400

    job_id = str(uuid.uuid4())
    job_status[job_id] = {"status": "queued", "progress": 0, "message": "Starting..."}
    t = threading.Thread(target=download_video, args=(url, format_id, title, job_id))
    t.daemon = True
    t.start()
    return jsonify({"job_id": job_id})


@app.route("/status/<job_id>")
def status(job_id):
    return jsonify(job_status.get(job_id, {"status": "not_found"}))


@app.route("/file/<job_id>")
def serve_file(job_id):
    info = job_status.get(job_id)
    if not info or info.get("status") != "done":
        return jsonify({"error": "Not ready"}), 404
    fp = info.get("filepath")
    if not fp or not os.path.exists(fp):
        return jsonify({"error": "File missing"}), 404
    return send_file(fp, as_attachment=True, download_name=info.get("filename"), mimetype="video/mp4")


if __name__ == "__main__":
    ffmpeg_ok = FFMPEG_LOCATION != "NOT_FOUND"
    print("\n  MP4 Video Downloader")
    if not ffmpeg_ok:
        print("  WARNING: ffmpeg not found!")
        print("  Windows: winget install ffmpeg")
        print("  macOS:   brew install ffmpeg")
        print("  Linux:   sudo apt install ffmpeg")
    else:
        print(f"  ffmpeg: {FFMPEG_LOCATION or 'system PATH'}")
    print("  Running at http://127.0.0.1:5000\n")
    app.run(debug=False, port=5000)
