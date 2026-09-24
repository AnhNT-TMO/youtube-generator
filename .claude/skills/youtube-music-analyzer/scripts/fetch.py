#!/usr/bin/env python3
"""Download everything needed to analyze one YouTube music video into a work dir.

  fetch.py URL WORKDIR [--no-audio] [--comments N]

Writes: video.info.json, thumbnail.jpg, audio.<ext>, captions.<lang>.vtt (if any),
fetch_summary.json (printed to stdout).
Uses yt-dlp from the skill venv; YouTube needs a JS runtime, node is used.
"""
import argparse
import glob
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
VENV_BIN = os.path.join(os.path.dirname(HERE), ".venv", "bin")
YTDLP = os.path.join(VENV_BIN, "yt-dlp")
BASE = [YTDLP, "--js-runtimes", "node", "--no-warnings", "--no-progress", "-q", "--no-playlist"]


def run(args, **kw):
    try:
        r = subprocess.run(args, capture_output=True, text=True, **kw)
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(args, 124, "", "timeout")
    if r.returncode != 0:
        print(r.stderr[-2000:], file=sys.stderr)
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("workdir")
    ap.add_argument("--no-audio", action="store_true")
    ap.add_argument("--comments", type=int, default=0, help="top comments to fetch (default 0: comments are not a criterion)")
    args = ap.parse_args()
    wd = os.path.abspath(args.workdir)
    os.makedirs(wd, exist_ok=True)

    # 1. metadata + thumbnail + comments + captions (no media)
    meta = BASE + ["--skip-download", "--write-info-json", "--write-thumbnail", "--convert-thumbnails", "jpg",
                   "--write-auto-subs", "--write-subs", "--sub-langs", "en.*,en-orig", "--sub-format", "vtt",
                   "-o", os.path.join(wd, "video.%(ext)s")]
    if args.comments:
        meta += ["--write-comments", "--extractor-args",
                 f"youtube:max_comments={args.comments},all,{args.comments},0;comment_sort=top"]
    run(meta + [args.url])
    info_path = os.path.join(wd, "video.info.json")
    if not os.path.exists(info_path):
        sys.exit("metadata download failed (see error above)")
    if os.path.exists(os.path.join(wd, "video.jpg")):
        os.replace(os.path.join(wd, "video.jpg"), os.path.join(wd, "thumbnail.jpg"))
    for f in glob.glob(os.path.join(wd, "video.*.vtt")):
        os.replace(f, os.path.join(wd, "captions." + f.split("video.", 1)[1]))
    info = json.load(open(info_path))

    # 2. audio (bestaudio, no re-encode; analysis decodes with ffmpeg)
    audio = None
    if not args.no_audio:
        def complete():
            # a cached audio.* only counts if it is not a partial download and matches this video's length
            out = []
            for f in glob.glob(os.path.join(wd, "audio.*")):
                if f.endswith(".video_id"):
                    continue
                if f.endswith((".part", ".ytdl")) or ".part-Frag" in f:
                    os.remove(f)
                    continue
                d = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f],
                                   capture_output=True, text=True).stdout.strip()
                want = info.get("duration") or 0
                if d and (not want or abs(float(d) - want) <= max(5, 0.01 * want)):
                    out.append(f)
                else:
                    print(f"cached {os.path.basename(f)} is {d} s, video is {want} s: re-downloading", file=sys.stderr)
                    os.remove(f)
            return out
        idf = os.path.join(wd, "audio.video_id")
        if os.path.exists(idf) and open(idf).read().strip() != info.get("id"):
            for f in glob.glob(os.path.join(wd, "audio.*")):
                os.remove(f)      # audio of another video left in this slug
        existing = complete()
        if not existing:
            run(BASE + ["-f", "bestaudio/best", "--retries", "20", "-o", os.path.join(wd, "audio.%(ext)s"), args.url])
            existing = complete()
        audio = existing[0] if existing else None
        if audio:
            open(idf, "w").write(info.get("id") or "")
        if not audio:
            sys.exit("audio download failed or incomplete (see error above)")

    caps = sorted(glob.glob(os.path.join(wd, "captions.*.vtt")))
    summary = {
        "workdir": wd,
        "id": info.get("id"), "title": info.get("title"), "channel": info.get("channel"),
        "channel_url": info.get("channel_url"), "subscribers": info.get("channel_follower_count"),
        "upload_date": info.get("upload_date"), "duration_s": info.get("duration"),
        "views": info.get("view_count"), "likes": info.get("like_count"),
        "comments_fetched": len(info.get("comments") or []),
        "chapters": len(info.get("chapters") or []),
        "heatmap": bool(info.get("heatmap")),
        "tags": info.get("tags"),
        "captions": [os.path.basename(c) for c in caps],
        "audio": audio, "thumbnail": os.path.join(wd, "thumbnail.jpg"),
    }
    json.dump(summary, open(os.path.join(wd, "fetch_summary.json"), "w"), indent=1, ensure_ascii=False)
    print(json.dumps(summary, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
