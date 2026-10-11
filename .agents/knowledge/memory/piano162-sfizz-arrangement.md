---
name: piano162-sfizz-arrangement
description: CEO 2026-10-10 arrangement experiment — Piano in 162 (Ivy Audio sfz) rendered by sfizz_render on the server, phrase-aware performance rules, full snowglobe ensemble, no deep booming left hand
metadata:
  type: project
---

CEO 2026-10-10 asked for a hand-arranged test of Silent Night: first piano solo (Salamander sf2), then the full snowglobe
ensemble (harp, strings, celesta, sparse sleigh) around **Piano in 162** (Ivy Audio, `~/music-tools/sfz/piano162/`, Close mics).
Feedback on the solo: the left hand was too low and boomy ("trầm vang"), so the ensemble version keeps the piano LH in C3–E4,
2–4 notes/bar, and leaves the bass to the cello.

- `sfizz_render` built from source 1.2.3 → `~/music-tools/bin/sfizz_render` (flags --sfz --midi --wav -s -q --use-eot; output is
  16-bit PCM, so the piano needs `<global> global_volume=30` via the wrapper `p162-close-hot.sfz`; region `volume=` overrides a
  plain `<global> volume`).
- VSCO-2-CE and `sfz/real` have no .sfz files, only wav + index.json → harp/strings/celesta/sleigh keep the custom sampler code.
- Scripts (local only, not in a skill yet): `research/christmas-carols/experiments/piano-arrange/piano_arrange.py` and
  `ensemble_arrange.py`; renders under `audio/christmas/experiments/piano-arrange/` on the server, copies pulled to the same folder on the Mac.
- Performance layer: phrase detection from long notes on bar lines (phrases < 2 bars merged), parabolic rubato ±3–7 %, 0.12 s breath,
  final rit ×1.45, melody velocity = base + phrase arch + pitch height − phrase-end, melody lead 12 ms, bass early, per-verse texture change.

**Why:** fixed LAYERS tables + sin velocity + one RNG seed made every song sound like the same machine (CEO complaint).
**How to apply:** if the CEO approves this direction, move the performance layer into `ambient_render.py` for every vibe and add
the sfizz piano path there; keep Piano in 162 as the lead piano. See [[christmas-ambient-standard]], [[piano-channel-lead]], [[ambient-even-passes]].
