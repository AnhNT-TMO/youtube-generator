#!/usr/bin/env python3
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import cv2
import numpy as np

WIDTH = 312
REFERENCE_SECOND = 1


def second_frames(clip):
    probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate",
                            "-of", "csv=p=0", str(clip)], capture_output=True, text=True, check=True).stdout.strip()
    numerator, _, denominator = probe.partition("/")
    fps = round(float(numerator) / float(denominator or 1))
    with tempfile.TemporaryDirectory() as folder:
        subprocess.run(["ffmpeg", "-v", "error", "-i", str(clip), "-vf", f"select='not(mod(n,{fps}))',scale={WIDTH}:-2",
                        "-fps_mode", "passthrough", f"{folder}/%03d.png"], check=True)
        return [cv2.imread(str(path), cv2.IMREAD_GRAYSCALE) for path in sorted(Path(folder).glob("*.png"))]


def corner_shift(orb, reference, frame):
    keys_a, desc_a = orb.detectAndCompute(reference, None)
    keys_b, desc_b = orb.detectAndCompute(frame, None)
    if desc_a is None or desc_b is None or len(keys_a) < 10 or len(keys_b) < 10:
        return None
    matches = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True).match(desc_a, desc_b)
    if len(matches) < 10:
        return None
    points_a = np.float32([keys_a[match.queryIdx].pt for match in matches])
    points_b = np.float32([keys_b[match.trainIdx].pt for match in matches])
    transform, _ = cv2.estimateAffinePartial2D(points_a, points_b, method=cv2.RANSAC, ransacReprojThreshold=2.0)
    if transform is None:
        return None
    height, width = reference.shape
    corners = np.float32([[0, 0], [width, 0], [0, height], [width, height]])
    moved = corners @ transform[:, :2].T + transform[:, 2]
    scale = float(np.hypot(transform[0, 0], transform[1, 0]))
    return float(np.max(np.linalg.norm(moved - corners, axis=1)) / width), scale


def measure(clip):
    frames = second_frames(clip)
    if len(frames) <= REFERENCE_SECOND + 1:
        return {"camera_shift": None, "per_second": [], "scale": None}
    orb = cv2.ORB_create(1500)
    reference = frames[REFERENCE_SECOND]
    results = [corner_shift(orb, reference, frame) for frame in frames[REFERENCE_SECOND + 1:]]
    shifts = [round(result[0], 3) if result else None for result in results]
    scales = [result[1] for result in results if result]
    known = [shift for shift in shifts if shift is not None]
    return {"camera_shift": max(known) if known else None, "per_second": shifts,
            "scale": round(max(scales, key=lambda value: abs(np.log(value))), 3) if scales else None}


if __name__ == "__main__":
    print(json.dumps(measure(sys.argv[1])))
