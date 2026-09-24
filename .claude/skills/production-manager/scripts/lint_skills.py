#!/usr/bin/env python3
import argparse, glob, os, re, sys

SCAN = [".claude/skills", "templates"]
SKIP_DIRS = {".venv", ".cache", "node_modules", "__pycache__", ".git"}
TEXT_EXT = {".md", ".py", ".js", ".sh", ".yaml", ".yml", ".json", ".txt", ".example", ".toml", ".cfg"}


def yaml_block(path):
    if not os.path.exists(path):
        return ""
    m = re.search(r"```yaml\n(.*?)```", open(path, encoding="utf-8").read(), re.S)
    return m.group(1) if m else ""


def channel_terms(ch_dir):
    slug = os.path.basename(ch_dir)
    terms = {slug: "channel slug"}
    md = os.path.join(ch_dir, "channel.md")
    if os.path.exists(md):
        m = re.match(r"#\s+(.+)", open(md, encoding="utf-8").readline())
        if m:
            name = m.group(1).strip()
            terms[name] = "channel name"
            terms[name.replace(" ", "")] = "channel name"
    rules = yaml_block(os.path.join(ch_dir, "rules.md"))
    for m in re.finditer(r"-\s*name:\s*\"?([^\"\n]+?)\"?\s*\n\s*id:\s*([0-9a-f-]{8,})", rules):
        terms[re.sub(r"\s*\(.*\)$", "", m.group(1)).strip()] = "Suno Voice name"
        terms[m.group(2)[:8]] = "Suno Voice id"
    tr = os.path.join(ch_dir, "translate.yaml")
    if os.path.exists(tr):
        m = re.search(r"^channel_id:\s*(UC[\w-]+)", open(tr, encoding="utf-8").read(), re.M)
        if m:
            terms[m.group(1)] = "YouTube channel id"
    return terms


def files():
    for root in SCAN:
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for f in filenames:
                if f == "remote.env" or os.path.splitext(f)[1] not in TEXT_EXT:
                    continue
                yield os.path.join(dirpath, f)


def main():
    ap = argparse.ArgumentParser(description="Báo chỗ skill/template nhắc tới một kênh cụ thể (tên, slug, Voice, channel id)")
    ap.parse_args()
    terms = {}
    for ch_dir in sorted(glob.glob("channel/*/")):
        ch = os.path.basename(ch_dir.rstrip("/"))
        if ch.startswith("_"):
            continue
        for t, kind in channel_terms(ch_dir.rstrip("/")).items():
            terms[t] = f"{kind} ({ch})"
    pats = [(re.compile(re.escape(t), re.I), t, kind) for t, kind in terms.items() if len(t) >= 4]
    hits = 0
    for path in files():
        try:
            lines = open(path, encoding="utf-8").read().splitlines()
        except (UnicodeDecodeError, OSError):
            continue
        for n, line in enumerate(lines, 1):
            for rx, t, kind in pats:
                if rx.search(line):
                    hits += 1
                    print(f"{path}:{n}: {kind} '{t}': {line.strip()[:110]}")
    print(f"\n{hits} chỗ nhắc tới kênh cụ thể" if hits else "✔ skill và template không nhắc tới kênh cụ thể nào")
    sys.exit(1 if hits else 0)


if __name__ == "__main__":
    main()
