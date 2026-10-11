---
name: christmas-instrumental-brainstorm
description: "Christmas PD carol pool — CEO locked the standard 2026-10-04 (Deck r009): 3 versions plain Piano+Pad / Celesta / Vibraphone, piano+pad, 3-statement key lift, per-verse support patterns, 1 real chime at 1/3; state in research/christmas-carols/HANDOFF.md"
metadata:
  node_type: memory
  type: project
  originSessionId: 4168c5ca-072c-425d-850c-01a77092ff22
  modified: 2026-10-04T08:22:45.238Z
---

SUPERSEDED 2026-10-05 by [[christmas-music-direction]] (ACE-Step dropped). Old standard below kept for form/tier/album rules. It does not use Suno. Skill: `audio-christmas-workflow`.

**CEO 2026-10-04: standard locked after hearing Deck the Halls r009.**
- Three versions per song: plain Piano + Pad (no support, otherwise identical config), Piano + Pad + Celesta, Piano + Pad + Vibraphone. Glockenspiel is dropped. Plain added by CEO 2026-10-04 after r010; Deck gets no plain re-render.
- The piano plays the complete melody at ×0.85 relative level. The pad is GM89, with no strings, cello or viola.
- Form: 3 melody statements, each lifted one whole step (G → A → B for Deck), with a dominant pivot before each lift, plus a short interlude and outro.
- Support patterns are chosen per verse from `research/christmas-carols/SUPPORT_PATTERNS.md`: sparse, then developed, then fullest.
  - Each pattern symbol is one beat; use chord tones only, at least 3 semitones above the phrase melody.
  - Celesta plays broken chords; vibraphone holds sustained tones.
- One recorded chime, Freesound 414559 (up), at the real statement 1→2 boundary near 1/3. The CEO removed the 2/3 chime as too much (2026-10-04). Finish at −18 LUFS.
- Covers use seed 23 × noise 0.35/0.5 (n50 primary). No seed search. Gates include a per-section key gate and a source buzz precheck.
- **Why:** the CEO listened through r001–r009. r008's fast 3–4-note fills felt rushed. Glockenspiel E7 notes were harsh.
- **How to apply:** read `research/christmas-carols/STANDARD.md` and `HANDOFF.md` first. The next step is a 5-song evaluation batch built from `work/deck_the_halls/r009-pm/make_plan.py` and `r009-tools/`.
- CEO 2026-10-04: a long video uses 20 songs (× 3 styles ≈ 180 min; repeat only if short). Popularity tiers I/II/III: tier I opens, II/III later with a tier I song every 4–5 tracks; policy in STANDARD.md "Video dài".
- Tempo: approved Deck = quarter 72 (the 84 in early notes was a replaced pilot). Old `tempo_refs` calm-piano medians (category 1) match Deck (72.5) and are the per-song starting point; festive/double-time numbers are not. Song tiers: songlist.md I/II/III (R&D 2026-10-04). First batch brief: BATCH_EVAL5_2026-10-05.md.
- Old notes and test media are archived in `~/Desktop/youtube-archive/2026-10-04-christmas-*`.

Related: [[ace-step-on-server]] [[no-listening-questions]] [[heavy-work-on-server]]
