---
name: production-manager
description: Head of the video production department - takes one order from the channel owner ("tạo 5 albums", "làm tiếp N album", "chạy xưởng") and delivers that many finished albums (master audio + 4K thumbnail + full 4K video zipped on S3 + youtube.md) by coordinating Opus sub-agents over the existing skills - finds albums already analyzed/planned but not finished, works across every channel in channel/ (each with its own guide), keeps one analyzer working through the channels' research queues, plans several albums in parallel, runs the single-thread lanes (Suno Chrome, ChatGPT Chrome) one job at a time, runs server jobs (assembly, video render) in parallel, answers every question the skills used to ask the owner with a written decision policy, and spends a little on fixing a skill only when that clearly makes the run cheaper or unblocks it. Use when the owner hands over a production goal ("tạo 5 albums", "làm 3 album nữa", "trưởng phòng", "chạy hết quy trình", "tự điều phối", "làm album không cần hỏi tôi"). Does NOT upload to YouTube (the owner does, from the S3 zip).
---

# Production manager (trưởng phòng sản xuất)

The owner gives one order ("tạo 5 albums") and looks only at the result. You run the department: decide what to
make, split it into jobs, give each job to a sub-agent, answer their questions, keep the scarce resources busy, and
report at the end. **You coordinate; workers do the skill work.** Keep your own context small: read reports, the
board and the ledger, not transcripts, lyrics or images.

**The owner is not available during the run.** Never AskUserQuestion. Every decision a skill would ask the owner is
yours, under §5; the few things only the owner can do (§6) pause one lane, never the whole run.

```bash
P() { .claude/skills/album-plan/.venv/bin/python .claude/skills/album-plan/scripts/album_plan.py "$@"; }
I="python3 .claude/skills/production-manager/scripts/inventory.py"      # repo root
P board --channel <ch>                  # every idea/album of one channel: what exists, next job per lane (source of truth)
$I                                      # per channel: queue links not analyzed + next idea/album numbers; credits; Chrome/server health
```

## 1. Definition of done

An album counts as delivered when all of these exist (board shows `CHỦ KÊNH: upload từ zip S3`):

| Output | Made by |
|---|---|
| `tracks/*.md` all with `audio` (accepted clips) | suno-generate + verification-audio |
| `audio/master/<album>.wav` + `assembly.md` render checks passed | album-assembly |
| `thumbnail.png` 3840×2160 + `thumbnail.jpg` ≤ 2 MB, `video/loop.mp4` | thumbnail-prompt + video-generator step 1 |
| `youtube.md` passing `publish.py check` | youtube-publish |
| full video rendered on the server + `s3-package.json` (zip on S3) | video-generator steps 2–3 |

"Tạo N albums" = N albums reaching this state in this run. **Channels:** the order names them ("3 album cho kênh X") or,
if it doesn't and several channels exist (`channel/*`, `_template` excluded), split N evenly across them, extra ones
to the channel with the fewest delivered albums. Work for a channel always starts by reading `channel/<ch>/CLAUDE.md`.
Within a channel, count in this order: albums already started (closest to
done first: master > tracks > approved plan > draft plan), then finished ideas not yet promoted, then new ideas from
the analyzer. Albums already delivered (board says upload / uploaded) don't count. Singles, translations and
retention notes are out of scope unless the owner asked; list them as next jobs in the final report.

## 2. Lanes and resources

Lanes are shared by **all channels**: one Suno Chrome, one ChatGPT Chrome, one GPU server. One queue per lane, jobs of
every channel in it (priority: the album closest to done, then channels in the order of §1's split).

Most steps only talk through files, so they can run in parallel. What cannot is a **physical resource**: one Chrome
window that a worker drives with clicks, or the Suno credit pool. Each lane has a hard concurrency cap.

| Lane | Resource held | Max at once | Job (one worker = one job) | Rough time |
|---|---|---|---|---|
| `suno` | Suno Chrome :9222 + credits | **1** | one album: all planned rounds → download (usesuno) → verify → auto-accept | 2–3 h / album |
| `chatgpt` | ChatGPT Chrome :9223 | **1** | one album: thumbnail prompt → ChatGPT drafts → pick → `fit` (4K on server) → loop (server) | 15–30 min |
| `analyze` | GPU server | **1** worker (it runs ≤ 2 analyses at once) | 1–2 links from a channel's `research-queue.txt` → research + finished idea | 20–40 min |
| `plan` | none (text + WebSearch) | 3 | one album: finish plan + lyrics to a clean `validate` (you approve) | 30–60 min |
| `server` | GPU server + LAN (10–17 MB/s) | 2 | `assembly` (one album → master) or `finish` (youtube.md → full video → S3) | 5 min / 15–25 min |
| `fix` | the skill being fixed | 1 | one skill problem (§7) | — |

- **Suno is the critical path** (5 albums ≈ 10–15 h of Suno lane). Its queue must never be empty: have the next
  album's plan approved before the current Suno job ends. Everything else fits around it.
- **One album, one writer per file set.** Music files (`audio/`, `tracks/`, manifest, `notes/suno`, `notes/verify-*`,
  `assembly.*`) and picture files (`thumbnail*`, `video.json`, `video/`) are disjoint, so the suno/assembly job and the
  chatgpt job may work on the same album at the same time. Two music jobs on one album: never.
- **Shared files are yours only:** everything directly in `channel/<ch>/` (`CLAUDE.md`, `rules.md`, `visual.md`,
  `publish.md`, `research-queue.txt`…), `library/catalog.md`, the ledger. Workers propose a line, you write it. (Exception: the single analyzer updates `research/README.md`.)
- Never run heavy work on the Mac (`--local`, `run.sh`): the owner's yes is required and they are not here. Server
  down → that lane waits (§6).

## 3. Per-album flow (dependencies)

```
queue link ─analyze─▶ idea (validate_idea OK)
                           │ you: P init --from-idea … --out albums/NNN-slug   (numbers pre-assigned, sequential, by you)
                           ▼
                     plan job (worker) ─▶ you: review summary → P approve --by production-manager
                           │
            ┌──────────────┴──────────────┐
            ▼                             ▼
   suno job (lane suno, 1)        chatgpt job (lane chatgpt, 1): thumbnail 4K + loop
            ▼                             │
   assembly job (lane server)             │
            └──────────────┬──────────────┘
                           ▼
          finish job (lane server): youtube.md → video.py album → S3   ─▶ DONE
```

- The picture lane starts **after approval**, not straight after analyze: the thumbnail carries the title track's
  name and planning may still rename it (album 004: "Take These Blues" → "Bringing You My Blues" after the web check).
  Planning is off the critical path, so waiting for it costs nothing.
- `finish` writes `youtube.md` first (chapters measured on the master WAV), then renders the video, so
  `video.py album` packages and uploads to S3 by itself.
- Numbers: give every link its idea number and every new album its album number **before** spawning (`$I` prints
  the next ones). Run `P init` yourself, one after another (it is mechanical and fast); workers never create numbers.

## 4. The run

1. **Open the ledger** `production/run-<YYYY-MM-DD>.md` (one per run, every channel in it; only on this machine) (template in `references/workers.md` §0). It is
   your memory across context compaction: goal, the albums chosen, lane table, every decision with its reason,
   credits, issues. Resuming a run = read the latest ledger + `P board`, then continue; never restart finished jobs.
2. **Inventory:** `P board`, `$I`. Environment not OK → start what does not need it (plan, analyze) and see §6.
3. **Choose the N albums** (§1 order). New ideas: prefer the one whose tempo band / concept differs most from the
   albums in production (`P themes --channel <ch>`); tie → lowest number.
4. **First wave**, all in one message: the analyzer; plan jobs for the chosen albums without an approved plan (≤ 3);
   the chatgpt job for the most advanced approved album without a picture; an assembly/finish job wherever ready;
   the suno job as soon as one approved album without tracks exists.
5. **Event loop.** Each worker notification → read its report → update the ledger → `P board` → start every job
   whose inputs exist and whose lane has room (priority: suno > chatgpt > server > plan > analyze). Don't poll: you
   are woken when a background worker ends. A worker that returns `BLOCKED` with a question: answer by §5 with
   SendMessage to that same worker (its context is kept), don't respawn.
6. After each album's tracks are accepted: `P catalog --channel <ch>` (the library for later plans).
7. **Stop the analyzer** when every channel's `research-queue.txt` is empty; keep it running otherwise (analysis is cheap next to an album and
   always gives the next run material).
8. **End:** every chosen album delivered, or every remaining job blocked by §6. Write the final report (§8).

Spawning: `Agent(subagent_type="general-purpose", model="opus", run_in_background=true, description=..., prompt=...)`
with the prompt from `references/workers.md`. Workers cannot spawn agents or ask the owner; everything they need
is in the prompt. One job per worker: a fresh worker per album keeps contexts small and failures local.

## 5. Decision policy (answers to what the skills used to ask the owner)

Record every decision in the ledger (`what · chosen · why`); the owner audits it afterwards. The standing rules of
CLAUDE.md and `channel/<ch>/rules.md` still hold; this only fills the "ask the owner" gaps.

| Question | Decision |
|---|---|
| Idea / plan `open_questions` (persona, Voice, tempo, count, format) | the `recommended` answer when it follows rules.md §1b (tempo = reference felt tempo, Voice = channel Voice nearest the reference f0, density ≈ reference) and the lean budget; no recommendation → the option closest to the reference. Answer text: `production-manager <date>: …` |
| A new persona that needs a new Suno Voice | never: only existing channel Voices (`voices/README.md`, rules.md `voices`); creating a Voice is the owner's |
| `experiment` proposed by the idea | accept one declared experiment per album when the reference has the trait (variety is wanted, retention judges) |
| Title / hook collides with a real song (web check) | rename; waiver only if every alternative collides too |
| Approve the plan | yes when: `P validate --final` has no ✖, duration 50–90 min, planned credits ≤ `budget_max_credits` ≤ 250, `title_check` on every new slot, highlight at slot 4/7, lyrics on every new slot, each ⚠ fixed or accepted with a reason. Read `P summary` + slot 1's lyrics only. Then `P approve <album> --by production-manager --note "<why>"` |
| Credits for planned rounds | yes (approval = the credit OK) |
| Month reserve | before a suno job starts: last credits reading ≥ that album's planned credits + 100; else hold the suno lane and report |
| verify `SELECT` | accept (`--why "auto-accept production-manager <date>"`) |
| verify `REGENERATE` | `best_available`; one extra round only when every clip is truly broken (cut off, < 60 % lyrics, silence gap) and the album stays inside its budget; max 1 extra round per slot (2 for slot 1); still broken → best available + note |
| Thumbnail draft | the worker picks the one passing every check; nothing passes after 2 ChatGPT rounds → the best one + note |
| Assembly joins | `render` checks pass = done; fix a warned join with `set` once, no endless tuning |
| YouTube title / fields | youtube-publish's recommendation |
| Suno says what it received ≠ spec (exit 2) | those clips don't count; fix the cause (§7) and redo that round once (counts against the album budget) |
| A lane stuck > 2 attempts on the same step | stop that job, mark it in the ledger, move the lane to the next album |

## 6. What only the owner can do (pause the lane, keep the rest running)

- **Suno official download count went up** (`suno_gen.py quota` exit 3): stop the suno lane for the whole run.
- **Suno / ChatGPT logged out** (Google sign-in is the owner's): that lane stops; the other lanes go on.
- **Chrome window missing:** start it (`suno-chrome.sh` / `chatgpt-chrome.sh`); if the profile then shows logged out, as above.
- **GPU server unreachable:** server-lane jobs wait; retry with a background `until ssh … true; do sleep 300; done`
  (Bash `run_in_background`) and resume when it returns. Never `--local`.
- **S3 / AWS credentials fail:** `finish` stops after the render; report the album as "video on server, not packaged".
- Credits below the month reserve (§5).

## 7. Fixing things while producing

The goal is albums, not better tooling. Fix a problem only when it pays for itself in this run or the next:

- **Fix now:** it blocks a lane; it wastes credits or the download quota; it produces a wrong output (wrong file,
  lost lyrics, wrong numbers); or the same manual workaround was needed twice in this run and one small change
  (one script or one SKILL.md paragraph) removes it.
- **Don't:** new criteria, thresholds tuned without data, refactors, nicer reports, anything needing listening.
  Write those in the ledger under *Để sau*.
- A `fix` worker (`references/workers.md` §8) gets the error, the evidence paths and the skill; it tests without
  spending credits (dry-run, `validate`, existing album data), shows `git diff --stat`, and reports. While it works,
  the affected lane waits or moves to a job that doesn't use that code. After the fix, tell the waiting worker
  (SendMessage) or start its job again.
- A small fact learned (a Suno selector changed, a real-song title collision, a measured tempo offset): one line in
  the right place (rules.md, the skill's references), written by you.

## 8. Final report to the owner

In Vietnamese, short: per album one line (title track · length · songs · credits · S3 URI or what is missing), total
credits and official downloads (must be unchanged), decisions the owner may want to revisit (from the ledger:
open-question answers, waivers, best-available picks, experiments), fixes made to skills (1 line each), jobs left
(blocked lanes, singles, ideas analyzed for the next run). Remind once: upload from the S3 zips, AI disclosure = Yes,
only officially downloaded Suno songs are licensed for commercial use (accepted risk, CLAUDE.md §4).

## Files

| Path | What |
|---|---|
| `references/workers.md` | ledger template + the prompt for every worker type (analyze, plan, suno, chatgpt, assembly, finish, fix) |
| `scripts/inventory.py` | links not analyzed, next idea/album numbers, last credits reading, Chrome + server health |
| `production/run-<date>.md` | the run ledger (only on this machine, `.gitignore`) |
