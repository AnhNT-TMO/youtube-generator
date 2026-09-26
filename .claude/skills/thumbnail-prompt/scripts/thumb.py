#!/usr/bin/env python3
USAGE = """thumbnail-prompt helper (trên Mac chỉ cần python3 + ffmpeg/ffprobe + ssh, không venv).

  list  <channel dir>                 mọi ảnh của channel (album / idea / single): cảnh, tư thế, bố cục → tránh lặp
  fit   <dir> <ảnh ChatGPT> [--x 0.5 --y 0.5] [--no-upscale]
                                      cắt về 16:9 quanh điểm (x, y) ở độ phân giải gốc → GPU server upscale SeedVR2 7B
                                      → <dir>/thumbnail.png 3840×2160 (bản 4K giữ trên máy) + thumbnail.jpg ≤ 2 MB (YouTube)
                                      <dir> là Short (shorts/NNN-slug): cắt 9:16 → 2160×3840 (--no-upscale: 1080×1920)
                                      --no-upscale: Lanczos 1920×1080 ngay trên Mac (khi server không kết nối được)
  check <dir> [--image <ảnh>]         kích thước, dung lượng, 3 vùng bị phủ trong video, điểm sáng (lantern), prompt
  upscale-setup                       một lần / khi hỏng: cài SeedVR2 + model 7B (~17 GB) vào ~/thumbnail-prompt trên server

Chạy từ gốc repo. <dir> = channel/<ch>/{albums,ideas,singles,shorts}/NNN-slug
"""
import argparse
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
W, H = 1920, 1080
UW, UH = 3840, 2160
ZONES = {
    "logo (trên phải)": (0.84, 0.00, 1.00, 0.27),
    "subscribe (dưới phải)": (0.72, 0.86, 1.00, 1.00),
    "sóng nhạc (dưới giữa)": (0.28, 0.84, 0.72, 1.00),
}
ZONES_SHORT = {
    "thanh trên YouTube": (0.00, 0.00, 1.00, 0.10),
    "dải lời bài (giữa dưới)": (0.05, 0.56, 0.88, 0.70),
    "nút bên phải": (0.88, 0.35, 1.00, 0.90),
    "title + kênh (dưới)": (0.00, 0.76, 1.00, 1.00),
}
BUSY_WARN = 1.3
GW, GH = 192, 108
CW, CH = 64, 36
FILE_MAX = 2_000_000
HOUSE = "## Prompt ảnh mặc định (ChatGPT)"
HOUSE_SHORT = "## Prompt ảnh dọc Shorts (ChatGPT)"
DURATION = "## Dòng thời lượng"


def dims(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                          "-of", "csv=p=0:s=x", str(path)], capture_output=True, text=True).stdout.strip()
    w, h = out.split("x")
    return int(w), int(h)


def pixels(path, w, h, fmt):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-vf", f"scale={w}:{h}:flags=area,format={fmt}",
                          "-frames:v", "1", "-f", "rawvideo", "-"], capture_output=True, check=True).stdout
    return raw


def front_matter(md):
    text = Path(md).read_text()
    m = re.match(r"^---\n(.*?)\n---", text, re.S)
    if not m:
        return {}
    fm = {}
    for line in m.group(1).splitlines():
        k, sep, v = line.partition(":")
        if sep and not line.startswith((" ", "#")):
            v = re.sub(r"\s+#.*$", "", v).strip().strip('"')
            fm[k.strip()] = v
    return fm


def code_block(text, heading):
    i = text.find(heading)
    if i < 0:
        return None
    m = re.search(r"```[a-z]*\n(.*?)\n```", text[i:], re.S)
    return m.group(1) if m else None


def channel_of(d):
    d = Path(d).resolve()
    for p in [d, *d.parents]:
        if (p / "channel.md").exists():
            return p
    sys.exit(f"không tìm thấy channel.md phía trên {d}")


def cmd_list(a):
    ch = Path(a.channel)
    rows = []
    for kind in ("albums", "ideas", "singles"):
        for d in sorted((ch / kind).glob("*/")):
            pm = d / "thumbnail-prompt.md"
            fm = front_matter(pm) if pm.exists() else {}
            img = next((d / f for f in ("thumbnail.png", "thumbnail.jpg") if (d / f).exists()), None)
            if not fm and not img:
                continue
            rows.append((f"{kind}/{d.name}", fm.get("title_text", ""), fm.get("duration_line", ""), fm.get("signature", ""), fm.get("lettering", ""),
                         fm.get("wardrobe", "").split(":")[0], fm.get("framing", ""), fm.get("light", ""), fm.get("palette", ""),
                         fm.get("setting", ""), fm.get("time", ""), Path(fm.get("pose", "")).name, fm.get("layout", ""),
                         fm.get("status", "") or ("ảnh có sẵn, chưa có thumbnail-prompt.md" if img else "")))
    print("| thư mục | chữ | dòng thời lượng | chữ ký album | kiểu chữ | trang phục | khung | ánh sáng | màu | bối cảnh | thời điểm | tư thế | bố cục | trạng thái |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        print("| " + " | ".join(r) + " |")


def renv():
    env = {}
    for line in (HERE.parent / "remote.env").read_text().splitlines():
        k, sep, v = line.partition("=")
        if sep and not line.lstrip().startswith("#"):
            env[k.strip()] = os.path.expandvars(v.strip())
    return env


LIMIT = ("S=~/.config/systemd/user/youtube.slice; [ -f $S ] || { mkdir -p ${S%/*} && printf \"[Unit]\\nDescription="
         "youtube project: every skill shares this cap (CLAUDE.md)\\n[Slice]\\nCPUQuota=%s%%\\nMemoryHigh=60%%\\n"
         "MemoryMax=70%%\\n\" $(( $(nproc) * 60 )) > $S && systemctl --user daemon-reload; }; "
         "systemd-run --user --scope --quiet --collect --slice=youtube.slice -- bash -c ")


def limited(cmd):
    return LIMIT + shlex.quote(cmd)


def ssh(env, cmd, **kw):
    return subprocess.run(["ssh", "-i", env["TP_KEY"], "-o", "BatchMode=yes", "-o", "ConnectTimeout=8",
                           env["TP_REMOTE"], cmd], **kw)


def scp(env, src, dst):
    subprocess.run(["scp", "-q", "-i", env["TP_KEY"], "-o", "BatchMode=yes", src, dst], check=True)


def reach(env):
    if ssh(env, "true", capture_output=True).returncode:
        sys.exit(f"GPU server {env['TP_REMOTE']} không kết nối được. Hỏi chủ kênh: chờ server, hay "
                 "`fit ... --no-upscale` (1920×1080, video vẫn làm được; gói S3 sẽ cảnh báo thumbnail chưa 4K).")
    R = env["TP_DIR"]
    ssh(env, f"mkdir -p {R}/scripts", check=True)
    scp(env, str(HERE / "upscale_server.py"), f"{env['TP_REMOTE']}:{R}/scripts/upscale_server.py")
    return R


def upscale(src, dst, uw=UW, uh=UH):
    env = renv()
    R = reach(env)
    if ssh(env, f"test -x {R}/.venv/bin/python && test -f {R}/models/seedvr2/seedvr2_ema_7b_fp16.safetensors").returncode:
        sys.exit("server chưa cài upscaler: chạy `python3 .claude/skills/thumbnail-prompt/scripts/thumb.py upscale-setup`")
    job = f"{R}/jobs/{time.strftime('%Y%m%d-%H%M%S')}-{os.getpid()}"
    t0 = time.time()
    ssh(env, f"mkdir -p {job}", check=True)
    try:
        scp(env, str(src), f"{env['TP_REMOTE']}:{job}/in.png")
        p = ssh(env, limited(f"cd ~/{R} && .venv/bin/python scripts/upscale_server.py run ~/{job}/in.png ~/{job}/out.png "
                             f"--w {uw} --h {uh}"), capture_output=True, text=True)
        if p.returncode:
            sys.exit(f"upscale lỗi trên server:\n{p.stdout}{p.stderr}")
        scp(env, f"{env['TP_REMOTE']}:{job}/out.png", str(dst))
    finally:
        ssh(env, f"rm -rf {job}")
    print(f"SeedVR2 7B trên server: {p.stdout.strip().splitlines()[-1]} · tổng {time.time() - t0:.0f} s (gồm truyền file)")


def cmd_upscale_setup(_):
    env = renv()
    R = reach(env)
    print(f"cài SeedVR2 vào {env['TP_REMOTE']}:~/{R} (lần đầu tải ~17 GB model, 25–30 phút) …", flush=True)
    sys.exit(ssh(env, f"python3 {R}/scripts/upscale_server.py setup").returncode)


def youtube_jpg(png, jpg):
    w, _ = dims(png)
    for width in (w, 2560, 1920, 1280):
        if width > w:
            continue
        for q in (2, 3, 4, 5, 6):
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(png), "-vf", f"scale={width}:-2:flags=lanczos",
                            "-q:v", str(q), str(jpg)], check=True)
            if jpg.stat().st_size <= FILE_MAX:
                return width, q
    sys.exit(f"không nén {png} xuống ≤ 2 MB được")


def is_short(d):
    return Path(d).resolve().parent.name == "shorts"


def frame_of(d):
    return ((9, 16), (H, W), (UH, UW)) if is_short(d) else ((16, 9), (W, H), (UW, UH))


def cmd_fit(a):
    d, src = Path(a.dir), Path(a.image)
    (rw, rh), (fw, fh), (uw, uh) = frame_of(d)
    w, h = dims(src)
    if w / h > rw / rh:
        cw, chh = round(h * rw / rh), h
    else:
        cw, chh = w, round(w * rh / rw)
    x = round((w - cw) * min(max(a.x, 0), 1))
    y = round((h - chh) * min(max(a.y, 0), 1))
    out = d / "thumbnail.png"
    drafts = d / "thumbnail-drafts"
    drafts.mkdir(exist_ok=True)
    if out.exists():
        bk = drafts / f"prev-{time.strftime('%Y%m%d-%H%M%S')}.png"
        shutil.copy(out, bk)
        print(f"thumbnail.png cũ → {bk}")
        if src.resolve() == out.resolve():
            src = bk
    lost = (1 - cw * chh / (w * h)) * 100
    crop = f"crop={cw}:{chh}:{x}:{y}"
    if a.no_upscale:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-vf",
                        f"{crop},scale={fw}:{fh}:flags=lanczos,format=rgb24", str(out)], check=True)
        print(f"{src.name} {w}×{h} → cắt {cw}×{chh} tại ({x},{y}), mất {lost:.0f}% diện tích → {out} {fw}×{fh} (Lanczos)")
        print(f"⚠️  chưa phải 4K: khi server có lại, chạy lại `fit` (không --no-upscale) từ cùng ảnh nháp")
    else:
        tmp = drafts / f".crop-{os.getpid()}.png"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-vf", f"{crop},format=rgb24", str(tmp)],
                       check=True)
        print(f"{src.name} {w}×{h} → cắt {cw}×{chh} tại ({x},{y}), mất {lost:.0f}% diện tích → upscale {uw}×{uh}",
              flush=True)
        try:
            upscale(tmp, out, uw, uh)
        finally:
            tmp.unlink(missing_ok=True)
        print(f"→ {out} {uw}×{uh} {out.stat().st_size / 1e6:.1f} MB (bản 4K giữ trên máy; video-generator đẩy lên server)")
        print("   SeedVR2 vẽ thêm chi tiết: Read ảnh, so với bản nháp — chữ, mặt, tay không được đổi")
    jpg = d / "thumbnail.jpg"
    if out.stat().st_size > FILE_MAX:
        jw, q = youtube_jpg(out, jpg)
        print(f"thumbnail.png {out.stat().st_size / 1e6:.2f} MB > 2 MB → bản upload YouTube: {jpg} "
              f"({jw}px, q{q}, {jpg.stat().st_size / 1e6:.2f} MB); video-generator vẫn dùng thumbnail.png")
    elif jpg.exists():
        jpg.unlink()


def grad_map(path):
    g = pixels(path, GW, GH, "gray")
    m = [[0.0] * GW for _ in range(GH)]
    for yy in range(GH - 1):
        r, r2 = yy * GW, (yy + 1) * GW
        for xx in range(GW - 1):
            v = g[r + xx]
            m[yy][xx] = abs(g[r + xx + 1] - v) + abs(g[r2 + xx] - v)
    return m, g


def zone_mean(m, z):
    x0, y0, x1, y1 = z
    xs = range(int(x0 * GW), min(GW - 1, int(x1 * GW)))
    ys = range(int(y0 * GH), min(GH - 1, int(y1 * GH)))
    vals = [m[y][x] for y in ys for x in xs]
    return sum(vals) / max(1, len(vals))


def bright_spots(path, n=3):
    raw = pixels(path, CW, CH, "rgb24")
    score = []
    for i in range(CW * CH):
        r, g, b = raw[3 * i], raw[3 * i + 1], raw[3 * i + 2]
        lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
        score.append(lum * (0.6 + 0.4 * max(0, r - b) / 255))
    picks = []
    for i in sorted(range(len(score)), key=lambda k: -score[k]):
        x, y = i % CW, i // CW
        if all((x - px) ** 2 + (y - py) ** 2 > 36 for px, py, _ in picks):
            picks.append((x, y, score[i]))
        if len(picks) == n:
            break
    return [((x + 0.5) / CW, (y + 0.5) / CH, s) for x, y, s in picks]


def cmd_check(a):
    d = Path(a.dir)
    img = Path(a.image) if a.image else next((d / f for f in ("thumbnail.png",) if (d / f).exists()), None)
    err, warn = [], []
    short = is_short(d)
    (rw, rh), (fw, fh), (uw, uh) = frame_of(d)
    if img and img.exists():
        w, h = dims(img)
        size = img.stat().st_size
        print(f"ảnh: {img}  {w}×{h}  {size / 1e6:.2f} MB")
        if abs(w / h - rw / rh) > 0.01:
            err.append(f"tỉ lệ {w / h:.3f} ≠ {rw}:{rh} ({rw / rh:.3f}): chạy `thumb.py fit`")
        if min(w, h) < 720:
            err.append("cạnh ngắn nhỏ hơn 720 px")
        elif w < uw:
            warn.append(f"{w}×{h} chưa đủ {uw}×{uh}: `thumb.py fit` từ ảnh nháp để upscale "
                        "(gói S3 của video-generator sẽ cảnh báo)")
        jpg = img.with_suffix(".jpg")
        if size > FILE_MAX and not (jpg.exists() and jpg.stat().st_size <= FILE_MAX):
            warn.append("> 2 MB: upload thumbnail YouTube cần bản JPG (`thumb.py fit` tự tạo, hoặc sips -s format jpeg)")
        m, _ = grad_map(img)
        whole = sum(map(sum, m)) / (GW * GH)
        print("\nvùng bị phủ trong video (độ chi tiết so với cả ảnh; > {:.1f} = rối):".format(BUSY_WARN))
        for name, z in (ZONES_SHORT if short else ZONES).items():
            r = zone_mean(m, z) / whole if whole else 0
            flag = "⚠️ " if r > BUSY_WARN else "  "
            print(f"  {flag}{name:<24} {r:.2f}")
            if r > BUSY_WARN:
                warn.append(f"vùng {name} nhiều chi tiết ({r:.2f}): xem có mặt/chữ/vật quan trọng bị che không")
        print("\nđiểm sáng + ấm nhất (x, y theo tỉ lệ khung) — ứng viên `lantern.center` trong video.json:")
        for x, y, s in bright_spots(img):
            print(f"  [{x:.3f}, {y:.3f}]  score {s:.0f}")
    else:
        warn.append("chưa có thumbnail.png")

    pm = d / "thumbnail-prompt.md"
    if pm.exists():
        text = pm.read_text()
        fm = front_matter(pm)
        prompt = code_block(text, "## Prompt")
        ch = channel_of(d)
        head = HOUSE_SHORT if short else HOUSE
        vis = next((f for f in (ch / "visual.md", ch / "channel.md") if f.exists() and head in f.read_text()), None)
        house = code_block(vis.read_text(), head) if vis else None
        existing = fm.get("status") == "existing"
        if not prompt and not existing:
            err.append("thumbnail-prompt.md thiếu khối ``` trong ## Prompt")
        elif prompt:
            if house and fm.get("status") == "chosen":
                pass
            elif house:
                for line in house.splitlines():
                    if line.strip() and line not in prompt:
                        err.append(f"prompt thiếu dòng của mẫu channel ({head[3:]}): {line[:60]}…")
            else:
                (err if short else warn).append(f"visual.md của channel chưa có mục `{head}`")
            t = fm.get("title_text")
            if t and f'"{t}"' not in prompt:
                err.append(f'prompt không có chữ title nguyên văn trong ngoặc kép: "{t}"')
            if re.search(r"<[^>\n]+>", prompt):
                err.append("prompt còn placeholder <...>")
            dl = fm.get("duration_line")
            if dl and fm.get("kind") in ("single", "short"):
                err.append(f'single không có dòng thời lượng (duration_line: "{dl}"): chỉ ảnh album mới có')
            elif dl and f'Duration line: "{dl}"' not in prompt:
                err.append(f'prompt thiếu dòng THIS IMAGE nguyên văn: Duration line: "{dl}"')
            elif (not dl and fm.get("kind") in ("album", "idea") and fm.get("status") != "chosen"
                  and vis and DURATION in vis.read_text()):
                warn.append(f"ảnh album chưa có duration_line (visual.md → {DURATION[3:]})")
        pose = fm.get("pose")
        if pose and pose.endswith(".png") and not (channel_of(d) / pose).exists():
            err.append(f"không thấy ảnh tham chiếu {pose}")
        print(f"\nprompt: {pm.name} · status {fm.get('status') or '?'} · {len(prompt or '')} ký tự")
    else:
        warn.append("chưa có thumbnail-prompt.md")

    print()
    for x in warn:
        print(f"⚠️  {x}")
    for x in err:
        print(f"❌ {x}")
    if not err:
        print("✅ không có lỗi (vẫn phải NHÌN ảnh: chính tả chữ, mặt giống model, tay, góc phủ)")
    sys.exit(1 if err else 0)


def main():
    ap = argparse.ArgumentParser(description=USAGE, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("list")
    s.add_argument("channel")
    s.set_defaults(fn=cmd_list)
    s = sub.add_parser("fit")
    s.add_argument("dir")
    s.add_argument("image")
    s.add_argument("--x", type=float, default=0.5, help="0 = giữ mép trái, 1 = giữ mép phải")
    s.add_argument("--y", type=float, default=0.5, help="0 = giữ mép trên, 1 = giữ mép dưới")
    s.add_argument("--no-upscale", action="store_true", help="Lanczos 1920×1080 trên Mac, không dùng GPU server")
    s.set_defaults(fn=cmd_fit)
    s = sub.add_parser("upscale-setup")
    s.set_defaults(fn=cmd_upscale_setup)
    s = sub.add_parser("check")
    s.add_argument("dir")
    s.add_argument("--image")
    s.set_defaults(fn=cmd_check)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
