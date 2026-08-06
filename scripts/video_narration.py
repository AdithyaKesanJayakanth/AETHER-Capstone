"""Narration of the AETHER video, first person.

usage: python scripts/video_narration.py <work_dir>   -> <work_dir>/audio/s*.wav + segments.json

Backend: ElevenLabs when ELEVENLABS_API_KEY is set in the environment (the key is never stored
in the repository), otherwise macOS speech. Voice and pace:
  ELEVENLABS_VOICE_ID   (default bIHbv24MWmeRgasZH58o, "Will": young American male, calm, conversational)
  ELEVENLABS_SPEED      (default 1.12; model range 0.7-1.2)
  AETHER_NARRATION_TARGET_S  optional total length; a mild tempo correction (<= 1.15x) is applied if exceeded
"""
import json
import os
import subprocess
import sys
import urllib.request

WORK = os.path.join(sys.argv[1], "audio")
os.makedirs(WORK, exist_ok=True)
os.chdir(WORK)
API_KEY = os.environ.get("ELEVENLABS_API_KEY")
VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID", "bIHbv24MWmeRgasZH58o")
SPEED = float(os.environ.get("ELEVENLABS_SPEED", "1.12"))
MODEL = os.environ.get("ELEVENLABS_MODEL", "eleven_multilingual_v2")

SEG = [
    ("s1", "Two years ago my project was a model Formula One car. Shape it, simulate it, race it, and find out whether the numbers were right. It left me with one habit: change one thing at a time, and measure."),
    ("s2", "Then I visited ISRO. In front of a re-entry capsule, the first thing you notice is how blunt it is. To someone who had spent a year chasing streamlines, it looked wrong. Blunt is the point: the flat face pushes the shock away, and that keeps the heat off the shield. I went home with a question. If the shape makes both the drag and the heating, how do you choose it?"),
    ("s3", "So AETHER became a bounded experiment. One capsule family: nose radius, shoulder radius, cone angle. One condition: the Apollo wind-tunnel test NASA published in 1966, so there was real data to be judged against. Two objectives: maximise drag, minimise peak heat flux. And one rule, written before any result: the lowest heating among shapes keeping ninety-eight percent of the baseline drag."),
    ("s4", "I built the pipeline myself. One parameter table draws the shape, meshes it, and runs the solver. Twenty shapes, fifty-nine cases, three mesh levels, two benchmarks against NASA data."),
    ("s5", "And the solver fought back. The residuals converged, to a solution that was wrong: a carbuncle, a numerical shock mode with the stagnation pressure twelve percent above anything physics allows. The monitors said done. The pitot pressure said no. The fix was not a setting. It was the mesh: stretch the cells along the shock, and the instability disappears."),
    ("s6", "The answer. Drag follows the nose and shoulder radius; the cone angle does nothing. The heating peak lives at the shoulder. And a nose radius of one diameter gives five percent less peak heating for under two percent of drag, four times the margin I measured by refining the mesh."),
    ("s7", "What I take with me. Write the rule before the result. A converged solution is not a correct one until the physics agrees. Keep the failures; they are the evidence. The capsule at ISRO looked wrong until I understood it. Now I know what it costs to make it look right. I'm Adithya, and this is Project AETHER."),
]


def elevenlabs(name, text):
    body = json.dumps({"text": text, "model_id": MODEL,
                       "voice_settings": {"stability": 0.55, "similarity_boost": 0.8, "style": 0.15, "use_speaker_boost": True, "speed": SPEED}}).encode()
    req = urllib.request.Request(f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}?output_format=mp3_44100_128", data=body,
                                 headers={"xi-api-key": API_KEY, "Content-Type": "application/json", "Accept": "audio/mpeg"})
    with urllib.request.urlopen(req, timeout=120) as r, open(f"{name}.mp3", "wb") as fh:
        fh.write(r.read())
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", f"{name}.mp3", "-ar", "48000", "-ac", "2", f"{name}.wav"], check=True)


def mac_say(name, text):
    subprocess.run(["say", "-v", "Reed (English (US))", "-r", "210", "-o", f"{name}.aiff", text], check=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", f"{name}.aiff", "-ar", "48000", "-ac", "2", f"{name}.wav"], check=True)


def duration(path):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                                capture_output=True, text=True).stdout.strip())


out = {}
for name, text in SEG:
    (elevenlabs if API_KEY else mac_say)(name, text)
    out[name] = {"text": text, "duration": duration(f"{name}.wav")}
    print(name, round(out[name]["duration"], 2), "s")
TARGET = float(os.environ.get("AETHER_NARRATION_TARGET_S", "0"))
total = sum(v["duration"] for v in out.values())
if TARGET and total > TARGET:
    f = min(total / TARGET, 1.15)
    for name in out:
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", f"{name}.wav", "-filter:a", f"atempo={f:.4f}", f"{name}_t.wav"], check=True)
        os.replace(f"{name}_t.wav", f"{name}.wav")
        out[name]["duration"] = duration(f"{name}.wav")
    print(f"tempo x{f:.3f} applied")
json.dump(out, open("segments.json", "w"), indent=1)
print("backend", "elevenlabs" if API_KEY else "macos-say", "| total", round(sum(v["duration"] for v in out.values()), 1), "s")
