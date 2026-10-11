#!/usr/bin/env python3
import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[4]
AUDIT = ROOT / "research" / "christmas-carols" / "pd-audit"
WORK = AUDIT / "_work"
OUT = ROOT / "production" / "codex" / "pd-read"
SCRIPTS = Path(__file__).resolve().parent
PY = sys.executable
MODEL = "cx/gpt-6.1-sol"
IMG_EXT = {".png", ".jpg", ".jpeg"}

PICK_PROMPT = """You help verify a public-domain melody. Song id: {slug}.
Printed sources we know for it (title, year, page):
{sources}

The attached images are scans saved for this song, in this order:
{names}

Look at every image. Find the page image(s) of ONE printed edition dated 1930 or earlier that show this song's melody with notes
(prefer the first source listed that you can find; prefer full pages over partial crops; when two images show the same page, take the one with
the most pixels). Only pages holding the first verse's notes; skip pages that hold only later verses or words.
First write one line per image: its name, what it shows (book/edition if visible, title of the piece, first lyric words, whether it is
a full page or a crop/zoom).
Then output ONE json block:
```json
{{"status": "OK" or "NO_SCAN", "pages": ["<file names of the chosen pages, in reading order, only pages that hold this song's notes>"],
  "edition": "<book title + year as printed or from the source list>", "piece_title": "<title printed above the piece>",
  "first_words": "<first lyric words under the melody, or empty>", "melody_staff": "<which staff/voice holds the tune, e.g. top voice of the treble staff, the voice staff above the piano>",
  "where": "<where on the page the piece starts and ends if the page holds other pieces>", "doubts": "<anything unclear>"}}
```
Use NO_SCAN when no image shows this song's notes from a 1930-or-earlier print."""

READ_PROMPT = """The attached images come from a printed score ({edition}), piece "{piece_title}".
Image 1 = an overview of the whole page; then the page cut into {kind} in reading order, top to bottom{overlap}: {names}.
The tune is in: {melody_staff}. First lyric words: "{first_words}". Where on the page: {where}.

First say in one line whether you can see the images and what is on them (lyrics you can read, clefs, time signature, key signature).
Then transcribe ONLY the melody line ({melody_staff}) of this piece, first verse, every bar from the first note to the final bar line.
Write repeats out in full (play them as printed, no repeat signs, no first/second-ending signs; take the ending that is printed for each pass).
ABC: X:1, M:<as printed>, L:1/4, K:<key as printed>, bar lines as printed, inline [M:..] for meter changes, keep the printed accidentals.
Never use a version of the tune you know from memory; write what is printed even if it looks odd. Mark every bar you are unsure of with a
comment line "% unsure bar N: <why>". If a bar is cut off between two images, read it from the image where it is whole.
End with the ABC inside one ```abc block."""


def codex(prompt, images, out_md, log, effort="high"):
    with tempfile.TemporaryDirectory(prefix="pdread-") as tmp:
        cmd = ["codex", "exec", "-m", MODEL, "-c", f"model_reasoning_effort={effort}", "-s", "read-only",
               "--skip-git-repo-check", "--json", "-o", str(out_md)]
        for img in images:
            cmd += ["-i", str(img)]
        cmd.append("-")
        with open(log, "w") as lf:
            subprocess.run(cmd, input=prompt, text=True, cwd=tmp, stdout=lf, stderr=subprocess.STDOUT)
    return out_md.read_text() if out_md.exists() else ""


def block(text, lang):
    found = re.findall(rf"```{lang}\s*\n(.*?)```", text, re.S)
    return found[-1] if found else None


def sources_text(slug):
    audit = json.loads((AUDIT / f"{slug}.json").read_text())
    rows = []
    for s in audit["melody"].get("pd_sources", []):
        rows.append(f"- {s.get('title')} ({s.get('year')}, {s.get('kind')}) {s.get('url', '')}")
    return "\n".join(rows) or "- none recorded"


def candidates(slug):
    d = WORK / slug
    if not d.exists():
        return []
    out = []
    for p in sorted(d.iterdir()):
        if p.is_file() and p.suffix.lower() in IMG_EXT:
            try:
                w, h = Image.open(p).size
            except Exception:
                continue
            if h >= 600 and w >= 500:
                out.append(p)
    return out


def thumb(src, dst, width=1400):
    img = Image.open(src).convert("L")
    if img.width > width:
        img = img.resize((width, round(img.height * width / img.width)), Image.LANCZOS)
    img.save(dst)


def stage_pick(slug):
    d = OUT / slug
    d.mkdir(parents=True, exist_ok=True)
    pick = d / "pick.json"
    if pick.exists():
        return json.loads(pick.read_text())
    cands = candidates(slug)
    if not cands:
        result = {"status": "NO_SCAN", "pages": [], "doubts": "no saved image in _work"}
        pick.write_text(json.dumps(result, indent=2))
        return result
    tdir = d / "thumbs"
    tdir.mkdir(exist_ok=True)
    thumbs = []
    for p in cands:
        t = tdir / (p.stem + ".png")
        thumb(p, t)
        thumbs.append(t)
    names = "\n".join(f"{i}. {p.name} ({Image.open(p).size[0]}x{Image.open(p).size[1]} px)" for i, p in enumerate(cands, 1))
    text = codex(PICK_PROMPT.format(slug=slug, sources=sources_text(slug), names=names), thumbs, d / "pick.md", d / "pick.log",
                 effort="medium")
    raw = block(text, "json")
    try:
        result = json.loads(raw)
    except Exception:
        result = {"status": "ERROR", "pages": [], "doubts": "no json from picker"}
    by_stem = {p.stem: p.name for p in cands}
    result["pages"] = [by_stem.get(Path(p).stem, p) for p in result.get("pages", [])]
    result["pages"] = [p for p in result["pages"] if (WORK / slug / p).exists()]
    if result.get("status") == "OK" and not result["pages"]:
        result["status"] = "ERROR"
    pick.write_text(json.dumps(result, indent=2, ensure_ascii=False))
    return result


def stage_cut(slug, pick):
    d = OUT / slug / "sys"
    if (d / "systems.json").exists():
        return json.loads((d / "systems.json").read_text())
    pages = [str(WORK / slug / p) for p in pick["pages"]]
    subprocess.run([PY, str(SCRIPTS / "pd_systems.py"), *pages, "--out", str(d)], check=True, capture_output=True)
    return json.loads((d / "systems.json").read_text())


def stage_read(slug, pick, index, reader):
    d = OUT / slug
    abc = d / f"read{reader}.abc"
    if abc.exists() and abc.stat().st_size:
        return abc
    images, names, kinds = [], [], set()
    for n, page in enumerate(index, 1):
        images.append(d / "sys" / page["overview"])
        for c in page["crops"]:
            images.append(d / "sys" / c["file"])
            names.append(c["file"])
        kinds.add(page["mode"])
    if len(index) > 1:
        images = [d / "sys" / p["overview"] for p in index] + [i for i in images if not i.name.endswith("-page.png")]
    kind = "bands" if "bands" in kinds else "systems"
    prompt = READ_PROMPT.format(
        edition=pick.get("edition", ""), piece_title=pick.get("piece_title", ""), kind=kind,
        overlap=" (the bands overlap a little: do not count a bar twice)" if kind == "bands" else "",
        names=", ".join(names) + (f" (first {len(index)} images are page overviews p1..p{len(index)})" if len(index) > 1 else ""),
        melody_staff=pick.get("melody_staff", "the melody"), first_words=pick.get("first_words", ""), where=pick.get("where", "whole page"))
    text = codex(prompt, images, d / f"read{reader}.md", d / f"read{reader}.log")
    abc.write_text(block(text, "abc") or "")
    return abc


def compare(slug, abc):
    if not abc.exists() or not abc.read_text().strip():
        return None, "no abc"
    r = subprocess.run([PY, str(SCRIPTS / "pd_audit.py"), "compare", slug, str(abc), "--limit", "60"],
                       capture_output=True, text=True, cwd=ROOT)
    out = r.stdout + r.stderr
    (abc.with_suffix(".compare.txt")).write_text(out)
    m = re.search(r"pitch\+rhythm match: \d+/\d+ of ours \((\d+)%\), \d+/\d+ of source \((\d+)%\)", out)
    p = re.search(r"pitch-only match: \d+/\d+ of ours \((\d+)%\)", out)
    if not m:
        return None, out.strip().splitlines()[-1] if out.strip() else "compare failed"
    return (int(m.group(1)), int(m.group(2)), int(p.group(1)) if p else None), out


def diff_lines(out):
    return [l.strip() for l in out.splitlines() if l.strip().startswith("beat ")]


def run_slug(slug, readers):
    try:
        return read_slug(slug, readers)
    except Exception as e:
        return {"slug": slug, "pick": "ERROR", "note": repr(e)[:300]}


def read_slug(slug, readers):
    t0 = time.time()
    pick = stage_pick(slug)
    row = {"slug": slug, "pick": pick.get("status"), "pages": pick.get("pages", []), "edition": pick.get("edition")}
    if pick.get("status") != "OK":
        row["note"] = pick.get("doubts")
        return row
    index = stage_cut(slug, pick)
    with ThreadPoolExecutor(readers) as ex:
        abcs = list(ex.map(lambda r: stage_read(slug, pick, index, r), range(1, readers + 1)))
    for a in abcs:
        compare(slug, a)
    row.update(vote(slug))
    row["min"] = round((time.time() - t0) / 60, 1)
    return row


def beat_of(line):
    m = re.match(r"beat ([\d.]+)", line)
    return float(m.group(1)) if m else None


def vote(slug):
    d = OUT / slug
    reads = []
    for txt in sorted(d.glob("read*.compare.txt")):
        out = txt.read_text()
        m = re.search(r"pitch\+rhythm match: \d+/\d+ of ours \((\d+)%\)", out)
        p = re.search(r"pitch-only match: \d+/\d+ of ours \((\d+)%\)", out)
        if m:
            reads.append({"file": txt.name, "pr": int(m.group(1)), "p": int(p.group(1)) if p else None, "diffs": diff_lines(out)})
    n = len(reads)
    if not n:
        return {"readers": 0, "verdict": "NO_READ"}
    tally = {}
    for r in reads:
        for line in r["diffs"]:
            tally.setdefault(line, set()).add(r["file"])
    need = n // 2 + 1
    real = sorted((l for l, who in tally.items() if len(who) >= need), key=lambda l: beat_of(l) or 0)
    noise = sorted((l for l, who in tally.items() if len(who) < need), key=lambda l: beat_of(l) or 0)
    clean_votes = sum(1 for r in reads if not r["diffs"])
    if clean_votes >= need:
        verdict = "MATCH"
    elif real:
        verdict = "DIFFERS"
    else:
        verdict = "UNSETTLED"
    return {"readers": n, "scores": [[r["pr"], r["p"]] for r in reads], "verdict": verdict,
            "real": real, "noise": noise}


def stage_report(slugs):
    rows = []
    for slug in slugs:
        d = OUT / slug
        pick = json.loads((d / "pick.json").read_text()) if (d / "pick.json").exists() else {}
        row = {"slug": slug, "pick": pick.get("status", "-"), "pages": pick.get("pages", [])}
        if pick.get("status") == "OK":
            row.update(vote(slug))
        rows.append(row)
    return rows


def main():
    ap = argparse.ArgumentParser(description="PD melody check by Codex readers: pick the scan page, cut systems, blind reads, compare, vote per difference")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="pick + cut + reads (resumes: existing picks and reads are kept)")
    r.add_argument("slugs", nargs="+")
    r.add_argument("--jobs", type=int, default=8, help="songs in parallel")
    r.add_argument("--readers", type=int, default=2, help="independent reads per song; raise it to add votes to unsettled songs")
    s = sub.add_parser("report", help="vote over existing reads: MATCH, DIFFERS (majority-backed differences), UNSETTLED")
    s.add_argument("slugs", nargs="*")
    s.add_argument("--json", action="store_true")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if args.cmd == "report":
        slugs = args.slugs or sorted(p.name for p in OUT.iterdir() if (p / "pick.json").exists())
        for row in stage_report(slugs):
            if args.json:
                print(json.dumps(row, ensure_ascii=False))
                continue
            print(f"{row['slug']} | {row['pick']} | {row.get('verdict', '-')} | readers {row.get('readers', 0)} | "
                  f"{row.get('scores', '')} | real {len(row.get('real', []))} noise {len(row.get('noise', []))}")
            for l in row.get("real", []):
                print(f"    REAL  {l}")
        return
    summary = OUT / "summary.jsonl"
    with ThreadPoolExecutor(args.jobs) as ex:
        for row in ex.map(lambda sl: run_slug(sl, args.readers), args.slugs):
            with open(summary, "a") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
            print(json.dumps(row, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
