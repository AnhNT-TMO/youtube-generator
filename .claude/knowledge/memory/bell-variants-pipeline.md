---
name: bell-variants-pipeline
description: "CEO 2026-10-10 — per-song arrangement variants for the Christmas piano channel (162_bell): instrument set, grace/sleigh limits, output layout, rollout plan"
metadata:
  node_type: memory
  type: project
  originSessionId: 08cba8d3-3080-4b20-8fef-fa668a368654
  modified: 2026-10-10T04:13:45.891Z
---

CEO decisions 2026-10-10 for the bell-register carol arrangements (`research/christmas-carols/experiments/piano-arrange/ensemble_arrange.py`, DECISIONS.md):

- Instruments: celesta (+12 only), vibraphone (0 or −12), glockenspiel (0 only, tuned + LP + −16 dB). Bed: strings (vla+vc) default, viola alone, or pad = sf2:89 Warm Pad, no octave layer. PADsynth and handchimes rejected.
- Grace notes are decoration only: `--grace-max` 5 per song, ≥ 4 bars apart. Sleigh bells variant: 8–10 sparse, quiet hits per song (vel 24–30, −26 dB).
- Per song: PM designs 3–4 fitting variants (1 is fine if the form allows only one); variety across the album. Spec `variants_006_first5.json`, batch `render_variants.py` on server → `~/youtube-qc/audio/162_bell/<slug>/<variant>.wav` (+mp3/json/mid), mirrored to Mac `audio/162_bell/`.
- Rollout: first 5 songs of album 006 (silent_night, away_mueller, bleak_midwinter_cranham, it_came_upon, o_little_town_st_louis) → CEO listens (incl. sleigh sound) → then all tier I+II songs with PD verdict clean (skip we_wish_you etc.).
- Choir (CEO 10-10 final): source = HeavenChoir.SF2 preset 2 "MU80 SlowChoir" (`--choir sf2:~/music-tools/sf2/HeavenChoir.SF2:2 --choir-db -6`; CEO picked it from 17 choir-only demos, then −8/−6/−4 test → −6). `--choir women` (SSO female, −8) stays as fallback. 3 voices D4–D5, enters at verse 2 only; sf2 path ties common tones across chords + 0.8 s overlap (`choir_legato`, CEO 10-11: no gaps at chord changes). Level depends on source: re-test 3 levels when the source changes. Every song gets one `*_choir` variant: song's main bed, celesta or glock double, never vibraphone, never sleigh (PRINCIPLES §7b table). Album join rotation: track 1 plain, 2 sleigh, 3 choir, repeat (§10); every song therefore needs all three kinds. Spec `variants_006_choir.json`, order `join_006_rotation.json`.
- Sonnet sub-agents do the mechanical part (server render via guard, rsync, ffprobe/ebur128 checks); PM writes the MIDI/variant ideas.

**Why:** CEO wants the channel sound (clear bell register) applied to every song with per-song character, not one template.
**How to apply:** new songs = add entry to a variants spec, dry-run `--no-audio` to check phrases/ornaments/sleigh count, then render via agent. See [[bell-register-doubling]], [[christmas-ambient-standard]], [[sleigh-bells-sparse]].
