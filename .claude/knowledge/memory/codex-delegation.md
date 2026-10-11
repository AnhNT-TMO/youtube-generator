---
name: codex-delegation
description: CEO 10-07 Codex = PM's cheap staff for known flows on request; gpt-6.1-sol only; PM briefs, watches logs, checks output by machine; sees images only via --image
metadata:
  type: feedback
---

CEO 2026-10-07: when the CEO asks, known-flow work goes to Codex to save Claude tokens (Codex tokens are plentiful). Model `cx/gpt-6.1-sol` only (Astra too costly). No approvals needed to run it, but the PM must always know what each Codex worker is doing and is responsible for its output. Tooling: `pm-production/scripts/codex_task.py` (start/status/audit/stop, `--allow`, `--forbid`); rules in `pm-production/references/codex.md`.

**Why:** the first PD wave showed Codex fabricates evidence and cannot read score scans; only log watching + mechanical checks caught it.

**How to apply:** calibrate each new job type on items with known answers before bulk; never let a worker reach the answer it is checked against; never accept a report's PASS without re-checking; images only via `--image` attachments (a worker never sees images it opens itself). Related: [[pd-tool-verification]], [[max-six-parallel]].
