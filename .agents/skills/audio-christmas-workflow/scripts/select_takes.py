import argparse
import json
import math
import sys
from pathlib import Path


def number(data, key):
    value = data.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"Missing numeric measurement: {key}")
    if not math.isfinite(value):
        raise ValueError(f"Nonfinite measurement: {key}")
    return value


def json_safe(value):
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    if isinstance(value, dict):
        return {key: json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    return value


def choir_policy(config, song, arrangement):
    if song is None and arrangement is None:
        return None
    if not song or not arrangement:
        raise ValueError("Song and arrangement must be supplied together")
    exception = config.get("song_exceptions", {}).get(song, {})
    if arrangement not in exception.get("requested_arrangements", []):
        raise ValueError(f"Unconfigured arrangement exception: {song}: {arrangement}")
    if "choir" not in arrangement.lower():
        return None
    if not exception.get("choir_pad"):
        raise ValueError(f"Intentional choir is not authorized for {song}")
    verification = exception.get("verification_policy", {})
    return {
        "song": song,
        "arrangement": arrangement,
        "choir_background_max_db": number(verification, "choir_background_max_db"),
        "choir_vs_source_max_db": number(verification, "choir_vs_source_max_db"),
    }


def select(config, evaluation, vocal_rows, source_name, song=None, arrangement=None):
    policy = config["selection"]
    policy_keys = (
        "source_similarity_min", "ce_min", "vocal_share_max",
        "reference_copy_max_exclusive", "buzz_median_floor_db",
        "buzz_median_allowance_db", "buzz_max_floor_db", "buzz_max_ceiling_db",
        "buzz_max_allowance_db", "opening_excess_vs_source_max_db",
        "source_similarity_weight", "ce_weight", "ce_center", "duration_tolerance_s",
    )
    limits = {key: number(policy, key) for key in policy_keys}
    intentional_choir = choir_policy(config, song, arrangement)
    source = evaluation.get(source_name, {})
    vocals = {Path(row["file"]).name: row for row in vocal_rows}
    rows = []
    for name, metrics in evaluation.items():
        if not name.startswith("cov_"):
            continue
        row = {"name": name, "metrics": json_safe(metrics), "fails": [], "score": None}
        try:
            similarity = number(metrics, "melody_copy")
            ce = number(metrics, "CE")
            voice_metrics = vocals.get(name, {})
            if intentional_choir:
                vocal_level = number(voice_metrics, "vocal_to_mix_db")
                source_vocal_level = number(vocals.get(source_name, {}), "vocal_to_mix_db")
                vocal_delta = vocal_level - source_vocal_level
                row["choir_review"] = {
                    "vocal_to_mix_db": vocal_level,
                    "source_vocal_to_mix_db": source_vocal_level,
                    "vocal_level_vs_source_db": round(vocal_delta, 4),
                }
            else:
                vocal = number(voice_metrics, "prominent_vocal_share")
            copy_similarity = number(metrics, "copy_max_sim")
            median = number(metrics, "buzz_median_db")
            peak = number(metrics, "buzz_max_db")
            source_median = number(source, "buzz_median_db")
            source_peak = number(source, "buzz_max_db")
            cover_opening = number(metrics, "hf_start_excess_db")
            source_opening = number(source, "hf_start_excess_db")
            opening = cover_opening - source_opening
            opening_growth = max(0.0, cover_opening) - max(0.0, source_opening)
            duration = number(metrics, "seconds")
            source_duration = number(source, "seconds")
        except ValueError as error:
            row["fails"].append(str(error))
            row["measurement_review"] = True
            rows.append(row)
            continue
        median_cap = max(limits["buzz_median_floor_db"], source_median + limits["buzz_median_allowance_db"])
        peak_cap = min(limits["buzz_max_ceiling_db"], max(limits["buzz_max_floor_db"], source_peak + limits["buzz_max_allowance_db"]))
        checks = (
            (similarity < limits["source_similarity_min"], "source feature similarity"),
            (ce < limits["ce_min"], "CE"),
            (copy_similarity >= limits["reference_copy_max_exclusive"], "reference recording similarity"),
            (median > median_cap or peak > peak_cap, "source-relative harshness"),
            (opening_growth > limits["opening_excess_vs_source_max_db"], "opening HF relative to own source"),
            (duration <= 0 or source_duration <= 0 or abs(duration - source_duration) > limits["duration_tolerance_s"], "duration relative to source"),
        )
        row["fails"].extend(label for failed, label in checks if failed)
        if intentional_choir:
            if vocal_level > intentional_choir["choir_background_max_db"]:
                row["fails"].append("intentional choir too foreground")
            if vocal_delta > intentional_choir["choir_vs_source_max_db"]:
                row["fails"].append("intentional choir level relative to source")
        elif vocal > limits["vocal_share_max"]:
            row["fails"].append("unintended vocal proxy")
        row["measurement_review"] = False
        row["opening_hf_vs_source_db"] = round(opening, 4)
        row["opening_hf_positive_growth_db"] = round(opening_growth, 4)
        row["score"] = round(limits["source_similarity_weight"] * similarity + limits["ce_weight"] * (ce - limits["ce_center"]), 8)
        rows.append(row)
    rows.sort(key=lambda row: (bool(row["fails"]), -(row["score"] if row["score"] is not None else -math.inf), row["name"]))
    passed = [row["name"] for row in rows if not row["fails"]]
    retained = passed[:2]
    result = {
        "status": "ready_for_listening" if retained else "technical_review_needed",
        "picks_instr": retained[:1],
        "picks_vocal": [],
        "backups": retained[1:2],
        "retained_takes": retained,
        "other_passing_takes": passed[2:],
        "passing_count": len(passed),
        "backup_available": len(retained) == 2,
        "needs_measurement_review": any(row["measurement_review"] for row in rows),
        "rows": rows,
        "listener_review_pending": True,
        "release_accepted": False,
        "opening_hf_rule": "max(0, cover signed excess) - max(0, source signed excess); signed excess is first-five-second HF peak minus whole-track active HF P95",
        "caveat": "Technical shortlist only. Source feature similarity is not note transcription; scores do not establish Christmas character, natural timbre or listener preference.",
    }
    if intentional_choir:
        result["choir_exception"] = {
            **intentional_choir,
            "global_no_vocal_policy_changed": False,
            "wordlessness_verified": False,
            "natural_timbre_verified": False,
            "caveat": "Source-relative separator levels only; these checks do not detect words, natural choir timbre or exact instrument retention.",
        }
    return result


def main():
    parser = argparse.ArgumentParser(description="Select one technical primary and one backup from instrumental cover evaluations.")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--eval-a", type=Path, required=True)
    parser.add_argument("--eval-b", type=Path, required=True)
    parser.add_argument("--source", default="src_A.wav")
    parser.add_argument("--song", help="Song slug for an explicitly configured arrangement exception")
    parser.add_argument("--arrangement", help="Exact requested arrangement name from the song exception")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        config = json.loads(args.config.read_text())
        evaluation = json.loads(args.eval_a.read_text())
        vocal_rows = json.loads(args.eval_b.read_text())
        result = select(config, evaluation, vocal_rows, args.source, args.song, args.arrangement)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        print(f"Selection inputs need review: {error}", file=sys.stderr)
        return 2
    print(json.dumps({key: result[key] for key in ("status", "picks_instr", "backups", "passing_count", "needs_measurement_review")}, indent=2))
    return 0 if result["picks_instr"] else 2


if __name__ == "__main__":
    sys.exit(main())
