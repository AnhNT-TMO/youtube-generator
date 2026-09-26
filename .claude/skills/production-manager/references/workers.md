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

## R&D
| Channel | Report | Topic decided (why) | Deep dive: refs → set → idea no. | State |
|---|---|---|---|---|

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

You work for the PM (CLAUDE.md §0). The PM's word is binding: first production/<ch>/direction.md (the channel's
current direction), then the target's brief (`brief` + `brief.decisions` in idea.yaml / plan.yaml, or short.md).
Be creative inside what the brief leaves open (lyrics, melody, the exact scene, wording), always within the channel
rules; never contradict the brief or silently change a decision. Brief missing, contradictory or impossible → stop.
The CEO is NOT available. Never use AskUserQuestion. Where a skill says "ask the user", apply the decision policy
below; if it doesn't cover the case, stop and return STATUS: BLOCKED with the question, the options and your
recommendation (the PM answers and resumes you).
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
STATUS: DONE | BLOCKED | FAILED | REVIEW (a picture waits for the PM's look)
OUTPUTS: files made/changed (paths)
DECISIONS: each choice you made inside the brief's open parts (what · chosen · why); none that changes a PM decision
CREDITS: before → after (suno job only)
ISSUES: skill problems met (skill, file:line or command, what happened, workaround used, cost to fix: small/large)
NEXT: what the next job for this target needs
```

## 1. rnd (lane rnd)

Skills: `youtube-trend-research` (+ `youtube-music-analyzer` for a deep dive). One worker at a time.

**Daily report:**
```
Job: R&D report for channel <ch> (youtube-trend-research SKILL.md §2): pulse, topics<, discover (the watchlist is stale)>
<, weekly: discover --shorts + shorts (§4) and thumbs → label every sheet → thumbs --summarize (§5)>.
Write research/trends/<ch>/reports/<date>.md + update state.md (references/report-template.md). Then
.claude/skills/youtube-translate/.venv/bin/python .claude/skills/production-manager/scripts/analytics.py fetch --channel <ch>
(skip if it says there is no token) and .claude/skills/album-plan/.venv/bin/python .claude/skills/production-manager/scripts/results.py --channel <ch>. Classify every finding
(CLAUDE.md §0): topic / music branch / packaging / outside the contract → new-channels.md. Recommend keep or switch
with the numbers; don't decide. Current topic: <topic since date>; our recent videos: <from state.md>.
Return: the report's "Kết luận cho PM" lines, the Ý tưởng thumbnail / Ý tưởng Shorts tables (weekly) + units used today.
```

**Deep dive → idea** (after you chose the topic and the brief):
```
Job: new idea <NNN-slug> for channel <ch>. Brief (<trend|ceo|pm>): "<brief>". Topic: <topic> [+ branch <branch>].
PM decisions: production/<ch>/decisions/<NNN-slug>.yaml (brief.decisions: music, title_direction, description_angle,
thumbnail_concept, shorts, packaging_version, success, by) → pass it to idea.py --decisions; implement them, never change them.
1. trend.py refs --topic <topic> [<branch>] → 3–5 videos, 1 per channel, in our music branch when possible (channel.md →
   Hợp đồng kênh); plus these owner links if any: <research-queue links of this topic>.
2. Measure each with youtube-music-analyzer remote.sh (≤ 2 at once), check each song split, one analysis.md each.
3. refset.py → research/set-<ch>-<topic>-<date>; fix its warnings (drop a tempo outlier); write the set's analysis.md.
4. trend.py comments on the 2–3 strongest + sheet of the refs; note viewers' needs and the niche's look in the report.
5. idea.py --refset … --brief … → fill every todo (analyzer SKILL.md §6: our story, set medians ~50 %, library first,
   copy guard from the set + sheet) → validate_idea.py OK → idea.md.
Open questions: write them with your recommendation (the PM answers them), don't decide silently.
Return: the idea's title track + angle, the set (members, medians), library songs proposed, open questions.
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
Job: thumbnail + loop for <album dir> (approved plan; main text on the image "<the phrase in brief.decisions.thumbnail_concept,
or what visual.md → Chữ chính trên ảnh says>").
thumbnail-prompt steps 1-6: python3 thumb.py list for the previous album's signature, write thumbnail-prompt.md,
chatgpt_images.py gen (background, 1 image per round), check the draft by the skill's checks, ALWAYS chatgpt_images.py
delete <conversation-id> afterwards (shared account). Then return STATUS: REVIEW with the draft path (+ its -phone.png) and
your check results, BEFORE thumb.py fit: the PM looks at it and answers (SendMessage) "accept" or "again: <what to change>".
After accept: thumb.py fit on that draft only (4K on the server), Read thumbnail.png vs the draft, thumb.py check.
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

## 7. single (release package: 1 per album, the highlight song)

Skills: `album-assembly` (single), `thumbnail-prompt` (lane chatgpt), `video-generator`, `youtube-publish` single mode.

```
Job: the single of album <album> (channel <ch>): slot <highlight> → channel/<ch>/singles/<NNN-slug> (number assigned by
the PM; slug = the song title).
1. mkdir the folder, copy templates/single.md → single.md; fill the front matter (id, track = ../../albums/<album>/tracks/<NN-slug>.md,
   track_id, album, album_video_url: leave empty until the album is uploaded) and the two "why / how the picture differs" lines.
2. Audio: album-assembly `assemble.py single <single dir>` (server) → audio/master/<NNN-slug>.wav; its render checks decide.
3. Picture: thumbnail-prompt on the single folder (lane chatgpt: tell the PM when you need it; one ChatGPT job at a time):
   the album's signature + the PM's concept (plan brief.decisions.thumbnail_concept), a different scene/pose from the album image;
   main text = the song title (visual.md → Chữ chính trên ảnh). Same PM review as the chatgpt job (STATUS: REVIEW before fit).
4. youtube-publish single mode → youtube.md (title/description by brief.decisions + publish.md; the album link line waits
   for album_video_url) → publish.py check <single dir> (no --video: the video lives on the server) until no ❌.
5. Loop + video on the server: video.py loop <single dir> → video.py album <single dir> audio/master/<NNN-slug>.wav
   (youtube.md exists, so it packages to S3 into the album's folder by itself).
Return: folder, audio length + vocal entry, chosen draft, title, S3 URI, what waits for the album URL.
```

## 7c. after-upload (after the CEO uploaded; lane post)

```
Job: the CEO uploaded <album> (and/or its singles / Shorts). Their Video URLs: <album: URL · single NNN: URL · short NNN: URL>.
1. Write each Video URL (+ upload date) into its youtube.md; album URL → album_video_url of the album's single.md.
2. Singles and Shorts whose youtube.md needed a link (album link line, Related video, pinned comment): fill it, rerun
   publish.py check / shorts.py check, then repackage (video.py package <dir>) so the CEO's zip has the final text.
3. youtube-translate for every uploaded video still missing a language (--yes).
4. Tick checklist items 15–16 (report the lines; the PM writes them).
Return: each video with URL, repackaged zips (S3 URI), translations written, anything still missing.
```

## 7b. shorts (release package: 1 per album, after its single)

```
Job: the Short of album <album> (channel <ch>), skill youtube-shorts (read its SKILL.md and docs/seo-youtube/09-shorts.md §4).
Role A: slot 1, target = the album.
Short idea chosen from R&D (report "Ý tưởng Shorts"): <format · part · hook angle · picture · version | default>.
Write the version into short.md; it differs in format or picture pattern from the channel's last Short.
1. shorts.py new → write hook_text + cta_text in short.md (channel publish.md → Shorts; new hook lines).
2. shorts.py pick → read the candidate table and the lyric lines; --pick K if the chosen one misses lines or ends mid-thought.
3. If research/trends/<ch>/shorts/ has nothing from the last 7 days: youtube-trend-research `trend.py shorts --channel <ch>`.
4. thumbnail-prompt on the Short folder (lane chatgpt, one job at a time): vertical CORE, trend patterns named under
   Ý tưởng, check the draft, delete the ChatGPT thread, STATUS: REVIEW to the PM (as the chatgpt job), after accept `thumb.py fit` (2160×3840).
5. video.py frame --at 5 → <short>/video.json (lantern, light, lanes) → video.py short --no-package (server) → Read
   check_hook/mid/cta.png (text never on the face or flame).
6. youtube.md from templates/youtube-short.md → shorts.py check → video.py package.
Stop (BLOCKED): no Whisper cache for the song; ChatGPT not logged in; server down.
Return: segment + length, hook line, chosen draft + why, S3 URI, warnings.
```

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

## 9. review (after a batch; no lane)

```
Job: review the production process after run <ledger path> (CLAUDE.md §0 "Cải tiến liên tục").
Read: the ledger (decisions, issues, Để sau, credits, time per lane), the R&D reports of the run, our channel numbers
(research/trends/<ch>/topics/<latest>.md → own channel), CLAUDE.md, the SKILL.md of every skill used.
Find what cost the most (credits, hours, manual workarounds, failed rounds, wrong outputs) and what would move views most.
Propose at most 5 changes, each: problem (with the evidence) · change · expected value · effort (hours, credits) · risk.
Drop anything whose value is not clearly above its effort; list those in one line under "không đáng làm lúc này".
Change nothing. Return the proposals in Vietnamese, most valuable first.
```
