"""A comic's ambiences and one-shot sounds from Paul's files, for the page.

  python3 tools/make_ambience.py --comic obtran001

Paul sent five sounds for OBTRAN 001 on 25 October, "name is where they should be used" (originals in
comics/<id>/source/sfx/, outside git). Ambiences become seamless loops: the fade in at the head and any fade out at
the tail are cut off, then the last LOOP_X seconds are blended into the opening (equal power), so the page can loop
them with no seam. Every ambience is brought to the same loudness (-24 dB RMS) and one-shots to a -3 dB peak, with
peaks held under full scale (fire.mp3 arrived clipping). Writes 44.1 kHz stereo MP3 to comics/<id>/assets/sfx/:
  amb-chanting.mp3   chanting.mp3 (12 s of voices): under the bonfire ritual
  amb-fire.mp3       fire.mp3 (11 s of crackling fire): under the bonfire, and quietly under Lyra's ruins
  amb-cockpit.mp3    spaceship_interior_2_preferred.mp3 (11 s of hum): in the cryptid's cockpit (Paul's preferred take)
  amb-cockpit-2.mp3  spaceship_interior.mp3 (16 s): the other take, kept as a spare
  spaceship.mp3      spaceship_1.mp3 (2.4 s, a ship passing): as the vessel opens, and the fold's slingshot
"""
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
SR = 44100
LOOP_X = 2.0
AMB_RMS = -24.0
# name: (source, start, end or None for its length, loop?)
SOUNDS = {
    "obtran001": {
        "amb-chanting": ("chanting.mp3", 0.45, 10.9, True),
        "amb-fire": ("fire.mp3", 0.35, None, True),
        "amb-cockpit": ("spaceship_interior_2_preferred.mp3", 0.45, None, True),
        "amb-cockpit-2": ("spaceship_interior.mp3", 0.1, None, True),
        "spaceship": ("spaceship_1.mp3", 0.1, None, False),
    },
}


def read(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2).astype(np.float64)


def write(a, path):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ac", "2", "-ar", str(SR), "-i", "-", "-b:a", "192k", str(path)],
                   input=a.astype(np.float32).tobytes(), check=True)


def soft_limit(a, ceil=0.89):
    # leave everything under the ceiling alone; above it, bend smoothly towards full scale
    over = np.abs(a) > ceil
    a = a.copy()
    a[over] = np.sign(a[over]) * (ceil + (1 - ceil) * np.tanh((np.abs(a[over]) - ceil) / (1 - ceil)))
    return a


def loop(a):
    n = int(LOOP_X * SR)
    t = np.linspace(0, np.pi / 2, n)[:, None]
    head, tail = a[:n], a[-n:]
    body = a[n:-n] if len(a) > 2 * n else a[n:n]
    blend = tail * np.cos(t) + head * np.sin(t)      # the tail fades out over the head fading in
    return np.concatenate([blend, body])


def main():
    cid = sys.argv[sys.argv.index("--comic") + 1] if "--comic" in sys.argv else "obtran001"
    base = ROOT / "comics" / cid
    out = base / "assets" / "sfx"
    out.mkdir(parents=True, exist_ok=True)
    for name, (src, t0, t1, is_loop) in SOUNDS[cid].items():
        a = read(base / "source" / "sfx" / src)
        a = a[int(t0 * SR):int(t1 * SR) if t1 else len(a)]
        if is_loop:
            a = loop(a)
            a *= 10 ** (AMB_RMS / 20) / np.sqrt((a ** 2).mean())
        else:
            a *= 10 ** (-3 / 20) / np.abs(a).max()
            fade = int(0.08 * SR)
            a[-fade:] *= np.linspace(1, 0, fade)[:, None]
        a = soft_limit(a)
        write(a, out / f"{name}.mp3")
        print(f"{name}.mp3  {len(a) / SR:.2f} s  rms {20 * np.log10(np.sqrt((a ** 2).mean())):.1f} dB  peak {20 * np.log10(np.abs(a).max()):.1f} dB")


if __name__ == "__main__":
    main()
