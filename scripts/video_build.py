"""Assemble the AETHER video (1920x1080, 30 fps) from the ParaView frames, matplotlib
animations and the narration segments.

usage: python scripts/video_build.py <work_dir> <out.mp4>

<work_dir> must contain frames3d/rot_*.png and stills/*.png (scripts/video_frames.py)
and audio/segments.json + audio/s*.wav (narration). Frames are piped to ffmpeg.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import wave

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK, OUT = sys.argv[1], sys.argv[2]
W, H, FPS = 1920, 1080, 30
BG = (14, 19, 26)
INK = (236, 238, 242)
ACCENT = (255, 158, 64)
MUTED = (160, 168, 180)


def font(size, bold=False):
    for path, idx in (("/System/Library/Fonts/Avenir Next.ttc", 2 if bold else 0),
                      ("/System/Library/Fonts/HelveticaNeue.ttc", 1 if bold else 0),
                      ("/System/Library/Fonts/Helvetica.ttc", 1 if bold else 0)):
        try:
            return ImageFont.truetype(path, size, index=idx)
        except Exception:
            continue
    return ImageFont.load_default()


F_TITLE, F_SUB, F_CAP, F_SMALL, F_BIG = font(96, True), font(42), font(40, True), font(30), font(64, True)

# ----------------------------------------------------------------------------- data
res = pd.read_csv(os.path.join(ROOT, "results", "results.csv"))
cap = res[(res["kind"] == "capsule") & (res["status"] == "converged")].set_index("case_id")


def vals(cid):
    r = cap.loc[cid]
    return float(r["cd"]), float(r["q_max_shield"]) / 1e3


seg = json.load(open(os.path.join(WORK, "audio", "segments.json")))
DUR = {k: v["duration"] for k, v in seg.items()}
GAP = 0.15                      # silence after each narration segment
LEAD = 0.25                     # narration starts this long after the scene cut


# ----------------------------------------------------------------------------- helpers
def ease(t):
    t = min(max(t, 0.0), 1.0)
    return t * t * (3 - 2 * t)


def load(path, size=(W, H)):
    im = Image.open(path).convert("RGB")
    return im if im.size == size else im.resize(size, Image.LANCZOS)


def ken_burns(im, t, z0=1.0, z1=1.08, cx=0.5, cy=0.5):
    z = z0 + (z1 - z0) * t
    w, h = int(W / z), int(H / z)
    x0 = int((W - w) * cx); y0 = int((H - h) * cy)
    return im.crop((x0, y0, x0 + w, y0 + h)).resize((W, H), Image.BILINEAR)


def blend(a, b, t):
    return Image.blend(a, b, ease(t)) if 0 < t < 1 else (a if t <= 0 else b)


def text(im, xy, s, f, fill=INK, anchor="la", shadow=True, alpha=1.0):
    if alpha <= 0:
        return im
    layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    if shadow:
        d.text((xy[0] + 2, xy[1] + 3), s, font=f, fill=(0, 0, 0, int(160 * alpha)), anchor=anchor)
    d.text(xy, s, font=f, fill=fill + (int(255 * alpha),), anchor=anchor)
    return Image.alpha_composite(im.convert("RGBA"), layer).convert("RGB")


def lower_third(im, title, sub="", alpha=1.0):
    if alpha <= 0:
        return im
    layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.rectangle((70, H - 190, 86, H - 70), fill=ACCENT + (int(255 * alpha),))
    im = Image.alpha_composite(im.convert("RGBA"), layer).convert("RGB")
    im = text(im, (110, H - 190), title, F_CAP, alpha=alpha)
    if sub:
        im = text(im, (110, H - 128), sub, F_SMALL, fill=MUTED, alpha=alpha)
    return im


def fade(im, a):
    if a >= 1:
        return im
    return Image.blend(Image.new("RGB", im.size, BG), im, max(a, 0.0))


def vignette(im, strength=0.35):
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).ellipse((-W * 0.25, -H * 0.45, W * 1.25, H * 1.45), fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(220))
    dark = Image.new("RGB", (W, H), BG)
    return Image.composite(im, Image.blend(im, dark, strength), mask)


# ----------------------------------------------------------------------------- matplotlib scenes
plt.rcParams.update({"figure.facecolor": "#0e131a", "axes.facecolor": "#0e131a", "axes.edgecolor": "#c8ccd4",
                     "axes.labelcolor": "#eceef2", "xtick.color": "#c8ccd4", "ytick.color": "#c8ccd4",
                     "text.color": "#eceef2", "font.size": 18, "axes.titlesize": 24, "legend.facecolor": "#161c25",
                     "legend.edgecolor": "#3a4250", "grid.color": "#2a313c"})


def fig_to_image(fig):
    fig.canvas.draw()
    buf = np.asarray(fig.canvas.buffer_rgba())[:, :, :3]
    return Image.fromarray(buf.copy())


def wall_frames(n):
    """wall heat flux of four named shapes drawn progressively"""
    picks = [("baseline  B00", "B00_t15", "#4c9be8"), ("highest drag  S03", "S03_t20", "#ff9e40"),
             ("lowest heating  K03", "K03_t15", "#5ad17a"), ("selected  N10", "N10_t15", "#f2545b")]
    data = []
    for lab, cid, col in picks:
        w = pd.read_csv(os.path.join(ROOT, "cases", "variant", cid, "wall_profile.csv"))
        meta = json.load(open(os.path.join(ROOT, "cases", "variant", cid, "case.json")))
        D = meta["params"]["D"]; s2 = meta["geometry"]["s_P2"] / D
        data.append((lab, col, w["s"].to_numpy() / D, w["Heat_Flux"].to_numpy() / 1e3, s2))
    frames = []
    fig, ax = plt.subplots(figsize=(W / 100, H / 100), dpi=100)
    fig.subplots_adjust(left=0.08, right=0.97, top=0.88, bottom=0.12)
    for i in range(n):
        t = i / (n - 1)
        ax.cla()
        ax.set_xlim(0, 0.75); ax.set_ylim(0, 125)
        ax.set_xlabel("distance along the wall  s / D"); ax.set_ylabel("wall heat flux  [kW/m$^2$]")
        ax.set_title("Heat flux along the heat shield: a plateau set by the nose radius, a peak at the shoulder", loc="left")
        ax.grid(True, alpha=0.4)
        for k, (lab, col, s, q, s2) in enumerate(data):
            start = 0.12 * k; prog = ease((t - start) / 0.62)
            if prog <= 0:
                continue
            m = s <= 0.75 * prog
            ax.plot(s[m], q[m], color=col, lw=3.2, label=lab)
            if prog >= 1:
                ax.axvline(s2, color=col, lw=1, ls=":", alpha=0.7)
        if t > 0.05:
            ax.legend(loc="upper right", fontsize=20, frameon=True)
        frames.append(fig_to_image(fig))
    plt.close(fig)
    return frames


def pareto_frames(n):
    ts = pd.read_csv(os.path.join(ROOT, "results", "tradespace.csv"))
    pa = json.load(open(os.path.join(ROOT, "results", "pareto_analysis.json")))
    unc = pa["uncertainty"]; sel = pa["selections"]["lowest_q_at_98pct_drag"]["case_id"]
    groups = [("nose", "#4c9be8", "nose radius"), ("cone", "#5ad17a", "cone angle"),
              ("shoulder", "#ff9e40", "shoulder radius"), ("combo", "#c48bf0", "combinations"), ("extreme", "#9a8578", "off-range"), ("baseline", "#eceef2", "baseline")]
    nd = ts[ts["nondominated"]].sort_values("cd")
    frames = []
    fig, ax = plt.subplots(figsize=(W / 100, H / 100), dpi=100)
    fig.subplots_adjust(left=0.08, right=0.97, top=0.88, bottom=0.12)
    # timeline (fractions of the scene): groups appear 0-0.55, line 0.55-0.72, star 0.72-0.85, hold
    order = ["baseline", "nose", "cone", "shoulder", "combo", "extreme"]
    for i in range(n):
        t = i / (n - 1)
        ax.cla()
        ax.set_xlim(0.9, 1.54); ax.set_ylim(99, 129)
        ax.set_xlabel(r"drag coefficient  $C_D$   (more is better)  $\rightarrow$")
        ax.set_ylabel(r"peak heat flux on the shield  [kW/m$^2$]   $\leftarrow$ (less is better)")
        ax.set_title("Drag versus peak heating, Mach 10.18: twenty shapes, one condition", loc="left")
        ax.grid(True, alpha=0.4)
        for k, g in enumerate(order):
            col, lab = next((c, l) for gg, c, l in groups if gg == g)
            sub = ts[ts["group"] == g] if g != "baseline" else ts[ts["case_id"] == "B00"]
            if g == "nose":
                sub = ts[(ts["group"] == g)]
            a = ease((t - 0.08 * k) / 0.10)
            if a <= 0 or sub.empty:
                continue
            ax.errorbar(sub["cd"], sub["q_max_shield"] / 1e3, xerr=unc["u_cd"] * sub["cd"], yerr=unc["u_q"] * sub["q_max_shield"] / 1e3,
                        fmt="o", color=col, ms=11 if g == "baseline" else 9, capsize=3, alpha=a, label=lab if g != "baseline" else "baseline (Apollo)")
            for _, r in sub.iterrows():
                ax.annotate(r["case_id"], (r["cd"], r["q_max_shield"] / 1e3), textcoords="offset points", xytext=(8, 6), fontsize=15, alpha=a, color=col)
        lp = ease((t - 0.56) / 0.16)
        if lp > 0:
            x = nd["cd"].to_numpy(); y = nd["q_max_shield"].to_numpy() / 1e3
            npts = max(2, int(round(1 + lp * (len(x) - 1) + 1e-9)))
            # draw partial polyline
            total = np.cumsum(np.r_[0, np.hypot(np.diff(x) / 0.64, np.diff(y) / 30)])
            L = total[-1] * lp
            xs, ys = [x[0]], [y[0]]
            for j in range(1, len(x)):
                if total[j] <= L:
                    xs.append(x[j]); ys.append(y[j])
                else:
                    f = (L - total[j - 1]) / (total[j] - total[j - 1])
                    xs.append(x[j - 1] + f * (x[j] - x[j - 1])); ys.append(y[j - 1] + f * (y[j] - y[j - 1])); break
            ax.plot(xs, ys, "-", color="#f2545b", lw=3, label="nondominated set" if lp >= 1 else None)
        sp = ease((t - 0.74) / 0.10)
        if sp > 0:
            r = ts[ts["case_id"] == sel].iloc[0]
            ax.plot(r["cd"], r["q_max_shield"] / 1e3, "*", color="#f2545b", ms=28 + 10 * (1 - sp), mfc="none", mew=3, alpha=sp, label="selected: 98 % drag rule")
            cdb, qb = pa["baseline"]["cd"], pa["baseline"]["q_max_shield"]
            ax.annotate(f"{sel}: {100*(r['cd']/cdb-1):+.1f} % drag, {100*(r['q_max_shield']/qb-1):+.1f} % peak heating",
                        (r["cd"], r["q_max_shield"] / 1e3), textcoords="data", xytext=(1.30, 100.4), fontsize=22, color="#f2545b", alpha=sp)
        if t > 0.02:
            ax.legend(loc="upper right", fontsize=16)
        frames.append(fig_to_image(fig))
    plt.close(fig)
    return frames


# ----------------------------------------------------------------------------- scenes
rot = sorted(os.path.join(WORK, "frames3d", f) for f in os.listdir(os.path.join(WORK, "frames3d")) if f.endswith(".png"))
still = lambda name: load(os.path.join(WORK, "stills", name))

NOSE = [("N06_t15", "0.60"), ("N08_t15", "0.80"), ("N10_t15", "1.00"), ("B00_t15", "1.20"), ("N14_t15", "1.40"), ("N16_t15", "1.60")]
SHOULDER = [("S03_t20", "0.030"), ("S08_t15", "0.080"), ("B00_t15", "0.051"), ("S12_t15", "0.120"), ("S18_t15", "0.180"), ("X02_t15", "0.450")]
SHOULDER = [SHOULDER[0], SHOULDER[2], SHOULDER[1], SHOULDER[3], SHOULDER[4], SHOULDER[5]]   # ordered by radius


class Scene:
    def __init__(self, name, dur, seg_id):
        self.name, self.dur, self.seg = name, dur, seg_id


scenes = [Scene("title", DUR["s1"] + LEAD + GAP, "s1"), Scene("rot3d", DUR["s2"] + LEAD + GAP, "s2"),
          Scene("nose", DUR["s3"] + LEAD + GAP, "s3"), Scene("shoulder", DUR["s4"] + LEAD + GAP, "s4"),
          Scene("wall", DUR["s5"] + LEAD + GAP, "s5"), Scene("pareto", DUR["s6"] + LEAD + GAP, "s6"),
          Scene("outro", DUR["s7"] + LEAD + 1.6, "s7")]
total = sum(s.dur for s in scenes)
print(f"scenes: {[(s.name, round(s.dur, 1)) for s in scenes]} total {total:.1f} s")

title_bg = still("B00_t15_Mach.png")
wall_fr = wall_frames(int(scenes[4].dur * FPS) + 1)
pareto_fr = pareto_frames(int(scenes[5].dur * FPS) + 1)
apollo = load(os.path.join(ROOT, "results", "figures", "validation_apollo.png"))
apollo_card = Image.new("RGB", (W, H), BG); apollo_card.paste(apollo.resize((1500, int(1500 * apollo.height / apollo.width))), (210, 90))


def sweep_frame(items, field, t, dur, label, key):
    """cross-dissolve through stills with a caption per shape"""
    n = len(items); per = dur / n
    k = min(int(t / per), n - 1); u = (t - k * per) / per
    cur = still(f"{items[k][0]}_{field}.png")
    if k + 1 < n and u > 0.75:
        nxt = still(f"{items[k + 1][0]}_{field}.png")
        cur = blend(cur, nxt, (u - 0.75) / 0.25)
    cd, q = vals(items[k][0])
    cur = ken_burns(cur, (k + u) / n, 1.0, 1.05, 0.45, 0.55)
    cur = lower_third(cur, f"{label}  {key} = {items[k][1]}", f"C_D = {cd:.3f}      peak heat flux = {q:.1f} kW/m²      {items[k][0].split('_')[0]}")
    return cur


def frame_of(scene, t):
    d = scene.dur
    if scene.name == "title":
        im = ken_burns(title_bg, t / d, 1.15, 1.0, 0.4, 0.5)
        im = fade(vignette(Image.blend(Image.new("RGB", (W, H), BG), im, 0.55), 0.3), min(1, t / 1.2))
        im = text(im, (W / 2, H * 0.40), "PROJECT AETHER", F_TITLE, anchor="mm", alpha=ease((t - 0.6) / 1.2))
        im = text(im, (W / 2, H * 0.50), "Which capsule shape slows you down without burning you up?", F_SUB, anchor="mm", alpha=ease((t - 1.4) / 1.2))
        im = text(im, (W / 2, H * 0.60), "A multi-objective shape study of an Apollo-like re-entry capsule heat shield", F_SMALL, fill=MUTED, anchor="mm", alpha=ease((t - 2.2) / 1.2))
        im = text(im, (W / 2, H * 0.88), "Adithya Kesan Jayakanth  ·  2026", F_SMALL, fill=MUTED, anchor="mm", alpha=ease((t - 3.0) / 1.2))
        return im
    if scene.name == "rot3d":
        k = min(int(t / d * len(rot)), len(rot) - 1)
        im = load(rot[k])
        return lower_third(im, "Baseline capsule, Mach 10.18, Re = 1.1 million", "heat shield coloured by wall heat flux  ·  Mach number in the symmetry plane  ·  laminar Navier–Stokes, SU2", alpha=ease((t - 0.8) / 1.0))
    if scene.name == "nose":
        return sweep_frame(NOSE, "Mach", t, d, "Nose radius sweep", "R_n / D")
    if scene.name == "shoulder":
        return sweep_frame(SHOULDER, "Temperature", t, d, "Shoulder radius sweep", "R_s / D")
    if scene.name == "wall":
        return wall_fr[min(int(t * FPS), len(wall_fr) - 1)]
    if scene.name == "pareto":
        return pareto_fr[min(int(t * FPS), len(pareto_fr) - 1)]
    if scene.name == "outro":
        if t < 5.2:
            im = ken_burns(apollo_card, t / 5.2, 1.0, 1.06)
            im = lower_third(im, "Validated against NASA TM X-1243 and NASA TM 100484", "three-level mesh study  ·  59 solver cases  ·  every number traceable to its case directory", alpha=ease(t / 0.8))
            return fade(im, 1 - ease((t - 4.6) / 0.6))
        u = t - 5.2
        im = Image.new("RGB", (W, H), BG)
        im = text(im, (W / 2, H * 0.42), "PROJECT AETHER", F_TITLE, anchor="mm", alpha=ease(u / 0.8))
        im = text(im, (W / 2, H * 0.54), "Adithya Kesan Jayakanth", F_SUB, anchor="mm", alpha=ease((u - 0.4) / 0.8))
        im = text(im, (W / 2, H * 0.62), "Aerodynamic Evaluation of Thermal Hazards in Entry Regimes", F_SMALL, fill=MUTED, anchor="mm", alpha=ease((u - 0.8) / 0.8))
        return fade(im, 1 - ease((t - d + 1.0) / 1.0))
    raise ValueError(scene.name)


# ----------------------------------------------------------------------------- audio track
n_samples = int(total * 48000) + 48000
track = np.zeros((n_samples, 2), dtype=np.float32)
t0 = 0.0
for sc in scenes:
    with wave.open(os.path.join(WORK, "audio", f"{sc.seg}.wav")) as w:
        data = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).reshape(-1, w.getnchannels()).astype(np.float32) / 32768.0
    start = int((t0 + LEAD) * 48000)
    track[start:start + len(data)] += data[:, :2] if data.shape[1] >= 2 else np.repeat(data, 2, axis=1)
    t0 += sc.dur
track = np.clip(track * 0.95, -1, 1)
apath = os.path.join(WORK, "narration_track.wav")
with wave.open(apath, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(48000)
    w.writeframes((track * 32767).astype(np.int16).tobytes())

# ----------------------------------------------------------------------------- encode
nf = int(round(total * FPS))
cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
       "-i", apath, "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
       "-shortest", "-movflags", "+faststart", OUT]
proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
XF = 0.6   # cross-fade between scenes [s]
starts = np.cumsum([0] + [s.dur for s in scenes])
for i in range(nf):
    T = i / FPS
    k = max(0, min(len(scenes) - 1, int(np.searchsorted(starts, T, side="right") - 1)))
    sc = scenes[k]; t = T - starts[k]
    im = frame_of(sc, t)
    if k + 1 < len(scenes) and t > sc.dur - XF:
        im = blend(im, frame_of(scenes[k + 1], 0.0), (t - (sc.dur - XF)) / XF)
    proc.stdin.write(im.tobytes())
    if i % 300 == 0:
        print(f"frame {i}/{nf} ({sc.name})", flush=True)
proc.stdin.close(); proc.wait()
print("wrote", OUT, f"{total:.1f} s")
