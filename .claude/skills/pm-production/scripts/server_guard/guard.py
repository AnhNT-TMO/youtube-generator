import json
import os
import signal
import subprocess
import sys
import time

HOME = os.path.expanduser("~")
DIR = os.path.join(HOME, "youtube-guard")
SLICE = f"/sys/fs/cgroup/user.slice/user-{os.getuid()}.slice/user@{os.getuid()}.service/youtube.slice"
DEFAULTS = {
    "poll_seconds": 2,
    "idle_exit_seconds": 900,
    "min_available_ram_share": 0.15,
    "slice_ram_share": 0.60,
    "scope_ram_gb": 40,
    "gpu_mem_gb": 60,
    "gpu_temp_c": 88,
    "load_factor": 1.5,
    "load_strikes": 5,
    "max_runtime_hours": 4,
    "max_threads": 3000,
    "warn_share": 0.8,
    "dry_run": False,
}


def cfg():
    c = dict(DEFAULTS)
    p = os.path.join(DIR, "guard.json")
    if os.path.exists(p):
        c.update(json.load(open(p)))
    return c


def log(kind, **kw):
    rec = dict(t=time.strftime("%Y-%m-%d %H:%M:%S"), kind=kind, **kw)
    with open(os.path.join(DIR, "guard.log"), "a") as fh:
        fh.write(json.dumps(rec) + "\n")
    if kind in ("kill", "kill_slice"):
        with open(os.path.join(DIR, "kills.log"), "a") as fh:
            fh.write(json.dumps(rec) + "\n")


def read(path, default=""):
    try:
        return open(path).read()
    except OSError:
        return default


def stat_kv(path):
    out = {}
    for line in read(path).splitlines():
        k, _, v = line.partition(" ")
        if v.strip().isdigit():
            out[k] = int(v)
    return out


def meminfo():
    m = {}
    for line in read("/proc/meminfo").splitlines():
        k, v = line.split(":", 1)
        m[k] = int(v.split()[0]) * 1024
    return m


def scopes():
    out = []
    for name in sorted(os.listdir(SLICE)) if os.path.isdir(SLICE) else []:
        p = os.path.join(SLICE, name)
        if os.path.isdir(p) and name.endswith((".scope", ".service")):
            pids = [int(x) for x in read(os.path.join(p, "cgroup.procs")).split()]
            if pids:
                out.append((name, p, pids))
    return out


def cmdline(pid):
    return read(f"/proc/{pid}/cmdline").replace("\0", " ").strip()[:200]


def age_seconds(pids):
    hz = os.sysconf("SC_CLK_TCK")
    up = float(read("/proc/uptime", "0 0").split()[0])
    ages = []
    for pid in pids:
        f = read(f"/proc/{pid}/stat").rsplit(")", 1)
        if len(f) == 2:
            ages.append(up - int(f[1].split()[19]) / hz)
    return max(ages, default=0.0)


def gpu():
    try:
        apps = subprocess.run(["nvidia-smi", "--query-compute-apps=pid,used_memory", "--format=csv,noheader,nounits"],
                              capture_output=True, text=True, timeout=10).stdout
        temp = subprocess.run(["nvidia-smi", "--query-gpu=temperature.gpu", "--format=csv,noheader,nounits"],
                              capture_output=True, text=True, timeout=10).stdout
    except (OSError, subprocess.TimeoutExpired):
        return {}, 0
    mem = {}
    for line in apps.splitlines():
        parts = [x.strip() for x in line.split(",")]
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            mem[int(parts[0])] = int(parts[1]) * 1024 * 1024
    temps = [int(x) for x in temp.split() if x.strip().isdigit()]
    return mem, max(temps, default=0)


def kill_cgroup(path, name, reason, c, **info):
    log("kill" if path != SLICE else "kill_slice", scope=name, reason=reason, dry_run=c["dry_run"], **info)
    if c["dry_run"]:
        return
    ok = os.path.exists(os.path.join(path, "cgroup.kill"))
    if ok:
        try:
            with open(os.path.join(path, "cgroup.kill"), "w") as fh:
                fh.write("1")
            return
        except OSError:
            pass
    for pid in [int(x) for x in read(os.path.join(path, "cgroup.procs")).split()]:
        try:
            os.kill(pid, signal.SIGKILL)
        except OSError:
            pass


def check(c, state):
    mi = meminfo()
    total, avail = mi["MemTotal"], mi["MemAvailable"]
    sc = scopes()
    if not sc:
        return False
    per = []
    for name, path, pids in sc:
        ms = stat_kv(os.path.join(path, "memory.stat"))
        cpu = stat_kv(os.path.join(path, "cpu.stat")).get("usage_usec", 0)
        threads = int(read(os.path.join(path, "pids.current"), "0").strip() or 0)
        per.append(dict(name=name, path=path, pids=pids, anon=ms.get("anon", 0), cpu=cpu, threads=threads,
                        age=age_seconds(pids), cmd=cmdline(pids[0])))
    gmem, gtemp = gpu()
    for s in per:
        s["gpu"] = sum(v for pid, v in gmem.items() if pid in s["pids"])
    gb = 1024 ** 3
    slice_anon = sum(s["anon"] for s in per)
    biggest = max(per, key=lambda s: s["anon"])
    if avail < total * c["min_available_ram_share"]:
        kill_cgroup(biggest["path"], biggest["name"], "server RAM available below "
                    f"{c['min_available_ram_share']:.0%}", c, avail_gb=round(avail / gb, 1), cmd=biggest["cmd"])
        return True
    if slice_anon > total * c["slice_ram_share"]:
        kill_cgroup(biggest["path"], biggest["name"], f"youtube.slice RAM above {c['slice_ram_share']:.0%}", c,
                    slice_gb=round(slice_anon / gb, 1), cmd=biggest["cmd"])
        return True
    for s in per:
        if s["anon"] > c["scope_ram_gb"] * gb:
            kill_cgroup(s["path"], s["name"], f"job RAM above {c['scope_ram_gb']} GB", c, ram_gb=round(s["anon"] / gb, 1), cmd=s["cmd"])
            return True
        if s["gpu"] > c["gpu_mem_gb"] * gb:
            kill_cgroup(s["path"], s["name"], f"job GPU memory above {c['gpu_mem_gb']} GB", c, gpu_gb=round(s["gpu"] / gb, 1), cmd=s["cmd"])
            return True
        if s["age"] > c["max_runtime_hours"] * 3600:
            kill_cgroup(s["path"], s["name"], f"job running over {c['max_runtime_hours']} h", c, hours=round(s["age"] / 3600, 2), cmd=s["cmd"])
            return True
        if s["threads"] > c["max_threads"]:
            kill_cgroup(s["path"], s["name"], f"job threads above {c['max_threads']}", c, threads=s["threads"], cmd=s["cmd"])
            return True
        if s["anon"] > c["warn_share"] * c["scope_ram_gb"] * gb and not state["warned"].get(s["name"]):
            state["warned"][s["name"]] = True
            log("warn", scope=s["name"], ram_gb=round(s["anon"] / gb, 1), cmd=s["cmd"])
    gtot = sum(gmem.values())
    if gtemp >= c["gpu_temp_c"]:
        top = max(per, key=lambda s: s["gpu"])
        if top["gpu"] > 0:
            kill_cgroup(top["path"], top["name"], f"GPU temperature {gtemp} C", c, gpu_gb=round(top["gpu"] / gb, 1), cmd=top["cmd"])
            return True
    load1 = float(read("/proc/loadavg", "0").split()[0])
    now = time.time()
    rates = {}
    for s in per:
        prev = state["cpu"].get(s["name"])
        if prev:
            rates[s["name"]] = (s["cpu"] - prev[0]) / 1e6 / max(1e-3, now - prev[1])
        state["cpu"][s["name"]] = (s["cpu"], now)
    if load1 > c["load_factor"] * os.cpu_count() and rates:
        state["load_strikes"] += 1
        if state["load_strikes"] >= c["load_strikes"]:
            top = max(per, key=lambda s: rates.get(s["name"], 0))
            if rates.get(top["name"], 0) > 1:
                kill_cgroup(top["path"], top["name"], f"server load {load1:.0f} above {c['load_factor']}x cores", c,
                            cores=round(rates[top["name"]], 1), cmd=top["cmd"])
                state["load_strikes"] = 0
                return True
    else:
        state["load_strikes"] = 0
    if now - state["last_beat"] > 60:
        state["last_beat"] = now
        log("beat", jobs=len(per), slice_ram_gb=round(slice_anon / gb, 1), avail_gb=round(avail / gb, 1),
            gpu_gb=round(gtot / gb, 1), gpu_temp=gtemp, load=load1)
    return True


def main():
    os.makedirs(DIR, exist_ok=True)
    state = {"warned": {}, "cpu": {}, "load_strikes": 0, "last_beat": 0.0}
    idle_since = time.time()
    log("start", pid=os.getpid(), config=cfg())
    while True:
        c = cfg()
        busy = check(c, state)
        if busy:
            idle_since = time.time()
        elif time.time() - idle_since > c["idle_exit_seconds"]:
            log("stop", reason="idle")
            return
        time.sleep(c["poll_seconds"])


if __name__ == "__main__":
    sys.exit(main())
