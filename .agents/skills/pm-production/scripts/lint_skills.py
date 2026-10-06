#!/usr/bin/env python3
import argparse, glob, os, re, sys

SCAN = [".claude/skills", "templates"]
SKIP_DIRS = {".venv", ".cache", "node_modules", "__pycache__", ".git"}
TEXT_EXT = {".md", ".py", ".js", ".sh", ".yaml", ".yml", ".json", ".txt", ".example", ".toml", ".cfg"}


def genre_words(ch_dir):
    p = os.path.join(ch_dir, "channel.md")
    m = re.search(r"\*\*Thể loại:\*\*\s*([^,(:;\n]+)", open(p, encoding="utf-8").read()) if os.path.exists(p) else None
    if not m or m.group(1).strip().startswith("<"):
        return set()
    return {w.lower() for w in re.findall(r"[A-Za-z]{4,}", m.group(1))}


def channel_name(ch_dir):
    for f, part in (("channel.md", 0), ("CLAUDE.md", 0), ("publish.md", -1), ("naming.md", -1)):
        p = os.path.join(ch_dir, f)
        m = re.match(r"#\s+(.+)", open(p, encoding="utf-8").readline()) if os.path.exists(p) else None
        name = m.group(1).split(":")[part].strip() if m else ""
        if name and not name.startswith("<"):
            return name
    return None


def channel_terms(ch_dir):
    terms = {os.path.basename(ch_dir): "channel slug"}
    genre = genre_words(ch_dir)
    for w in sorted(genre):
        terms[rf"\b{w}\b"] = "genre word (channel.md Thể loại)"
    name = channel_name(ch_dir)
    if name:
        terms[name] = terms[name.replace(" ", "")] = "channel name"
        for w in re.findall(r"[A-Za-z]{5,}", name):
            if w.lower() not in genre:
                terms[rf"\b{w}\b"] = "channel name word"
    tr = os.path.join(ch_dir, "translate.yaml")
    m = re.search(r"^channel_id:\s*(UC[\w-]+)", open(tr, encoding="utf-8").read(), re.M) if os.path.exists(tr) else None
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
    ap = argparse.ArgumentParser(description="Báo chỗ skill/template nhắc tới một kênh cụ thể (tên, slug, thể loại, channel id)")
    ap.parse_args()
    os.chdir(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))
    dirs = [d.rstrip("/") for d in sorted(glob.glob("channel/*/")) if not os.path.basename(d.rstrip("/")).startswith("_")]
    terms = {}
    for d in dirs:
        for t, kind in channel_terms(d).items():
            terms[t] = f"{kind} ({os.path.basename(d)})"
    pats = [(re.compile(t if t.startswith(r"\b") else re.escape(t), re.I), t, kind) for t, kind in terms.items() if len(t) >= 4]
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
