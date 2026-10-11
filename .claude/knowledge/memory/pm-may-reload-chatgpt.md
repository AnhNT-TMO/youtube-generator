---
name: pm-may-reload-chatgpt
description: "CEO 10-04 — PM may reload hung ChatGPT/muse tabs itself (incl. killing the hung tab renderer), no asking"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 29f4a079-0b21-4544-ae0c-464bb65417dc
  modified: 2026-10-04T10:54:49.059Z
---

PM tự reload tab ChatGPT khi tab treo. Nếu renderer treo 100 % CPU và CDP navigate timeout, kill đúng tiến trình renderer của tab đó, rồi navigate lại chatgpt.com trong chính tab ấy.

**Why:** CEO 2026-10-04: "cho phép PM reload không sao cả cái này PM quyết được". Tab mở liền ~29 giờ thì treo, làm lane ảnh dừng.

**How to apply:** vẫn không tạo/đóng tab, không đổi profile/proxy. Khởi động lại generator sau khi reload. Liên quan [[resource-queue-workflow]].
