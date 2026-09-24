#!/usr/bin/env python3
import argparse
import glob
import os
import re
import sys

import yaml

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))
LIST_TAIL = r"((?:\s*[,;–-]\s*\d{1,3})*)"


def channel_rules(channel):
    f = os.path.join(REPO, "channel", channel or "", "rules.md")
    m = re.search(r"```yaml\n(.*?)```", open(f).read(), re.S) if channel and os.path.isfile(f) else None
    return (yaml.safe_load(m.group(1)) or {}) if m else {}


def source_numbers(ref, pat):
    ref = str(ref or "")
    if ":" in ref:
        hits = [(m.start(1), int(m.group(1))) for m in pat.finditer(ref)]
        if hits:
            hits += [(m.start(1), int(m.group(1))) for m in re.finditer(r";\s*(\d{1,3})", ref)]
        return [x for _, x in sorted(hits)]
    lst = re.compile(f"(?:{pat.pattern}){LIST_TAIL}", re.I)
    return [int(x) for m in lst.finditer(ref) for x in [m.group(1)] + re.findall(r"\d{1,3}", m.group(m.re.groups))]


def secs(x):
    m = re.match(r"^(\d+):(\d\d)$", str(x or ""))
    return int(m[1]) * 60 + int(m[2]) if m else None


def our_titles_and_hooks(idea_path, channel, own_album=None):
    used = {}
    if not channel:
        return used
    own = os.path.abspath(os.path.join(REPO, own_album)) if own_album else None
    for md in glob.glob(os.path.join(REPO, "channel", channel, "albums", "*", "tracks", "*.md")):
        if own and os.path.abspath(os.path.dirname(os.path.dirname(md))) == own:
            continue
        m = re.match(r"^---\s*\n(.*?)\n---\s*\n", open(md).read(), re.S)
        if m:
            fm = yaml.safe_load(m.group(1)) or {}
            for k in ("title", "hook_phrase"):
                if fm.get(k):
                    used[str(fm[k]).lower().strip()] = f"{os.path.basename(os.path.dirname(os.path.dirname(md)))}/{fm.get('id')}"
    for other in glob.glob(os.path.join(REPO, "channel", channel, "ideas", "*", "idea.yaml")):
        if os.path.abspath(other) == os.path.abspath(idea_path):
            continue
        o = yaml.safe_load(open(other)) or {}
        for sl in o.get("slots") or []:
            for k in ("title", "hook_phrase"):
                if sl.get(k):
                    used.setdefault(str(sl[k]).lower().strip(), f"{o.get('id')}")
    return used


REQUIRED = ["id", "slug", "status", "provenance", "hypothesis", "differentiation", "target", "identity", "style_prompt",
            "track01", "slots", "lyrics_rules", "generation", "qc", "packaging", "metrics", "open_questions", "next_steps"]


def walk(x, path=""):
    if isinstance(x, dict):
        for k, v in x.items():
            yield from walk(v, f"{path}.{k}" if path else str(k))
    elif isinstance(x, list):
        for i, v in enumerate(x):
            yield from walk(v, f"{path}[{i}]")
    else:
        yield path, x


def norm(s):
    return re.sub(r"[^a-z0-9 ]", " ", str(s).lower().replace("'", "").replace("’", "")).split()


def contains_phrase(text, phrase):
    t, p = " ".join(norm(text)), " ".join(norm(phrase))
    return bool(p) and re.search(rf"(^| ){re.escape(p)}( |$)", t) is not None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("idea")
    ap.add_argument("--draft", action="store_true")
    a = ap.parse_args()
    d = yaml.safe_load(open(a.idea))
    rules = channel_rules(d.get("channel"))
    intro_vocab = set((rules.get("research") or {}).get("intro_vocab") or [])
    numbered = (rules.get("sources") or {}).get("numbered") or {}
    num_re = re.compile(numbered["pattern"], re.I) if numbered.get("pattern") else None
    num_fmt = numbered.get("format") or "{n}"
    E, W = [], []
    err = E.append
    warn = W.append

    for k in REQUIRED:
        if k not in d or d[k] in (None, "", [], {}):
            err(f"missing/empty: {k}")
    if d.get("todo"):
        (warn if a.draft else err)(f"`todo` still lists {len(d['todo'])} item(s): {d['todo'][:4]}{' ...' if len(d['todo']) > 4 else ''}")
    todos = [p for p, v in walk(d) if isinstance(v, str) and "TODO" in v]
    (warn if a.draft else err)(f"{len(todos)} TODO placeholder(s): {', '.join(todos[:8])}{' ...' if len(todos) > 8 else ''}") if todos else None

    sp = d.get("style_prompt") or {}
    text = sp.get("text") or ""
    if len(text) > 1000:
        err(f"style_prompt.text is {len(text)} chars (> 1000, Suno limit)")
    if text and sp.get("chars") != len(text):
        warn(f"style_prompt.chars says {sp.get('chars')} but text is {len(text)}")
    if re.search(r"[^\x00-\x7f]", text):
        warn("style_prompt.text has non-ASCII characters (Suno text must be English)")

    guard = ((d.get("differentiation") or {}).get("copy_guard") or {})
    bad = [x for x in (guard.get("titles") or []) + (guard.get("branding") or []) if x and len(norm(x)) >= 1]
    slots = d.get("slots") or []
    t1 = d.get("track01") or {}
    ours = [("style_prompt", text), ("track01.title", t1.get("title")), ("track01.hook", t1.get("hook_phrase")),
            ("title_working", d.get("title_working"))]
    ours += [(f"slot{s.get('n')}.title", s.get("title")) for s in slots] + [(f"slot{s.get('n')}.hook", s.get("hook_phrase")) for s in slots]
    ours += [(f"packaging.title[{i}]", t) for i, t in enumerate((d.get("packaging") or {}).get("video_title_candidates") or [])]
    for where, val in ours:
        if not val or "TODO" in str(val):
            continue
        for g in bad:
            if contains_phrase(val, g) and len(" ".join(norm(g))) >= 5:
                err(f"copy_guard hit: {where} contains '{g}'")

    avoid = {str(x).lower() for x in guard.get("source_avoid") or []}
    avoid |= {(num_fmt.format(n=x) if isinstance(x, int) else str(x)).lower() for x in guard.get("scripture_avoid") or []}
    for s in slots if num_re else []:
        ref = s.get("source_ref") or s.get("scripture")
        for x in source_numbers(ref, num_re):
            if num_fmt.format(n=x).lower() in avoid:
                err(f"slot {s.get('n')} uses {num_fmt.format(n=x)}, listed in source_avoid")
    their_hooks = [h for h in guard.get("hooks") or [] if h]
    for s in slots:
        for h in their_hooks:
            for k in ("hook_phrase", "title"):
                if s.get(k) and contains_phrase(s[k], h):
                    err(f"slot {s.get('n')} {k} contains their hook '{h}'")
    used = our_titles_and_hooks(a.idea, d.get("channel"), d.get("album"))
    for s in slots:
        for k in ("title", "hook_phrase"):
            v = str(s.get(k) or "").lower().strip()
            if v and v in used and not (k == "hook_phrase" and v == str(s.get("title") or "").lower().strip() and s.get("n") == 1 and used[v].startswith("idea")):
                (err if k == "title" else warn)(f"slot {s.get('n')} {k} '{s.get(k)}' is already used by {used[v]}")

    tg = d.get("target") or {}
    n = tg.get("track_count")
    if not isinstance(n, int):
        err("target.track_count must be an integer")
    if isinstance(n, int) and len(slots) != n:
        err(f"target.track_count={n} but {len(slots)} slots")
    ns = [s.get("n") for s in slots]
    if ns != list(range(1, len(slots) + 1)):
        err(f"slot numbers must be 1..N in order, got {ns}")
    if slots:
        if slots[0].get("arc_role") != "anchor":
            err("slot 1 must have arc_role: anchor (title track)")
        if slots[0].get("source") != "new":
            err("slot 1 must be source: new (CLAUDE.md: title track is never reused)")
    en = [s.get("energy") for s in slots]
    bad_en = [s.get("n") for s in slots if not isinstance(s.get("energy"), (int, float)) or isinstance(s.get("energy"), bool)]
    if bad_en:
        err(f"energy must be a number for every slot (missing/invalid: {bad_en})")
    bad_va = [s.get("n") for s in slots if s.get("valence") is not None and not isinstance(s.get("valence"), (int, float))]
    if bad_va:
        err(f"valence must be a number (slots {bad_va})")
    if not any(s.get("arc_role") == "peak" for s in slots):
        err("no slot has arc_role: peak (CLAUDE.md arc)")
    for s in slots:
        if intro_vocab and s.get("intro_type") and "TODO" not in str(s.get("intro_type")) and s["intro_type"] not in intro_vocab:
            err(f"slot {s.get('n')} intro_type '{s['intro_type']}' not in the vocabulary {sorted(intro_vocab)} (rules.md research.intro_vocab)")
        sd = secs(s.get("target_duration"))
        if s.get("target_duration") and sd is None:
            err(f"slot {s.get('n')} target_duration must be m:ss")
        if sd and sd > 360:
            err(f"slot {s.get('n')} target_duration {s['target_duration']} > 6:00 (Suno limit)")
    mx = ((d.get("qc") or {}).get("rules") or {}).get("max_intro_seconds")
    for s in slots:
        if s.get("n") != 1 and s.get("intro_length") in ("medium", "long") and isinstance(mx, (int, float)) and mx <= 15:
            warn(f"slot {s.get('n')} intro_length '{s['intro_length']}' vs qc.rules.max_intro_seconds={mx}: make sure a voice/hum still comes by {mx} s")
    if all(isinstance(x, (int, float)) for x in en) and en:
        for i in range(1, len(en)):
            if abs(en[i] - en[i - 1]) > 2:
                err(f"energy jump > 2 between slots {i} and {i + 1} ({en[i - 1]} -> {en[i]})")
        curve = tg.get("energy_curve")
        if isinstance(curve, list) and curve and curve != en:
            warn(f"target.energy_curve {curve} differs from slot energies {en}")
        peak = en.index(max(en)) + 1
        if not (len(en) * 0.4 <= peak <= len(en) * 0.8):
            warn(f"energy peak at slot {peak}: CLAUDE.md wants the climax around 60-70 % of the album")
    it = [s.get("intro_type") for s in slots]
    for i in range(1, len(it)):
        if it[i] and it[i] == it[i - 1] and "TODO" not in str(it[i]):
            err(f"slots {i} and {i + 1} both open with intro_type '{it[i]}' (§7.2)")
    hooks = [str(s.get("hook_phrase") or "").lower().strip() for s in slots if s.get("hook_phrase") and "TODO" not in str(s.get("hook_phrase"))]
    dup = {h for h in hooks if hooks.count(h) > 1}
    if dup:
        err(f"duplicate hook_phrase: {sorted(dup)}")
    titles = [str(s.get("title") or "").lower() for s in slots]
    for s in slots:
        h = str(s.get("hook_phrase") or "").lower()
        if s.get("n") != 1 and h and any(h == t for t in titles if t != str(s.get("title") or "").lower()):
            err(f"slot {s.get('n')} hook equals another slot's title")

    if slots:
        s0 = slots[0]
        for k, k0 in (("title", "title"), ("hook_phrase", "hook_phrase")):
            if t1.get(k) and s0.get(k0) and str(t1[k]).strip().lower() != str(s0[k0]).strip().lower():
                err(f"track01.{k} '{t1[k]}' differs from slots[0].{k0} '{s0[k0]}' (slots[0] is what album-plan reads)")
    tempo = (tg.get("tempo") or {}).get("felt_bpm_qc")
    if not isinstance(tempo, (int, float)):
        err("target.tempo.felt_bpm_qc must be a number")
    for m in re.finditer(r"(\d{2,3})\s*bpm", text or "", re.I):
        if isinstance(tempo, (int, float)) and abs(int(m.group(1)) - tempo) > 1:
            err(f"style_prompt says {m.group(1)} BPM but target.tempo.felt_bpm_qc is {tempo} (prompt BPM = target, no compensation)")
    qt = ((d.get("qc") or {}).get("tempo") or {}).get("target_bpm")
    if isinstance(qt, (int, float)) and isinstance(tempo, (int, float)) and abs(qt - tempo) > 1:
        err(f"qc.tempo.target_bpm {qt} != target.tempo.felt_bpm_qc {tempo}")
    an = str((slots[0].get("arrangement_note") if slots else "") or "")
    if slots and (len(an) < 40 or an.lower().startswith("see ")):
        err("slots[0].arrangement_note must carry the Track 01 arrangement itself (album-plan reads slots, not track01.tag_skeleton)")
    if not t1.get("opening_spec"):
        err("track01.opening_spec missing (the 0-15 s timeline is the most important brief)")
    if not t1.get("gate"):
        err("track01.gate missing")
    vo = (tg.get("vocal") or {}).get("presence_max_s") or {}
    if isinstance(vo.get("track01"), (int, float)) and vo["track01"] > 15:
        err("target.vocal.presence_max_s.track01 > 15 s violates CLAUDE.md")

    gen = d.get("generation") or {}
    b = gen.get("budget") or {}
    gens = b.get("gens") or {}
    n_new = sum(1 for s in d.get("slots") or [] if (s.get("source") or "new") == "new")
    if isinstance(b.get("total_credits"), (int, float)):
        if n_new and all(isinstance(gens.get(k), (int, float)) for k in ("track01", "others_each")):
            want = gens["track01"] * (b.get("credits_per_max_gen") or 20) + gens["others_each"] * 10 * max(n_new - 1, 0)
            if want != b["total_credits"]:
                warn(f"budget: slot 1 {gens['track01']} Max + {n_new - 1} new x {gens['others_each']} normal = {want} != {b['total_credits']} credits")
        if gen.get("max_mode") or (gens.get("track01") or 2) > 2 or (gens.get("others_each") or 1) > 1:
            warn("budget: CLAUDE.md = slot 1 two Max rounds, others one normal round (max_mode false)")
        if b["total_credits"] > 250:
            err("budget: album over 250 credits (CLAUDE.md)")
        if b["total_credits"] > (b.get("credits_per_month") or 2500):
            err("budget exceeds the monthly credits")
    dl = gen.get("download") or {}
    if dl.get("official_downloads", 0) != 0:
        err("generation.download.official_downloads must be 0 (never use Suno Download; usesuno route only)")
    voice = ((d.get("identity") or {}).get("suno_voice") or {})
    if not voice.get("id"):
        warn("identity.suno_voice.id empty: suno-generate needs a Voice id (or null on purpose for a new persona)")
    pd = (d.get("identity") or {}).get("persona_decision") or {}
    if d.get("status") in ("approved", "promoted") and not pd.get("decided"):
        err("status approved but persona_decision.decided is false")
    for r in (d.get("provenance") or {}).get("research") or []:
        rp = r.get("reference") and os.path.join(REPO, r["reference"])
        if rp and os.path.exists(rp):
            ref = yaml.safe_load(open(rp)) or {}
            rtm = (ref.get("album") or {}).get("tempo") or {}
            rt = rtm.get("felt_bpm_median", rtm.get("felt_bpm_qc_median"))
            it = (tg.get("tempo") or {}).get("reference_measured")
            if rt and it and abs(rt - it) > 1:
                warn(f"target.tempo.reference_measured {it} != reference.yaml {rt}")
            miss = [x for x in (ref.get("copy_guard_seed") or {}).get("song_titles") or []
                    if x and not any(contains_phrase(x, g) or contains_phrase(g, x) for g in guard.get("titles") or [])]
            if miss:
                warn(f"copy_guard.titles lacks reference song titles: {miss[:5]}")
    blocking = [q for q in d.get("open_questions") or [] if q.get("blocking")]
    if d.get("status") in ("approved", "promoted") and blocking and not all(q.get("answer") for q in blocking):
        err("status approved but blocking open_questions have no answer")

    durs = []
    for s in slots:
        m = re.match(r"^(\d+):(\d\d)$", str(s.get("target_duration") or ""))
        if m:
            durs.append(int(m[1]) * 60 + int(m[2]))
    rng = tg.get("duration_min")
    if durs and isinstance(rng, list) and len(rng) == 2:
        total = sum(durs) / 60
        if not (rng[0] - 3 <= total <= rng[1] + 3):
            warn(f"slot durations sum to {total:.1f} min vs target {rng} (crossfades trim a few minutes)")

    if a.draft:
        W += [f"(to do) {e}" for e in E]
        E = []
    for w in W:
        print("WARN ", w)
    for e in E:
        print("ERROR", e)
    print(f"{'OK' if not E else 'FAIL'}: {len(E)} error(s), {len(W)} warning(s) - {a.idea}")
    sys.exit(1 if E else 0)


if __name__ == "__main__":
    main()
