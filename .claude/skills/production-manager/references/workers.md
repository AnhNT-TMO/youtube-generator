# Worker prompts

Fill the `<…>` fields and paste the **common block** + the job block as the Agent prompt
(`subagent_type: general-purpose`, `model: opus`, `run_in_background: true`). Keep prompts self-contained: the worker
has no memory of this conversation. Put the decisions you already made (§5 answers, numbers, budget) in the prompt.

## 0. Ledger template (`production/run-<YYYY-MM-DD>.md`)

```markdown
# Production run <date> · goal: <N> albums · channels: <ch>: <n>, <ch>: <n>

## Albums
| # | Channel | Album | Start state | plan | suno | picture | assembly | finish | Credits | Note |
|---|---|---|---|---|---|---|---|---|---|---|

## Lanes (now)
| Lane | Worker (agent id) | Job | Since |
|---|---|---|---|

## Analyzer queue
| Channel | Idea no. | Video id | State |
|---|---|---|---|

## Decisions (what · chosen · why)
## Credits log (time · reading · album)
## Issues / fixes (what · fixed? · by whom · git diff --stat)
## Để sau
```

## Common block (every worker)

```
You are a worker in a production run (repo /Users/tienanh/Desktop/youtube, channel channel/<ch>). Your job:
<JOB NAME> for <TARGET DIR>. Read CLAUDE.md, then channel/<ch>/CLAUDE.md (the channel's own guide: which of its files
hold the rules for your step), then the SKILL.md files named below. The skills are the procedure; everything about
what this channel's music, images and texts should be comes from channel/<ch>/.

The channel owner is NOT available. Never use AskUserQuestion. Where a skill says "ask the user", apply the
decision policy below; if it doesn't cover the case, stop and return STATUS: BLOCKED with the question, the options
and your recommendation (the manager answers and resumes you).
Decision policy for this job: <paste the relevant rows of SKILL.md §5 + any decision already made>.

Limits:
- Write only inside <TARGET DIR> and the outputs your skills create for it. Never edit the files directly in
  channel/<ch>/ (CLAUDE.md, rules.md, visual.md, publish.md, research-queue.txt…), library/catalog.md, other albums,
  or any skill's code; propose such changes in your report.
- Heavy work only on the GPU server (the skills do this by default). Never pass --local / run.sh.
- Don't spawn agents. Run long commands in the background and wait for them; don't sleep-poll.
- Media never goes into git. Suno downloads only through usesuno.com, never Suno's Download buttons.
- A command failing twice the same way: stop and report (don't improvise workarounds that change outputs).

Return (≤ 20 lines, plain text):
STATUS: DONE | BLOCKED | FAILED
OUTPUTS: files made/changed (paths)
DECISIONS: each decision you took for the owner (what · chosen · why)
CREDITS: before → after (suno job only)
ISSUES: skill problems met (skill, file:line or command, what happened, workaround used, cost to fix: small/large)
NEXT: what the next job for this target needs
```

## 1. analyze

Skill: `youtube-music-analyzer`. One worker, 1–2 links (the skill runs 2 at once on the GPU box).

```
Job: analyze these links from channel/<ch>/research-queue.txt for channel <ch>, idea numbers already assigned (don't pick others):
  <idea NNN> ← <url>
  <idea NNN> ← <url>
For each: remote.sh run (background) → check the song split (fix with segments.yaml if needed) → analysis.md →
fill idea.yaml (empty todo) → validate_idea.py OK → idea.md → add a row to research/README.md.
Open questions in the idea: write them with your recommendation (album-plan answers them), don't decide silently.
A link that is not an album in this channel's genre (channel/<ch>/channel.md) (e.g. a single, off-genre, < 10 min):
analyze nothing, report it as SKIPPED with the reason.
```

## 2. plan

Skill: `album-plan` (+ its `references/lyrics.md`, `channel/<ch>/rules.md`). The manager already ran `P init`.

```
Job: finish the plan of <album dir> (plan.yaml exists; it may be half done - continue from its state, don't redo).
Answer every open question by the policy (recommended answer when it follows rules.md §1b and the lean budget;
answer text "production-manager <date>: ..."). Only existing channel Voices. Web-check every new title and hook.
Other albums being planned right now: <list> - avoid their title-track concepts, titles and hooks (validate
cross_plan sees them once written).
Write all lyrics, then `P validate <album>` until no ✖, then `P summary <album>`.
Do NOT run `P approve`. Return the summary table, the remaining ⚠ with why each is acceptable, and the waivers.
```

Manager then: read the summary + slot 1 lyrics → approve by §5, or SendMessage the fix to the same worker.

## 3. suno (lane suno, only one at a time)

Skills: `suno-generate`, `verification-audio`.

```
Job: generate album <album dir> on Suno from its approved generation.yaml, verify, accept.
The plan approval is the credit OK for every PLANNED round (budget <budget_max_credits> credits). Credits now: <C>.
Order: slot 1's planned rounds → download + ingest its clips → verify.py check --slot 1 → accept (slot 1 must be
accepted before any other slot: gates.anchor_first) → every other planned round (one generation at a time up to
`complete`) → download + ingest all → verify.py check --slot all → accept each slot.
Accept every SELECT without asking: verify.py accept ... --why "auto-accept production-manager <date>".
REGENERATE: use best_available (accept with --why). An extra round only if EVERY clip of the slot is truly broken
(cut off, < 60 % lyrics, silence gap) and the album stays inside its budget: max 1 extra round per slot (2 for slot 1),
suno_gen.py next --slot N --purpose regenerate --reason "<hints>".
Hard stops (return BLOCKED immediately): quota exit 3 (official downloads rose), Suno logged out, check-form never
reaches FORM KHỚP SPEC after fixing, exit 2 on submitted/complete (report the mismatch; don't retry).
The Suno MCP tools are mcp__suno-chrome__* (load them with ToolSearch "select:..." first). If they are not
available to you, return BLOCKED "no suno-chrome MCP" at once.
Report the credits reading before and after, and `suno_gen.py status` at the end.
```

If a worker cannot see `mcp__suno-chrome__*`, the manager runs the suno lane in the main session (same steps) and
keeps the rest delegated.

## 4. chatgpt (lane chatgpt, only one at a time)

Skills: `thumbnail-prompt`, then `video-generator` step 1.

```
Job: thumbnail + loop for <album dir> (approved plan; title track "<exact title>").
thumbnail-prompt steps 1-6: python3 thumb.py list for the previous album's signature, write thumbnail-prompt.md,
chatgpt_images.py gen (background), pick the draft yourself by the skill's checks (max 2 ChatGPT rounds; none passes
→ best one + note), ALWAYS chatgpt_images.py delete <conversation-id> afterwards (shared account), thumb.py fit on the
chosen draft only (4K on the server), Read thumbnail.png vs the draft, thumb.py check.
Then video-generator step 1: frame --at 30 / --at 25 → album video.json (lantern.center from check's bright spot) →
video.py loop → check intro + seam frames.
Stop (BLOCKED): ChatGPT logged out; server down (don't use --no-upscale without the manager's OK).
```

## 5. assembly (lane server)

Skill: `album-assembly`.

```
Job: assemble <album dir> (every tracks/*.md has audio). assemble.py plan → review assembly.md as the skill's step 2
says → at most one pass of `set` fixes → render → read "Kiểm tra sau khi ghép" + "Cảnh báo". Checks pass = done; don't
ask anyone to listen. Report: length, join types, vocal entry of track 01, warnings left.
```

## 6. finish (lane server; needs master + thumbnail.png + video/loop.mp4)

Skills: `youtube-publish`, then `video-generator` steps 2–3.

```
Job: publish files + full video for <album dir>. Master: <album dir>/audio/master/<album>.wav.
1. If the picture was made in the idea folder: album_plan.py sync <album>.
2. youtube-publish: publish.py chapters <album> --audio <master.wav> (the video's audio is the master from 0:00) →
   write youtube.md (recommended title + 2 alternatives, description template, tracklist, tags, pinned comment) →
   publish.py check <album> (no --video; the video will live on the server) until no ❌.
3. video.py album <album> <master.wav> (background, ~15-25 min; packages + uploads to S3 by itself because
   youtube.md exists) → check video/video.mp4.json (duration = master, 3840×2160, audio stream), check_5s.png,
   check_mid.png, s3-package.json.
Stop (BLOCKED): server down; AWS/S3 error (report "video on server, not packaged").
Report the S3 URI and any warning from s3-package.json.
```

## 7. single (only when the owner asked for singles)

Skills: `album-assembly single`, `thumbnail-prompt` (lane chatgpt), `youtube-publish` single mode,
`video-generator`. Same limits; the highlight song (slot 4/7) of each album.

## 8. fix (lane fix)

```
Job: fix one problem in skill <skill> that blocked/costs the production run.
Evidence: <error text, command, file paths, which album>. Expected: <what should have happened>.
Rules: smallest change that fixes it; match the surrounding code; no new criteria or thresholds; test without
spending Suno credits or ChatGPT rounds (dry run, validate, re-run on existing album data); don't touch albums'
outputs except to re-run the failed command. If the fix is large (several files, redesign), don't do it: report
the cause and a proposal. Update the skill's SKILL.md / references only if a documented step changed.
Return: cause, change (git diff --stat), how it was tested, what the waiting lane should do now.
```
