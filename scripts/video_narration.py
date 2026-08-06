"""Narration of the AETHER video, first person, synthesised with macOS speech.

usage: python scripts/video_narration.py <work_dir> [voice]   -> <work_dir>/audio/s*.wav + segments.json
Default voice: "Reed (English (US))" (a young male voice); "Aman (English (India))" is the alternative.
"""
import json
import os
import subprocess
import sys

WORK = os.path.join(sys.argv[1], "audio")
VOICE = sys.argv[2] if len(sys.argv) > 2 else "Reed (English (US))"
RATE = "210"
os.makedirs(WORK, exist_ok=True)
os.chdir(WORK)

SEG = [
    ("s1", "Two years ago my project was a model Formula One car. Shape it, simulate it, race it, and find out whether the numbers were right. It left me with one habit: change one thing at a time, and measure."),
    ("s2", "Then I visited ISRO. In front of a re-entry capsule, the first thing you notice is how blunt it is. To someone who had spent a year chasing streamlines, it looked wrong. Blunt is the point: the flat face pushes the shock away, and that keeps the heat off the shield. I went home with a question. If the shape makes both the drag and the heating, how do you choose it?"),
    ("s3", "So AETHER became a bounded experiment. One capsule family: nose radius, shoulder radius, cone angle. One condition: the Apollo wind-tunnel test NASA published in 1966, so there was real data to be judged against. Two objectives: maximise drag, minimise peak heat flux. And one rule, written before any result: the lowest heating among shapes keeping ninety-eight percent of the baseline drag."),
    ("s4", "I built the pipeline myself. One parameter table draws the shape, meshes it, and runs the solver. Twenty shapes, fifty-nine cases, three mesh levels, two benchmarks against NASA data."),
    ("s5", "And the solver fought back. The residuals converged, to a solution that was wrong: a carbuncle, a numerical shock mode with the stagnation pressure twelve percent above anything physics allows. The monitors said done. The pitot pressure said no. The fix was not a setting. It was the mesh: stretch the cells along the shock, and the instability disappears."),
    ("s6", "The answer. Drag follows the nose and shoulder radius; the cone angle does nothing. The heating peak lives at the shoulder. And a nose radius of one diameter gives five percent less peak heating for under two percent of drag, four times the margin I measured by refining the mesh."),
    ("s7", "What I take with me. Write the rule before the result. A converged solution is not a correct one until the physics agrees. Keep the failures; they are the evidence. The capsule at ISRO looked wrong until I understood it. Now I know what it costs to make it look right. I'm Adithya, and this is Project AETHER."),
]
out = {}
for name, text in SEG:
    subprocess.run(["say", "-v", VOICE, "-r", RATE, "-o", f"{name}.aiff", text], check=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", f"{name}.aiff", "-ar", "48000", "-ac", "2", f"{name}.wav"], check=True)
    d = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f"{name}.wav"],
                             capture_output=True, text=True).stdout.strip())
    out[name] = {"text": text, "duration": d}
    print(name, round(d, 2), "s")
TARGET = float(os.environ.get("AETHER_NARRATION_TARGET_S", "0"))   # 0 = keep the synthesised pace
total = sum(v["duration"] for v in out.values())
if TARGET and total > TARGET:
    f = min(total / TARGET, 1.25)
    for name in out:
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", f"{name}.wav", "-filter:a", f"atempo={f:.4f}", f"{name}_t.wav"], check=True)
        os.replace(f"{name}_t.wav", f"{name}.wav")
        out[name]["duration"] = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f"{name}.wav"],
                                                     capture_output=True, text=True).stdout.strip())
    print(f"tempo x{f:.3f} applied")
json.dump(out, open("segments.json", "w"), indent=1)
print("total", round(sum(v["duration"] for v in out.values()), 1), "s")
