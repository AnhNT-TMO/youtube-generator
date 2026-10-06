# Listening Notes and Targeted Feedback

Read when planning sections, delivering an audition or applying listener feedback. The owner wants understandable music structure and short feedback, not a technical scoring form. Arrangement quality, phrasing, transitions and source balance lead the work; generation and diagnostics support those choices.

## A Small Note Beside Each Audition

Deliver `NGHE_THU.md` beside the MP3, using [the note template](../assets/listening-note-template.md). One shared note may cover the configured styles if their structure matches and every audio filename/revision is identified. Keep it to a few section rows, the instruments actually used, notable accents and a feedback example. No long report or required questionnaire.

Use stable section IDs from the track plan, a familiar Vietnamese label and mm:ss ranges. Label repeated carol statements as repetitions of the melody, not invented pop verses/choruses. An intro, bridge or breakdown is present only when the arrangement actually contains one. Distinguish a phrase inside a section from a section boundary; a chime accent inside a phrase is not automatically a transition.

List instrument names together with their roles. The instrument and the role are different: piano can carry both melody and left-hand accompaniment; pad supplies sustained harmony and the support instrument gives sparse responses. Keep part IDs linked to the actual note plan/roster so a comment resolves to the right notes, patch, gain and entry/exit window.

A few terms useful to the listener:

| Term | Meaning |
|---|---|
| Giai điệu chính / melody | The recognizable tune, usually foreground piano here. |
| Bè đệm / accompaniment | Parts supporting the melody; a playing role, not one instrument. |
| Hòa âm / harmony | Chords and the relationship of simultaneous notes. |
| Pad / lớp nền ngân | A warm sustained nonvocal background texture that rises and falls with piano phrases. |
| Bè đáp / response | A short musical reply to a phrase; a longer independent line can be a counter-melody. |
| Chuyển câu / transition | A link between phrases or sections; not a compulsory drum fill. |
| Điểm nhấn / accent | A local color event, which can also occur inside a phrase. |
| Bar-chime sweep / mark tree | A sweep across hanging metal bars with overlapping ringing tones; record the actual patch/sample and gesture. |
| Harp glissando | A flowing sweep across harp strings, used once at the configured transition. |
| Glockenspiel run | A short sequence of pitched metal-bar notes; keep it soft and compatible with the local harmony. |
| Legato | Connected notes without an intentionally detached gap. |
| Coda / đoạn kết | Closing musical material; separate its final played note from the reverb tail. |

Only show terms present in the current song's short note. Do not make the listener learn all of music theory to request a change. If they identify a sound imprecisely, their timestamp and description are enough to locate it; suggest the likely term without silently changing their intended request.

## Honest Timing and Instrument Claims

Keep `listening-map.json` as a compact machine-readable companion. Suggested contract:

```json
{
  "schema_version": 1,
  "song_slug": "example_carol",
  "revision": "r001",
  "auditions": [{"variant": "celesta", "audio_file": "Example.mp3", "duration_s": 180}],
  "timing_basis": "source_plan",
  "audition_alignment": {"status": "unverified", "evidence": null},
  "parts": [{"id": "piano", "name_vi": "Piano", "role_vi": "Giai điệu chính và tay trái đệm"}],
  "sections": [{
    "id": "A1", "label_vi": "Lượt giai điệu 1",
    "source_start_s": 0, "source_end_s": 54,
    "audition_start_s": null, "audition_end_s": null,
    "purpose_vi": "Giới thiệu carol và màu Christmas",
    "planned_part_ids": ["piano"],
    "instrument_retention": "unverified"
  }],
  "accents": [],
  "tail": {"source_start_s": 174, "source_end_s": 180},
  "feedback": []
}
```

Use only parts/events present in the actual spec/note plan; the example is a schema illustration before accent insertion, not a complete tune. Populate one accent record per configured accent per style from the actual post-cover manifest. Derive source times from verified beat/tempo data, including pickup, meter/tempo changes and expressive delays when present. Do not compute every tune as 4/4 or assume one BPM when maps differ. Include sample onset/active duration and the musical ending versus tail.

Source timestamps are source facts. Equal total durations and high feature similarity do not verify individual section boundaries, entrances or timbres in a cover. Set unknown audition positions to null. On the short note, say once: "Mốc gần đúng theo bản phối nguồn; khi feedback có thể dùng thời gian trên MP3." A verified output alignment may update the audition timestamps with its method; timing alignment alone still does not prove instrument retention or natural sound. Regenerate/update the note for the actual delivered revision/file after a changed source, pick or timeline.

## Convert Feedback Into a Specific Revision

A useful optional format is: "A2, khoảng 1:10, harp glissando hơi to; giảm điểm nhấn và giữ piano/pad." Ordinary descriptions like "tiếng leng keng lúc 1:10" are also valid. Do not require a numeric verdict or a questionnaire.

Resolve the comment to revision, audio style, section/phrase/time, part or accent ID, desired change and what to preserve. Record the listener's words and the resolved target. If a timestamp and ID disagree, inspect the actual artifact before editing; clarify only when multiple different edits remain plausible.

Identify the owner of the issue:

- Piano/pad/support timbre or balance: adjust that source part's patch/playing/gain and interaction with its neighbors.
- Inserted accent timbre, level or timing: adjust its sample/mix-plan and remix the same raw base without generation.
- Phrase or transition problem: adjust the relevant note plan, entrance/exit or gesture; check sustained harmony and overlap.
- One take's execution: try its stored backup before rebuilding the arrangement.
- Whole-arrangement direction: change the arrangement, not more random seeds.

Keep other approved source decisions. Write a short change manifest of targeted edits and known global effects, including source normalization if it changed. Verify the part/timeline actually changed, then use the configured targeted-revision take policy.

Current ACE-Step cover regenerates a whole recording. A section-specific source edit does not guarantee unchanged waveforms or unchanged execution elsewhere. State this limitation when relevant; keep the previous audition and check that untargeted source choices remain. Do not promise patch-only/local audio editing, true isolated AI stems, inpainting or sectional splice preservation until a suitable backend/method has actually been implemented and approved. The current flow explicitly adds the configured real recorded accents after cover. Accent-only level/timing/asset edits remix the same raw base; preserve and verify its hash. Cutting/splicing base phrases remains outside the flow.

Track listener `use_now`, `small_revision` and `rearrange` separately from technical pass. A repeated timbre complaint is a source/asset lesson for future songs, not a reason to run more seeds on the same unsuitable asset.

## Inserted accent timing

For the post-cover accents, copy actual onset/tail times, gesture, asset hash, gain and evidence from the mix manifest into `listening-map.json`. Mark their timing basis `post_cover_mix`; do not leave measured inserted events as unverified source-plan events. Keep source-only section times approximate until output alignment is established. The backup cover needs its own boundary evidence if it becomes the selected base. The inserted events do not certify that the generated base has no extra similar gestures.
