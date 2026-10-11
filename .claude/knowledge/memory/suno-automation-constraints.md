---
name: suno-automation-constraints
description: Suno Sept-2026 constraints (v6 only, Pro 20 downloads/month, no official API) and chosen automation route; full research in .claude/skills/audio-suno-generate/references/suno-research.md
metadata:
  type: project
---
As of 2026-09-23: Suno has no public API; v6 launched 2026-09-09 and retired all older models; since 2026-09-03 Pro gets only 20 song downloads/month and commercial use requires downloading via Suno itself. usesuno.com "WAV" is lossy Opus in a WAV container (Album 01 files included).

**Why:** these facts decide how the `audio-suno-generate` skill works — download quota, not credits, is the bottleneck.
**How to apply:** default route is Chrome DevTools MCP driving the user's logged-in suno.com (not resellers/cookie wrappers); every download, drafts and finals, goes through usesuno ([[never-use-suno-download]]). Browser = dedicated Chrome launched by .claude/skills/audio-suno-generate/scripts/suno-chrome.sh (profile ~/.suno-chrome/profile, port 9222) + MCP server `suno-chrome` at LOCAL scope (`claude mcp add -s local`, in ~/.claude.json; moved out of .mcp.json on 2026-09-23 because the VS Code extension auto-rejects project .mcp.json servers → invisible in /mcp), because the plugin's self-launched Chrome is blocked by Google sign-in and Suno has no email login (phone login would create a new account). User chose usesuno.com for downloads (lossy is fine). Re-verify before relying on it, Suno changes fast. Details: .claude/skills/audio-suno-generate/references/suno-research.md. Related: [[pool-production-flow]]
