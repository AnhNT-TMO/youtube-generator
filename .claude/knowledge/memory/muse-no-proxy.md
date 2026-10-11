---
name: muse-no-proxy
description: "CEO 10-05 — muse Chrome (9224/9226) now runs without the US socks proxy (MUSE_CHROME_PROXY=none, cookies kept); proxy caused 'Delivery not confirmed' stalls; max 3 tabs/port"
metadata:
  node_type: memory
  type: project
  originSessionId: 29f4a079-0b21-4544-ae0c-464bb65417dc
  modified: 2026-10-05T06:08:55.506Z
---

2026-10-05: with the US proxy muse stalled all lunch ("Delivery not confirmed", 15-min timeouts); the same profile without proxy delivered a clip in ~1.5 min while the proxied port kept failing. CEO approved turning the proxy off on both muse ports; login survived the IP change.

**Why:** proxy (≈1.4 s/request) made muse drop messages; 4 tabs/port also broke muse.

**How to apply:** launch muse Chrome with `MUSE_CHROME_PROXY=none` (script default still proxies); keep 3 tabs/port. Log in image_source/OPTIMIZATION.md. Related [[resource-queue-workflow]], [[muse-clip-production]].
