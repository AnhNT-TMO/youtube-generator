---
name: album-gentle-intro
description: CEO 10-05: every album opens gently — softest-intro song first + 12 s sin² master fade-in (audio-album-assembly intro_fade_s)
metadata:
  type: feedback
---
Every album opens gently, not abruptly: track 1 = the song whose first 20 s is softest relative to its whole (`intro_lu`), and the master gets a 12 s sin² fade-in (`afade curve=hsin`, slow at first). Lives in audio-album-assembly `intro_fade_s` (album_rules, default 12, 0 = off).

**Why:** CEO listened to the Suno waltz 3-h test mix (production/listen-test/suno-waltz/) and wanted that opening applied to all albums; replaces the old "vào giọng ngay" rule.

**How to apply:** PM picks track 1 among the lowest `intro_lu` songs that fit the theme; assembly.md warns ⚠️ if track 1 is not the softest. See [[pool-production-flow]].
