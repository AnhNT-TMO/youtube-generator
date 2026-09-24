#!/usr/bin/env python3
import argparse
import datetime
import glob
import json
import os
import re
import statistics as st

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
METER = {"compound": "6/8·12/8", "simple": "4/4"}


def channel_rules(channel_dir):
    f = os.path.join(channel_dir or "", "rules.md")
    m = re.search(r"```yaml\n(.*?)```", open(f).read(), re.S) if channel_dir and os.path.isfile(f) else None
    return (yaml.safe_load(m.group(1)) or {}) if m else {}


def intro_vocab(rules):
    return list((rules.get("research") or {}).get("intro_vocab") or [])


def numbered_source(rules):
    nb = (rules.get("sources") or {}).get("numbered") or {}
    return (re.compile(nb["pattern"], re.I), nb.get("format") or "{n}") if nb.get("pattern") else (None, None)


def load(path, kind="json"):
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f) if kind == "json" else yaml.safe_load(f)


def med(vals, n=1):
    v = [x for x in vals if x is not None]
    return round(float(st.median(v)), n) if v else None


def first_lyric(whisper, captions):
    if whisper is None or captions is None:
        return whisper if captions is None else captions
    return round(min(whisper, captions), 1) if abs(whisper - captions) <= 3 else captions


GENERIC_WORDS = set("""music playlist songs song hour hours nonstop collection best new video official lyric lyrics
the a of for to your you and with in on my me i is it at by from 2024 2025 2026""".split())


def genre_words(rules):
    return GENERIC_WORDS | {str(x).lower() for x in (rules.get("research") or {}).get("genre_words") or []}


def words(s):
    return re.findall(r"[a-z0-9']+", (s or "").lower())


def title_phrases(titles, rules=None):
    rules = rules or {}
    gw, (num_re, _) = genre_words(rules), numbered_source(rules)
    out = set()
    for t in titles:
        t = re.sub(r"[^\w\s'&|:–—\-(),\[\]•]", " ", t or "")
        for part in re.split(r"\s[|:–—\-•]\s|[|–—•\[\]()]|:\s", t):
            p = re.sub(r"\s+", " ", part).strip(" -,'")
            w = words(p)
            if re.match(r"^\d+\s*(hours?|hrs?|minutes?|mins?)\b", p.lower()) or p.lower() in ("second song", "part 2"):
                continue
            if len(w) >= 2 and not all(x in gw for x in w):
                out.add(p)
            elif len(w) == 2 and num_re and num_re.fullmatch(p):
                out.add(p)
    return sorted(out)


def source_numbers(texts, rules):
    num_re, _ = numbered_source(rules)
    return sorted({int(m.group(1)) for t in texts for m in num_re.finditer(t or "")}) if num_re else []


def channel_single(title, videos):
    w = [x for x in words(re.sub(r"\([^)]*\)", "", title or "")) if x not in ("the", "a", "of")]
    if len(w) < 2:
        return None
    for v in sorted(videos or [], key=lambda v: -(v.get("views") or 0)):
        vt = " ".join(words(v.get("title")))
        if v.get("kind") == "single" and re.search(r"(^| )" + re.escape(" ".join(w)) + r"( |$)", vt):
            return {"title": v.get("title"), "views": v.get("views")}
    return None


def single_candidates(duration_s, videos, tol=2.0):
    return [{"title": v.get("title"), "views": v.get("views"), "duration_s": v.get("duration_s")}
            for v in sorted(videos or [], key=lambda v: -(v.get("views") or 0))
            if v.get("kind") == "single" and v.get("duration_s") and abs(v["duration_s"] - duration_s) <= tol][:3]


def our_baseline(channel_dir):
    albums = sorted(glob.glob(os.path.join(channel_dir or "", "albums", "*")))
    albums.sort(key=lambda a: bool(glob.glob(os.path.join(a, "audio", "tracks", "*.wav"))))
    for alb in reversed(albums):
        sel = load(os.path.join(alb, "selection.yaml"), "yaml") or {}
        man = load(os.path.join(alb, "audio", "raw_tracks", "manifest.json")) or {}
        measured = [(c.get("verify") or {}).get("bpm") for c in man.get("clips", []) if c.get("status") == "selected"]
        t1 = sorted(f for f in glob.glob(os.path.join(alb, "tracks", "01-*.md")) if "." not in os.path.basename(f)[:-3])
        meta = {}
        if t1:
            m = re.match(r"^---\s*\n(.*?)\n---\s*\n", open(t1[0]).read(), re.S)
            meta = (yaml.safe_load(m.group(1)) if m else None) or {}
        if not (sel or meta):
            continue
        return {"album": os.path.basename(alb), "prompt_bpm": (sel.get("tempo") or {}).get("target_bpm") or meta.get("target_bpm") or meta.get("bpm"),
                "measured_felt_bpm_median": med(measured), "n_measured": len([x for x in measured if x]),
                "vocal_persona": meta.get("vocal_persona"), "band_profile": meta.get("band_profile"),
                "_prov": "prompt = selection.yaml / track front matter; measured = verify.py on selected clips (null = never measured)"}
    return None


def register(gender, f0):
    if not f0:
        return None
    lo, hi = (280, 400) if gender == "female" else (200, 270)
    return "low" if f0 < lo else "high" if f0 > hi else "mid"


def density(wpm):
    return None if wpm is None else "sparse" if wpm < 50 else "dense" if wpm > 90 else "medium"


def mmss(sec):
    sec = int(round(sec or 0))
    return f"{sec // 3600}:{sec % 3600 // 60:02d}:{sec % 60:02d}" if sec >= 3600 else f"{sec // 60}:{sec % 60:02d}"


def build(run, channel_dir=None):
    info = load(os.path.join(run, "raw", "video.info.json")) or {}
    A = load(os.path.join(run, "audio", "analysis.json"))
    Q = load(os.path.join(run, "audio", "qc.json")) or {}
    CH = load(os.path.join(run, "channel.json")) or {}
    tracks = A["tracks"]
    if Q and Q.get("bounds_s") is not None and [round(x, 1) for x in Q["bounds_s"]] != [round(t["start_s"], 1) for t in tracks]:
        print("WARNING: audio/qc.json was measured on a different song split - ignoring it (re-run measure.py)")
        Q = {}
    qs = {s["n"]: s for s in Q.get("songs", [])}
    q1, qa = Q.get("track01") or {}, Q.get("album") or {}
    ly1 = q1.get("lyrics") or {}
    dur = info.get("duration") or A["video"].get("duration")
    title = info.get("title") or ""

    rows = []
    for t in tracks:
        q, v = qs.get(t["n"], {}), t.get("vocals") or {}
        rows.append({"n": t["n"], "title": t.get("title"), "start_s": t["start_s"], "duration_s": t["duration_s"],
                     "bpm": q.get("felt_bpm"), "time_signature": METER.get(q.get("meter")),
                     "tempo_uncertain": q.get("tempo_uncertain"), "felt_bpm_fast_candidate": q.get("felt_bpm_fast_candidate"),
                     "voice": q.get("voice"), "f0_median_hz": q.get("f0_median_hz"),
                     "first_lyric_s": v.get("first_line_s"), "words_per_min_sung": v.get("words_per_min_sung")})
    lens = [t["duration_s"] for t in tracks]

    calls = qa.get("voice_calls") or {}
    gender = max(("male", "female"), key=lambda g: calls.get(g, 0)) if calls.get("male") or calls.get("female") else None
    op = A.get("video_opening") or {}
    fl = first_lyric(ly1.get("first_word_s"), rows[0]["first_lyric_s"])
    voice_s = q1.get("vocal_start_s")
    wpm_c = med([r["words_per_min_sung"] for r in rows])
    wpm = wpm_c if wpm_c is not None else ly1.get("words_per_min_sung")
    mc = qa.get("meter_counts") or {}
    criteria = {
        "video": {"duration_s": dur, "duration": mmss(dur), "n_songs": len(tracks)},
        "song_length": {"median_s": med(lens), "median": mmss(med(lens)), "min_s": min(lens), "max_s": max(lens)},
        "tempo": {"felt_bpm_median": qa.get("felt_bpm_median"), "felt_bpm_range": qa.get("felt_bpm_range"),
                  "meter": METER.get(max(mc, key=mc.get)) if any(mc.values()) else None, "meter_counts": mc or None,
                  "tempo_uncertain_songs": qa.get("tempo_uncertain_songs"),
                  "_unit": "felt BPM (dotted quarter in 6/8·12/8, quarter in 4/4) = the unit of verify.py and the Style prompt"},
        "voice": {"gender": gender, "register": register(gender, qa.get("f0_median_hz")), "f0_median_hz": qa.get("f0_median_hz"),
                  "calls": calls or None, "_prov": "AudioSet Male/Female singing + pYIN f0 on the Demucs vocal stem"},
        "opening": {"voice_s": voice_s, "first_lyric_s": fl, "level_0_15s_db": op.get("rel_db_0_15s"),
                    "quiet_start_s": op.get("quiet_start_s"),
                    "gate": {"voice_within_10s": voice_s is not None and voice_s <= 10,
                             "lyric_within_15s": fl is not None and fl <= 15,
                             "level_ok": op.get("rel_db_0_15s") is not None and op["rel_db_0_15s"] >= -4},
                    "_prov": "voice = first sung run on the Demucs vocal stem (hums included); first lyric = Whisper + captions; "
                             "level = 0-15 s vs the body of song 1"},
        "lyric_density": {"words_per_min_sung": wpm, "label": density(wpm),
                          "source": "captions, median of the songs" if wpm_c is not None else ("Whisper, song 1" if wpm else None)},
    }
    if voice_s is not None and fl is not None and fl - voice_s > 5:
        criteria["opening"]["note"] = ("sound on the vocal stem before the first lyric: a hum/ad-lib, or an instrument "
                                       "(slide guitar) leaking into the stem - not certain")

    desc = info.get("description") or ""
    chan = None
    if CH:
        chan = {k: CH.get(k) for k in ("channel", "channel_url", "subscribers", "n_uploads", "first_upload_approx",
                                        "views_total_listed", "views_by_kind", "top1_share", "focus_rank_by_views",
                                        "focus_share_of_views", "focus_upload_index_from_oldest")}
        chan["launch_uploads"] = [{"kind": v["kind"], "views": v["views"], "title": v["title"]} for v in (CH.get("oldest") or [])[:10]]
        single = channel_single(tracks[0].get("title"), CH.get("videos"))
        chan["opener_single"] = single
        chan["opener_single_candidates"] = None if single else single_candidates(tracks[0]["duration_s"], CH.get("videos"))
        chan["_prov"] = "measured (yt-dlp listing; dates approximate); opener_single_candidates = same length ±2 s (inferred)"
    packaging = {"title": title, "title_chars": len(title), "tags": info.get("tags") or [],
                 "description_chars": len(desc), "hashtags": re.findall(r"#\w+", desc)[:20],
                 "chapters": bool(info.get("chapters")), "thumbnail": "thumbnail.jpg"}
    auto = A.get("auto_segmentation") or {}
    seg = {"source": A["segmentation_source"],
           "weak_joins": [{"at_s": c["at_s"], "score": c["score"]} for c in auto.get("chosen", [])
                          if c.get("score", 9) < (auto.get("threshold") or 0) + 0.5],
           "timestamps_snapped": len(A.get("timestamp_corrections") or [])}
    ch_titles = [v["title"] for v in (CH.get("top") or [])] + [v["title"] for v in (CH.get("oldest") or [])]
    song_titles = [re.sub(r"\s*\([^)]*\)", "", r["title"]).strip() for r in rows if r["title"]]
    rules = channel_rules(channel_dir)
    guard = {"titles": title_phrases([title] + song_titles + ch_titles, rules), "song_titles": sorted(set(song_titles)),
             "branding": sorted({x for x in (info.get("channel"), info.get("uploader_id")) if x}),
             "sources_used": source_numbers([title] + song_titles + ch_titles, rules),
             "sources_in_this_video": source_numbers([title] + song_titles, rules)}

    return {
        "schema": "reference/v3", "generated_at": datetime.date.today().isoformat(),
        "source": {"url": info.get("webpage_url"), "video_id": info.get("id"), "title": title, "channel": info.get("channel"),
                   "channel_url": info.get("channel_url"), "subscribers": info.get("channel_follower_count"),
                   "views": info.get("view_count"), "likes": info.get("like_count"),
                   "upload_date": info.get("upload_date"), "duration_s": dur},
        "criteria": criteria, "tracks": rows,
        "packaging": packaging, "channel": chan, "copy_guard_seed": guard, "segmentation": seg,
        "our_baseline": our_baseline(channel_dir) if channel_dir else None,
    }


def fill_from_channel(tpl, channel_dir):
    if not channel_dir:
        return
    albums = sorted(glob.glob(os.path.join(channel_dir, "albums", "*")))
    latest = albums[-1] if albums else None
    ident = tpl.setdefault("identity", {})
    if latest:
        t1 = sorted(f for f in glob.glob(os.path.join(latest, "tracks", "01-*.md")) if "." not in os.path.basename(f)[:-3])
        if t1:
            m = re.match(r"^---\s*\n(.*?)\n---\s*\n", open(t1[0]).read(), re.S)
            meta = (yaml.safe_load(m.group(1)) if m else None) or {}
            ident["vocal_persona"] = meta.get("vocal_persona")
            ident["band_profile"] = meta.get("band_profile")
        q = tpl.setdefault("qc", {})
        produced = [a for a in albums if glob.glob(os.path.join(a, "audio", "tracks", "*.wav"))]
        if produced:
            q["references"] = f"{os.path.relpath(produced[-1], REPO)}/audio/tracks/*.wav"
        sel = load(os.path.join(latest, "selection.yaml"), "yaml")
        if sel:
            q["style"] = {"positive": [x for x in (sel.get("style") or {}).get("positive") or [] if x],
                          "negative": (sel.get("style") or {}).get("negative") or {}}
            q["intro_types"] = sel.get("intro_types") or q.get("intro_types")
            q["rules"] = {**(q.get("rules") or {}), **(sel.get("rules") or {})}
    cands = []
    for g in glob.glob(os.path.join(channel_dir, "albums", "*", "generation.yaml")):
        v = ((load(g, "yaml") or {}).get("defaults") or {}).get("voice") or {}
        if v.get("id"):
            cands.append((os.path.getmtime(g), v))
    for g in glob.glob(os.path.join(channel_dir, "ideas", "*", "idea.yaml")):
        v = ((load(g, "yaml") or {}).get("identity") or {}).get("suno_voice") or {}
        if v.get("id"):
            cands.append((os.path.getmtime(g), v))
    if cands:
        ident["suno_voice"] = {k: v for k, v in sorted(cands, key=lambda c: c[0])[-1][1].items() if k in ("name", "id", "origin_clip")}
    tpl.setdefault("packaging", {}).setdefault("ai_disclosure", {"youtube_altered_content_label": True})


def fmt_s(x):
    return "unknown" if x is None else f"{x:g} s"


def seed_idea(ref, run, idea_dir, channel_dir):
    tpl = yaml.safe_load(open(os.path.join(REPO, "templates", "idea.yaml")))
    todo = []
    rules = channel_rules(channel_dir)
    vocab = intro_vocab(rules)
    _, num_fmt = numbered_source(rules)

    def need(path, what):
        todo.append(f"{path}: {what}")
        return None
    rel = os.path.relpath(os.path.abspath(run), REPO)
    slug = os.path.basename(idea_dir.rstrip("/"))
    s, c = ref["source"], ref["criteria"]
    tempo, voice, op, lyr = c["tempo"], c["voice"], c["opening"], c["lyric_density"]
    ob = ref.get("our_baseline") or (our_baseline(channel_dir) if channel_dir else None) or {}
    tpl.update({"id": "idea-" + slug.split("-")[0], "slug": slug.split("-", 1)[1] if "-" in slug else slug,
                "title_working": need("title_working", "working title (English)"),
                "channel": os.path.basename(os.path.abspath(channel_dir)) if channel_dir else None,
                "status": "draft", "created_at": ref["generated_at"], "updated_at": ref["generated_at"],
                "status_log": [{"date": ref["generated_at"], "status": "draft", "by": "build_reference.py", "note": f"seeded from {rel}/reference.yaml"}]})
    has_analysis = os.path.exists(os.path.join(run, "analysis.md"))
    tpl["provenance"] = {"research": [{"path": f"{rel}/analysis.md" if has_analysis else None, "reference": f"{rel}/reference.yaml",
                                       "url": s["url"], "channel": s["channel"], "video_id": s["video_id"],
                                       "analyzed_at": ref["generated_at"], "views": s["views"], "subs": s["subscribers"],
                                       "published_at": s["upload_date"], "duration": s["duration_s"]}],
                         "derived_by": need("provenance.derived_by", "session / agent"),
                         "baseline_album": ob.get("album"),
                         "confidence_notes": ["The reference gives the frame only (6 criteria, SKILL.md); genre, instruments and arc come from our channel."]
                         + ([] if has_analysis else ["analysis.md not written yet: write it first (SKILL.md step 4)."])}
    ch = ref.get("channel") or {}
    share = ch.get("focus_share_of_views")
    cands = ch.get("opener_single_candidates") or []
    if ch.get("opener_single"):
        single, single_src = f"yes, {ch['opener_single']['views'] or 0:,} views as a single", "measured"
    elif cands:
        single, single_src = f"likely: same length (±2 s) as the single '{cands[0]['title']}' ({cands[0]['views'] or 0:,} views)", "inferred"
    else:
        single, single_src = "no match (by title or length)", "measured"
    meter_txt = ", ".join(f"{n} songs {METER.get(k, k)}" for k, n in (tempo.get("meter_counts") or {}).items() if n) or "unknown"
    if tempo.get("tempo_uncertain_songs"):
        meter_txt += f"; tempo uncertain: songs {tempo['tempo_uncertain_songs']}"
    tpl["hypothesis"] = {"statement": need("hypothesis.statement", "why this idea should work for our channel"), "risks": [], "evidence": [
        {"claim": "Reference reach", "value": f"{s['views']:,} views" + (f", {share:.0%} of the channel's listed views" if share else ""), "source": "measured"},
        {"claim": "Reference opener is the channel's own single", "value": single, "source": single_src},
        {"claim": "1. Video length / songs", "value": f"{c['video']['duration']}, {c['video']['n_songs']} songs", "source": "measured"},
        {"claim": "2. Song length", "value": f"median {c['song_length']['median']} ({mmss(c['song_length']['min_s'])}-{mmss(c['song_length']['max_s'])})", "source": "measured"},
        {"claim": "3. Tempo / meter", "value": f"median {tempo.get('felt_bpm_median')} felt BPM, range {tempo.get('felt_bpm_range')}; {meter_txt}", "source": "measured"},
        {"claim": "4. Voice", "value": f"{voice.get('gender')}, {voice.get('register')} (f0 {voice.get('f0_median_hz')} Hz)", "source": "measured/model"},
        {"claim": "5. First 15 s", "value": f"voice {fmt_s(op.get('voice_s'))}, first lyric {fmt_s(op.get('first_lyric_s'))}, "
                                            f"0-15 s level {op.get('level_0_15s_db')} dB vs body", "source": "measured"},
        {"claim": "6. Lyric density", "value": f"{lyr.get('words_per_min_sung')} words per sung minute ({lyr.get('label')})", "source": "measured"}]}
    todo.append("hypothesis.risks: 2-4 risks")
    g = ref["copy_guard_seed"]
    used = g.get("sources_used", g.get("psalms_used")) or []
    src_avoid = [num_fmt.format(n=x) if num_fmt and isinstance(x, int) else str(x) for x in used]
    tpl["differentiation"] = {"keep": [], "change": [],
                              "copy_guard": {"titles": g["titles"] + [x for x in g.get("song_titles", []) if x not in g["titles"]],
                                             "hooks": [], "branding": g["branding"], "visual": [],
                                             "source_avoid": src_avoid,
                                             "lyric_rule": "Paraphrase in our own words; never transcribe the reference captions or any existing song."}}
    todo += ["differentiation.keep: the spirit we keep", "differentiation.change: what we do differently",
             "differentiation.copy_guard.branding: add their thumbnail/video wordmarks (look at thumbnail.jpg)",
             "differentiation.copy_guard.visual: their visual traits we must not reuse (thumbnail.jpg)"]
    tg = tpl["target"]
    tg["track_count"] = need("target.track_count", f"integer (reference: {c['video']['n_songs']} songs in {c['video']['duration']})")
    tg["track_duration"] = {"target": need("target.track_duration.target", "m:ss"), "range": [], "reference_median_s": c["song_length"]["median_s"]}
    ours = (f"ours ({ob.get('album')}): prompt {ob.get('prompt_bpm')}, measured {ob.get('measured_felt_bpm_median') or 'not measured'}"
            if ob else "ours: no album yet")
    tg["tempo"] = {"meter": need("target.tempo.meter", f"reference: {meter_txt}"),
                   "felt_bpm_qc": need("target.tempo.felt_bpm_qc", f"felt BPM (reference {tempo.get('felt_bpm_median')}; {ours})"),
                   "felt_bpm_qc_range": [], "reference_measured": tempo.get("felt_bpm_median"),
                   "ours_prompt_bpm": ob.get("prompt_bpm"), "ours_measured": ob.get("measured_felt_bpm_median"), "baseline_album": ob.get("album")}
    tg["loudness"] = {"master_lufs": -14, "true_peak_max_dbtp": -1.0, "song_lufs_spread_max_lu": 2, "first15s_max_below_body_db": 4,
                      "_unit": "channel rules (CLAUDE.md), not measured on the reference"}
    tg["vocal"] = {"presence_max_s": {"track01": 4, "others": 15}, "first_lyric_max_s": {"track01": 10, "others": 20},
                   "first_hook_max_s": {"track01": 75, "others": None},
                   "words_per_min": [], "reference_words_per_min": lyr.get("words_per_min_sung"),
                   "_defaults": "presence/lyric limits = CLAUDE.md channel rule; words_per_min = per sung minute (album-plan's unit)"}
    todo.append("target.vocal.words_per_min: [lo, hi]")
    tg["energy_curve"] = []
    todo.append("target.energy_curve: list of ints, one per slot, adjacent delta <= 2, peak around 60-70 % of the album")
    calls = voice.get("calls") or {}
    tpl["identity"]["persona_decision"] = {"decided": False, "owner": "user", "recommended": None,
                                           "evidence": {"reference_voice": f"{voice.get('gender')}, {voice.get('register')}",
                                                        "reference_f0_median_hz": voice.get("f0_median_hz"),
                                                        "our_persona": ob.get("vocal_persona")},
                                           "options": {"A": "keep our persona", "B": "new persona closer to the reference"}}
    todo.append("identity.persona_decision.recommended: A or B, with the reason")
    tpl["track01"].update({"title": None, "concept": None, "hook_phrase": None, "opening_spec": [], "gate": [], "variants": [],
                           "reference": op})
    todo += ["track01.title", "track01.concept", "track01.hook_phrase", "track01.opening_spec: 0-15 s timeline",
             "track01.gate", "track01.variants: 2-3 generation variants"]
    tpl["slots"] = [{"n": i + 1, "title": None, "source_ref": None, "theme": None, "emotion": None, "energy": None, "valence": None,
                     "arc_role": "anchor" if i == 0 else None, "intro_type": None, "intro_length": None, "target_duration": None,
                     "bpm": None, "hook_phrase": None, "imagery": [], "arrangement_note": None,
                     "source": "new" if i == 0 else None, "library_id": None, "lyrics_file": None} for i in range(10)]
    vocab_txt = vocab if vocab else "channel rules.md research.intro_vocab (not set)"
    todo.append(f"slots: fill every slot (count = target.track_count; intro_type from {vocab_txt}); slots[0] is authoritative for the title track")
    tpl["lyrics_rules"] = {**(tpl.get("lyrics_rules") or {}),
                           "reference": {"words_per_min_sung": lyr.get("words_per_min_sung"), "density": lyr.get("label"), "source": lyr.get("source")}}
    tpl["style_prompt"] = {"version": None, "text": None, "chars": None,
                           "exclude_styles": (rules.get("house_style") or {}).get("exclude"),
                           "reference_voice": f"{voice.get('gender')}, {voice.get('register')}", "reference_tempo": tempo.get("felt_bpm_median")}
    todo.append("style_prompt: version + text (English, <= 1000 chars, BPM = target.tempo.felt_bpm_qc; genre/instruments from our channel)")
    tpl["open_questions"] = [{"id": "q1", "q": "Persona: keep ours or new? (see identity.persona_decision.evidence)", "owner": "user", "blocking": True},
                             {"id": "q2", "q": f"Tempo target: reference {tempo.get('felt_bpm_median')} vs {ours}?", "owner": "user", "blocking": True}]
    fill_from_channel(tpl, channel_dir)
    gen = tpl.setdefault("generation", {}).setdefault("settings", {})
    gen["voice"] = "identity.suno_voice" if (tpl.get("identity") or {}).get("suno_voice", {}).get("id") else None
    gen["vocal_gender"] = gen.get("vocal_gender") or ("male" if calls.get("male", 0) >= calls.get("female", 0) else "female")
    q = tpl.setdefault("qc", {})
    q["tempo"] = {"target_bpm": None, "meter": None, "_note": "= target.tempo (filled by album-plan)"}
    q.setdefault("intro_types", {})
    if isinstance(q.get("style"), dict) and q["style"].get("positive"):
        todo.append("qc.style.positive: adapt the first line to this idea's sound")
    tpl["next_steps"] = [
        {"step": "User answers blocking open_questions -> status approved", "consumer": "user", "reads": ["open_questions"]},
        {"step": "[music] Plan the album (tracklist, lyrics, plan.yaml -> generation.yaml / selection.yaml / tracks)", "consumer": "album-plan (init from this idea)",
         "reads": ["slots", "track01", "style_prompt", "identity", "target", "generation", "qc", "lyrics_rules", "differentiation"]},
        {"step": "[music] Generate Track 01 first, then the other slots", "consumer": "suno-generate", "reads": ["<album>/generation.yaml"]},
        {"step": "[music] Verify / pick clips", "consumer": "verification-audio", "reads": ["<album>/selection.yaml"]},
        {"step": "[music] Join the album", "consumer": "album-assembly", "reads": ["<album>/tracks/*.md", "<album>/plan.yaml target.vocal/loudness"]},
        {"step": "[picture] ChatGPT image prompt -> thumbnail.png", "consumer": "thumbnail-prompt", "reads": ["packaging.thumbnail_brief"]},
        {"step": "[picture] Thumbnail -> 5-min loop video", "consumer": "video-generator step 1", "reads": ["thumbnail.png", "video.json (lantern.center from thumb.py check)"]},
        {"step": "Full video (master audio + loop + bars)", "consumer": "video-generator step 2", "reads": ["<album>/audio/master/<album>.wav"]},
        {"step": "Title, description, chapters, tags, upload; log retention (metrics)", "consumer": "youtube-publish",
         "reads": ["packaging.video_title_candidates", "packaging.title_rules", "packaging.description_outline", "differentiation.copy_guard"]}]
    todo += ["packaging: title candidates, thumbnail brief, description outline (ABOUT THIS VIDEO points only)",
             "generation.budget.gens + total_credits", "metrics.targets"]
    tpl.pop("todo", None)
    tpl = {"todo": todo, **tpl}
    os.makedirs(idea_dir, exist_ok=True)
    out = os.path.join(idea_dir, "idea.yaml")
    if os.path.exists(out):
        out = os.path.join(idea_dir, "idea.seed.yaml")
    with open(out, "w") as f:
        f.write("# Seeded by youtube-music-analyzer/build_reference.py from reference.yaml. Fill every item of `todo`, delete it,\n"
                "# then run validate_idea.py. Intro vocabulary: "
                + (", ".join(vocab) if vocab else "channel rules.md research.intro_vocab (not set)") + "\n")
        yaml.safe_dump(tpl, f, sort_keys=False, allow_unicode=True, width=120)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    ap.add_argument("--idea-dir")
    ap.add_argument("--channel-dir")
    ap.add_argument("--seed-only", action="store_true", help="seed the idea from the existing reference.yaml (no raw/ needed)")
    a = ap.parse_args()
    p = os.path.join(a.run, "reference.yaml")
    if a.seed_only:
        ref = yaml.safe_load(open(p))
    else:
        ref = build(a.run, a.channel_dir)
        with open(p, "w") as f:
            f.write("# Machine-readable facts about the reference video (youtube-music-analyzer). Interpretation lives in analysis.md.\n")
            yaml.safe_dump(ref, f, sort_keys=False, allow_unicode=True, width=120)
        print("wrote", p)
    if a.idea_dir:
        print("seeded", seed_idea(ref, a.run, a.idea_dir, a.channel_dir))


if __name__ == "__main__":
    main()
