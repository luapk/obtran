"""Paul's sound effects, trimmed for the page.

  python3 tools/make_sfx.py

Paul sent five sounds on 24 October, named for where they go ("edit according to time, hit or
extend"). The originals (96 kHz WAV) live in source/sfx/, outside git; this cuts each to the moment
it is used, with short fades, and writes 44.1 kHz stereo MP3 to prototype/assets/sfx/. Cut points come
from their loudness over time (ffmpeg, -45 dB as silence):
  crackle.mp3     crsshk2.wav: 32 s of steady pulsing static. The first 14 s, faded out over the last
                  2: it starts on CRSSHKKKKK! and runs under Smokehouse's first line, and the page
                  fades it as the line ends, so the length only has to outlast that.
  transition.mp3  transition.wav: one hit at 0.3 s with a long tail, gone by about 2.4 s. 0 to 2.6 s.
  unlock.mp3      UI_track_unlock.wav: the same chime twice (0 to 0.7 s and 1.74 to 2.67 s). Both, as Paul sent
                  it again: they go with the tab's flash and scroll.
  whoosh-1/2/3    whoosh.wav: three whooshes, at 0 to 2.3 s, 2.97 to 5.63 s and 6.37 to 8.04 s.
  power-up.mp3    biometric_power_up.wav: a pulsing hum in two halves, 0 to 4.57 s and 4.82 to 8.26 s.
                  The first half: the hold lasts 1.4 s, so the page plays it faster as the charge
                  rises and cuts it on release.
  bed.mp3         intro_comic_singularity.mp3: 14 s of steady atmosphere for the comic page and the
                  singularity, rising from silence and stopping dead. Made into a loop: from 0.8 s (after
                  its fade in), with its last 2 s blended into its opening (equal power), so the page can
                  loop it with no seam.
"""
import subprocess
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "source" / "sfx"
OUT = ROOT / "prototype" / "assets" / "sfx"
# name: (source file, start, end, fade in, fade out), seconds
CUTS = {
    "crackle": ("crsshk2.wav", 0.0, 14.0, 0.02, 2.0),
    "transition": ("transition.wav", 0.0, 2.6, 0.0, 0.4),
    "unlock": ("UI_track_unlock.wav", 0.0, 2.8, 0.0, 0.15),
    "whoosh-1": ("whoosh.wav", 0.0, 2.35, 0.0, 0.1),
    "whoosh-2": ("whoosh.wav", 2.92, 5.68, 0.0, 0.1),
    "whoosh-3": ("whoosh.wav", 6.32, 8.26, 0.0, 0.1),
    "power-up": ("biometric_power_up.wav", 0.0, 4.6, 0.01, 0.08),
}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name, (src, a, b, fi, fo) in CUTS.items():
        af = []
        if fi: af.append(f"afade=t=in:d={fi}")
        af.append(f"afade=t=out:st={b - a - fo:.3f}:d={fo}")
        out = OUT / f"{name}.mp3"
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", f"{a}", "-to", f"{b}", "-i", str(SRC / src),
                        "-af", ",".join(af), "-ar", "44100", "-ac", "2", "-b:a", "160k", str(out)], check=True)
        print(f"{name}.mp3 {b - a:.2f} s {out.stat().st_size // 1024} KB")
    make_loop("intro_comic_singularity.mp3", "bed", start=0.8, blend=2.0)


def make_loop(src, name, start, blend):
    sr = 44100
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(SRC / src), "-ar", str(sr), "-ac", "2", "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    x = np.frombuffer(raw, np.float32).reshape(-1, 2)[int(start * sr):]
    c = int(blend * sr)
    k = np.linspace(0, 1, c)[:, None]
    y = x[:len(x) - c].copy()
    y[:c] = x[:c] * np.sin(k * np.pi / 2) + x[len(x) - c:] * np.cos(k * np.pi / 2)   # the tail runs into the head
    out = OUT / f"{name}.mp3"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "f32le", "-ar", str(sr), "-ac", "2", "-i", "-",
                    "-b:a", "160k", str(out)], input=y.astype(np.float32).tobytes(), check=True)
    print(f"{name}.mp3 loop {len(y) / sr:.2f} s {out.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
