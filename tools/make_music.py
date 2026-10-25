"""Paul's music, made into loops for the page.

  python3 tools/make_music.py

Paul sent smokehouse_shift.mp3 on 25 October (25.9 s of QNTM CTRL's Smokehouse Shift, 44.1 kHz,
320 kbps; kept in source/music/, outside git): "loop this music to play, starting at the same time as
the first VO, fade at end with slight reverb to ensure seamless loop". The excerpt opens on a hit that
decays and ends at full level, mid build, so as it stands the loop would cut dead at the seam. Here
the last FADE seconds fade out, a slight reverb (a synthetic decaying stereo tail, TAIL seconds, mixed
at WET) is laid over the end, and the part of the reverb that rings past the end is folded back onto
the start, so it rings on under the opening hit as the loop comes round. The loop keeps the excerpt's
length, so it holds its tempo, and plays with no seam. pulsar_forest.mp3 (32.7 s, 25 October) is made the same way. Writes prototype/assets/music/<name>.loop.mp3.

  python3 tools/make_music.py --comic obtran001

OBTRAN 001's excerpts (Paul, 25 October: RANDOM.mp3, ENDLESS.mp3, EAGLE_SENSES.mp3; in comics/obtran001/source/music/,
outside git) are cut on the beat instead: each loop starts on a beat and runs a whole number of bars, at the tempo
measured from the excerpt (low band onset flux, the grid that best fits it), and the music just past the cut is
blended over the loop's opening (XFADE, equal power), so the loop comes round in time with no fade. A loop that
starts on a beat and holds whole bars keeps one beat grid however often it repeats, so the page can lock the drum
to it (bpm in the music index). Writes comics/<id>/assets/music/<name>.loop.mp3.
"""
import subprocess
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "source" / "music"
OUT = ROOT / "prototype" / "assets" / "music"
SR = 44100
LOOPS = {"smokehouse-shift": "smokehouse_shift.mp3", "pulsar-forest": "pulsar_forest.mp3"}   # track id (assets/music/index.json): source file
FADE = 2.5        # the end fades out over this long
TAIL = 3.0        # the reverb's length
WET = 0.28        # how much reverb
VERB_IN = 5.0     # the reverb hears this much of the end
LEVEL = -22.0     # loudness of every loop (RMS, dB full scale)
XFADE = 0.45      # beat-cut loops: the music past the cut, blended over the opening
# beat-cut loops per comic: track id: (source file, bpm, first beat s, beats)
BEAT_LOOPS = {
    "obtran001": {
        "random-value": ("random_value.mp3", 135.0, 0.177, 88),              # 22 bars, 39.11 s
        "endless-expansion": ("endless_expansion.mp3", 100.0, 0.110, 64),    # 16 bars, 38.40 s
        "the-eagle-and-the-senses": ("eagle_senses.mp3", 120.0, 0.096, 60),  # 15 bars, 30.00 s
    },
}


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
    # every loop to the same loudness (Paul's excerpts arrived 17 dB apart), with peaks kept under full scale
    y *= 10 ** (LEVEL / 20) / np.sqrt(np.mean(y ** 2))
    peak = np.abs(y).max()
    if peak > 0.98: y *= 0.98 / peak
    out = OUT / f"{track}.loop.mp3"
    OUT.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-",
                    "-b:a", "192k", str(out)], input=y.astype(np.float32).tobytes(), check=True)
    print(f"{out.name} {n / SR:.2f} s, peak {20 * np.log10(np.abs(y).max()):.1f} dB, {out.stat().st_size // 1024} KB")


def make_beat(src_dir, out_dir, track, src, bpm, first, beats):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(src_dir / src), "-ar", str(SR), "-ac", "2", "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    x = np.frombuffer(raw, np.float32).reshape(-1, 2).astype(np.float64)
    a, n, xf = round(first * SR), round(beats * 60 / bpm * SR), round(XFADE * SR)
    if a + n + xf > len(x):
        raise SystemExit(f"{src}: {beats} beats at {bpm} from {first} s need {(a + n + xf) / SR:.2f} s, the excerpt is {len(x) / SR:.2f} s")
    y = x[a:a + n].copy()
    t = np.linspace(0, np.pi / 2, xf)[:, None]
    y[:xf] = y[:xf] * np.sin(t) + x[a + n:a + n + xf] * np.cos(t)          # what follows the cut, fading over the opening
    y *= 10 ** (LEVEL / 20) / np.sqrt(np.mean(y ** 2))
    peak = np.abs(y).max()
    if peak > 0.98: y *= 0.98 / peak
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{track}.loop.mp3"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-", "-b:a", "192k", str(out)],
                   input=y.astype(np.float32).tobytes(), check=True)
    print(f"{out.name} {n / SR:.3f} s ({beats} beats at {bpm} bpm), peak {20 * np.log10(np.abs(y).max()):.1f} dB, {out.stat().st_size // 1024} KB")


if __name__ == "__main__":
    import sys
    if "--comic" in sys.argv and sys.argv[sys.argv.index("--comic") + 1] != "obtran003":
        cid = sys.argv[sys.argv.index("--comic") + 1]
        base = ROOT / "comics" / cid
        for track, spec in BEAT_LOOPS[cid].items():
            make_beat(base / "source" / "music", base / "assets" / "music", track, *spec)
    else:
        for track, src in LOOPS.items():
            make(track, src)
