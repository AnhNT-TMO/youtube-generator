import subprocess

import numpy as np
from scipy.signal import stft

PITCH_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
MAJOR = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
MINOR = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])


def decode(path, rate=16000, channels=1, cutoff=None):
    command = ['ffmpeg', '-nostdin', '-v', 'error', '-i', str(path)]
    if cutoff:
        command += ['-af', f'lowpass=f={cutoff}:p=2']
    raw = subprocess.run(command + ['-f', 'f32le', '-ar', str(rate), '-ac', str(channels), '-'], capture_output=True, check=True).stdout
    data = np.frombuffer(raw, dtype='<f4')
    return data.reshape(-1, channels) if channels > 1 else data


def chroma(samples):
    frequency, times, spectrum = stft(samples, 16000, nperseg=2048, noverlap=448)
    power = np.abs(spectrum) ** 2
    keep = (frequency > 150) & (frequency < 1800)
    pitch_class = np.round(69 + 12 * np.log2(frequency[keep] / 440)).astype(int) % 12
    result = np.zeros((12, len(times)))
    for pitch in range(12):
        result[pitch] = power[keep][pitch_class == pitch].sum(axis=0)
    return times, result / (np.linalg.norm(result, axis=0, keepdims=True) + 1e-12)


def key_chroma(samples):
    frequency, times, spectrum = stft(samples, 16000, nperseg=8192, noverlap=8192 - 1600)
    magnitude = np.abs(spectrum)
    keep = (frequency >= 60) & (frequency <= 2100)
    pitch_class = np.round(69 + 12 * np.log2(frequency[keep] / 440)).astype(int) % 12
    result = np.zeros((12, len(times)))
    for pitch in range(12):
        result[pitch] = magnitude[keep][pitch_class == pitch].sum(axis=0)
    return times, result


def estimate_key(profile):
    scores = []
    for tonic in range(12):
        for mode, template in [('major', MAJOR), ('minor', MINOR)]:
            scores.append((float(np.corrcoef(profile, np.roll(template, tonic))[0, 1]), f'{PITCH_NAMES[tonic]} {mode}'))
    scores.sort(reverse=True)
    return scores


def align(source_path, cover_path):
    source_times, source = chroma(decode(source_path))
    cover_times, cover = chroma(decode(cover_path))
    count, target_count = source.shape[1], cover.shape[1]
    cost = np.full((count, target_count), np.inf)
    parent = np.zeros((count, target_count), dtype=np.int8)
    similarity = source.T @ cover
    for source_index in range(count):
        for target_index in range(max(0, source_index - 20), min(target_count, source_index + 21)):
            if source_index == 0 and target_index == 0:
                cost[0, 0] = 1 - similarity[0, 0]
                continue
            previous = [cost[source_index - 1, target_index - 1] if source_index and target_index else np.inf, cost[source_index - 1, target_index] if source_index else np.inf, cost[source_index, target_index - 1] if target_index else np.inf]
            direction = int(np.argmin(previous))
            cost[source_index, target_index] = previous[direction] + 1 - similarity[source_index, target_index]
            parent[source_index, target_index] = direction
    assert np.isfinite(cost[-1, -1]), 'Actual-cover alignment unresolved'
    source_index, target_index = count - 1, target_count - 1
    path = [(source_index, target_index)]
    while source_index or target_index:
        direction = parent[source_index, target_index]
        source_index -= direction != 2
        target_index -= direction != 1
        path.append((source_index, target_index))
    path.reverse()

    def map_time(seconds):
        index = int(np.argmin(np.abs(source_times - seconds)))
        return float(np.median([cover_times[target] for s, target in path if s == index]))

    mean_cosine = float(np.mean([similarity[s, t] for s, t in path]))
    return map_time, mean_cosine, (cover_times, cover)
