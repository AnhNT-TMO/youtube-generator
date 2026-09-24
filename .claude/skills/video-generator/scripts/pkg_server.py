#!/usr/bin/env python3
import glob
import hashlib
import http.client
import json
import os
import subprocess
import sys
import time
import urllib.parse
import zipfile


def sha256(path, bs=8 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for b in iter(lambda: fh.read(bs), b""):
            h.update(b)
    return h.hexdigest()


def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", path],
                         capture_output=True, text=True, check=True).stdout
    d = json.loads(out)
    v = next((s for s in d["streams"] if s["codec_type"] == "video"), {})
    a = next((s for s in d["streams"] if s["codec_type"] == "audio"), {})
    num, _, den = (v.get("avg_frame_rate") or "0/1").partition("/")
    return {"duration": round(float(d["format"]["duration"]), 2), "width": v.get("width"), "height": v.get("height"),
            "video_codec": v.get("codec_name"), "fps": round(float(num) / float(den or 1), 3),
            "audio_codec": a.get("codec_name"), "audio_sample_rate": a.get("sample_rate"),
            "bit_rate": int(d["format"].get("bit_rate") or 0)}


def fmt(s):
    s = int(round(s))
    return f"{s // 3600}:{s // 60 % 60:02d}:{s % 60:02d}" if s >= 3600 else f"{s // 60}:{s % 60:02d}"


README = """{title}
Gói upload YouTube · {slug} · tạo {created}

Trong gói
  {video_name:<22} video chính ({width}×{height}, {duration}, {size_gb:.2f} GB)
  thumbnail.jpg          ảnh thumbnail để upload lên YouTube (≤ 2 MB, {jpg_w}×{jpg_h})
  {full_name:<22} ảnh thumbnail gốc độ phân giải đầy đủ ({full_w}×{full_h}), để lưu trữ / community post
  youtube.md             bản đầy đủ: title + phương án khác, description, tags, pinned comment, cài đặt Studio
  upload/title.txt       dán vào ô Title
  upload/description.txt dán vào ô Description (đã có TRACKLIST = chapters)
  upload/tags.txt        dán vào ô Tags
  upload/pinned_comment.txt  đăng làm comment đầu rồi ghim
  manifest.json          kích thước + sha256 từng file, thông số video

Các bước trong YouTube Studio
  1. Upload {video_name}, dán title / description / tags từ upload/.
  2. Thumbnail: thumbnail.jpg.
  3. Altered or synthetic content: Yes. Không ghi dòng AI trong description.
  4. Các mục còn lại: bảng "Cài đặt khi upload" trong youtube.md.
  5. Sau khi đăng: đăng + ghim pinned comment, điền Video URL vào youtube.md.
{warn}"""


def cmd_build(a):
    pkg, video, zip_out = a[0], a[1], a[3]
    audio = next(iter(sorted(glob.glob(os.path.join(a[2], "audio.*")))), None)
    name = a[a.index("--video-name") + 1]
    meta_f = os.path.join(pkg, "meta.json")
    meta = json.load(open(meta_f)) if os.path.exists(meta_f) else {}
    dst = os.path.join(pkg, name)
    if os.path.exists(dst):
        os.remove(dst)
    os.link(video, dst)
    v = probe(dst)
    warnings = list(meta.get("warnings", []))
    if (v["width"], v["height"]) != (3840, 2160):
        warnings.append(f"video {v['width']}×{v['height']}, không phải 4K (3840×2160)")
    if audio:
        ad = probe(audio)["duration"]
        if abs(ad - v["duration"]) > 1.5:
            warnings.append(f"video dài {fmt(v['duration'])} ≠ audio đã ghép {fmt(ad)}")
    files = {}
    for root, _, names in os.walk(pkg):
        for n in sorted(names):
            p = os.path.join(root, n)
            if p == meta_f:
                continue
            files[os.path.relpath(p, pkg)] = {"size": os.path.getsize(p), "sha256": sha256(p)}
    manifest = {"slug": os.path.basename(pkg), "created": meta.get("created"), "title": meta.get("title"),
                "channel": meta.get("channel"), "source_audio": meta.get("source_audio"),
                "video": dict(v, file=name), "thumbnail": meta.get("thumbnail"), "youtube": meta.get("youtube"),
                "files": files, "warnings": warnings}
    json.dump(manifest, open(os.path.join(pkg, "manifest.json"), "w"), indent=1, ensure_ascii=False)
    th = meta.get("thumbnail") or {}
    open(os.path.join(pkg, "README.txt"), "w").write(README.format(
        title=meta.get("title") or manifest["slug"], slug=manifest["slug"], created=meta.get("created"),
        video_name=name, width=v["width"], height=v["height"], duration=fmt(v["duration"]),
        size_gb=files[name]["size"] / 1e9, jpg_w=th.get("jpg_width"), jpg_h=th.get("jpg_height"),
        full_name=th.get("full_file", "thumbnail_full.png"), full_w=th.get("width"), full_h=th.get("height"),
        warn="".join(f"\n⚠ {w}" for w in warnings)))
    if os.path.exists(meta_f):
        os.remove(meta_f)

    top = os.path.basename(pkg)
    tmp = zip_out + ".part"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_STORED, allowZip64=True) as z:
        for root, _, names in os.walk(pkg):
            for n in sorted(names):
                p = os.path.join(root, n)
                z.write(p, os.path.join(top, os.path.relpath(p, pkg)))
    os.replace(tmp, zip_out)
    print(json.dumps({"zip": zip_out, "size": os.path.getsize(zip_out), "sha256": sha256(zip_out),
                      "video": v, "files": files, "warnings": warnings}, ensure_ascii=False))


class _Slice:

    def __init__(self, fh, start, n):
        self.fh, self.left = fh, n
        fh.seek(start)

    def read(self, size=-1):
        if self.left <= 0:
            return b""
        b = self.fh.read(self.left if size < 0 else min(size, self.left))
        self.left -= len(b)
        return b


def _put(url, fh, start, n):
    u = urllib.parse.urlsplit(url)
    conn = http.client.HTTPSConnection(u.hostname, timeout=900, blocksize=1 << 20)
    conn.request("PUT", u.path + "?" + u.query, body=_Slice(fh, start, n), headers={"Content-Length": str(n)})
    r = conn.getresponse()
    body = r.read()
    if r.status != 200:
        raise RuntimeError(f"HTTP {r.status}: {body[:300]!r}")
    return r.getheader("ETag")


def cmd_upload(a):
    zip_path, spec = a[0], json.load(open(a[1]))
    size = os.path.getsize(zip_path)
    t0 = time.time()
    part, etags = spec["part_size"], []
    if part * len(spec["urls"]) < size:
        sys.exit(f"presign chỉ đủ {len(spec['urls'])} part cho {size} byte")
    with open(zip_path, "rb") as fh:
        for i, url in enumerate(spec["urls"]):
            start = i * part
            n = min(part, size - start)
            if n <= 0:
                break
            for attempt in range(3):
                try:
                    etags.append(_put(url, fh, start, n))
                    break
                except Exception as e:            # noqa: BLE001 - retry any network error
                    if attempt == 2:
                        sys.exit(f"part {i + 1}: {e}")
                    time.sleep(5 * (attempt + 1))
            print(f"part {i + 1}/{len(spec['urls'])} ok ({time.time() - t0:.0f}s)", file=sys.stderr, flush=True)
    print(f"uploaded {size / 1e9:.2f} GB in {time.time() - t0:.0f}s", file=sys.stderr)
    print(json.dumps({"etags": etags}))


if __name__ == "__main__":
    {"build": cmd_build, "upload": cmd_upload}[sys.argv[1]](sys.argv[2:])
