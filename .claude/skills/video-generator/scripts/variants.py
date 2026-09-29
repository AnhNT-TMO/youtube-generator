import copy
import glob
import hashlib
import itertools
import json
import os
import random

AXES = ("camera", "parallax", "atmosphere", "lighting")


def _anchors_needed(node):
    if isinstance(node, str) and node.startswith("@"):
        return {node[1:]}
    if isinstance(node, dict):
        return set().union(*(_anchors_needed(v) for v in node.values())) if node else set()
    if isinstance(node, list):
        return set().union(*(_anchors_needed(v) for v in node)) if node else set()
    return set()


def _resolve(node, anchors):
    if isinstance(node, str) and node.startswith("@"):
        return list(anchors[node[1:]])
    if isinstance(node, dict):
        return {k: _resolve(v, anchors) for k, v in node.items()}
    if isinstance(node, list):
        return [_resolve(v, anchors) for v in node]
    return node


def history(channel_dir, skip):
    seen = []
    for f in glob.glob(os.path.join(channel_dir, "*", "*", "video.json")):
        if os.path.dirname(os.path.abspath(f)) == os.path.abspath(skip):
            continue
        try:
            v = (json.load(open(f)).get("cinema") or {}).get("variant")
        except (OSError, ValueError):
            continue
        if isinstance(v, dict):
            seen.append((os.path.getmtime(f), v))
    return [v for _, v in sorted(seen, key=lambda x: x[0])]


def pick(job, seed=None, dry_run=False, force=None):
    chan = json.load(open(job.layers[0]))
    pool = chan.get("cinema_pool")
    if not pool:
        raise SystemExit(f"{job.layers[0]} has no cinema_pool")
    own_path = os.path.join(job.dir, "video.json")
    own = json.load(open(own_path)) if os.path.exists(own_path) else {}
    anchors = (own.get("cinema") or {}).get("anchors") or {}
    lighting = {k: v for k, v in pool["lighting"].items() if _anchors_needed(v) <= set(anchors)}
    dropped = sorted(set(pool["lighting"]) - set(lighting))
    if dropped:
        print(f"lighting sets needing anchors this image lacks ({sorted(set().union(*(_anchors_needed(pool['lighting'][k]) for k in dropped)))}): "
              f"{', '.join(dropped)}", flush=True)
    names = {"camera": list(pool["camera"]), "parallax": list(pool["parallax"]),
             "atmosphere": list(pool["atmosphere"]), "lighting": list(lighting)}
    if not all(names.values()):
        raise SystemExit("an axis of cinema_pool has no usable option")
    past = history(job.channel_dir, job.dir)
    n_avoid = int(pool.get("avoid_last", 3))
    recent = past[-n_avoid:] if n_avoid > 0 else []
    for axis, name in (force or {}).items():
        if axis not in AXES or name not in names[axis]:
            raise SystemExit(f"--set {axis}={name}: choose from {names.get(axis, AXES)}")
        names[axis] = [name]
    combos = [dict(zip(AXES, c)) for c in itertools.product(*(names[a] for a in AXES))]
    used = [tuple(v.get(a) for a in AXES) for v in past]
    fresh = [c for c in combos if tuple(c[a] for a in AXES) not in used] or combos
    for need in (len(AXES) - 1, len(AXES) - 2, 1, 0):
        ok = [c for c in fresh if all(sum(c[a] != r.get(a) for a in AXES) >= need for r in recent)]
        if ok:
            break
    if seed is None:
        seed = int(hashlib.sha1(job.dir.encode()).hexdigest()[:8], 16)
    rnd = random.Random(seed)
    c = rnd.choice(ok)
    atm = copy.deepcopy(pool["atmosphere"][c["atmosphere"]])
    parts = atm.get("particles", [])
    for p in parts:
        p["seed"] = rnd.randrange(1, 10 ** 6)
    cam = copy.deepcopy(pool["camera"][c["camera"]])
    cam["phase"] = round(rnd.uniform(0, 6.283), 3)
    cin = own.setdefault("cinema", {})
    cin.update({"enabled": True, "variant": dict(c, seed=seed), "camera": cam,
                "parallax": pool["parallax"][c["parallax"]],
                "lights": _resolve(copy.deepcopy(lighting[c["lighting"]]), anchors),
                "haze": atm.get("haze", {"enabled": False})})
    own["particles"] = parts
    label = " + ".join(f"{a}={c[a]}" for a in AXES)
    print(f"variant: {label} (seed {seed}; {len(ok)} candidates after avoiding the last {len(recent)} of {len(past)})")
    if dry_run:
        print(json.dumps(own, indent=1))
        return own
    json.dump(own, open(own_path, "w"), indent=1)
    print(f"wrote {os.path.relpath(own_path)}")
    return own
