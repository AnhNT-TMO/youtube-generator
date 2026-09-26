#!/usr/bin/env python3
import argparse
import datetime
import os
import sys

import yaml

from build_reference import REPO, channel_rules, fill_from_channel, intro_vocab, mmss, numbered_source, our_baseline


def fmt_s(x):
    return "unknown" if x is None else f"{x:g} s"


def seed(refset_dir, idea_dir, channel_dir, brief, brief_source, topic, trend, decisions_file=None):
    ref = yaml.safe_load(open(os.path.join(refset_dir, "reference.yaml")))
    if ref.get("schema") != "reference-set/v1":
        sys.exit(f"{refset_dir} is not a reference set: build one with refset.py (3-5 trend videos)")
    tpl = yaml.safe_load(open(os.path.join(REPO, "templates", "idea.yaml")))
    today = datetime.date.today().isoformat()
    todo = []
    rules = channel_rules(channel_dir)
    vocab = intro_vocab(rules)
    _, num_fmt = numbered_source(rules)

    def need(path, what):
        todo.append(f"{path}: {what}")
        return None

    rel = os.path.relpath(os.path.abspath(refset_dir), REPO)
    slug = os.path.basename(idea_dir.rstrip("/"))
    s, c, members = ref["source"], ref["criteria"], ref["members"]
    tempo, voice, op, lyr = c["tempo"], c["voice"], c["opening"], c["lyric_density"]
    ob = ref.get("our_baseline") or (our_baseline(channel_dir) if channel_dir else None) or {}
    topic = topic or s.get("topic")
    trend = trend or s.get("trend_report")
    tpl.update({"id": "idea-" + slug.split("-")[0], "slug": slug.split("-", 1)[1] if "-" in slug else slug,
                "title_working": need("title_working", "working title (English)"),
                "channel": os.path.basename(os.path.abspath(channel_dir)) if channel_dir else None,
                "status": "draft", "created_at": today, "updated_at": today,
                "status_log": [{"date": today, "status": "draft", "by": "idea.py", "note": f"seeded from {rel} + brief ({brief_source})"}]})
    existing = os.path.join(idea_dir, "idea.yaml")
    decisions = ((yaml.safe_load(open(existing)) or {}).get("brief") or {}).get("decisions") if os.path.exists(existing) else None
    if decisions_file:
        decisions = yaml.safe_load(open(decisions_file)) or {}
    tpl["brief"] = {"source": brief_source, "text": brief, "topic": topic, "trend_report": trend,
                    "angle": need("brief.angle", "how the brief meets the trend: the story, who sings to whom, why a viewer clicks"),
                    "decisions": decisions or need("brief.decisions", "the PM's decisions (production-manager §0b): ask the PM, never invent them")}
    has_analysis = os.path.exists(os.path.join(refset_dir, "analysis.md"))
    research = [{"path": f"{rel}/analysis.md", "reference": f"{rel}/reference.yaml",
                 "kind": "reference set", "members": len(members), "analyzed_at": ref["generated_at"]}]
    research += [{"path": f"{m['research']}/analysis.md",
                  "reference": f"{m['research']}/reference.yaml", "url": m["url"], "channel": m["channel"],
                  "video_id": m["video_id"], "views": m["views"], "subs": m["subscribers"],
                  "published_at": m["upload_date"], "duration": m["duration_s"]} for m in members]
    tpl["provenance"] = {"research": research, "trend": {"report": trend, "topic": topic},
                         "derived_by": need("provenance.derived_by", "session / agent"),
                         "baseline_album": ob.get("album"),
                         "confidence_notes": [f"Frame = medians of {len(members)} trend videos ({s.get('channel')}); "
                                              "genre, instruments and arc come from our channel; the story comes from the brief."]
                         + (ref.get("warnings") or [])
                         + ([] if has_analysis else [f"{rel}/analysis.md not written yet (SKILL.md step 4)."])}
    per = lambda key: ", ".join("–" if v is None else f"{v:g}" for v in key)
    meter_txt = ", ".join(f"{n} songs {k}" for k, n in (tempo.get("meter_counts") or {}).items() if n) or "unknown"
    tpl["hypothesis"] = {"statement": need("hypothesis.statement", "why this idea should work: the trend evidence + our angle"),
                         "risks": [], "evidence": [
        {"claim": "Trend topic", "value": f"{topic} (report {trend})", "source": "measured"},
        {"claim": "Reference set", "value": f"{len(members)} videos, {s.get('channel')}, median {s.get('views') or 0:,} views", "source": "measured"},
        {"claim": "1. Video length / songs", "value": f"median {c['video']['duration']}, {c['video']['n_songs']} songs", "source": "measured"},
        {"claim": "2. Song length", "value": f"median {c['song_length']['median']} ({mmss(c['song_length']['min_s'])}-{mmss(c['song_length']['max_s'])})", "source": "measured"},
        {"claim": "3. Tempo / meter", "value": f"median {tempo.get('felt_bpm_median')} felt BPM (members {per(tempo.get('members_felt_bpm') or [])}); {meter_txt}", "source": "measured"},
        {"claim": "4. Voice", "value": f"{voice.get('gender')}, {voice.get('register')} (f0 {voice.get('f0_median_hz')} Hz; members {per(voice.get('members_f0_hz') or [])})", "source": "measured/model"},
        {"claim": "5. First 15 s", "value": f"voice {fmt_s(op.get('voice_s'))}, first lyric {fmt_s(op.get('first_lyric_s'))}, "
                                            f"0-15 s level {op.get('level_0_15s_db')} dB vs body (medians)", "source": "measured"},
        {"claim": "6. Lyric density", "value": f"{lyr.get('words_per_min_sung')} words per sung minute ({lyr.get('label')}; members {per(lyr.get('members') or [])})", "source": "measured"}]}
    todo.append("hypothesis.risks: 2-4 risks")
    g = ref.get("copy_guard_seed") or {}
    used = g.get("sources_used") or []
    src_avoid = [num_fmt.format(n=x) if num_fmt and isinstance(x, int) else str(x) for x in used]
    tpl["differentiation"] = {"keep": [], "change": [],
                              "copy_guard": {"titles": (g.get("titles") or []) + [x for x in g.get("song_titles") or [] if x not in (g.get("titles") or [])],
                                             "hooks": [], "branding": g.get("branding") or [], "visual": [],
                                             "source_avoid": src_avoid,
                                             "lyric_rule": "Paraphrase in our own words; never transcribe the reference captions or any existing song."}}
    todo += ["differentiation.keep: what the trend expects (kept)", "differentiation.change: our own story / sound / look",
             "differentiation.copy_guard.branding: their thumbnail/video wordmarks (contact sheet)",
             "differentiation.copy_guard.visual: their visual traits we must not reuse (contact sheet)"]
    tg = tpl["target"]
    tg["track_count"] = need("target.track_count", f"integer (set median: {c['video']['n_songs']} songs in {c['video']['duration']}; master >= 60 min)")
    tg["track_duration"] = {"target": need("target.track_duration.target", "m:ss"), "range": [], "reference_median_s": c["song_length"]["median_s"]}
    ours = (f"ours ({ob.get('album')}): prompt {ob.get('prompt_bpm')}, measured {ob.get('measured_felt_bpm_median') or 'not measured'}"
            if ob else "ours: no album yet")
    tg["tempo"] = {"meter": need("target.tempo.meter", f"set: {tempo.get('meter')} ({meter_txt})"),
                   "felt_bpm_qc": need("target.tempo.felt_bpm_qc", f"felt BPM (set median {tempo.get('felt_bpm_median')}; {ours})"),
                   "felt_bpm_qc_range": [], "reference_measured": tempo.get("felt_bpm_median"),
                   "ours_prompt_bpm": ob.get("prompt_bpm"), "ours_measured": ob.get("measured_felt_bpm_median"), "baseline_album": ob.get("album")}
    tg["loudness"] = {"master_lufs": -14, "true_peak_max_dbtp": -1.0, "song_lufs_spread_max_lu": 2, "first15s_max_below_body_db": 4,
                      "_unit": "channel rules (CLAUDE.md), not measured on the references"}
    tg["vocal"] = {"presence_max_s": {"track01": 4, "others": 15}, "first_lyric_max_s": {"track01": 10, "others": 20},
                   "first_hook_max_s": {"track01": 75, "others": None},
                   "words_per_min": [], "reference_words_per_min": lyr.get("words_per_min_sung"),
                   "_defaults": "presence/lyric limits = CLAUDE.md channel rule; words_per_min = per sung minute (album-plan's unit)"}
    todo.append("target.vocal.words_per_min: [lo, hi] around the set median")
    tg["energy_curve"] = []
    todo.append("target.energy_curve: list of ints, one per slot, adjacent delta <= 2, peak around 60-70 % of the album")
    calls = voice.get("calls") or {}
    tpl["identity"]["persona_decision"] = {"decided": False, "owner": "PM", "recommended": None,
                                           "evidence": {"reference_voice": f"{voice.get('gender')}, {voice.get('register')}",
                                                        "reference_f0_median_hz": voice.get("f0_median_hz"),
                                                        "our_persona": ob.get("vocal_persona")},
                                           "options": {"A": "keep our persona", "B": "another channel Voice closer to the set (rules.md voices)"}}
    todo.append("identity.persona_decision.recommended: A or B, with the reason")
    tpl["track01"].update({"title": None, "concept": None, "hook_phrase": None, "opening_spec": [], "gate": [], "variants": [],
                           "reference": {k: op.get(k) for k in ("voice_s", "first_lyric_s", "level_0_15s_db", "gate")}})
    todo += ["track01.title", "track01.concept", "track01.hook_phrase", "track01.opening_spec: 0-15 s timeline",
             "track01.gate", "track01.variants: 2-3 generation variants"]
    tpl["slots"] = [{"n": i + 1, "title": None, "source_ref": None, "theme": None, "emotion": None, "energy": None, "valence": None,
                     "arc_role": "anchor" if i == 0 else None, "intro_type": None, "intro_length": None, "target_duration": None,
                     "bpm": None, "hook_phrase": None, "imagery": [], "arrangement_note": None,
                     "source": "new" if i == 0 else None, "library_id": None, "lyrics_file": None} for i in range(12)]
    vocab_txt = vocab if vocab else "channel rules.md research.intro_vocab (not set)"
    todo.append(f"slots: fill every slot (count = target.track_count; intro_type from {vocab_txt}); slots[0] is authoritative for the title track")
    todo.append("library_check: library songs that fit the brief (CLAUDE.md §0 budget: reuse up to the §7 limit)")
    tpl["lyrics_rules"] = {**(tpl.get("lyrics_rules") or {}),
                           "reference": {"words_per_min_sung": lyr.get("words_per_min_sung"), "density": lyr.get("label"), "source": lyr.get("source")}}
    tpl["style_prompt"] = {"version": None, "text": None, "chars": None,
                           "exclude_styles": (rules.get("house_style") or {}).get("exclude"),
                           "reference_voice": f"{voice.get('gender')}, {voice.get('register')}", "reference_tempo": tempo.get("felt_bpm_median")}
    todo.append("style_prompt: version + text (English, <= 1000 chars, BPM = target.tempo.felt_bpm_qc; genre/instruments from our channel)")
    tpl["open_questions"] = [{"id": "q1", "q": "Persona: keep ours or another channel Voice? (identity.persona_decision.evidence)", "owner": "PM", "blocking": True},
                             {"id": "q2", "q": f"Tempo target: set median {tempo.get('felt_bpm_median')} vs {ours}?", "owner": "PM", "blocking": True}]
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
        {"step": "PM answers blocking open_questions -> status approved", "consumer": "production-manager", "reads": ["open_questions"]},
        {"step": "[music] Plan the album (tracklist, lyrics, plan.yaml -> generation.yaml / selection.yaml / tracks)", "consumer": "album-plan (init from this idea)",
         "reads": ["slots", "track01", "style_prompt", "identity", "target", "generation", "qc", "lyrics_rules", "differentiation", "brief"]},
        {"step": "[picture] ChatGPT image prompt -> thumbnail.png", "consumer": "thumbnail-prompt", "reads": ["packaging.thumbnail_brief"]},
        {"step": "Title, description, tags, upload", "consumer": "youtube-publish",
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
        f.write("# Seeded by youtube-music-analyzer/idea.py from a reference set + brief. Fill every item of `todo`, delete it,\n"
                "# then run validate_idea.py. Intro vocabulary: " + (", ".join(vocab) if vocab else "not set") + "\n")
        yaml.safe_dump(tpl, f, sort_keys=False, allow_unicode=True, width=120)
    return out


def main():
    ap = argparse.ArgumentParser(description="Seed an idea from a brief (trend topic or CEO idea) + a reference set")
    ap.add_argument("--refset", required=True, help="research/<set-slug> built by refset.py")
    ap.add_argument("--idea-dir", required=True, help="channel/<ch>/ideas/NNN-slug")
    ap.add_argument("--channel-dir", required=True)
    ap.add_argument("--brief", required=True, help="the idea in one or two sentences (English or Vietnamese)")
    ap.add_argument("--brief-source", choices=["trend", "ceo", "pm"], default="trend")
    ap.add_argument("--topic", help="trend topic (trends.yaml); default = the set's topic")
    ap.add_argument("--trend", help="trend report path; default = the set's report")
    ap.add_argument("--decisions", help="YAML file with the PM's brief.decisions (music, title_direction, description_angle, thumbnail_concept, shorts, packaging_version, success, by)")
    a = ap.parse_args()
    print("seeded", seed(a.refset, a.idea_dir, a.channel_dir, a.brief, a.brief_source, a.topic, a.trend, a.decisions))


if __name__ == "__main__":
    main()
