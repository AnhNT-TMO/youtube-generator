#!/usr/bin/env python3
import argparse, glob, json, os, re, subprocess, urllib.request
from urllib.parse import urlparse, parse_qs

REMOTE_ENV = ".claude/skills/verification-audio/remote.env"


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


def channels(only):
    names = sorted(os.path.basename(p) for p in glob.glob("channel/*") if os.path.isdir(p) and not os.path.basename(p).startswith("_"))
    return [c for c in names if not only or c in only]


def max_num(pattern):
    nums = [int(m.group(1)) for p in glob.glob(pattern) if (m := re.match(r"(\d{3})-", os.path.basename(p)))]
    return max(nums, default=0)


def pending_links(ch_dir, done):
    q = os.path.join(ch_dir, "research-queue.txt")
    seen, pending = set(), []
    if os.path.exists(q):
        for line in open(q, encoding="utf-8"):
            vid = video_id(line) if line.strip() and not line.startswith("#") else None
            if vid and vid not in seen:
                seen.add(vid)
                if vid not in done:
                    pending.append((vid, line.strip()))
    return seen, pending


def last_quota():
    rows = []
    for man in glob.glob("channel/*/albums/*/audio/raw_tracks/manifest.json"):
        try:
            for q in json.load(open(man, encoding="utf-8")).get("quota_log", []):
                rows.append((q.get("at", ""), q, man.split("/audio/")[0].removeprefix("channel/")))
        except (OSError, ValueError):
            pass
    return max(rows, key=lambda r: r[0]) if rows else None


def port_ok(port):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=2):
            return True
    except Exception:
        return False


def remote_env():
    env = {}
    if os.path.exists(REMOTE_ENV):
        for line in open(REMOTE_ENV, encoding="utf-8"):
            k, sep, v = line.strip().partition("=")
            if sep and not k.startswith("#"):
                env[k] = os.path.expandvars(v.strip().strip('"'))
    return env


def ssh_ok():
    env = remote_env()
    host = env.get("QC_REMOTE")
    if not host:
        return None
    cmd = ["ssh", "-o", "ConnectTimeout=5", "-o", "BatchMode=yes"]
    if env.get("QC_KEY"):
        cmd += ["-i", os.path.expanduser(env["QC_KEY"])]
    try:
        return subprocess.run(cmd + [host, "true"], capture_output=True, timeout=15).returncode == 0
    except Exception:
        return False


def main():
    ap = argparse.ArgumentParser(description="Việc chưa có trên board: link chờ analyze, số idea/album tiếp theo, credits, môi trường")
    ap.add_argument("--channel", nargs="*", help="chỉ các kênh này (mặc định: mọi kênh trong channel/)")
    a = ap.parse_args()
    done = analyzed_ids()

    for ch in channels(a.channel):
        ch_dir = f"channel/{ch}"
        seen, pending = pending_links(ch_dir, done)
        next_idea = max_num(f"{ch_dir}/ideas/*") + 1
        print(f"# {ch}\n")
        print(f"Next idea number: {next_idea:03d} · next album number: {max_num(f'{ch_dir}/albums/*') + 1:03d}\n")
        print(f"research-queue.txt: {len(pending)} link chưa analyze ({len(seen) - len(pending)} đã có research)\n")
        for i, (vid, url) in enumerate(pending):
            print(f"- idea {next_idea + i:03d} ← {vid}  {url}")
        print()

    q = last_quota()
    print("# Suno (lần đọc gần nhất)\n")
    if q:
        at, row, where = q
        print(f"- {at} · credits {row.get('credits')} · official downloads {row.get('downloads_used')} · {where} ({row.get('context', '')})")
    else:
        print("- chưa có quota_log")

    ssh = ssh_ok()
    print("\n# Môi trường\n")
    print(f"- Suno Chrome :9222   {'OK' if port_ok(9222) else 'TẮT → .claude/skills/suno-generate/scripts/suno-chrome.sh'}")
    print(f"- ChatGPT Chrome :9223 {'OK' if port_ok(9223) else 'TẮT → .claude/skills/thumbnail-prompt/scripts/chatgpt-chrome.sh'}")
    print(f"- GPU server ssh      {'OK' if ssh else ('chưa có ' + REMOTE_ENV if ssh is None else 'KHÔNG KẾT NỐI (không chạy --local; chờ + thử lại)')}")


if __name__ == "__main__":
    main()
