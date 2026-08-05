"""Narration segments of the AETHER video, synthesised with macOS speech (voice Daniel).

usage: python scripts/video_narration.py <work_dir>   -> <work_dir>/audio/s*.wav + segments.json
"""
import json, os, subprocess, sys
WORK = os.path.join(sys.argv[1], "audio"); os.makedirs(WORK, exist_ok=True); os.chdir(WORK)
SEG = [
 ("s1", "Project AETHER. A capsule returning from space needs drag to slow down. But the blunt face that makes the drag is where the gas burns hottest. Which shape slows you down, without burning you up?"),
 ("s2", "The Apollo-like baseline at Mach ten, computed with laminar Navier Stokes. A bow shock stands a sixth of a diameter ahead of the nose. The shield is coloured by heat flux: flat across the face, with a bright ring at the shoulder, where the flow accelerates around the corner."),
 ("s3", "Change the nose radius, and the shock moves with it. A rounder nose covers more of the frontal disc with high-pressure gas, so drag rises; but the shoulder expansion strengthens, and the peak heating rises too."),
 ("s4", "Open the shoulder, and the pressure falls away earlier. Drag drops by a quarter from the sharpest to the roundest shoulder, while the peak heating moves inward, and barely changes."),
 ("s5", "Along the wall, every shape tells the same story. A flat plateau, set by the nose radius. Then a peak at the tangency: sharper, and higher, the smaller the shoulder."),
 ("s6", "Twenty shapes, one condition, two objectives. The nondominated set runs from the sharpest shoulder, through the baseline, to a smaller nose radius. The rule, lowest heating at ninety-eight percent of baseline drag, picks a nose radius of one diameter: five percent less heating, for under two percent of drag."),
 ("s7", "Every number is validated against NASA wind-tunnel data, bounded by a mesh study, and traceable to its case. Project AETHER. Adithya Kesan Jayakanth."),
]
out = {}
for name, text in SEG:
    subprocess.run(["say", "-v", "Daniel", "-r", "186", "-o", f"{name}.aiff", text], check=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", f"{name}.aiff", "-ar", "48000", "-ac", "2", f"{name}.wav"], check=True)
    d = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f"{name}.wav"], capture_output=True, text=True).stdout.strip())
    out[name] = {"text": text, "duration": d}
    print(name, round(d, 2), "s")
json.dump(out, open("segments.json", "w"), indent=1)
print("total", round(sum(v["duration"] for v in out.values()), 1))
