import datetime as dt
import json
import math
import random
import re
from collections import Counter, defaultdict
from pathlib import Path

MOODS = {
    "eve": lambda t: t.get("time") in ("night", "twilight", "evening") and t.get("palette") != "cool-blue",
    "indoor": lambda t: t.get("place") == "indoor" and t.get("time") in ("night", "twilight", "evening"),
    "town": lambda t: t.get("time") in ("night", "twilight", "evening"),
    "winter": lambda t: t.get("palette") in ("cool-blue", "white-gold"),
    "morning": lambda t: t.get("time") in ("day", "golden"),
}
TIME_STEP = {"day": 0, "golden": 1, "twilight": 2, "evening": 3, "night": 3}
PALETTE_OK = {
    "warm-gold": {"warm-gold", "red-green", "white-gold"},
    "red-green": {"red-green", "warm-gold", "white-gold"},
    "white-gold": {"white-gold", "warm-gold", "red-green", "cool-blue"},
    "cool-blue": {"cool-blue", "white-gold"},
}
SCALE_ORDER = {"vista": 0, "street": 1, "room": 2, "macro": 3}

RULES = {
    "lead_share_min": 0.5,
    "lead_share_target": 0.6,
    "theme_max": 15,
    "macro_min": 0.10,
    "macro_max": 0.20,
    "wide_min": 0.25,
    "bridges_min": 10,
    "hero_count": 15,
    "hero_place": "indoor",
    "hero_scale_not": ["macro"],
    "hero_object_gap": 2,
    "hero_object_max": 2,
    "object_df_max": 0.15,
    "hero_cooldown_days": 30,
    "hero_per_theme": 2,
    "near_dup": 0.85,
    "near_adjacent": 0.80,
    "luma_jump": 0.08,
    "slide_dx": 0.05,
    "gap_minutes": 20,
    "gap_cycle_share": 0.75,
    "distinct_hi": 0.85,
    "distinct_hi_max_uses": 3,
    "same_camera_run": 2,
    "overlap_7d_max": 0.5,
    "overlap_any_max": 0.7,
}
GENERIC_OBJECTS = {"frame", "window", "wall", "door", "curtain", "cushion", "beam", "railing", "step", "post", "path", "branch",
                   "light", "garland", "bench", "chair", "table", "lamp", "lantern", "tree", "house", "rug", "floor",
                   "ceiling", "shelf", "plant", "pot", "vase", "ribbon", "ornament", "candle", "gift", "box", "basket",
                   "blanket", "pillow", "throw", "fence", "edge", "sky", "snow", "roof", "front", "pair", "gold",
                   "furniture", "string", "street", "slice", "doorway", "stack", "holder", "set", "top", "side"}
COST = {"theme_gap": 4, "theme_adj": 30, "object": 8, "camera": 2, "slide": 3, "route": 5, "luma": 4, "palette": 5, "time": 6, "place": 6, "near": 8, "pair": 80,
        "cycle": 60, "gap": 100}


class Clip:
    def __init__(self, cid, card, mp4):
        self.id = cid
        self.family, self.theme = cid.split("/")[0], "/".join(cid.split("/")[:2])
        self.tags = card.get("tags") or {}
        self.camera = card.get("camera")
        m = card["measure"]
        self.m = m
        self.seconds = float(m["seconds"])
        self.mp4 = mp4
        self.near = {n["id"].replace("__", "/"): n["sim"] for n in m.get("near", [])}
        self.distinct = float(m.get("distinct", 0.5))
        self.objects = lock_objects((card.get("clip") or {}).get("lock") or "")
        self.subject_words = {singular(w) for w in re.findall(r"[a-z]+", (card.get("subject") or "").lower())}
        self.anchors = set()

    @property
    def scale(self):
        return self.tags.get("scale")

    @property
    def bridge(self):
        return self.family == "detail" or self.tags.get("snow") == "window" or self.scale == "macro"

    def sim(self, other):
        return max(self.near.get(other.id, 0.0), other.near.get(self.id, 0.0))


def singular(w):
    if w.endswith(("lves", "rves")):
        return w[:-3] + "f"
    if w.endswith("ies"):
        return w[:-3] + "y"
    if w.endswith(("ches", "shes", "xes")):
        return w[:-2]
    if w.endswith("s") and not w.endswith("ss"):
        return w[:-1]
    return w


def lock_objects(lock):
    out = set()
    for item in re.split(r",|\band\b", lock.lower()):
        words = re.findall(r"[a-z]+", re.split(r"\b(?:with|of|on|in|under|beside)\b", item)[0])
        if words:
            out.add(singular(words[-1]))
    return out


def set_anchors(clips):
    vocab = set().union(*(c.objects for c in clips)) - GENERIC_OBJECTS
    for c in clips:
        c.objects = c.objects | (c.subject_words & vocab)
    df = Counter(o for c in clips for o in c.objects)
    limit = RULES["object_df_max"] * len(clips)
    for c in clips:
        c.anchors = {o for o in c.objects if df[o] <= limit and o not in GENERIC_OBJECTS}


def family_links(sdir):
    fams = {p.parent.name for p in sdir.glob("*/README.md")}
    links = {}
    for f in fams:
        text = (sdir / f / "README.md").read_text()
        line = next((ln for ln in text.splitlines() if "Ghép tốt với" in ln), "")
        links[f] = {w for w in re.findall(r"[a-z][a-z-]+", line) if w in fams and w != f}
        if "mọi nhóm" in line:
            links[f] = fams - {f}
    return links


def history(root, name):
    out = []
    for f in sorted(root.glob("*/montage.json")):
        if f.parent.name == name:
            continue
        try:
            out.append(json.loads(f.read_text()))
        except json.JSONDecodeError:
            pass
    return out


def build(clips, sdir, montage_root, a):
    rnd = random.Random(a.seed)
    links = family_links(sdir)
    lead = set(a.lead.split("+"))
    hist = history(montage_root, a.name)
    now = dt.datetime.now()
    uses_30 = Counter()
    hero_recent = set()
    for h in hist:
        made = dt.datetime.fromisoformat(h.get("created", "2000-01-01T00:00:00"))
        if (now - made).days <= 30:
            uses_30.update(h.get("cast", []))
            hero_recent.update(h.get("hero", []))

    set_anchors(clips)
    mood = MOODS[a.mood]
    pool = [c for c in clips if mood(c.tags)]
    by_id = {c.id: c for c in clips}

    if a.keep_cast:
        prev = json.loads(Path(a.keep_cast).read_text())
        cast = [by_id[i] for i in prev["cast"] if i in by_id]
        hero = [by_id[i] for i in prev["hero"] if i in by_id]
    else:
        cast = choose_cast(pool, lead, links, uses_30, a.cast, rnd)
        hero = choose_hero(cast, lead, hero_recent)

    seq, violations = sequence(cast, hero, lead, links, a, rnd)
    checks = check(cast, hero, seq, lead, hist, now, violations, a)
    return cast, hero, seq, checks, len(pool)


def choose_cast(pool, lead, links, uses_30, size, rnd):
    R = RULES
    order = sorted(pool, key=lambda c: (uses_30[c.id], rnd.random()))
    cast, theme_n, scale_n = [], Counter(), Counter()

    def ok(c, strict):
        if c in cast or theme_n[c.theme] >= R["theme_max"]:
            return False
        if c.scale == "macro" and scale_n["macro"] + 1 > R["macro_max"] * size:
            return False
        if strict and any(c.sim(o) >= R["near_dup"] for o in cast):
            return False
        return True

    def take(cands, limit):
        for strict in (True, False):
            for c in cands:
                if len(cast) >= size or limit():
                    return
                if ok(c, strict):
                    cast.append(c)
                    theme_n[c.theme] += 1
                    scale_n[c.scale] += 1

    lead_pool = [c for c in order if c.family in lead]
    lead_cap = sum(min(R["theme_max"], n) for n in Counter(c.theme for c in lead_pool).values())
    n_lead = max(math.ceil(R["lead_share_min"] * size), min(lead_cap, round(R["lead_share_target"] * size)))
    take(lead_pool, lambda: sum(c.family in lead for c in cast) >= n_lead)

    near_fams = set().union(*(links.get(f, set()) for f in lead)) - lead
    second = [c for c in order if c.family in near_fams] + [c for c in order if c.family not in near_fams | lead]
    take([c for c in second if c.bridge], lambda: sum(c.bridge for c in cast) >= R["bridges_min"])
    take([c for c in second if c.scale == "macro"], lambda: scale_n["macro"] >= R["macro_min"] * size)
    if not all(c.tags.get("place") == "indoor" for c in pool):
        take([c for c in second if c.scale in ("vista", "street")],
             lambda: scale_n["vista"] + scale_n["street"] >= R["wide_min"] * size)
    take(second, lambda: False)
    take(lead_pool, lambda: False)
    return cast


def choose_hero(cast, lead, hero_recent):
    R = RULES
    lum = sorted(c.m["luma"] for c in cast)
    floor = lum[len(lum) // 4]
    cands = sorted((c for c in cast if c.family in lead and c.id not in hero_recent and c.m["luma"] >= floor
                    and c.tags.get("place") == R["hero_place"] and c.scale not in R["hero_scale_not"]),
                   key=lambda c: -c.distinct)
    hero, per_theme, per_object = [], Counter(), Counter()
    for c in cands:
        if per_theme[c.theme] >= R["hero_per_theme"] or any(c.sim(h) >= R["near_dup"] for h in hero):
            continue
        if any(per_object[o] >= R["hero_object_max"] for o in c.anchors):
            continue
        hero.append(c)
        per_theme[c.theme] += 1
        per_object.update(c.anchors)
        if len(hero) == R["hero_count"]:
            break
    return hero


def order_hero(hero):
    gap = RULES["hero_object_gap"]
    out, rest = [], list(hero)
    while rest:
        recent = out[-gap:]
        p = out[-1] if out else None

        def key(c):
            clash = sum(bool(c.anchors & h.anchors) for h in recent)
            same_theme = sum(h.theme == c.theme for h in recent)
            return (clash, same_theme, len(joins(p, c, [], set())), -c.distinct)
        nxt = min(rest, key=key)
        out.append(nxt)
        rest.remove(nxt)
    return out


def joins(prev, c, recent_cams, relax):
    R = RULES
    bad = []
    if prev is None:
        return bad
    if "near" not in relax and c.sim(prev) >= R["near_adjacent"]:
        bad.append("near")
    if "object" not in relax and c.anchors & prev.anchors:
        bad.append("object")
    if "camera" not in relax and len(recent_cams) >= R["same_camera_run"] and all(x == c.camera for x in recent_cams[-R["same_camera_run"]:]):
        bad.append("camera")
    pdx, cdx = prev.m["cam"]["dx"], c.m["cam"]["dx"]
    if "slide" not in relax and abs(pdx) > R["slide_dx"] and abs(cdx) > R["slide_dx"] and (pdx > 0) != (cdx > 0):
        bad.append("slide")
    if "luma" not in relax and abs(prev.m["luma_out"] - c.m["luma_in"]) > R["luma_jump"]:
        bad.append("luma")
    if "place" not in relax and prev.tags.get("place") != c.tags.get("place") and not (prev.bridge or c.bridge):
        bad.append("place")
    tp, tc = TIME_STEP.get(prev.tags.get("time"), 3), TIME_STEP.get(c.tags.get("time"), 3)
    if "time" not in relax and abs(tp - tc) > 1:
        bad.append("time")
    pp, pc = prev.tags.get("palette"), c.tags.get("palette")
    if "palette" not in relax and pp and pc and pc not in PALETTE_OK.get(pp, {pc}):
        bad.append("palette")
    return bad


def sequence(cast, hero, lead, links, a, rnd):
    R = RULES
    slot = lambda c: c.seconds - a.xfade
    total = a.minutes * 60
    cycle = sum(slot(c) for c in cast)
    min_gap = min(R["gap_minutes"] * 60, R["gap_cycle_share"] * cycle)
    per_block = max(1, round(a.block / (cycle / len(cast))))
    uses, last, pairs = Counter(), {}, set()
    seq, cams, violations = [], [], Counter()
    themes = defaultdict(list)
    for c in cast:
        themes[c.theme].append(c)
    state = {"t": 0.0, "prev": None, "done": set(), "placed": []}

    def eligible(c):
        return not (c.distinct >= R["distinct_hi"] and uses[c.id] >= R["distinct_hi_max_uses"])

    def remaining():
        rem = [c for c in cast if c.id not in state["done"] and eligible(c)]
        if not rem:
            state["done"] = set()
            rem = [c for c in cast if eligible(c)] or list(cast)
        return rem

    def place(c, relaxed):
        prev = state["prev"]
        seq.append({"clip": c.id, "flip": uses[c.id] % 2 == 1, "start_s": round(state["t"], 2),
                    "dur_s": c.seconds, "relaxed": relaxed})
        for r in relaxed:
            violations[r] += 1
        if prev is not None:
            pairs.add((prev.id, c.id))
        uses[c.id] += 1
        last[c.id] = state["t"]
        state["done"].add(c.id)
        cams.append(c.camera)
        state["t"] += slot(c)
        state["prev"] = c
        state["placed"].append(c)

    def hard(c, relax):
        prev = state["prev"]
        bad = []
        if "gap" not in relax and c.id in last and state["t"] - last[c.id] < min_gap:
            bad.append("gap")
        if "pair" not in relax and prev is not None and (prev.id, c.id) in pairs:
            bad.append("pair")
        placed = state["placed"]
        if prev is not None and prev.theme == c.theme:
            bad.append("theme_adj")
        elif len(placed) >= 2 and placed[-2].theme == c.theme:
            bad.append("theme_gap")
        return bad + joins(prev, c, cams, relax)

    def choose(route_ids):
        route_fams = {th.split("/")[0] for th in route_ids}
        rem = {c.id for c in remaining()}
        prev = state["prev"]
        prog = SCALE_ORDER.get(prev.scale, 0) if prev else 0
        best = None
        for c in cast:
            bad = hard(c, set())
            if c.family != "detail":
                if c.family not in route_fams:
                    bad.append("route")
            if c.id not in rem:
                bad.append("cycle")
            key = (sum(COST[x] for x in bad), uses[c.id], abs(SCALE_ORDER.get(c.scale, 1) - prog - 0.5), rnd.random())
            if best is None or key < best[0]:
                best = (key, c, bad)
        return best[1], best[2]

    ordered_hero = order_hero(hero)
    for c in ordered_hero:
        place(c, joins(state["prev"], c, cams, set()))

    lead_time = sum(slot(c) for c in ordered_hero)
    recent = []
    near_fams = set().union(*(links.get(f, set()) for f in lead)) - lead
    while state["t"] < total:
        rem = remaining()
        left = Counter(c.theme for c in rem if c.id not in last or state["t"] - last[c.id] >= min_gap)
        if not left:
            left = Counter(c.theme for c in rem)
        lead_due = lead_time < R["lead_share_target"] * max(state["t"], 1)
        fams = lead if lead_due or not near_fams else near_fams
        cand = [th for th in left if th.split("/")[0] in fams and th.split("/")[0] != "detail"]
        if not cand:
            cand = [th for th in left if th.split("/")[0] != "detail"] or list(left)
        cand.sort(key=lambda th: (th in recent[-4:], -left[th], rnd.random()))
        route, n = [], 0
        first_fam = cand[0].split("/")[0] if cand else None
        for th in cand:
            if n >= per_block:
                break
            if th.split("/")[0] == first_fam or n < per_block // 2:
                route.append(th)
                n += left[th]
        recent.extend(route)
        block_end = state["t"] + a.block
        while state["t"] < min(block_end, total):
            c, relaxed = choose(set(route))
            if c.family in lead:
                lead_time += slot(c)
            place(c, relaxed)
    return seq, violations


def hero_check(hero, seq, by):
    R = RULES
    opening = [by[s["clip"]] for s in seq[:len(hero)]]
    bad = []
    for i, c in enumerate(opening):
        if c.tags.get("place") != R["hero_place"]:
            bad.append(f"{c.id}: place {c.tags.get('place')}")
        if c.scale in R["hero_scale_not"]:
            bad.append(f"{c.id}: scale {c.scale}")
        for j in range(max(0, i - R["hero_object_gap"]), i):
            shared = c.anchors & opening[j].anchors
            if shared:
                bad.append(f"{opening[j].id} ~ {c.id} ({i - j - 1} between): {', '.join(sorted(shared))}")
    return {"opening_s": round(seq[len(hero)]["start_s"], 1) if len(seq) > len(hero) else None,
            "objects": {c.id: sorted(c.anchors) for c in opening}, "violations": bad}


def check(cast, hero, seq, lead, hist, now, violations, a):
    R = RULES
    n = len(cast)
    fam = Counter(c.family for c in cast)
    scale = Counter(c.scale for c in cast)
    theme = Counter(c.theme for c in cast)
    uses = Counter(s["clip"] for s in seq)
    by = {c.id: c for c in cast}
    first_repeat = next((s["start_s"] for i, s in enumerate(seq) if s["clip"] in {x["clip"] for x in seq[:i]}), None)
    gaps = []
    lastpos = {}
    for s in seq:
        if s["clip"] in lastpos:
            gaps.append(s["start_s"] - lastpos[s["clip"]])
        lastpos[s["clip"]] = s["start_s"]
    pair_n = Counter((x["clip"], y["clip"]) for x, y in zip(seq, seq[1:]))
    lead_t = sum(s["dur_s"] - a.xfade for s in seq if by[s["clip"]].family in lead)
    total_t = seq[-1]["start_s"] + seq[-1]["dur_s"] if seq else 0
    overlap = []
    cast_ids = {c.id for c in cast}
    for h in hist:
        other = set(h.get("cast", []))
        if not other:
            continue
        made = dt.datetime.fromisoformat(h.get("created", "2000-01-01T00:00:00"))
        share = len(cast_ids & other) / len(cast_ids)
        limit = R["overlap_7d_max"] if (now - made).days <= 7 else R["overlap_any_max"]
        overlap.append({"montage": h.get("name"), "share": round(share, 3), "limit": limit, "ok": share <= limit})
    return {
        "cast": n,
        "lead_share_cast": round(sum(fam[f] for f in lead) / n, 3),
        "lead_share_time": round(lead_t / max(total_t, 1), 3),
        "families": dict(fam),
        "themes": len(theme),
        "theme_max": max(theme.values()),
        "scale": dict(scale),
        "macro_share": round(scale["macro"] / n, 3),
        "wide_share": round((scale["vista"] + scale["street"]) / n, 3),
        "bridges": sum(c.bridge for c in cast),
        "hero": len(hero),
        "hero_check": hero_check(hero, seq, by),
        "slots": len(seq),
        "total_s": round(total_t, 1),
        "uses_min_max": [min(uses.values()), max(uses.values())],
        "unused_cast": [c.id for c in cast if c.id not in uses],
        "first_repeat_s": first_repeat,
        "min_gap_s": round(min(gaps), 1) if gaps else None,
        "same_theme_adjacent": sum(by[x["clip"]].theme == by[y["clip"]].theme for x, y in zip(seq, seq[1:])),
        "same_theme_one_between": sum(by[x["clip"]].theme == by[y["clip"]].theme for x, y in zip(seq, seq[2:])),
        "same_object_adjacent": sum(bool(by[x["clip"]].anchors & by[y["clip"]].anchors) for x, y in zip(seq, seq[1:])),
        "repeated_pairs": sum(1 for v in pair_n.values() if v > 1),
        "flipped": sum(s["flip"] for s in seq),
        "relaxed_joins": dict(violations),
        "overlap": overlap,
    }
