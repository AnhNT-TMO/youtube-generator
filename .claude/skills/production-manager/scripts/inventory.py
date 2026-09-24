#!/usr/bin/env python3
"""Production-manager inventory: what the board does not show.

- links in research/list.txt not analyzed yet (video id not in any research/*/reference.yaml), with the idea
  number each would get if analyzed in this order
- next free idea / album numbers (pre-assign them before spawning workers so parallel runs never collide)
- last Suno account reading (credits, official downloads) from every album manifest
- environment: Suno Chrome (9222), ChatGPT Chrome (9223), GPU server ssh

Stdlib only. Run from the repo root:  python3 .claude/skills/production-manager/scripts/inventory.py [--channel lamplight_gospel]
"""
import argparse, glob, json, os, re, subprocess, urllib.request
from urllib.parse import urlparse, parse_qs

SERVER = "nguyentienanh@192.168.100.131"


def video_id(url):
    u = urlparse(url.strip())
    if u.netloc.endswith("youtu.be"):
        return u.path.strip("/") or None
    return (parse_qs(u.query).get("v") or [None])[0]


def analyzed_ids():
    ids = {}
    for ref in glob.glob("research/*/reference.yaml"):
        with open(ref, encoding="utf-8") as f:
            for line in f:
                m = re.match(r"\s*video_id:\s*['\"]?([\w-]{11})", line)
                if m:
                    ids[m.group(1)] = os.path.basename(os.path.dirname(ref))
                    break
    return ids


def max_num(pattern):
    nums = [int(m.group(1)) for p in glob.glob(pattern) if (m := re.match(r"(\d{3})-", os.path.basename(p)))]
    return max(nums, default=0)


def last_quota(ch_dir):
    rows = []
    for man in glob.glob(f"{ch_dir}/albums/*/audio/raw_tracks/manifest.json"):
        try:
            for q in json.load(open(man, encoding="utf-8")).get("quota_log", []):
                rows.append((q.get("at", ""), q, os.path.basename(man.split("/audio/")[0])))
        except (OSError, ValueError):
            pass
    return max(rows, key=lambda r: r[0]) if rows else None


def port_ok(port):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=2):
            return True
    except Exception:
        return False


def ssh_ok():
    try:
        return subprocess.run(["ssh", "-o", "ConnectTimeout=5", "-o", "BatchMode=yes", "-i",
                               os.path.expanduser("~/.ssh/id_rsa"), SERVER, "true"],
                              capture_output=True, timeout=15).returncode == 0
    except Exception:
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--channel", default="lamplight_gospel")
    a = ap.parse_args()
    ch_dir = f"channel/{a.channel}"

    done = analyzed_ids()
    seen, pending = set(), []
    if os.path.exists("research/list.txt"):
        for line in open("research/list.txt", encoding="utf-8"):
            vid = video_id(line) if line.strip() and not line.startswith("#") else None
            if vid and vid not in seen:
                seen.add(vid)
                if vid not in done:
                    pending.append((vid, line.strip()))

    next_idea = max_num(f"{ch_dir}/ideas/*") + 1
    next_album = max_num(f"{ch_dir}/albums/*") + 1

    print(f"# inventory · {a.channel}\n")
    print(f"Next idea number: {next_idea:03d} · next album number: {next_album:03d}\n")
    print(f"## research/list.txt: {len(pending)} link chưa analyze ({len(seen) - len(pending)} đã có research)\n")
    for i, (vid, url) in enumerate(pending):
        print(f"- idea {next_idea + i:03d} ← {vid}  {url}")

    q = last_quota(ch_dir)
    print("\n## Suno (lần đọc gần nhất)\n")
    if q:
        at, row, album = q
        print(f"- {at} · credits {row.get('credits')} · official downloads {row.get('downloads_used')} "
              f"· {album} ({row.get('context', '')})")
    else:
        print("- chưa có quota_log")

    print("\n## Môi trường\n")
    print(f"- Suno Chrome :9222   {'OK' if port_ok(9222) else 'TẮT → .claude/skills/suno-generate/scripts/suno-chrome.sh'}")
    print(f"- ChatGPT Chrome :9223 {'OK' if port_ok(9223) else 'TẮT → .claude/skills/thumbnail-prompt/scripts/chatgpt-chrome.sh'}")
    print(f"- GPU server ssh      {'OK' if ssh_ok() else 'KHÔNG KẾT NỐI (không chạy --local; chờ + thử lại)'}")


if __name__ == "__main__":
    main()
