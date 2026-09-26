#!/usr/bin/env python3
USAGE = """Tạo ảnh thumbnail bằng ChatGPT (Chrome riêng, agent-browser --cdp) rồi tải về thumbnail-drafts/.

  chatgpt_images.py gen    <dir> [--n 1] [--timeout 600]   chat mới → đính kèm ảnh model → dán prompt → chờ N ảnh → tải về
  chatgpt_images.py fetch  <dir>                          tải ảnh đã tạo trong thread đang mở (khi gen dừng giữa chừng)
  chatgpt_images.py delete <conversation-id>               xóa đúng thread đó (kiểm tra link trước khi bấm Delete)

Cần: scripts/chatgpt-chrome.sh đang chạy (cổng 9223) và đã đăng nhập ChatGPT trong Chrome đó; `agent-browser` trong PATH.
<dir> = channel/<ch>/{singles,albums,ideas}/NNN-slug có thumbnail-prompt.md (khối ``` sau "## Prompt", ảnh đính kèm ở "## Đính kèm").
Chạy từ gốc repo. Tài khoản ChatGPT có thể dùng chung: `gen` in ra conversation id, `delete` chỉ xóa thread có id đó.
"""
import argparse
import base64
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

PORT = "9223"
UPLOAD_SETTLE_S = 20


def _find_ab():
    cands = [os.environ.get("AGENT_BROWSER"), shutil.which("agent-browser"),
             *sorted(glob.glob(os.path.expanduser("~/.nvm/versions/node/*/bin/agent-browser")), reverse=True)]
    for c in cands:
        if c and os.path.exists(os.path.realpath(c)):
            return c
    sys.exit("không tìm thấy agent-browser (npm i -g agent-browser)")


AB = _find_ab()


def ab(*args, stdin=None, check=True):
    r = subprocess.run([AB, "--cdp", PORT, *args], input=stdin, capture_output=True, text=True)
    if check and r.returncode:
        sys.exit(f"agent-browser {' '.join(args)}: {r.stderr.strip() or r.stdout.strip()}")
    return r.stdout.strip()


def js(code):
    out = ab("eval", "--stdin", stdin=code)
    try:
        v = json.loads(out)
        return json.loads(v) if isinstance(v, str) and v[:1] in "[{" else v
    except json.JSONDecodeError:
        return out


def prompt_parts(d):
    text = (d / "thumbnail-prompt.md").read_text()
    m = re.search(r"^## Prompt\n+```[a-z]*\n(.*?)\n```", text, re.S | re.M)
    if not m:
        sys.exit(f"{d}/thumbnail-prompt.md: không thấy khối ``` trong ## Prompt")
    att = re.search(r"^## Đính kèm\n(.*?)(?=^## )", text, re.S | re.M)
    files = re.findall(r"`(channel/[^`]+\.png)`", att.group(1) if att else "")
    missing = [f for f in files if not Path(f).exists()]
    if missing:
        sys.exit(f"thiếu ảnh đính kèm: {missing}")
    return m.group(1), [str(Path(f).resolve()) for f in files]


GEN_IDS = r"""(() => { const fid = i => ((i.currentSrc || i.src).match(/id=(file_[0-9a-f]+)/) || [])[1] || ((i.currentSrc || i.src).match(/^blob:\S+/) || [])[0];
  const all = Array.from(document.querySelectorAll('main img, [role=dialog] img, img'));
  const refs = new Set(all.filter(i => /\.(png|jpe?g|webp)$/i.test(i.alt || '') || i.alt === 'User attachment').map(fid));
  const ids = all.filter(i => /^Generated image/i.test(i.alt || '') || (i.naturalWidth >= 1000 && !refs.has(fid(i))))
    .map(fid).filter(x => x && !refs.has(x));
  return JSON.stringify({url: location.href, ids: [...new Set(ids)],
    busy: !!document.querySelector('[data-testid="stop-button"], button[aria-label*="Stop"]')}); })()"""


CLEAR = """(() => { document.querySelectorAll('[aria-label^="Remove file"], [aria-label^="Remove "][aria-label$=".png"]').forEach(b => b.click());
  const k = 'oai/apps/conversationDrafts'; const v = JSON.parse(localStorage.getItem(k) || '{"drafts":[]}');
  v.drafts = (v.drafts || []).filter(d => d.id !== 'null_thread'); localStorage.setItem(k, JSON.stringify(v)); return 0; })()"""


COMPOSER_LEFTOVER = """(() => { const e = document.querySelector('#prompt-textarea, div.ProseMirror[role=textbox]'); if (!e) return -1;
  return e.innerText.trim().length + document.querySelectorAll('[aria-label^="Remove file"], [aria-label^="Remove "][aria-label$=".png"]').length; })()"""


def clear_composer():
    for _ in range(3):
        if js(COMPOSER_LEFTOVER) == 0:
            return
        js(CLEAR)
        time.sleep(1)
        ab("open", "https://chatgpt.com/")
        ab("wait", "--load", "networkidle", check=False)
    sys.exit("không xóa được chữ/ảnh còn sót trong ô chat ChatGPT; xóa tay rồi chạy lại")


def click_send():
    frame = Path(tempfile.gettempdir()) / "chatgpt-images-frame.png"
    ab("screenshot", str(frame), check=False)
    ab("click", '#composer-submit-button, button[aria-label="Send"]', check=False)


def ask_for_n_images(prompt, n):
    if n == 1:
        for pat, rep in (
            (r"Create THREE separate images", "Create ONE image"),
            (r": three variations of the scene described below, each a complete standalone", ": the scene described below, as one complete standalone"),
            (r"Do not combine them into one picture: no collage", "One single picture: no collage"),
            (r" The three variations may differ slightly in [^;.]*; everything else follows the description\.", ""),
        ):
            prompt = re.sub(pat, rep, prompt)
        return prompt
    return prompt.replace("Create THREE separate images", f"Create {n} separate images")


def cmd_gen(a):
    d = Path(a.dir)
    prompt, files = prompt_parts(d)
    prompt = ask_for_n_images(prompt, a.n)
    ab("open", "https://chatgpt.com/")
    ab("wait", "--load", "networkidle", check=False)
    if "Log in" in ab("snapshot", "-i", "-c") and "profile menu" not in ab("snapshot", "-i", "-c"):
        sys.exit("ChatGPT chưa đăng nhập trong chatgpt-chrome: đăng nhập tay một lần rồi chạy lại")
    clear_composer()
    for k, f in enumerate(files, 1):
        ab("upload", '#upload-photos, input[type=file][accept="image/*"]', f)
        for _ in range(30):
            if js("document.querySelectorAll('[aria-label^=\"Remove file\"], [aria-label^=\"Remove \"][aria-label$=\".png\"]').length") >= k:
                break
            time.sleep(1)
        else:
            sys.exit(f"ChatGPT không nhận ảnh đính kèm {Path(f).name} sau 30s; xem cửa sổ Chrome")
        time.sleep(UPLOAD_SETTLE_S)
    ab("focus", "#prompt-textarea, div.ProseMirror[role=textbox]")
    ab("keyboard", "inserttext", prompt)
    got = js("document.querySelector('#prompt-textarea, div.ProseMirror[role=textbox]').innerText.length")
    if not isinstance(got, int) or got < len(prompt) * 0.95:
        sys.exit(f"prompt chưa vào ô chat đủ ({got}/{len(prompt)} ký tự)")
    for i in range(45):
        time.sleep(2)
        click_send()
        if i >= 3:
            time.sleep(2)
            if js("(document.querySelector('#prompt-textarea, div.ProseMirror[role=textbox]') || {}).innerText?.trim().length || 0"):
                ab("focus", "#prompt-textarea, div.ProseMirror[role=textbox]", check=False)
                ab("press", "Enter", check=False)
        time.sleep(2)
        if not js("(document.querySelector('#prompt-textarea, div.ProseMirror[role=textbox]') || {}).innerText?.trim().length || 0"):
            break
    else:
        js(CLEAR)
        sys.exit("bấm Send 45 lần (~3 phút) mà prompt vẫn nằm trong ô chat, thường do ảnh đính kèm kẹt 'File upload pending' (đã xóa ô chat); xem cửa sổ Chrome")
    t0, st = time.time(), {}
    while time.time() - t0 < a.timeout:
        time.sleep(10)
        st = js(GEN_IDS)
        print(f"  {int(time.time() - t0):>4}s  {len(st.get('ids', []))}/{a.n} ảnh  {'đang tạo' if st.get('busy') else ''}", flush=True)
        if len(st.get("ids", [])) >= a.n and not st.get("busy"):
            break
    download(d, st, a.n, a.timeout)


def cmd_fetch(a):
    download(Path(a.dir), js(GEN_IDS), a.n, 0)


def download(d, st, n, timeout):
    ids = st.get("ids", [])
    conv = (re.search(r"/c/([\w:-]+)", st.get("url", "")) or [None, None])[1]
    if not ids:
        sys.exit(f"hết {timeout}s chưa có ảnh (conversation {conv}); xem cửa sổ Chrome")
    out = d / "thumbnail-drafts"
    out.mkdir(exist_ok=True)
    n0 = max([int(p.stem) for p in out.glob("[0-9][0-9].*")] or [0])
    saved = []
    for k, fid in enumerate(ids, 1):
        data = js(f"""(async () => {{ const img = Array.from(document.querySelectorAll('img')).find(i => (i.currentSrc||i.src).includes('{fid}'));
  const r = await fetch(img.currentSrc || img.src, {{credentials: 'include'}}); const b = new Uint8Array(await r.arrayBuffer());
  let s = ''; for (let i = 0; i < b.length; i += 32768) s += String.fromCharCode.apply(null, b.subarray(i, i + 32768));
  return r.headers.get('content-type') + '|' + btoa(s); }})()""")
        ct, b64 = data.split("|", 1)
        ext = {"image/png": "png", "image/webp": "webp", "image/jpeg": "jpg"}.get(ct, "bin")
        f = out / f"{n0 + k:02d}.{ext}"
        f.write_bytes(base64.b64decode(b64))
        saved.append(str(f))
    print(json.dumps({"conversation": conv, "images": saved}, ensure_ascii=False))
    if len(ids) < n:
        print(f"⚠️  chỉ có {len(ids)}/{n} ảnh", file=sys.stderr)


def cmd_delete(a):
    cid = a.conversation
    hrefs = js(f"""JSON.stringify(Array.from(document.querySelectorAll('nav a[href*="/c/{cid}"]')).map(x => [x.getAttribute('href'), x.innerText.trim()]))""")
    if not hrefs:
        ab("open", f"https://chatgpt.com/c/{cid}")
        ab("wait", "--load", "networkidle", check=False)
        hrefs = js(f"""JSON.stringify(Array.from(document.querySelectorAll('nav a[href*="/c/{cid}"]')).map(x => [x.getAttribute('href'), x.innerText.trim()]))""")
    if not hrefs:
        sys.exit(f"không thấy thread {cid} trong sidebar (đã xóa?)")
    title = hrefs[0][1]
    link = f'nav a[href*="/c/{cid}"]'
    js(f"""(() => {{ const a = document.querySelector('{link}'); const b = a && (a.querySelector('button[aria-label^="Open conversation options"]') || a.closest('.group')?.querySelector('button[aria-label="Chat actions"]')); if (b) b.setAttribute('data-thread-options', '{cid}'); return !!b; }})()""")
    btn = f'[data-thread-options="{cid}"]'
    for _ in range(3):
        ab("scrollintoview", link, check=False)
        ab("hover", link, check=False)
        refs = re.findall(rf'button "Open conversation options for {re.escape(title)}"[^\n]*ref=(e\d+)', ab("snapshot", "-i", check=False))
        ab("click", f"@{refs[0]}" if len(refs) == 1 else btn, check=False)
        time.sleep(1.5)
        if 'menuitem "Delete"' in ab("snapshot", "-i", check=False):
            break
    else:
        sys.exit(f"không mở được menu của thread '{title}'")
    ab("find", "role", "menuitem", "click", "--name", "Delete")
    time.sleep(1.5)
    dialog = ab("get", "text", "[role=dialog]", check=False)
    if f"delete {title}" not in dialog:
        ab("press", "Escape", check=False)
        sys.exit(f"hộp xác nhận không khớp thread '{title}', không xóa: {dialog[:120]}")
    confirm = "Delete chat" if 'button "Delete chat"' in ab("snapshot", "-i", check=False) else "Delete"
    ab("find", "role", "button", "click", "--name", confirm, "--exact")
    time.sleep(3)
    left = js(f"""document.querySelectorAll('nav a[href*="/c/{cid}"]').length""")
    print(f"đã xóa '{title}' ({cid})" if left == 0 else f"⚠️  thread {cid} vẫn còn trong sidebar")


def main():
    ap = argparse.ArgumentParser(description=USAGE, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("gen")
    g.add_argument("dir")
    g.add_argument("--n", type=int, default=1)
    g.add_argument("--timeout", type=int, default=600)
    g.set_defaults(fn=cmd_gen)
    f = sub.add_parser("fetch")
    f.add_argument("dir")
    f.add_argument("--n", type=int, default=1)
    f.set_defaults(fn=cmd_fetch)
    d = sub.add_parser("delete")
    d.add_argument("conversation")
    d.set_defaults(fn=cmd_delete)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
