import json
from pathlib import Path

from resq import REPO


class ResourceSet:
    def __init__(self, name):
        self.name = name.strip("/")
        self.root = REPO / self.name
        manifest = self.root / "resource.json"
        if not manifest.exists():
            raise SystemExit(f"{manifest} không có: bộ resource cần resource.json (xem pm-production/references/resource-queue.md)")
        self.config = json.loads(manifest.read_text())
        self.blocks = json.loads((self.root / "blocks.json").read_text()) if (self.root / "blocks.json").exists() else {}

    def themes(self, groups=None):
        found = sorted(path.parent.relative_to(self.root).as_posix() for path in self.root.glob(self.config.get("shots", "*/*/shots.json")))
        return [theme for theme in found if not groups or theme.split("/")[0] in groups]

    def spec(self, theme):
        return json.loads((self.root / theme / "shots.json").read_text())

    def shots(self, theme):
        spec = self.spec(theme)
        defaults = spec.get("defaults", {})
        for shot in spec["shots"]:
            merged = {key: value for key, value in defaults.items() if key != "tags"}
            merged.update(shot)
            merged["tags"] = {**defaults.get("tags", {}), **shot.get("tags", {})}
            yield merged

    def shot(self, theme, shot_id):
        for shot in self.shots(theme):
            if shot["id"] == shot_id:
                return shot
        raise SystemExit(f"{self.name}/{theme}: không có cảnh {shot_id}")

    def path(self, theme, shot_id, suffix):
        return f"{self.name}/{theme}/{shot_id}{suffix}"

    def card(self, theme, shot_id):
        path = self.root / theme / f"{shot_id}.json"
        return json.loads(path.read_text()) if path.exists() else None

    def exists(self, theme, shot_id, suffix):
        return (self.root / theme / f"{shot_id}{suffix}").exists()
