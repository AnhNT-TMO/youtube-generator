---
name: no-listening-questions
description: "Never ask the user to listen to audio and judge it (hum vs guitar, grit, taps per chord...); decisions (persona, tempo, etc.) are fine"
metadata:
  node_type: memory
  type: feedback
  originSessionId: db0d85a7-264f-4ed6-a1c0-1c369de70cf3
  modified: 2026-09-23T06:10:50.022Z
---

Do not give the user listening checklists or ask them to judge audio by ear. Answer audio questions with measurements (tools/qc, AudioSet/CLAP, pYIN, Demucs stems) and state what stays uncertain. Asking for decisions (keep the channel's voice, tempo target, thumbnail, ToS) is fine.

**Why:** the user says their hearing is weak, so their listening answers are not reliable input (2026-09-23; the listening checklist was removed from youtube-music-analyzer and idea 001).

**How to apply:** in research/ideas/verification, never add "listen and tell me" steps or `track01.listener`-style gates; replace them with measurable checks. Related: [[suno-automation-constraints]]
