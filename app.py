from flask import Flask, render_template, request, send_file, jsonify
from werkzeug.utils import secure_filename
import os, subprocess, uuid

app = Flask(__name__)
UPLOAD = "uploads"
OUT = "outputs"
os.makedirs(UPLOAD, exist_ok=True)
os.makedirs(OUT, exist_ok=True)

@app.get("/")
def index():
    return render_template("index.html")

@app.post("/upload")
def upload():
    f = request.files.get("video")
    if not f or not f.filename:
        return jsonify(error="Video belum dipilih"), 400
    ext = f.filename.rsplit(".", 1)[-1].lower()
    if ext not in {"mp4", "mov", "webm", "mkv"}:
        return jsonify(error="Format video tidak didukung"), 400
    name = uuid.uuid4().hex + "." + ext
    f.save(os.path.join(UPLOAD, name))
    return jsonify(filename=name)

@app.post("/clip")
def clip():
    d = request.json or {}
    src = os.path.join(UPLOAD, secure_filename(d.get("filename", "")))
    if not os.path.exists(src):
        return jsonify(error="Video tidak ditemukan"), 404
    try:
        start = float(d.get("start", 0))
        end = float(d.get("end", 30))
        if end <= start:
            return jsonify(error="Waktu selesai harus lebih besar dari waktu mulai"), 400
        ratio = d.get("ratio", "9:16")
        if ratio == "9:16":
            vf = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"
        elif ratio == "1:1":
            vf = "scale=1080:1080:force_original_aspect_ratio=increase,crop=1080:1080"
        else:
            vf = "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080"
        filename = secure_filename(d.get("name", "clip")) or "clip"
        out = os.path.join(OUT, uuid.uuid4().hex + "_" + filename + ".mp4")
        cmd = [
            "ffmpeg", "-y", "-ss", str(start), "-i", src, "-t", str(end-start),
            "-vf", vf, "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
            "-c:a", "aac", "-movflags", "+faststart", out
        ]
        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if p.returncode:
            return jsonify(error="FFmpeg gagal", details=p.stderr[-1000:]), 500
        return jsonify(download="/download/" + os.path.basename(out))
    except Exception as e:
        return jsonify(error=str(e)), 500

@app.get("/download/<name>")
def download(name):
    path = os.path.join(OUT, secure_filename(name))
    if not os.path.exists(path):
        return "Tidak ditemukan", 404
    return send_file(path, as_attachment=True, download_name="clip.mp4")

@app.post("/analyze")
def analyze():
    return jsonify(candidates=[
        {"start": 12, "end": 58, "title": "Momen dengan hook kuat", "reason": "Pembukaan langsung ke inti", "score": 96},
        {"start": 91, "end": 140, "title": "Cerita paling menarik", "reason": "Storytelling dan emosi", "score": 92},
        {"start": 205, "end": 252, "title": "Tips yang actionable", "reason": "Ada poin praktis", "score": 89},
        {"start": 318, "end": 365, "title": "Momen paling menghibur", "reason": "Punchline / reaction", "score": 86}
    ])

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
