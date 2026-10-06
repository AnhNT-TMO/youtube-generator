#!/usr/bin/env python3
USAGE = """Mac side of `video.py package` (runs in the skill venv: Pillow + boto3).

    package.py stage PKGDIR --youtube-md F --thumbnail IMG --jpg OUT.jpg --channel CH [--source-audio NAME] [--vertical]
        PKGDIR/youtube.md, upload/{title,description,tags,pinned_comment}.txt, thumbnail.jpg (YouTube: <= 2 MB),
        thumbnail_full.<ext> (the original, full resolution), meta.json; the same JPG is written to OUT.jpg
    package.py presign  --bucket B --key K --region R --size N [--profile P] [--expires S]
        multipart upload + one presigned PUT url per 256 MB part (any size; a single POST stops at 5 GB)
    package.py complete --bucket B --key K --region R --upload-id U --etags FILE [--profile P]
    package.py abort    --bucket B --key K --region R --upload-id U [--profile P]
    package.py head     --bucket B --key K --region R [--profile P]
Every command prints one JSON line. AWS credentials: this Mac's default chain (or --profile / AWS_PROFILE).
"""
import argparse
import json
import math
import os
import re
import shutil
import sys
import time

PART = 256 * 1024 ** 2
YT_THUMB_MAX = 2 * 1024 * 1024


def code_block(text, heading):
    i = text.find(heading)
    if i < 0:
        return None
    m = re.search(r"```[a-z]*\n(.*?)\n```", text[i:], re.S)
    return m.group(1) if m else None


def youtube_jpg(src, out):
    from PIL import Image
    im = Image.open(src).convert("RGB")
    w, h = im.size
    scale = 1.0
    while True:
        img = im if scale == 1.0 else im.resize((round(w * scale), round(h * scale)), Image.LANCZOS)
        for q in (95, 92, 90, 87, 85, 82, 80):
            img.save(out, "JPEG", quality=q, optimize=True, progressive=True, subsampling=0 if q >= 90 else 2)
            if os.path.getsize(out) <= YT_THUMB_MAX:
                return img.size, q
        if img.size[0] <= 1280:
            sys.exit(f"{src}: không nén được xuống ≤ 2 MB")
        scale *= 0.85


def cmd_stage(a):
    ytmd = open(a.youtube_md).read()
    fields = {"title": code_block(ytmd, "## Title"), "description": code_block(ytmd, "## Description"),
              "tags": code_block(ytmd, "## Tags"), "pinned_comment": code_block(ytmd, "## Pinned comment")}
    missing = [k for k, v in fields.items() if not v]
    if missing:
        sys.exit(f"youtube.md thiếu khối: {', '.join(missing)} (chạy skill upload-youtube-publish; Short: video-shorts)")
    os.makedirs(os.path.join(a.pkgdir, "upload"), exist_ok=True)
    shutil.copy2(a.youtube_md, os.path.join(a.pkgdir, "youtube.md"))
    for k, v in fields.items():
        open(os.path.join(a.pkgdir, "upload", f"{k}.txt"), "w").write(v.strip() + "\n")

    from PIL import Image
    w, h = Image.open(a.thumbnail).size
    if (os.path.exists(a.jpg) and os.path.getmtime(a.jpg) >= os.path.getmtime(a.thumbnail)
            and os.path.getsize(a.jpg) <= YT_THUMB_MAX):
        (jw, jh), q = Image.open(a.jpg).size, None
    else:
        (jw, jh), q = youtube_jpg(a.thumbnail, a.jpg)
    shutil.copy2(a.jpg, os.path.join(a.pkgdir, "thumbnail.jpg"))
    full = "thumbnail_full" + os.path.splitext(a.thumbnail)[1].lower()
    shutil.copy2(a.thumbnail, os.path.join(a.pkgdir, full))
    warnings = []
    ratio, full_w = (9 / 16, 2160) if a.vertical else (16 / 9, 3840)
    if w < full_w:
        warnings.append(f"thumbnail gốc {w}×{h}, chưa đủ {full_w} px chiều ngang")
    if abs(w / h - ratio) > 0.01:
        warnings.append(f"thumbnail {w}×{h} không phải {'9:16' if a.vertical else '16:9'}")
    tags = [t.strip() for t in fields["tags"].split(",") if t.strip()]
    meta = {"created": time.strftime("%Y-%m-%d %H:%M"), "title": fields["title"].strip(), "channel": a.channel,
            "source_audio": a.source_audio,
            "thumbnail": {"width": w, "height": h, "full_file": full, "jpg_width": jw, "jpg_height": jh,
                          "jpg_quality": q, "jpg_bytes": os.path.getsize(a.jpg)},
            "youtube": {"title_chars": len(fields["title"].strip()), "description_chars": len(fields["description"]),
                        "tags": len(tags)},
            "warnings": warnings}
    json.dump(meta, open(os.path.join(a.pkgdir, "meta.json"), "w"), indent=1, ensure_ascii=False)
    print(json.dumps({"thumbnail": meta["thumbnail"], "warnings": warnings}, ensure_ascii=False))


def s3(a):
    try:
        import boto3
        from botocore.config import Config
    except ImportError:
        sys.exit("thiếu boto3 trong venv của skill")
    ses = boto3.Session(profile_name=a.profile) if a.profile else boto3.Session()
    if ses.get_credentials() is None:
        sys.exit("không thấy AWS credentials trên máy này (aws configure / AWS_PROFILE / VG_AWS_PROFILE trong remote.env)")
    return ses.client("s3", region_name=a.region, endpoint_url=f"https://s3.{a.region}.amazonaws.com",
                      config=Config(signature_version="s3v4", s3={"addressing_style": "virtual"}))


def cmd_presign(a):
    c = s3(a)
    up = c.create_multipart_upload(Bucket=a.bucket, Key=a.key, ContentType="application/zip")["UploadId"]
    n = math.ceil(a.size / PART)
    urls = [c.generate_presigned_url("upload_part", ExpiresIn=a.expires, Params={
        "Bucket": a.bucket, "Key": a.key, "UploadId": up, "PartNumber": i + 1}) for i in range(n)]
    print(json.dumps({"mode": "multipart", "upload_id": up, "part_size": PART, "urls": urls}))


def cmd_complete(a):
    etags = json.load(open(a.etags))["etags"]
    r = s3(a).complete_multipart_upload(Bucket=a.bucket, Key=a.key, UploadId=a.upload_id, MultipartUpload={
        "Parts": [{"ETag": e, "PartNumber": i + 1} for i, e in enumerate(etags)]})
    print(json.dumps({"etag": r.get("ETag")}))


def cmd_abort(a):
    s3(a).abort_multipart_upload(Bucket=a.bucket, Key=a.key, UploadId=a.upload_id)
    print(json.dumps({"aborted": a.upload_id}))


def cmd_head(a):
    r = s3(a).head_object(Bucket=a.bucket, Key=a.key)
    print(json.dumps({"size": r["ContentLength"], "etag": r["ETag"],
                      "last_modified": r["LastModified"].isoformat()}))


def main():
    ap = argparse.ArgumentParser(description=USAGE, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    st = sub.add_parser("stage")
    st.add_argument("pkgdir")
    for k in ("--youtube-md", "--thumbnail", "--jpg", "--channel"):
        st.add_argument(k, required=True)
    st.add_argument("--source-audio")
    st.add_argument("--vertical", action="store_true", help="Short: 9:16 thumbnail")
    for name in ("presign", "complete", "abort", "head"):
        p = sub.add_parser(name)
        for k in ("--bucket", "--key", "--region"):
            p.add_argument(k, required=True)
        p.add_argument("--profile", default=os.environ.get("AWS_PROFILE") or None)
        if name == "presign":
            p.add_argument("--size", type=int, required=True)
            p.add_argument("--expires", type=int, default=12 * 3600)
        if name in ("complete", "abort"):
            p.add_argument("--upload-id", required=True)
        if name == "complete":
            p.add_argument("--etags", required=True)
    a = ap.parse_args()
    {"stage": cmd_stage, "presign": cmd_presign, "complete": cmd_complete, "abort": cmd_abort,
     "head": cmd_head}[a.cmd](a)


if __name__ == "__main__":
    main()
