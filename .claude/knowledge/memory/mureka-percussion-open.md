---
name: mureka-percussion-open
description: "Open question CEO 10-09: why Mureka adds drums unasked — so far concentrated in Deck the Halls × pad_celesta (4/4 takes); Deck v4 accepted for now"
metadata:
  type: project
---

CEO 2026-10-09 asked to note and investigate later why Mureka often adds drums though no prompt asks for them. Data on 10-09 (Demucs drums stem, cut 1 %): 5 of 15 takes had percussion. All four Deck the Halls pad_celesta takes (m001 v1/v2, m007 v3/v4) had drums, against only 1 of 11 takes in other song × style pairs (silent_night strings_glockenspiel m006 v2). Deck pad_celesta v4 (3 %) was accepted by the CEO for now via `mureka_web.py accept`.

**Why:** the CEO wants the cause (this prompt? this song? Mureka?) found before batch generation, not more one-off rejections.

**How to apply:** when more songs are generated, tally percussion by song and by style from stems.json. Test one variable at a time only with CEO/PM approval, since it spends Gold. Candidates: the 4/4 lively carol, the pad_celesta wording, or "72 BPM". Never add an exclusion line ([[thin-piano-accompaniment]]). Related: [[mureka-flag-not-reject]], [[mureka-album-rules]].
