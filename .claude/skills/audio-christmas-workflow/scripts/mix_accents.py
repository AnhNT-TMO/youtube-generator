#!/usr/bin/env python3
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def require(condition, message):
    if not condition:
        raise ValueError(message)


def number(value, name):
    require(isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value), f"{name} must be finite numeric data")
    return float(value)


def nonempty(value, name):
    require(isinstance(value, str) and bool(value.strip()), f"Missing {name}")


def file_record(record, root, name):
    nonempty(record.get("path"), f"{name}.path")
    path = (root / record["path"]).resolve()
    require(path.is_file(), f"Missing {name}: {path}")
    digest = record.get("sha256", "")
    require(isinstance(digest, str) and len(digest) == 64
            and all(c in "0123456789abcdef" for c in digest), f"Invalid {name}.sha256")
    return path


def validate_base_gesture_review(plan):
    verified = plan.get("base_has_no_accent_gestures")
    review = plan.get("base_gesture_review", {})
    require(verified is not False and review.get("status") != "known_extra",
            "Known extra base gestures require a different base or source revision")
    if verified is True:
        return "confirmed_no_extra"
    require(plan.get("audition_only") is True and verified is None
            and review.get("status") == "unverified",
            "Unverified base gestures require an explicit audition-only pending review")
    nonempty(review.get("evidence"), "base_gesture_review.evidence")
    return "unverified"


def validate(plan, config, root, output):
    contract = config["arrangement_contract"]
    policy = contract["accents"]
    count = policy["count"]
    require(isinstance(count, int) and 1 <= count <= 2 and policy["processing"] == "post_cover",
            "Config must authorize one or two post_cover accents")
    fractions = [number(f, "target fraction") for f in policy["target_fractions"]]
    require(len(fractions) == count and all(0 < f < 1 for f in fractions)
            and fractions == sorted(fractions), "target_fractions must match count, ascending inside (0, 1)")
    tolerance = number(policy["max_shift_fraction"], "max_shift_fraction")
    require(0 <= tolerance < 1 / 6, "Invalid phrase-boundary tolerance")
    style = contract["styles"][plan["style"]]
    require(len(style["accents"]) == count, "Style accent gestures must match the configured count")
    base = file_record(plan["base"], root, "base")
    end = number(plan["musical_end_s"], "musical_end_s")
    require(end > 0, "musical_end_s must exclude the final reverb tail")
    nonempty(plan.get("musical_end_evidence"), "musical_end_evidence")
    validate_base_gesture_review(plan)
    require(len(plan["accents"]) == count, "Plan accent count differs from config")
    low, high = [number(v, "relative_db_range") for v in policy["relative_db_range"]]
    require(-36 <= low <= high <= -10, "Quiet accent range must stay at or below -10 dB")
    transient_relative_db = number(policy.get("transient_peak_relative_db", -6), "transient_peak_relative_db")
    require(-18 <= transient_relative_db <= 3, "Transient peak cap must stay between -18 and +3 dB re local RMS")
    normalized = []
    for index, accent in enumerate(plan["accents"]):
        require(accent["gesture"] == style["accents"][index], "Accent order differs from style")
        time = number(accent["onset_s"], "onset_s")
        require(0 < time < end and abs(time / end - fractions[index]) <= tolerance,
                f"Accent {index + 1} is outside the permitted phrase-boundary window")
        boundary = accent["phrase_boundary"]
        require(boundary.get("timeline") == "actual_cover", "Boundary must refer to actual cover")
        require(boundary.get("base_sha256") == plan["base"]["sha256"], "Boundary base hash mismatch")
        nonempty(boundary.get("method"), "phrase_boundary.method")
        nonempty(boundary.get("evidence"), "phrase_boundary.evidence")
        require(abs(number(boundary["time_s"], "boundary time") - time) <= 0.05,
                "Onset must coincide with the documented actual-cover phrase boundary")
        sample = accent["sample"]
        sample_path = file_record(sample, root, f"accent {index + 1} sample")
        require(sample.get("real_recording") is True, "Use a real recorded gesture, not synthesis")
        require(sample.get("gesture") == accent["gesture"], "Sample gesture mismatch")
        for field in ["source", "recordist", "license", "license_evidence", "recording_evidence"]:
            nonempty(sample.get(field), f"sample.{field}")
        require(sample.get("production_use_authorized") is True, "Sample production use must be authorized")
        compatibility = accent["tonal_compatibility"]
        nonempty(compatibility.get("evidence"), "tonal_compatibility.evidence")
        if accent["gesture"] != "bar_chime_sweep":
            require(compatibility.get("verified") is True, "Pitched gesture needs known tonal compatibility")
            for field in ["sample_notes", "cover_key", "boundary_harmony"]:
                nonempty(compatibility.get(field), f"tonal_compatibility.{field}")
        else:
            require(compatibility.get("non_tonal") is True, "Bar sweep must be verified as non-tonal")
        level = number(accent.get("relative_db", policy["initial_relative_db"]), "relative_db")
        require(low <= level <= high, "Accent gain is outside configured quiet range")
        trim = number(sample.get("trim_start_s", 0), "trim_start_s")
        require(trim >= 0, "trim_start_s must be nonnegative")
        cutoff = sample.get("lowpass_hz")
        if cutoff is not None:
            require(2500 <= number(cutoff, "lowpass_hz") <= 8000, "Use only a gentle sample lowpass")
        normalized.append((accent, sample_path, time, level, trim, cutoff))
    require(all(a[2] < b[2] for a, b in zip(normalized, normalized[1:])), "Accents must be in temporal order")
    require(output.resolve() not in [base] + [row[1] for row in normalized], "Never overwrite source assets")
    require(not output.exists() and not Path(str(output) + ".json").exists(), "Output already exists")
    return base, end, normalized


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def require_guard():
    cgroup = Path("/proc/self/cgroup")
    require(sys.platform == "linux" and cgroup.exists() and "youtube.slice" in cgroup.read_text(),
            "Run audio processing on GPU server through pm-production server_guard/guard.sh run")


def decode(path, destination, cutoff=None):
    command = ["ffmpeg", "-nostdin", "-v", "error", "-i", str(path), "-ar", "48000", "-ac", "2"]
    if cutoff is not None:
        command += ["-af", f"lowpass=f={cutoff}:p=2"]
    subprocess.run(command + ["-c:a", "pcm_f32le", "-y", str(destination)], check=True)


def render(plan, config, config_path, plan_path, output, validated):
    require_guard()
    import numpy as np
    import soundfile as sf

    base_path, musical_end, accents = validated
    require(sha256(base_path) == plan["base"]["sha256"], "Base audio checksum changed")
    output.parent.mkdir(parents=True, exist_ok=True)
    manifest = {"schema": "real-accents-v1", "config_sha256": sha256(config_path),
                "plan_sha256": sha256(plan_path), "plan": plan, "accents": [],
                "status": "needs_listening_review", "sample_rate": 48000,
                "processing": "fixed sample gain; unchanged base; no ducking or limiting"}
    manifest.update({"base_gesture_review_status": validate_base_gesture_review(plan),
                     "total_base_gesture_count_verified": plan.get("base_has_no_accent_gestures") is True,
                     "inserted_event_count": len(accents), "release_approved": False,
                     "audition_only": plan.get("audition_only", False)})
    with tempfile.TemporaryDirectory(prefix="accent-mix-", dir=output.parent) as work:
        work = Path(work)
        decode(base_path, work / "base.wav")
        base, rate = sf.read(work / "base.wav", dtype="float64", always_2d=True)
        require(np.isfinite(base).all(), "Base contains nonfinite audio")
        duration = len(base) / rate
        require(musical_end <= duration, "musical_end_s exceeds actual base duration")
        require(float(np.max(np.abs(base))) <= 0.98, "Base lacks the required conservative mixing headroom")
        mix = base.copy()
        previous_tail = 0
        for index, (accent, path, time, relative_db, trim, cutoff) in enumerate(accents):
            require(sha256(path) == accent["sample"]["sha256"], "Sample checksum changed")
            decode(path, work / f"sample-{index}.wav", cutoff)
            sample, _ = sf.read(work / f"sample-{index}.wav", dtype="float64", always_2d=True)
            require(np.isfinite(sample).all(), "Sample contains nonfinite audio")
            trim_frames = round(trim * rate)
            original_peak = float(np.max(np.abs(sample)))
            require(trim_frames < len(sample) and (trim_frames == 0 or
                    float(np.max(np.abs(sample[:trim_frames]))) <= original_peak * 0.0032),
                    "trim_start_s may only remove leading silence, never an attack")
            sample = sample[trim_frames:]
            require(len(sample) > rate * 0.1, "Sample must retain a complete gesture and natural tail")
            peak = float(np.max(np.abs(sample)))
            require(peak > 1e-6, "Sample is silent")
            active = np.flatnonzero(np.max(np.abs(sample), axis=1) > peak * 0.001)
            require(len(active) > 0, "Sample has no active gesture")
            sample = sample[max(0, int(active[0]) - round(0.01 * rate)):]
            ending = sample[-round(0.02 * rate):]
            require(float(np.max(np.abs(ending))) <= peak * 0.0032,
                    "Sample file cuts off a decay; supply the complete natural tail")
            last = np.flatnonzero(np.max(np.abs(sample), axis=1) > peak * 0.001)[-1]
            sample = sample[:min(len(sample), int(last) + round(0.08 * rate))]
            fade = min(round(0.008 * rate), len(sample) // 4)
            sample[:fade] *= np.linspace(0, 1, fade)[:, None]
            fade_out = min(round(0.05 * rate), len(sample) // 4)
            sample[-fade_out:] *= np.linspace(1, 0, fade_out)[:, None]
            onset = round(time * rate)
            tail = onset + len(sample)
            require(onset >= previous_tail and tail <= len(base), "Accent tails overlap or exceed the base duration")
            previous_tail = tail
            window = base[max(0, onset - 4 * rate):min(len(base), onset + 4 * rate)]
            frame_rms = [float(np.sqrt(np.mean(frame ** 2))) for frame in
                         np.array_split(window, max(1, len(window) // round(0.1 * rate))) if len(frame)]
            non_silent = [v for v in frame_rms if v > max(frame_rms) * 0.1 and v > 1e-5]
            require(len(non_silent) >= 10, "Phrase boundary lacks a stable nonsilent local level reference")
            reference = float(np.median(non_silent))
            active_sample = sample[np.max(np.abs(sample), axis=1) > peak * 0.1]
            rms = float(np.sqrt(np.mean(active_sample ** 2)))
            sample_peak = float(np.max(np.abs(sample)))
            target_gain = reference * 10 ** (relative_db / 20) / rms
            transient_relative_db = config["arrangement_contract"]["accents"].get("transient_peak_relative_db", -6)
            transient_ceiling = reference * 10 ** (transient_relative_db / 20)
            headroom = max(0, 0.98 - float(np.max(np.abs(base[onset:tail]))))
            gain_limits = {"requested_level": target_gain, "transient_peak": transient_ceiling / sample_peak,
                           "headroom": headroom / sample_peak}
            limiting_reason = min(gain_limits, key=gain_limits.get)
            gain = gain_limits[limiting_reason]
            require(gain > 0, "Base has no headroom for this accent")
            spectrum = (np.abs(np.fft.rfft(sample, axis=0)) ** 2).sum(axis=1)
            frequencies = np.fft.rfftfreq(len(sample), 1 / rate)
            hf_ratio = float(spectrum[frequencies >= 5000].sum() / max(float(spectrum.sum()), 1e-20))
            require(hf_ratio <= 0.30, "Gesture is too bright for provisional gate; review or gently filter sample")
            mix[onset:tail] += sample * gain
            manifest["accents"].append({"gesture": accent["gesture"], "onset_s": onset / rate,
                "tail_end_s": tail / rate, "sample_sha256": sha256(path), "gain": gain,
                "requested_relative_db": relative_db, "actual_relative_db": 20 * math.log10(gain * rms / reference),
                "local_reference_rms": reference, "hf_power_ratio_above_5khz": hf_ratio,
                "transient_ceiling": transient_ceiling, "transient_peak_relative_db": transient_relative_db,
                "sample_crest_factor_db": 20 * math.log10(sample_peak / rms),
                "gain_limited_by": limiting_reason, "lowpass_hz": cutoff})
        require(np.isfinite(mix).all() and float(np.max(np.abs(mix))) <= 0.980001,
                "Mixed output exceeds conservative sample-peak ceiling")
        candidate = work / "finished.wav"
        sf.write(candidate, mix, rate, subtype="PCM_24")
        manifest.update({"duration_s": duration, "frames": len(base), "output_sha256": sha256(candidate),
                         "output": str(output.resolve()), "output_subtype": "PCM_24"})
        manifest_candidate = work / "manifest.json"
        manifest_candidate.write_text(json.dumps(manifest, ensure_ascii=True, indent=2) + "\n")
        os.link(candidate, output)
        os.link(manifest_candidate, Path(str(output) + ".json"))
    return manifest


def main():
    parser = argparse.ArgumentParser(description="Add the configured documented quiet real-recorded accents on the guarded server")
    parser.add_argument("plan", type=Path)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--validate-only", action="store_true", help="Inspect plan/config/files without decoding or hashing media")
    args = parser.parse_args()
    try:
        plan = json.loads(args.plan.read_text())
        config = json.loads(args.config.read_text())
        validated = validate(plan, config, args.plan.resolve().parent, args.output)
        if args.validate_only:
            print(json.dumps({"status": "plan_valid", "media_not_verified": True, "accents": len(validated[2])}))
        else:
            result = render(plan, config, args.config, args.plan, args.output, validated)
            print(json.dumps({"status": result["status"], "output": result["output"]}))
    except (ValueError, KeyError, TypeError, AttributeError, IndexError, OSError, RuntimeError,
            subprocess.CalledProcessError) as error:
        parser.exit(2, f"Accent mix rejected: {error}\n")


if __name__ == "__main__":
    main()
