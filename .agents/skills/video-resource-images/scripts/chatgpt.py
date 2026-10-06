import base64
import json
import re
import struct
import time

from cdp import Page, pages

ORIGIN = "https://chatgpt.com"
COMPOSER = "#prompt-textarea, div.ProseMirror[role=textbox]"
VISIBLE = "(sel => Array.from(document.querySelectorAll(sel)).find(e => e.getBoundingClientRect().width > 0) || null)"
SEND_BUTTON = ('#composer-submit-button, button[data-testid="send-button"], button[aria-label="Send"], '
               'button[aria-label="Send prompt"], button[aria-label="Send message"]')
BUSY_RE = re.compile(r"Sketching|Creating image|Generating|Thinking|Getting started|Adding details|Finishing|\b\d{1,2}%")
UNAVAILABLE_RE = re.compile(r"Image generation failed|image generation is currently unavailable|Something went wrong", re.I)
QUOTA_RE = re.compile(r"(?:hit|reached).{0,120}(?:image generat|plan limit)|image generation limit|image generat.{0,100}(?:limit|quota)", re.I)
IMAGE_STATE = r"""(() => { const visible = """ + VISIBLE + r"""; const fid = i => ((i.currentSrc || i.src).match(/id=(file_[0-9a-f]+)/) || [])[1] || ((i.currentSrc || i.src).match(/^blob:\S+/) || [])[0];
  const all = Array.from(document.querySelectorAll('img'));
  const refs = new Set(all.filter(i => /\.(png|jpe?g|webp)$/i.test(i.alt || '') || i.alt === 'User attachment').map(fid));
  const ids = all.filter(i => /^Generated image/i.test(i.alt || '') || (i.naturalWidth >= 1000 && !refs.has(fid(i)))).map(fid).filter(x => x && !refs.has(x));
  const tail = ((visible('main') || document.body).innerText || '').split('ChatGPT can make mistakes')[0].slice(-400);
  return {url: location.href, ids: [...new Set(ids)], tail,
    busy: !!document.querySelector('[data-testid="stop-button"], button[aria-label*="Stop"]')}; })()"""
USER_TEXTS = """(() => ({url: location.href, users: Array.from(((""" + VISIBLE + """)('main') || document)
  .querySelectorAll('[data-message-author-role="user"], [data-user-message-bubble="true"]'))
  .map(e => (e.textContent || '').replace(/\\s+/g, ' ').trim())}))()"""


class Blocked(RuntimeError):
    pass


class NotSent(RuntimeError):
    pass


class Uncertain(RuntimeError):
    pass


class NoImage(RuntimeError):
    pass


class Quota(RuntimeError):
    pass


class Unavailable(RuntimeError):
    pass


def conversation(url):
    match = re.search(r"/c/([0-9a-f-]{36})", url or "")
    return match.group(1) if match else None


def png_size(raw):
    if raw[:8] != b"\x89PNG\r\n\x1a\n":
        return None, None
    return struct.unpack(">II", raw[16:24])


class ChatGPT:
    def __init__(self, port, page_id=None):
        candidates = pages(port, ORIGIN)
        if page_id:
            candidates = [target for target in candidates if target["id"] == page_id]
        if len(candidates) != 1:
            raise Blocked(f"cổng {port}: cần đúng 1 tab chatgpt.com, thấy {len(candidates)} (truyền --page-id)")
        self.page = Page(port, candidates[0]["id"], ORIGIN)

    def open(self, conv=None):
        self.page.navigate(f"{ORIGIN}/c/{conv}" if conv else f"{ORIGIN}/")
        time.sleep(2)
        stable = 0
        for _ in range(90):
            time.sleep(1)
            self.page.repaint()
            state = self.page.js(f"""(() => ({{ready: document.readyState === 'complete' && !!{VISIBLE}({json.dumps(COMPOSER)}),
              login: !!document.querySelector('[data-testid="login-button"]'),
              broken: /Could not load this ChatGPT conversation/.test(document.body ? document.body.innerText : '')}}))()""")
            if state["login"]:
                raise Blocked("LOGIN: ChatGPT chưa đăng nhập trên Chrome này")
            stable = stable + 1 if state["ready"] and not state["broken"] else 0
            if stable >= 3:
                if conv and conversation(self.page.url()) != conv:
                    raise Uncertain(f"không mở được chat {conv}")
                if not conv and conversation(self.page.url()):
                    raise NotSent("chat mới lại mở vào một chat cũ")
                return
        raise NotSent("trang ChatGPT không sẵn sàng sau 90 s")

    def send(self, prompt):
        page = self.page
        target = " ".join(prompt.split())
        page.js(f"(() => {{ const e = {VISIBLE}({json.dumps(COMPOSER)}); e.focus(); window.getSelection().selectAllChildren(e); return true; }})()")
        page.call("Input.insertText", text=prompt)
        typed = page.js(f"({VISIBLE}({json.dumps(COMPOSER)}).innerText || '').replace(/\\s+/g, ' ').trim()")
        if typed != target:
            raise NotSent(f"prompt trong ô chat không khớp ({len(typed or '')}/{len(target)} ký tự)")
        deadline = time.time() + 15
        while not page.js(f"""(() => {{ const b = Array.from(document.querySelectorAll({json.dumps(SEND_BUTTON)}))
              .find(e => e.getBoundingClientRect().width > 0 && !e.disabled); if (!b) return false; b.click(); return true; }})()"""):
            if time.time() > deadline:
                raise NotSent("nút Send không bật sau 15 s")
            time.sleep(0.5)
        for _ in range(45):
            time.sleep(2)
            page.repaint()
            state = page.js(USER_TEXTS)
            conv = conversation(state["url"])
            if conv and any(target == text or target in text for text in state["users"]):
                return conv
        raise Uncertain("đã bấm Send nhưng 90 s chưa thấy tin nhắn trong chat")

    def wait_image(self, timeout=600):
        started, idle = time.time(), None
        while time.time() - started < timeout:
            time.sleep(6)
            self.page.repaint()
            state = self.page.js(IMAGE_STATE)
            busy = state["busy"] or bool(BUSY_RE.search(state["tail"][-300:]))
            if state["ids"] and not busy:
                time.sleep(4)
                state = self.page.js(IMAGE_STATE)
                if state["ids"]:
                    return state["ids"][-1]
            if busy:
                idle = None
                continue
            if QUOTA_RE.search(state["tail"]):
                raise Quota(state["tail"][-200:])
            if UNAVAILABLE_RE.search(state["tail"][-400:]):
                raise Unavailable(state["tail"][-200:])
            idle = idle or time.time()
            if time.time() - idle > 150:
                raise NoImage(state["tail"][-300:])
        raise Uncertain(f"{timeout} s chưa có ảnh")

    def fetch(self, file_id):
        for _ in range(4):
            data = self.page.js(f"""(async () => {{
              const image = Array.from(document.querySelectorAll('img')).find(e => (e.currentSrc || e.src).includes({json.dumps(file_id)}));
              if (!image) throw new Error('không thấy ảnh ' + {json.dumps(file_id)});
              const response = await fetch(image.currentSrc || image.src, {{credentials: 'include'}});
              if (!response.ok) throw new Error('tải ảnh lỗi ' + response.status);
              const bytes = new Uint8Array(await response.arrayBuffer()); let text = '';
              for (let i = 0; i < bytes.length; i += 32768) text += String.fromCharCode.apply(null, bytes.subarray(i, i + 32768));
              return response.headers.get('content-type') + '|' + btoa(text); }})()""")
            kind, encoded = data.split("|", 1)
            raw = base64.b64decode(encoded, validate=True)
            width, _ = png_size(raw)
            if kind.startswith("image/png") and width and width >= 1000:
                return raw
            time.sleep(8)
        raise NoImage(f"ảnh {file_id} chưa tải được bản đủ lớn")

    def hide(self, conv):
        try:
            return self.page.js(f"""(async () => {{ const session = await (await fetch('/api/auth/session')).json();
              const response = await fetch('/backend-api/conversation/{conv}', {{method: 'PATCH',
                headers: {{'Content-Type': 'application/json', Authorization: 'Bearer ' + session.accessToken}},
                body: JSON.stringify({{is_visible: false}})}}); return response.status; }})()""") == 200
        except RuntimeError:
            return False
