import hashlib
import itertools
import json
import random
import re
import time
from pathlib import Path

POOL = "thumb_pool.json"
OUT = "thumb-variant.json"
NO_REPEAT = ("pose", "lettering")
CORNERS = {"left": {"logo": "tl", "subscribe": "bl", "badge": "br"},
           "right": {"logo": "tr", "subscribe": "br", "badge": "bl"},
           "center": {"logo": "tr", "subscribe": "br", "badge": "bl"}}


def channel_root(d):
    d = Path(d).resolve()
    parts = d.parts
    if "channel" not in parts:
        raise SystemExit(f"{d} không nằm trong channel/<ch>/")
    i = len(parts) - 1 - parts[::-1].index("channel")
    if i + 1 >= len(parts):
        raise SystemExit(f"{d}: thiếu tên kênh sau channel/")
    return Path(*parts[:i]), Path(*parts[:i + 2])


def load_pool(ch):
    f = ch / POOL
    if not f.exists():
        raise SystemExit(f"kênh chưa có {f}: kênh tự viết pool (axes → option → text) trước khi chọn biến thể")
    pool = json.loads(f.read_text())
    axes = pool.get("axes") or {}
    if not axes:
        raise SystemExit(f"{f}: thiếu \"axes\"")
    for axis, opts in axes.items():
        if not isinstance(opts, dict) or not opts:
            raise SystemExit(f"{f}: trục {axis} không có option nào")
        for name, o in opts.items():
            if not isinstance(o, dict) or not isinstance(o.get("text"), str) or not o["text"].strip():
                raise SystemExit(f"{f}: {axis}.{name} thiếu \"text\"")
            for key in ("needs", "avoid"):
                for ref in o.get(key, []):
                    if not resolve(ref, axes, axis):
                        raise SystemExit(f"{f}: {axis}.{name} {key} '{ref}' không phải option của trục khác")
    return pool


def resolve(ref, axes, own_axis):
    if "=" in ref:
        a, n = ref.split("=", 1)
        return {(a, n)} if a != own_axis and n in axes.get(a, {}) else set()
    return {(a, ref) for a, opts in axes.items() if a != own_axis and ref in opts}


def compatible(combo, axes):
    for axis, name in combo.items():
        o = axes[axis][name]
        groups = {}
        for ref in o.get("needs", []):
            for a, n in resolve(ref, axes, axis):
                groups.setdefault(a, set()).add(n)
        if any(combo[a] not in names for a, names in groups.items()):
            return False
        for ref in o.get("avoid", []):
            if any(combo[a] == n for a, n in resolve(ref, axes, axis)):
                return False
    return True


def history(ch, skip=None):
    rows = []
    for f in ch.glob(f"*/*/{OUT}"):
        if skip is not None and f.parent.resolve() == Path(skip).resolve():
            continue
        try:
            v = json.loads(f.read_text())
        except (OSError, ValueError):
            continue
        if isinstance(v.get("axes"), dict):
            rows.append((f.stat().st_mtime, f.parent, v))
    return sorted(rows, key=lambda r: r[0])


def title_of(d):
    pm = Path(d) / "thumbnail-prompt.md"
    if not pm.exists():
        return None
    text = pm.read_text()
    i = text.find("## Prompt")
    block = re.search(r"```[a-z]*\n(.*?)\n```", text[i:], re.S) if i >= 0 else None
    if block:
        m = re.search(r"^Title(?: text)?:\s*(.+?)\s*$", block.group(1), re.M)
        if m:
            t = m.group(1).strip().strip('"')
            return None if re.fullmatch(r"<[^>]*>", t) else t
    m = re.search(r"^title_text:\s*\"?(.*?)\"?\s*$", text, re.M)
    t = m.group(1).strip() if m else ""
    return t if t and not t.startswith("<") else None


def parse_sets(sets, axes):
    force = {}
    for s in sets or []:
        if "=" not in s:
            raise SystemExit(f"--set {s}: cần dạng axis=name, axis là một trong {list(axes)}")
        a, n = s.split("=", 1)
        if a not in axes:
            raise SystemExit(f"--set {s}: không có trục '{a}'; chọn trong {list(axes)}")
        if n not in axes[a]:
            raise SystemExit(f"--set {s}: trục {a} không có '{n}'; chọn trong {list(axes[a])}")
        force[a] = n
    return force


def eligible(axes, title, force):
    names = {}
    for axis, opts in axes.items():
        if axis in force:
            o = opts[force[axis]]
            if title is not None and len(title) > o.get("max_title_chars", 10 ** 6):
                print(f"⚠️  --set {axis}={force[axis]}: title {len(title)} ký tự > max_title_chars {o['max_title_chars']} (vẫn giữ theo --set)")
            names[axis] = [force[axis]]
            continue
        ok = [n for n, o in opts.items() if o.get("weight", 1) > 0
              and (title is None or len(title) <= o.get("max_title_chars", 10 ** 6))]
        dropped = [n for n in opts if n not in ok]
        if dropped:
            print(f"{axis}: loại {', '.join(dropped)} (weight 0 hoặc title dài hơn max_title_chars)")
        if not ok:
            raise SystemExit(f"trục {axis} không còn option nào dùng được (title {len(title or '')} ký tự)")
        names[axis] = ok
    return names


def choose(d, seed=None, sets=None, title=None, dry_run=False):
    d = Path(d)
    if not d.is_dir():
        raise SystemExit(f"không thấy thư mục {d}")
    repo, ch = channel_root(d)
    pool = load_pool(ch)
    axes = pool["axes"]
    order = list(axes)
    force = parse_sets(sets, axes)
    title = title if title is not None else title_of(d)
    if title is None:
        print("chưa biết title (không có --title, không có dòng Title trong khối Prompt): bỏ qua max_title_chars")
    names = eligible(axes, title, force)
    combos = [dict(zip(order, c)) for c in itertools.product(*(names[a] for a in order))]
    combos = [c for c in combos if compatible(c, axes)]
    if not combos:
        raise SystemExit(f"không tổ hợp nào thỏa needs/avoid{' với --set ' + str(force) if force else ''}")
    past = [v["axes"] for _, _, v in history(ch, d)]
    used = {tuple(p.get(a) for a in order) for p in past}
    fresh = [c for c in combos if tuple(c[a] for a in order) not in used]
    if not fresh:
        print("mọi tổ hợp còn lại đều đã dùng: cho phép lặp tổ hợp")
        fresh = combos
    if past:
        prev = past[-1]
        for axis in pool.get("no_repeat", NO_REPEAT):
            if axis in axes and axis not in force:
                alt = [c for c in fresh if c[axis] != prev.get(axis)]
                if alt:
                    fresh = alt
    n_avoid = int(pool.get("avoid_last", 3))
    recent = past[-n_avoid:] if n_avoid > 0 else []
    for need in range(len(order) - 1, -1, -1):
        ok = [c for c in fresh if all(sum(c[a] != r.get(a) for a in order) >= need for r in recent)]
        if ok:
            break
    if seed is None:
        rel = str(d.resolve().relative_to(repo.resolve()))
        seed = int(hashlib.sha1(rel.encode()).hexdigest()[:8], 16)
    rnd = random.Random(seed)
    weights = []
    for c in ok:
        w = 1.0
        for a in order:
            w *= max(axes[a][c[a]].get("weight", 1), 0) or 1e-9
        weights.append(w)
    c = rnd.choices(ok, weights=weights)[0]
    lines = {a: " ".join(axes[a][c[a]]["text"].split()) for a in order}
    side = next((axes[a][c[a]].get("side") for a in order if axes[a][c[a]].get("side")), None)
    result = {"axes": c, "seed": seed, "lines": lines, "side": side}
    print(f"{len(ok)} ứng viên (khác ≥ {need}/{len(order)} trục so với {len(recent)} ảnh gần nhất; lịch sử {len(past)} ảnh; seed {seed})\n")
    print("VARIANT (" + ", ".join(f"{a}={c[a]}" for a in order) + "):")
    for a in order:
        print(lines[a])
    if side in CORNERS:
        want = CORNERS[side]
        print(f"\n→ chữ ở {side}: {d / 'video.json'} phải đặt " + ", ".join(f"{k}.corner \"{v}\"" for k, v in want.items()))
        vj = d / "video.json"
        if vj.exists():
            try:
                cur = json.loads(vj.read_text())
            except ValueError:
                cur = {}
            diff = [f"{k} {(cur.get(k) or {}).get('corner', '(mặc định kênh)')} → {v}" for k, v in want.items()
                    if (cur.get(k) or {}).get("corner") != v]
            print("   video.json cần sửa: " + "; ".join(diff) if diff else "   video.json đã đúng góc")
    if dry_run:
        print("\n(--dry-run: không ghi)")
        return result
    (d / OUT).write_text(json.dumps(result, indent=1, ensure_ascii=False) + "\n")
    print(f"\nđã ghi {d / OUT}: dán khối VARIANT vào THIS IMAGE của khối Prompt")
    return result


def table(ch_dir):
    ch = Path(ch_dir)
    rows = history(ch)
    pool_f = ch / POOL
    order = list(json.loads(pool_f.read_text()).get("axes", {})) if pool_f.exists() else []
    for _, _, v in rows:
        order += [a for a in v["axes"] if a not in order]
    print("| thư mục | ngày | " + " | ".join(order) + " | side | seed |")
    print("|---|---|" + "---|" * len(order) + "---|---|")
    for mt, folder, v in rows:
        cells = [str(folder.relative_to(ch)), time.strftime("%Y-%m-%d %H:%M", time.localtime(mt))]
        cells += [v["axes"].get(a, "") for a in order] + [str(v.get("side") or ""), str(v.get("seed", ""))]
        print("| " + " | ".join(cells) + " |")
    if not rows:
        print(f"(chưa có {OUT} nào trong {ch})")
