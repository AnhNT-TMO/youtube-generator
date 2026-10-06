import base64
import json
import time
import os
import sys
import urllib.request
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
VENVS = [SKILL / ".venv", SKILL.parents[2] / ".claude" / "skills" / SKILL.name / ".venv"]


def websocket_module():
    try:
        import websocket
        return websocket
    except ImportError:
        for venv in VENVS:
            python = venv / "bin" / "python"
            if python.exists() and Path(sys.prefix).resolve() != venv.resolve():
                os.execv(str(python), [str(python), *sys.argv])
        sys.exit(f"thiếu websocket-client: python3 -m venv {VENVS[0]} && {VENVS[0]}/bin/pip install websocket-client")


def pages(port, origin):
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=10) as response:
        targets = json.loads(response.read())
    return [target for target in targets if target.get("type") == "page" and target.get("url", "").startswith(origin)]


class Page:
    def __init__(self, port, target_id, origin):
        self.port, self.id, self.origin = port, target_id, origin
        self.sequence = 0
        self.ws = websocket_module().create_connection(f"ws://127.0.0.1:{port}/devtools/page/{target_id}",
                                                       timeout=180, suppress_origin=True)
        self.call("Emulation.setFocusEmulationEnabled", enabled=True)

    def call(self, method, limit=150, **params):
        if method.startswith("Target.") or method == "Browser.close":
            raise RuntimeError("không tạo/đóng tab của Chrome đã giao")
        self.sequence += 1
        self.ws.send(json.dumps({"id": self.sequence, "method": method, "params": params}))
        deadline = time.time() + limit
        while True:
            if time.time() > deadline:
                raise TimeoutError(f"{method}: Chrome không trả lời sau {limit} s")
            message = json.loads(self.ws.recv())
            if message.get("id") == self.sequence:
                if "error" in message:
                    raise RuntimeError(f"{method}: {message['error'].get('message')}")
                return message.get("result", {})

    def js(self, expression):
        result = self.call("Runtime.evaluate", expression=expression, awaitPromise=True, returnByValue=True, userGesture=True)
        if result.get("exceptionDetails"):
            details = result["exceptionDetails"]
            raise RuntimeError("js: " + (details.get("exception", {}).get("description") or details.get("text", ""))[:300])
        return result.get("result", {}).get("value")

    def url(self):
        return self.js("location.href")

    def navigate(self, url):
        if not url.startswith(self.origin):
            raise RuntimeError(f"không điều hướng ra ngoài {self.origin}")
        self.call("Page.navigate", url=url)

    def repaint(self):
        try:
            self.call("Page.captureScreenshot", format="jpeg", quality=5)
        except RuntimeError:
            pass

    def screenshot(self, path):
        Path(path).write_bytes(base64.b64decode(self.call("Page.captureScreenshot", format="png")["data"]))

    def press(self, key="Enter"):
        code = {"Enter": 13, "Escape": 27}[key]
        for event in ("keyDown", "keyUp"):
            self.call("Input.dispatchKeyEvent", type=event, key=key, code=key, windowsVirtualKeyCode=code)

    def close(self):
        self.ws.close()
