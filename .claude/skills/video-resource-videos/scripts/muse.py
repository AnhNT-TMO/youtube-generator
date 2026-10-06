import base64
import json
import re
import time

from cdp import Page, pages

ORIGIN = "https://muse.ai"
NEW_THREAD = f"{ORIGIN}/thread/new"
COMPOSER = 'textarea[placeholder="Message"]'
SERVICE_RE = re.compile(r"rate limit|limit reached|quota|captcha|verify you are human|try again later", re.I)
UNDELIVERED_RE = re.compile(r"Delivery not confirmed", re.I)
WRAPPER = ('Image-to-video, attached image = first frame, exactly ONE generation. Pass this prompt to the video tool word '
           'for word, then paste back the exact prompt you sent: "{prompt}"')
STATE = f"""(() => {{ const box = document.querySelector({json.dumps(COMPOSER)}); const rect = box && box.getBoundingClientRect();
  const text = document.body ? document.body.innerText : ''; const log = document.querySelector('[role=log]');
  const video = Array.from(document.querySelectorAll('[role=log] video')).pop();
  return {{url: location.href, ready: !!rect && rect.width > 0 && rect.height > 0 && !box.disabled,
    loading: /Loading|Connecting/.test(text.slice(0, 3000)), login: /sign in|log in/i.test(text.slice(0, 3000)) && !box,
    captcha: /captcha|verify you are human/i.test(text), file_input: !!document.querySelector('input[type=file]'),
    log: (log ? log.innerText : '').replace(/\\s+/g, ' ').trim(), videos: document.querySelectorAll('[role=log] video').length,
    video: video ? {{src: video.currentSrc || video.src, ready_state: video.readyState, width: video.videoWidth, height: video.videoHeight}} : null}}; }})()"""


class Blocked(RuntimeError):
    pass


class NotSent(RuntimeError):
    pass


class Uncertain(RuntimeError):
    pass


def muse_tabs(port):
    return [target["id"] for target in pages(port, ORIGIN)]


def find_file_input(node):
    attributes = node.get("attributes", [])
    if node.get("nodeName") == "INPUT" and "type" in attributes and attributes[attributes.index("type") + 1] == "file":
        return node["backendNodeId"]
    children = node.get("children", []) + node.get("shadowRoots", [])
    if node.get("contentDocument"):
        children.append(node["contentDocument"])
    for child in children:
        found = find_file_input(child)
        if found:
            return found
    return None


class MuseTab:
    def __init__(self, port, page_id):
        if page_id not in muse_tabs(port):
            raise Blocked(f"cổng {port}: không có tab muse.ai {page_id}")
        self.port, self.id = port, page_id
        self.page = Page(port, page_id, ORIGIN)

    def state(self):
        return self.page.js(STATE)

    def ready(self, timeout=40):
        deadline = time.time() + timeout
        while True:
            state = self.state()
            if state["login"] or state["captcha"]:
                raise Blocked("LOGIN/CAPTCHA: muse.ai cần CEO xử lý trên Chrome này")
            if state["ready"] and not state["loading"] and state["file_input"]:
                return state
            if time.time() > deadline:
                raise NotSent(f"tab muse chưa sẵn sàng sau {timeout} s")
            self.page.repaint()
            time.sleep(1)

    def new_thread(self):
        self.page.navigate(NEW_THREAD)
        time.sleep(2)
        state = self.ready()
        if state["log"] or state["videos"]:
            raise NotSent("thread mới vẫn còn tin nhắn cũ")

    def attached(self, name):
        return self.page.js(f"""Array.from(document.querySelectorAll('img')).some(e => !e.closest('[role=log]')
          && e.alt === {json.dumps(name)} && e.complete && e.naturalWidth > 0)""")

    def attach(self, png):
        for attempt in range(2):
            if attempt:
                self.page.call("Page.bringToFront")
            document = self.page.call("DOM.getDocument", depth=-1, pierce=True)
            node = find_file_input(document["root"])
            if not node:
                raise NotSent("không thấy ô đính file")
            self.page.call("DOM.setFileInputFiles", backendNodeId=node, files=[str(png)])
            for _ in range(20):
                if self.attached(png.name):
                    return
                time.sleep(1)
        raise NotSent("ảnh chưa đính xong; chưa gửi")

    def send(self, prompt):
        message = WRAPPER.format(prompt=prompt)
        self.page.js(f"document.querySelector({json.dumps(COMPOSER)}).focus()")
        self.page.call("Input.insertText", text=message)
        if self.page.js(f"document.querySelector({json.dumps(COMPOSER)}).value") != message:
            raise NotSent("chữ trong ô chat khác prompt")
        return message

    def press_send(self, message):
        self.page.press("Enter")
        target = " ".join(message.split())
        for _ in range(20):
            time.sleep(1)
            state = self.state()
            if target in state["log"]:
                return state["url"]
        raise Uncertain("đã Enter nhưng 20 s chưa thấy tin nhắn trong thread")

    def poll(self):
        self.page.repaint()
        state = self.state()
        tail = state["log"][-1600:]
        if state["login"] or state["captcha"] or SERVICE_RE.search(tail):
            raise Blocked(f"muse báo: {tail[-300:]}")
        video = state["video"]
        ready = bool(video and video["src"] and video["ready_state"] >= 2 and video["width"] > 0)
        return {"url": state["url"], "video": video if ready else None, "undelivered": bool(UNDELIVERED_RE.search(tail)),
                "tail": tail[-300:]}

    def open(self, url):
        if self.page.url().split("?", 1)[0] != url.split("?", 1)[0]:
            self.page.navigate(url)
            time.sleep(3)
            self.ready()

    def fetch(self, src):
        payload = self.page.js(f"""(async () => {{ const response = await fetch({json.dumps(src)});
          if (!response.ok) throw new Error('tải video lỗi ' + response.status);
          const blob = await response.blob(); const bytes = new Uint8Array(await blob.arrayBuffer()); let text = '';
          for (let i = 0; i < bytes.length; i += 32768) text += String.fromCharCode.apply(null, bytes.subarray(i, i + 32768));
          return {{type: blob.type, size: blob.size, b64: btoa(text)}}; }})()""")
        raw = base64.b64decode(payload["b64"], validate=True)
        if not payload["type"].startswith("video/") or len(raw) != payload["size"]:
            raise Uncertain(f"blob tải về không phải video ({payload['type']}, {len(raw)} byte)")
        return raw
