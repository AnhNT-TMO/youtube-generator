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


def human(n):
    return f"{n / 1e9:.2f} GB" if n >= 1e9 else f"{n / 1e6:.1f} MB"


STEPS = {
    "album": ["Upload {video}, dán title / description / tags từ {up}.",
              "Thumbnail: {thumb}.",
              "Altered or synthetic content: Yes. Không ghi dòng AI trong description.",
              "Các mục còn lại: bảng \"Cài đặt khi upload\" trong {ytmd}.",
              "Sau khi đăng: đăng + ghim pinned comment, điền Video URL vào youtube.md."],
    "short": ["Upload {video} (dọc, ≤ 3 phút: YouTube tự xếp vào Shorts), dán title / description / tags từ {up}.",
              "Altered or synthetic content: Yes. Audience: No, it's not made for kids.",
              "Related video: video album vừa upload ở bước 1.",
              "Các mục còn lại: mục \"YouTube Studio\" trong {ytmd}.",
              "Sau khi đăng: đăng + ghim pinned comment."],
}


def part_lines(n, p, part, files):
    pre = p["sub"] + "/" if p["sub"] else ""
    th, v = part.get("thumbnail") or {}, part["video"]
    full = th.get("full_file", "thumbnail_full.png")
    what = "Short dọc" if p["key"] == "short" else "chính"
    rows = [(pre + p["name"], f"video {what} ({v['width']}×{v['height']}, {fmt(v['duration'])}, "
                              f"{human(files[pre + p['name']]['size'])})"),
            (pre + "thumbnail.jpg", f"ảnh thumbnail để upload lên YouTube (≤ 2 MB, {th.get('jpg_width')}×{th.get('jpg_height')})"),
            (pre + full, f"ảnh gốc độ phân giải đầy đủ ({th.get('width')}×{th.get('height')}), để lưu trữ / community post"),
            (pre + "youtube.md", "bản đầy đủ: title + phương án khác, description, tags, pinned comment, cài đặt Studio"),
            (pre + "upload/title.txt", "dán vào ô Title"),
            (pre + "upload/description.txt", "dán vào ô Description"
             + (" (đã có TRACKLIST = chapters)" if p["key"] == "album" else "")),
            (pre + "upload/tags.txt", "dán vào ô Tags"),
            (pre + "upload/pinned_comment.txt", "đăng làm comment đầu rồi ghim")]
    head = {"album": "ALBUM", "short": "SHORT (thư mục short/, đăng sau album)"}.get(p["key"], "VIDEO")
    out = [f"{n}. {head}: {part.get('title') or p['name']}"]
    out += [f"  {a:<34} {b}" for a, b in rows]
    out.append("  Các bước trong YouTube Studio")
    out += [f"    {i}. " + s.format(video=pre + p["name"], up=pre + "upload/", thumb=pre + "thumbnail.jpg",
                                     ytmd=pre + "youtube.md")
            for i, s in enumerate(STEPS["short" if p["key"] == "short" else "album"], 1)]
    if p["key"] == "short" and "youtu" not in open(os.path.join(p["dir"], "upload", "description.txt")).read():
        out.append("  ⚠ description của Short chưa có link album: sau khi upload album, dán Video URL của album vào "
                   "description + pinned comment (dòng link album).")
    return out


def readme(spec, parts, files, warnings, created):
    main = spec["parts"][0]
    lines = [parts[main["key"]].get("title") or spec["name"],
             f"Gói upload YouTube · {spec['name']} · tạo {created}"]
    if spec["kind"] == "album":
        short = next((p for p in spec["parts"] if p["key"] == "short"), None)
        lines.append("Một zip cho cả gói: video album (thư mục này) + Short (short/)." if short else
                     "Gói này CHỈ có video album (--no-short): Short không nằm trong zip này.")
        lines += ["", "THỨ TỰ UPLOAD", f"  1. Album: {main['name']}."]
        if short:
            lines.append(f"  2. Short: short/{short['name']}, sau album; Related video = album ở bước 1.")
        lines.append("  AI: Altered or synthetic content = Yes cho " + ("cả hai video" if short else "video")
                     + "; không ghi dòng AI trong description.")
        if spec.get("order"):
            lines.append(f"  Theo channel/{spec['channel']}/publish.md:")
            lines += [f"    {x}" for x in spec["order"]]
    for n, p in enumerate(spec["parts"], 1):
        lines += [""] + part_lines(n, p, parts[p["key"]], files)
    lines += ["", f"  {'manifest.json':<34} kích thước + sha256 từng file, thông số video"]
    lines += [f"⚠ {w}" for w in warnings]
    return "\n".join(lines) + "\n"


def cmd_build(a):
    spec = json.load(open(os.path.expanduser(a[0])))
    top, zip_out = os.path.expanduser(spec["pkg"]), os.path.expanduser(spec["zip"])
    parts, warnings, created = {}, [], None
    for p in spec["parts"]:
        p["dir"] = os.path.join(top, p["sub"])
        meta_f = os.path.join(p["dir"], "meta.json")
        meta = json.load(open(meta_f)) if os.path.exists(meta_f) else {}
        if os.path.exists(meta_f):
            os.remove(meta_f)
        created = created or meta.get("created")
        dst = os.path.join(p["dir"], p["name"])
        if os.path.exists(dst):
            os.remove(dst)
        os.link(os.path.expanduser(p["video"]), dst)
        v = probe(dst)
        w = list(meta.get("warnings", [])) + p.get("warnings", [])
        ew, eh = (int(x) for x in p["expect"].split("x"))
        if (v["width"], v["height"]) != (ew, eh):
            w.append(f"video {v['width']}×{v['height']}, không phải {ew}×{eh}")
        audio = next(iter(sorted(glob.glob(os.path.join(os.path.expanduser(p["audio_dir"]), "audio.*")))),
                     None) if p.get("audio_dir") else None
        if audio:
            ad = probe(audio)["duration"]
            if abs(ad - v["duration"]) > 1.5:
                w.append(f"video dài {fmt(v['duration'])} ≠ audio đã ghép {fmt(ad)}")
        warnings += [(f"{p['key']}: " if len(spec["parts"]) > 1 else "") + x for x in w]
        parts[p["key"]] = {"title": meta.get("title"), "source_audio": meta.get("source_audio"),
                           "video": dict(v, file=os.path.join(p["sub"], p["name"])), "thumbnail": meta.get("thumbnail"),
                           "youtube": meta.get("youtube"), "warnings": w}
    files = {}
    for root, _, names in os.walk(top):
        for n in sorted(names):
            p = os.path.join(root, n)
            files[os.path.relpath(p, top)] = {"size": os.path.getsize(p), "sha256": sha256(p)}
    manifest = {"name": spec["name"], "created": created, "channel": spec["channel"], "short": spec.get("short"),
                "parts": parts, "files": files, "warnings": warnings}
    json.dump(manifest, open(os.path.join(top, "manifest.json"), "w"), indent=1, ensure_ascii=False)
    text = readme(spec, parts, files, warnings, created)
    open(os.path.join(top, "README.txt"), "w").write(text)

    name = os.path.basename(top)
    tmp = zip_out + ".part"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_STORED, allowZip64=True) as z:
        for root, dirs, names in os.walk(top):
            dirs.sort()
            for n in sorted(names):
                p = os.path.join(root, n)
                z.write(p, os.path.join(name, os.path.relpath(p, top)))
    os.replace(tmp, zip_out)
    with zipfile.ZipFile(zip_out) as z:
        entries = [[i.filename, i.file_size] for i in z.infolist()]
    print(json.dumps({"zip": zip_out, "size": os.path.getsize(zip_out), "sha256": sha256(zip_out), "parts": parts,
                      "files": files, "entries": entries, "warnings": warnings, "readme": text}, ensure_ascii=False))


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
