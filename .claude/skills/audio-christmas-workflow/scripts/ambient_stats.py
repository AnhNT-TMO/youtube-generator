import sys
import numpy as np
import soundfile as sf

x, sr = sf.read(sys.argv[1], always_2d=True)
marks = [float(v) for v in sys.argv[2].split(',')]
names = sys.argv[3].split(',')
full = np.sqrt((x ** 2).mean())
for i, n in enumerate(names):
    a, b = int(marks[i] * sr), int(marks[i + 1] * sr)
    seg = x[a:b]
    m = seg.mean(1)
    sp = np.abs(np.fft.rfft(m * np.hanning(len(m)))) ** 2
    f = np.fft.rfftfreq(len(m), 1 / sr)
    tot = sp.sum()
    print(f'{n:3s} {marks[i]:6.1f}-{marks[i+1]:6.1f}s  rms {20*np.log10(np.sqrt((seg**2).mean())/full):+5.1f}dB  '
          f'<150 {100*sp[f<150].sum()/tot:4.1f}%  150-500 {100*sp[(f>=150)&(f<500)].sum()/tot:4.1f}%  500-2k {100*sp[(f>=500)&(f<2000)].sum()/tot:4.1f}%  '
          f'>4k {100*sp[f>4000].sum()/tot:4.1f}%  centroid {(sp*f).sum()/tot:5.0f}  corr {np.corrcoef(seg[:,0],seg[:,1])[0,1]:+.2f}')
