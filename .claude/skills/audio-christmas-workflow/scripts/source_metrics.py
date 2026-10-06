import hashlib
import json
from pathlib import Path
import shutil
import sys

import numpy as np
from scipy.signal import lfilter
import soundfile as sf


def digest(path):
    result = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            result.update(chunk)
    return result.hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def db(value):
    return float(20 * np.log10(max(float(value), 1e-12)))


def measure(samples, mask=None):
    selected = samples[mask] if mask is not None else samples
    return {'rms_dbfs': db(np.sqrt(np.mean(selected ** 2))), 'sample_peak_dbfs': db(np.abs(selected).max())}


def mask_for(notes, length, rate, beat_s):
    mask = np.zeros(length, dtype=bool)
    for note in notes:
        start = round(note['beat'] * beat_s * rate)
        end = round((note['beat'] + note['duration']) * beat_s * rate)
        mask[start:end] = True
    return mask


def spectrum(samples, notes, rate, beat_s):
    totals = {'low_mid_200_800': 0.0, 'core_800_5000': 0.0, 'upper_3000_8000': 0.0, 'total_200_8000': 0.0}
    for note in notes:
        start = round(note['beat'] * beat_s * rate)
        end = round((note['beat'] + note['duration']) * beat_s * rate)
        segment = samples[start:end]
        power = (np.abs(np.fft.rfft(segment * np.hanning(len(segment))[:, None], axis=0)) ** 2).sum(axis=1)
        frequencies = np.fft.rfftfreq(len(segment), 1 / rate)
        for name, lower, upper in [('low_mid_200_800', 200, 800), ('core_800_5000', 800, 5000), ('upper_3000_8000', 3000, 8000), ('total_200_8000', 200, 8000)]:
            totals[name] += float(power[(frequencies >= lower) & (frequencies < upper)].sum()) / len(segment)
    total = max(totals['total_200_8000'], 1e-30)
    return {'method': 'Hann-windowed stereo power accumulated over exact support note intervals; source only, not AI stems', 'bands': totals, 'low_mid_fraction': totals['low_mid_200_800'] / total, 'upper_fraction': totals['upper_3000_8000'] / total}


def biquad(samples, kind, frequency, gain_db, rate, quality=0.7):
    amplitude = 10 ** (gain_db / 40)
    omega = 2 * np.pi * frequency / rate
    cosine = np.cos(omega)
    if kind == 'high_shelf':
        alpha = np.sin(omega) / 2 * np.sqrt(2)
        beta = 2 * np.sqrt(amplitude) * alpha
        numerator = amplitude * np.array([(amplitude + 1) + (amplitude - 1) * cosine + beta, -2 * ((amplitude - 1) + (amplitude + 1) * cosine), (amplitude + 1) + (amplitude - 1) * cosine - beta])
        denominator = np.array([(amplitude + 1) - (amplitude - 1) * cosine + beta, 2 * ((amplitude - 1) - (amplitude + 1) * cosine), (amplitude + 1) - (amplitude - 1) * cosine - beta])
    else:
        alpha = np.sin(omega) / (2 * quality)
        numerator = np.array([1 + alpha * amplitude, -2 * cosine, 1 - alpha * amplitude])
        denominator = np.array([1 + alpha / amplitude, -2 * cosine, 1 - alpha / amplitude])
    coefficients = {'kind': kind, 'frequency_hz': frequency, 'gain_db': gain_db, 'Q': quality if kind == 'bell' else None, 'shelf_slope': 1 if kind == 'high_shelf' else None, 'b': (numerator / denominator[0]).tolist(), 'a': (denominator / denominator[0]).tolist()}
    return lfilter(numerator / denominator[0], denominator / denominator[0], samples, axis=0), coefficients
