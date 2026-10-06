#!/usr/bin/env python3
import argparse
import glob
import json
import os
import re
import subprocess
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
REMOTE_ENV = ".claude/skills/video-generator/remote.env"


def channels(only):
    if only:
        return [c for c in only if os.path.isdir(f"channel/{c}")]
    return sorted(os.path.basename(p) for p in glob.glob("channel/*")
                  if os.path.isdir(p) and not os.path.basename(p).startswith("_"))


def max_num(pattern):
    return max((int(m.group(1)) for p in glob.glob(pattern) if (m := re.match(r"(\d{3})-", os.path.basename(p)))), default=0)


def field(head, key):
    m = re.search(rf"^{key}:[ \t]*['\"]?([^'\"\n#]*)", head, re.M)
    return m.group(1).strip() if m else ""


def pool(ch_dir):
    named, types, seconds = set(), {}, 0.0
    cards = glob.glob(f"{ch_dir}/songs/*.md") + [p for p in glob.glob(f"{ch_dir}/songs/*/*.md") if "/songs/raw/" not in p]
    for md in cards:
        head = open(md, encoding="utf-8").read().split("\n---", 1)[0]
        if not field(head, "clip_id"):
            continue
        named.add(field(head, "clip_id")[:8])
        t = field(head, "type") or "?"
        types[t] = types.get(t, 0) + 1
        try:
            seconds += float(field(head, "duration_s") or 0)
        except ValueError:
            pass
    raw = {os.path.basename(p).split(".")[0] for ext in ("wav", "json") for p in glob.glob(f"{ch_dir}/songs/raw/*.{ext}")}
    return types, seconds / 60, len(raw - named)


def quota_log():
    rows = []
    for man in glob.glob("channel/*/songs/manifest.json"):
        try:
            rows += [(q.get("at", ""), q, man.split("/")[1]) for q in json.load(open(man, encoding="utf-8")).get("quota_log", [])]
        except (OSError, ValueError):
            pass
    return sorted(rows, key=lambda r: r[0])


def port_ok(port):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=2):
            return True
    except Exception:
        return False


def ssh_ok():
    env = {}
    if os.path.exists(REMOTE_ENV):
        for line in open(REMOTE_ENV, encoding="utf-8"):
            k, sep, v = line.strip().partition("=")
            if sep and not k.startswith("#"):
                env[k] = os.path.expandvars(v.strip().strip('"'))
    if not env.get("VG_REMOTE"):
        return None
    cmd = ["ssh", "-o", "ConnectTimeout=5", "-o", "BatchMode=yes", "-i", os.path.expanduser(env.get("VG_KEY") or "~/.ssh/id_rsa")]
    try:
        return subprocess.run(cmd + [env["VG_REMOTE"], "true"], capture_output=True, timeout=10).returncode == 0
    except Exception:
        return False


def main():
    ap = argparse.ArgumentParser(description="PM: kho bài mỗi kênh, số album tiếp theo, credits Suno, Chrome + GPU server")
    ap.add_argument("--channel", nargs="*", help="chỉ các kênh này (mặc định: mọi kênh trong channel/, trừ _*)")
    a = ap.parse_args()
    os.chdir(ROOT)
    for ch in channels(a.channel):
        d = f"channel/{ch}"
        types, minutes, unnamed = pool(d)
        print(f"# {ch}\n")
        print(f"- Kho bài: {sum(types.values())} bài đã đặt tên ({', '.join(f'{t} {n}' for t, n in sorted(types.items())) or '–'})"
              f" · {minutes:.0f} phút · {unnamed} clip chưa đặt tên (songs/raw/ → audio-song-naming)")
        print(f"- Album tiếp theo: {max_num(f'{d}/albums/*') + 1:03d} (Short nằm trong album: albums/NNN-slug/short/, không đánh số riêng)\n")

    rows = quota_log()
    print("# Suno (lần đọc tài khoản gần nhất, songs/manifest.json)\n")
    if rows:
        at, q, ch = rows[-1]
        print(f"- {at} · credits {q.get('credits')} · lượt tải chính thức {q.get('downloads_used')} · {ch} ({q.get('context', '')})")
        for at, q, ch in rows:
            if q.get("alert"):
                print(f"- 🚨 {at} {ch}: lượt tải chính thức TĂNG ({q['alert']}) → dừng lane suno, báo CEO")
    else:
        print("- chưa có quota_log")

    ssh = ssh_ok()
    print("\n# Môi trường\n")
    print(f"- Suno Chrome :9222    {'OK' if port_ok(9222) else 'TẮT → .claude/skills/audio-suno-generate/scripts/suno-chrome.sh'}")
    print(f"- ChatGPT Chrome :9223 {'OK' if port_ok(9223) else 'TẮT → .claude/skills/thumbnail-prompt/scripts/chatgpt-chrome.sh'}")
    print(f"- GPU server ssh       {'OK' if ssh else ('chưa có VG_REMOTE trong ' + REMOTE_ENV if ssh is None else 'KHÔNG KẾT NỐI (không chạy --local; chờ + thử lại)')}")


if __name__ == "__main__":
    main()
