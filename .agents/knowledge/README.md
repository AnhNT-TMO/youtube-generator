# Shared production knowledge

Claude and Codex use the same repository, channel contracts, research, album records and server assets. Source skills and this knowledge directory live in `.claude/`; `.agents/sync-skills.sh` mirrors them into `.agents/`.

## Read by task

- Production rules: `CLAUDE.md`, then `channel/README.md` and the selected channel's contracts.
- Album 005/006, piano bell arrangements, montage and countdown Shorts: `channel/everstill/production-handoff.md`.
- Imported Claude project memory: [memory/MEMORY.md](memory/MEMORY.md). Read linked entries relevant to the task, not the entire archive.
- Tools: `.agents/skills/` for discovery in Codex; examples using `.claude/skills/` intentionally remain executable from either assistant in this shared repo. Use the canonical commands when they need the existing source skill's `.venv` or `remote.env`.

## Authority and updates

The memory archive was imported from Claude's project memory on 2026-10-11. It contains dated decisions and superseded experiments. Apply the latest approved album brief and channel contract; use memory as context, never as a replacement for current state. In particular, Mureka's no-choir rules do not apply to the self-arranged bell-piano lane, and countdown Shorts have a separate delivery flow from lyric Shorts.

Write new reusable procedures into the source skill, channel decisions into channel guides, and per-release state into the album record. Update this directory only for knowledge that belongs here, then run:

```bash
.agents/sync-skills.sh
.agents/sync-skills.sh --check
```

To import later Claude memory additions, explicitly supply that project's memory directory:

```bash
.agents/sync-skills.sh --memory-source /path/to/claude/project/memory
```

Import merges Markdown files without deleting earlier imported entries; review superseded decisions against current contracts. There is no background or reverse sync. `.claude/skills/` and `.claude/knowledge/` remain the source of truth.

## Moving to another machine

Git alone does not carry `research/`, `audio/`, `production/`, album folders, scene media, branding, credentials, venvs or server sample libraries. Transfer the relevant shared data and provision the existing server/browser access separately. Do not treat synced skills as proof that those assets exist. Do not copy authentication values into this knowledge archive. On this machine both assistants read the same assets directly.
