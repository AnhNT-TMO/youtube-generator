---
name: never-use-suno-download
description: "Never click Suno's own Download / \"Unlock & Download\" (costs monthly quota); all downloads go through usesuno.com"
metadata:
  node_type: memory
  type: feedback
  originSessionId: a95f0a26-5296-49aa-a555-6ac6ad9ddb60
  modified: 2026-09-23T07:36:34.169Z
---

Never click Suno's Download menu or "Unlock & Download" button, in any flow (spike, test, final tracks), and never call `/api/download/authorize`. Every download goes through usesuno.com (tools/downloader): paste the suno.com/song/<id> link. Private links work too (tested 2026-09-23), so no Publish step is needed.

**Why:** Suno's official download uses up the monthly quota (Pro 20/month). On 2026-09-23 I clicked it once during the spike for "When The Night Is Long" (clip 3ab17d0d), before the user's objection reached me, and 1/20 was used up. The user wants the quota left untouched.
**How to apply:** Opening the Download dialog just to look is not needed either; the page map is already documented. If the only way forward seems to be an official download, stop and ask. Related: [[suno-automation-constraints]]

**Final tracks too (decided 2026-09-23, idea q7):** told that Suno's 03/09 ToS grants commercial use only to officially downloaded songs, the user still chose "all via usesuno" for Album 002, accepting the monetisation/claim risk. Don't re-ask per album. **Update 2026-09-25 (CEO):** ignore this risk entirely — no research, no reminder, not in reports or risk reviews (CLAUDE.md §5 'Điều khoản thương mại Suno: bỏ qua').
