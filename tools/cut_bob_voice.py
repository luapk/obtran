"""Bob's lines cut from the alien voice take Paul chose.

  python3 tools/cut_bob_voice.py

Paul, 24 October: "deep-wet-1 is good for Bob", and lose "Are you winding..." from his line. The
take (voices/alien-tests/deep-wet-1.mp3, ElevenLabs Voice Design) speaks all three of Bob's lines,
so they are cut from it, keeping the performance he heard rather than voicing them again. The cut
points sit in its pauses (ffmpeg silencedetect at -38 dB): "W-what the hell... tumbleweed." ends
at 8.49 s, "Are you winding..." runs from 9.01 to 10.54 and is left out, "Holy smokes! Er, ok."
runs from 11.00 to 15.36, and "Initiating quantum control..." from 15.84 to the end. Each cut keeps
a little air either side and a short fade, and is written as MP3 to prototype/assets/voice/, with
its entry in index.json (no radio: the take is heard as it is, which keeps its depth).
"""
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TAKE = ROOT / "voices" / "alien-tests" / "deep-wet-1.mp3"
OUT = ROOT / "prototype" / "assets" / "voice"
CUTS = {"bob1": (0.0, 8.75), "holy": (10.85, 15.6), "qntm": (15.65, None)}
FADE = 0.06


def main():
    index = json.loads((OUT / "index.json").read_text())
    dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(TAKE)]))
    for beat, (a, b) in CUTS.items():
        b = dur if b is None else b
        out = OUT / f"{beat}.mp3"
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", f"{a}", "-to", f"{b}", "-i", str(TAKE),
                        "-af", f"afade=t=in:d={FADE},afade=t=out:st={b - a - FADE:.3f}:d={FADE}",
                        "-ar", "44100", "-b:a", "128k", str(out)], check=True)
        data = out.read_bytes()
        index["lines"][beat] = {"file": out.name, "hash": "deep-wet-1-" + hashlib.sha256(data).hexdigest()[:10],
                                "bytes": len(data), "speaker": "bob", "radio": False}
        print(f"{beat}: {a:.2f} to {b:.2f} s, {len(data) // 1024} KB")
    (OUT / "index.json").write_text(json.dumps(index, indent=2) + "\n")


if __name__ == "__main__":
    main()
