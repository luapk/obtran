"""Paul's music, made into loops for the page.

  python3 tools/make_music.py

Paul sent smokehouse_shift.mp3 on 25 October (25.9 s of QNTM CTRL's Smokehouse Shift, 44.1 kHz,
320 kbps; kept in source/music/, outside git): "loop this music to play, starting at the same time as
the first VO, fade at end with slight reverb to ensure seamless loop". The excerpt opens on a hit that
decays and ends at full level, mid build, so as it stands the loop would cut dead at the seam. Here
the last FADE seconds fade out, a slight reverb (a synthetic decaying stereo tail, TAIL seconds, mixed
at WET) is laid over the end, and the part of the reverb that rings past the end is folded back onto
the start, so it rings on under the opening hit as the loop comes round. The loop keeps the excerpt's
length, so it holds its tempo, and plays with no seam. Writes prototype/assets/music/<name>.loop.mp3.
"""
import subprocess
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "source" / "music"
OUT = ROOT / "prototype" / "assets" / "music"
SR = 44100
LOOPS = {"smokehouse-shift": "smokehouse_shift.mp3"}   # track id (assets/music/index.json): source file
FADE = 2.5        # the end fades out over this long
TAIL = 3.0        # the reverb's length
WET = 0.28        # how much reverb
VERB_IN = 5.0     # the reverb hears this much of the end


def reverb_ir(n, rng):
    # a decaying noise tail per channel (decorrelated, so it opens out in stereo), darker as it decays
    t = np.arange(n) / SR
    ir = rng.standard_normal((n, 2)) * np.exp(-t * 6.9 / TAIL)[:, None]     # -60 dB at TAIL
    k = 1
    for i in range(0, n, 2048):
        k = 1 + 6 * i / n                                                    # a moving average that widens: highs fade first
        seg = ir[i:i + 2048]
        ir[i:i + 2048] = np.apply_along_axis(lambda c: np.convolve(c, np.ones(int(k)) / int(k), "same"), 0, seg)
    ir[: int(0.02 * SR)] = 0                                                 # a short pre-delay
    return ir / np.sqrt((ir ** 2).sum(axis=0))


def make(track, src):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(SRC / src), "-ar", str(SR), "-ac", "2", "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    x = np.frombuffer(raw, np.float32).reshape(-1, 2).astype(np.float64)
    n = len(x)
    # the reverb on the end, before the fade, so it carries the full level and then rings away
    v0 = n - int(VERB_IN * SR)
    ir = reverb_ir(int(TAIL * SR), np.random.default_rng(3))
    wet = np.stack([np.convolve(x[v0:, c], ir[:, c]) for c in range(2)], axis=1) * WET
    wet[: int(VERB_IN * SR)] *= np.linspace(0, 1, int(VERB_IN * SR))[:, None] ** 2   # comes up into the end
    y = x.copy()
    f = int(FADE * SR)
    y[n - f:] *= np.cos(np.linspace(0, np.pi / 2, f))[:, None]               # equal power fade out
    y[v0:] += wet[: n - v0]
    rest = wet[n - v0:]                                                      # rings past the end: fold onto the start
    y[: len(rest)] += rest
    peak = np.abs(y).max()
    if peak > 0.98: y *= 0.98 / peak
    out = OUT / f"{track}.loop.mp3"
    OUT.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-",
                    "-b:a", "192k", str(out)], input=y.astype(np.float32).tobytes(), check=True)
    print(f"{out.name} {n / SR:.2f} s, peak {20 * np.log10(np.abs(y).max()):.1f} dB, {out.stat().st_size // 1024} KB")


if __name__ == "__main__":
    for track, src in LOOPS.items():
        make(track, src)
