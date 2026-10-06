import argparse
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import sys


METER_CODES = {"3/4": "3", "6/8": "6", "4/4": "4", "2/4": "2", "2/2": "2", "3/2": "3", "9/8": "3", "12/8": "4"}


def read_json(path):
    return json.loads(Path(path).read_text())


def read_spec(path):
    text = Path(path).read_text()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        try:
            import yaml
        except ImportError as error:
            raise ValueError("Install PyYAML in the server generation environment to read YAML track plans") from error
        return yaml.safe_load(text)


def file_hash(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def identity_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def save_json(path, value):
    path = Path(path)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")
    temporary.replace(path)


def positive_number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be finite and positive")
    return value


def take_matrix(config, stage):
    generation = config["generation"]
    if generation.get("backend") != "ACE-Step 1.5" or generation.get("task_type") != "cover":
        raise ValueError("This runner requires ACE-Step 1.5 cover configuration")
    if generation.get("instrumental") is not True:
        raise ValueError("This runner requires instrumental=True; intentional choir belongs in source/caption")
    seed_field = "expansion_seeds" if stage == "expansion" else "initial_seeds"
    seeds = generation[seed_field]
    if not seeds or any(isinstance(seed, bool) or not isinstance(seed, int) or seed < 0 for seed in seeds):
        raise ValueError(f"{seed_field} must contain nonnegative integer seeds")
    if len(set(seeds)) != len(seeds):
        raise ValueError(f"{seed_field} contains duplicate seeds")
    if stage == "revision":
        revision_seed = generation.get("revision_seed")
        if isinstance(revision_seed, bool) or not isinstance(revision_seed, int) or revision_seed < 0:
            raise ValueError("revision_seed must be a nonnegative integer")
        seeds = [revision_seed]
    elif stage == "expansion" and set(seeds).intersection(generation["initial_seeds"]):
        raise ValueError("Expansion seeds must differ from initial seeds")
    strengths = generation["cover_noise_strengths"]
    if not strengths or len(set(strengths)) != len(strengths):
        raise ValueError("Cover noise strengths must be nonempty and unique")
    for strength in strengths:
        positive_number(strength, "cover_noise_strength")
        if strength > 1:
            raise ValueError("Cover noise strength must be at most 1")
    if len({noise_tag(strength) for strength in strengths}) != len(strengths):
        raise ValueError("Cover noise strengths collide in output filenames")
    policy = config["batch_policy"]
    count_field = {"initial": "initial_takes", "expansion": "extra_takes", "revision": "targeted_revision_takes"}[stage]
    if len(seeds) * len(strengths) != policy[count_field]:
        raise ValueError(f"Configured {stage} matrix disagrees with {count_field}")
    return [(strength, seed) for strength in strengths for seed in seeds]


def noise_tag(strength):
    return f"{strength * 100:g}".replace(".", "p")


def checkpoint_identity(backend, config):
    expected = config["generation"].get("model_checkpoint")
    if not isinstance(expected, str) or not expected:
        raise ValueError("generation.model_checkpoint must name the exact ACE-Step checkpoint")
    actual = getattr(backend, "DIT", None)
    if actual != expected:
        raise ValueError(f"Configured checkpoint {expected!r} differs from ace_bench.DIT {actual!r}")
    checkpoint = (Path(backend.ROOT).expanduser() / "checkpoints" / actual).resolve()
    if not checkpoint.is_dir():
        raise ValueError(f"Checkpoint directory unavailable: {checkpoint}")
    files = []
    for path in sorted(checkpoint.rglob("*")):
        if not path.is_file():
            continue
        stat = path.stat()
        row = {"file": path.relative_to(checkpoint).as_posix(), "bytes": stat.st_size, "mtime_ns": stat.st_mtime_ns}
        if path.suffix in (".json", ".yaml", ".yml") and stat.st_size <= 1024 * 1024:
            row["sha256"] = file_hash(path)
        files.append(row)
    if not files:
        raise ValueError(f"Checkpoint directory is empty: {checkpoint}")
    return {"name": actual, "path": str(checkpoint), "files": files, "fingerprint": identity_hash(files),
            "fingerprint_method": "Small configuration files SHA256; weight and other files size and modification time"}


def source_request(workdir, spec_path, config, checkpoint):
    sources = sorted(workdir.glob("src_*.wav"))
    if len(sources) != 1 or list(workdir.glob("vsrc_*.wav")):
        raise ValueError("A revision directory must contain exactly one instrumental src_*.wav source")
    source = sources[0]
    metadata_path = source.with_suffix(".json")
    meta = read_json(metadata_path)
    caption = meta.get("arrangement_caption")
    if not isinstance(caption, str) or not caption.strip():
        raise ValueError("Source metadata requires an explicit arrangement_caption; no generic fallback")
    spec = read_spec(spec_path)
    styles = config.get("arrangement_contract", {}).get("styles", {})
    if styles:
        style = spec.get("style")
        if style not in styles or meta.get("style") != style:
            raise ValueError("Track plan and source metadata must identify the same configured style")
        bed_parts = config["arrangement_contract"].get("bed_parts", ["pad"])
        if not isinstance(bed_parts, list) or not bed_parts or any(
                not isinstance(part, str) or not part.strip() for part in bed_parts):
            raise ValueError("arrangement_contract.bed_parts must contain named source instruments")
        support = styles[style].get("support")
        expected_parts = ["piano", *bed_parts, *([support] if support else [])]
        if len(set(expected_parts)) != len(expected_parts):
            raise ValueError("Configured foreground, bed and support instruments must be distinct")
        instrument_count = styles[style].get("base_instrument_count",
                                             config["arrangement_contract"].get("base_instrument_count", len(expected_parts)))
        if instrument_count != len(expected_parts):
            raise ValueError("base_instrument_count disagrees with configured physical instruments")
        if spec.get("base_parts") != expected_parts or meta.get("base_parts") != expected_parts:
            raise ValueError(f"This style requires exactly these ordered base parts: {expected_parts}")
        if spec.get("accents_in_source") != 0 or meta.get("accents_in_source") != 0:
            raise ValueError("The source must exclude accent gestures; add the recorded accents after cover")
    if spec["render"]["ace_step"].get("caption") != caption:
        raise ValueError("Source arrangement_caption differs from the track-plan caption")
    if meta.get("vocal"):
        raise ValueError("Historical vocalise source mode is unsupported; use intentional choir in the instrumental source")
    bpm = positive_number(meta.get("bpm"), "Source BPM")
    if spec["meta"].get("tempo") != bpm or spec["meta"].get("key") != meta.get("key") or spec["meta"].get("meter") != meta.get("meter"):
        raise ValueError("Source BPM/key/meter must match the track-plan meta")
    meter = meta.get("meter")
    omitted_meters = config["generation"].get("omit_timesignature_hint_for_meters", [])
    if meter not in METER_CODES and meter not in omitted_meters:
        raise ValueError(f"Unsupported explicit meter: {meta.get('meter')}")
    if not isinstance(meta.get("key"), str) or not meta["key"].strip():
        raise ValueError("Source metadata requires key")
    variant = meta.get("variant")
    if not isinstance(variant, str) or not variant.isalnum() or source.name != f"src_{variant}.wav":
        raise ValueError("Source filename must match its alphanumeric metadata variant")
    generation = config["generation"]
    steps = positive_number(generation["inference_steps"], "inference_steps")
    if int(steps) != steps:
        raise ValueError("inference_steps must be an integer")
    params = {"task_type": "cover", "caption": caption, "lyrics": "[Instrumental]", "instrumental": True,
              "vocal_language": "unknown", "bpm": bpm, "keyscale": meta["key"].replace(" major", " Major").replace(" minor", " Minor"),
              "timesignature": "" if meter in omitted_meters else METER_CODES[meter], "inference_steps": int(steps),
              "guidance_scale": positive_number(generation["guidance_scale"], "guidance_scale"),
              "shift": positive_number(generation["shift"], "shift"),
              "audio_cover_strength": positive_number(generation["audio_cover_strength"], "audio_cover_strength"), "thinking": False}
    if params["audio_cover_strength"] > 1:
        raise ValueError("audio_cover_strength must be at most 1")
    identity = {"schema": 1, "source": source.name, "timesignature_hint_omitted": meter in omitted_meters,
                "source_sha256": file_hash(source),
                "source_metadata_sha256": file_hash(metadata_path), "spec_sha256": file_hash(spec_path),
                "source_settings": {"variant": variant, "bpm": bpm, "key": meta["key"], "meter": meta["meter"],
                                    "style": meta.get("style"), "base_parts": meta.get("base_parts")},
                "checkpoint": checkpoint, "params": params,
                "generation_config": {"batch_size": 1, "use_random_seed": False, "audio_format": "flac"}}
    return source, meta, identity


def prepare_requests(workdir, identity, matrix, config):
    revision_hash = identity_hash(identity)
    revision_path = workdir / "cover-revision.json"
    if revision_path.exists() and read_json(revision_path) != {"identity": identity, "identity_sha256": revision_hash}:
        raise ValueError("Source/spec/checkpoint/settings identity changed; use a fresh revision directory")
    existing = sorted(workdir.glob("cov_*.flac"))
    for output in existing:
        sidecar = output.with_suffix(".json")
        if not sidecar.exists() or read_json(sidecar).get("revision_sha256") != revision_hash:
            raise ValueError(f"Cached output identity is missing or mismatched: {output.name}; use a fresh revision directory")
        saved = read_json(sidecar)
        request = saved.get("request", {})
        if request.get("revision") != identity or saved.get("request_sha256") != identity_hash(request):
            raise ValueError(f"Cached request identity is inconsistent: {output.name}")
        if saved.get("output_sha256") != file_hash(output):
            raise ValueError(f"Cached output checksum is missing or mismatched: {output.name}")
    maximum = config["batch_policy"]["max_takes_per_unchanged_source"]
    requested = []
    for strength, seed in matrix:
        variant = Path(identity["source"]).stem.removeprefix("src_")
        output = workdir / f"cov_{variant}_n{noise_tag(strength)}_s{seed}.flac"
        request = {"revision": identity, "cover_noise_strength": strength, "seed": seed}
        metadata = {"revision_sha256": revision_hash, "request_sha256": identity_hash(request), "request": request,
                    "src": identity["source"], "variant": variant, "cns": strength, "seed": seed,
                    "caption": identity["params"]["caption"], "bpm": identity["params"]["bpm"],
                    "key": identity["source_settings"]["key"], "meter": identity["source_settings"]["meter"]}
        sidecar = output.with_suffix(".json")
        if output.exists():
            saved = read_json(sidecar)
            saved.pop("output_sha256", None)
            if output.stat().st_size == 0 or saved != metadata:
                raise ValueError(f"Cached output request differs: {output.name}; use a fresh revision directory")
        elif sidecar.exists():
            raise ValueError(f"Orphan request metadata found: {sidecar.name}; inspect the interrupted revision")
        else:
            requested.append((output, metadata))
    if len(existing) + len(requested) > maximum:
        raise ValueError(f"Unchanged source revision would exceed {maximum} takes")
    return requested


def require_server_guard():
    cgroup = Path("/proc/self/cgroup")
    if sys.platform != "linux" or not cgroup.exists() or "youtube.slice" not in cgroup.read_text():
        raise ValueError("Run heavy cover generation on the GPU server through pm-production server_guard/guard.sh run")


def main(args):
    workdir = Path(args.workdir).expanduser().resolve()
    spec_path = Path(args.spec).expanduser().resolve() if args.spec else workdir / "track-plan.json"
    config = read_json(args.config)
    if config.get("production_hold"):
        raise ValueError("Production is held in this config; read the current handoff before generating")
    matrix = take_matrix(config, args.stage)
    require_server_guard()
    sys.path.insert(0, os.path.expanduser("~/ace-step"))
    import ace_bench
    from prompt_lab import wait_cool
    from acestep.inference import GenerationConfig, GenerationParams, generate_music

    checkpoint = checkpoint_identity(ace_bench, config)
    source, meta, identity = source_request(workdir, spec_path, config, checkpoint)
    requests = prepare_requests(workdir, identity, matrix, config)
    save_json(workdir / "cover-revision.json", {"identity": identity, "identity_sha256": identity_hash(identity)})
    print(json.dumps({"stage": args.stage, "requested_matrix": matrix, "checkpoint": checkpoint["name"],
                      "cached": len(matrix) - len(requests), "new": len(requests)}), flush=True)
    if not requests:
        return 0
    os.chdir(ace_bench.ROOT)
    failures = []
    with Path("/tmp/carol_gpu.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            wait_cool(70)
            with ace_bench.Probe(f"carol_{workdir.name}") as probe:
                dit = ace_bench.load_dit(probe)
                if checkpoint_identity(ace_bench, config) != checkpoint:
                    raise ValueError("Checkpoint identity changed during model loading; restart in a fresh revision directory")
                for output, metadata in requests:
                    wait_cool(70)
                    params = GenerationParams(src_audio=str(source), **identity["params"],
                                              cover_noise_strength=metadata["cns"], seed=metadata["seed"])
                    generation = GenerationConfig(**identity["generation_config"], seeds=[metadata["seed"]])
                    temporary = output.with_name(output.name + ".d")
                    if temporary.exists():
                        raise ValueError(f"Interrupted generation directory exists: {temporary}; inspect before resuming")
                    temporary.mkdir()
                    with probe.stage(output.name) as record:
                        result = generate_music(dit, None, params, generation, save_dir=str(temporary))
                        record["ok"] = result.success
                    if not result.success:
                        failures.append(output.name)
                        print("FAILED", output.name, result.error or result.status_message, flush=True)
                        continue
                    shutil.move(result.audios[0]["path"], output)
                    metadata["output_sha256"] = file_hash(output)
                    save_json(output.with_suffix(".json"), metadata)
                    shutil.rmtree(temporary)
                    print("OK", output.name, flush=True)
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)
    return 1 if failures else 0


def parser():
    argument_parser = argparse.ArgumentParser(description="Generate one source revision through the guarded GPU-server ACE-Step service")
    argument_parser.add_argument("workdir")
    argument_parser.add_argument("--config", required=True)
    argument_parser.add_argument("--spec", help="Track plan path; defaults to workdir/track-plan.json")
    argument_parser.add_argument("--stage", choices=("initial", "expansion", "revision"), default="initial")
    return argument_parser


if __name__ == "__main__":
    try:
        raise SystemExit(main(parser().parse_args()))
    except (ValueError, KeyError, OSError, json.JSONDecodeError) as error:
        print(f"COVER_CONFIGURATION_ERROR: {error}", file=sys.stderr)
        raise SystemExit(2)
