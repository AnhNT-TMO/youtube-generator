---
name: no-suno-behavior-assumptions
description: Don't bake guesses about Suno's behavior (e.g. "renders ~10% slower") into plans/prompts; prompt = our target, measure then fix
metadata:
  type: feedback
---

The user (2026-09-23): don't hardcode that Suno renders slower than the prompt BPM, and don't judge Suno from Album 001. Suno updates its models and algorithms over time and we can't predict that. Our job is to plan well: the prompt tempo equals the planned (felt) tempo.

**Why:** the 0.9× prompt→measured ratio came from a single album (wtnl-v1). Compensating in advance would silently push every future album off-target once Suno changes.
**How to apply:** the channel's prompt_suno.md is typed byte-exact (no "Suno tends to…" corrections). A systematic Suno quirk is fixed only with measured data and the CEO's OK (prompt changes are the CEO's). Related: [[pool-production-flow]]
