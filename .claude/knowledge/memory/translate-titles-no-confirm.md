---
name: translate-titles-no-confirm
description: "Owner wants every YouTube video's title AND description translated automatically (youtube-translate), no confirmation before writing"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 5c1820b3-7220-4147-a464-163df6aa9ff1
  modified: 2026-09-24T02:14:46.222Z
---

Owner 2026-09-24: "đọc xem video nào chưa dịch rồi dịch … bỏ qua bước xác nhận, video nào tôi cũng muốn dịch cả".
Run `yt_translate.py pull/apply --missing --channel <ch> --yes` and translate every video still missing a language,
without asking first; just report the table afterwards.

Owner 2026-09-24 (later): descriptions too ("dịch luôn cả description") → `translate_description: true` in the
channel's translate.yaml; description translated line by line, sung lyrics / chapters / hashtags / links stay English.

**Why:** translated titles are low-risk and the owner can't read most target languages anyway; asking adds friction only.
**How to apply:** after any upload (or when asked to translate), go straight through pull → translate → apply --yes.
Still never send a partial `localizations` update by hand (it replaces all languages). Related: [[pool-production-flow]].
