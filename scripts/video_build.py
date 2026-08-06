"""Assemble the AETHER video (1920x1080, 30 fps): a first-person account from the previous
project and the ISRO visit, through the design and the simulations, to the results and the lessons.

usage: python scripts/video_build.py <work_dir> <out.mp4>

<work_dir> must contain frames3d/rot_*.png, body/body_*.png and stills/*.png
(scripts/video_frames.py, then --extra) and audio/segments.json + audio/s*.wav
(scripts/video_narration.py). Frames are piped to ffmpeg.
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

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from aether.geometry import CapsuleParams, build_profile, sample_profile  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK, OUT = sys.argv[1], sys.argv[2]
W, H, FPS = 1920, 1080, 30
BG = (14, 19, 26)
INK = (236, 238, 242)
ACCENT = (255, 158, 64)
MUTED = (160, 168, 180)


def font(size, bold=False):
    for path, idx in (("/System/Library/Fonts/Avenir Next.ttc", 2 if bold else 0),
                      ("/System/Library/Fonts/HelveticaNeue.ttc", 1 if bold else 0)):
        try:
            return ImageFont.truetype(path, size, index=idx)
        except Exception:
            continue
    return ImageFont.load_default()


F_TITLE, F_SUB, F_CAP, F_SMALL, F_QUOTE = font(96, True), font(42), font(40, True), font(30), font(52)

res = pd.read_csv(os.path.join(ROOT, "results", "results.csv"))
cap = res[(res["kind"] == "capsule") & (res["status"] == "converged")].set_index("case_id")
seg = json.load(open(os.path.join(WORK, "audio", "segments.json")))
DUR = {k: v["duration"] for k, v in seg.items()}
GAP, LEAD = 0.25, 0.3


def vals(cid):
    r = cap.loc[cid]
    return float(r["cd"]), float(r["q_max_shield"]) / 1e3


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
    ImageDraw.Draw(layer).rectangle((70, H - 190, 86, H - 70), fill=ACCENT + (int(255 * alpha),))
    im = Image.alpha_composite(im.convert("RGBA"), layer).convert("RGB")
    im = text(im, (110, H - 190), title, F_CAP, alpha=alpha)
    if sub:
        im = text(im, (110, H - 128), sub, F_SMALL, fill=MUTED, alpha=alpha)
    return im


def fade(im, a):
    return im if a >= 1 else Image.blend(Image.new("RGB", im.size, BG), im, max(a, 0.0))


def dim(im, k):
    return Image.blend(Image.new("RGB", im.size, BG), im, k)


def vignette(im, strength=0.35):
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).ellipse((-W * 0.25, -H * 0.45, W * 1.25, H * 1.45), fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(220))
    return Image.composite(im, Image.blend(im, Image.new("RGB", (W, H), BG), strength), mask)


def statements(im, lines, t, start=0.2, step=1.2, y0=0.36, dy=0.12, fade_out_at=None):
    for k, (s, f, col) in enumerate(lines):
        a = ease((t - start - k * step) / 0.8)
        if fade_out_at is not None:
            a *= 1 - ease((t - fade_out_at) / 0.8)
        im = text(im, (W / 2, H * (y0 + k * dy)), s, f, fill=col, anchor="mm", alpha=a)
    return im


# ----------------------------------------------------------------------------- matplotlib scenes
plt.rcParams.update({"figure.facecolor": "#0e131a", "axes.facecolor": "#0e131a", "axes.edgecolor": "#c8ccd4",
                     "axes.labelcolor": "#eceef2", "xtick.color": "#c8ccd4", "ytick.color": "#c8ccd4",
                     "text.color": "#eceef2", "font.size": 18, "axes.titlesize": 24, "legend.facecolor": "#161c25",
                     "legend.edgecolor": "#3a4250", "grid.color": "#2a313c"})


def fig_to_image(fig):
    fig.canvas.draw()
    return Image.fromarray(np.asarray(fig.canvas.buffer_rgba())[:, :, :3].copy())


def morph_frames(n):
    """the capsule profile morphing through the nose, shoulder and cone sweeps"""
    base = CapsuleParams(D=0.17577, Rn_D=1.20231, Rs_D=0.05058, theta_c_deg=33.0, rb_D=0.20)
    bxy = sample_profile(build_profile(base)); bx, by = bxy[:, 0] / base.D, bxy[:, 1] / base.D
    frames = []
    fig, ax = plt.subplots(figsize=(W / 100, H / 100), dpi=100)
    fig.subplots_adjust(left=0.06, right=0.97, top=0.92, bottom=0.06)
    for i in range(n):
        t = i / (n - 1)
        if t < 0.38:
            u = 0.5 - 0.5 * np.cos(2 * np.pi * t / 0.38); p = CapsuleParams(D=base.D, Rn_D=0.6 + 1.0 * u, Rs_D=base.Rs_D, theta_c_deg=33.0, rb_D=base.rb_D); lab = f"nose radius   R_n / D = {p.Rn_D:.2f}"
        elif t < 0.72:
            u = 0.5 - 0.5 * np.cos(2 * np.pi * (t - 0.38) / 0.34); p = CapsuleParams(D=base.D, Rn_D=base.Rn_D, Rs_D=0.03 + 0.15 * u, theta_c_deg=33.0, rb_D=base.rb_D); lab = f"shoulder radius   R_s / D = {p.Rs_D:.3f}"
        else:
            u = 0.5 - 0.5 * np.cos(2 * np.pi * (t - 0.72) / 0.28); p = CapsuleParams(D=base.D, Rn_D=base.Rn_D, Rs_D=base.Rs_D, theta_c_deg=25 + 16 * u, rb_D=base.rb_D); lab = f"cone half-angle   {p.theta_c_deg:.0f} deg"
        xy = sample_profile(build_profile(p)); x, y = xy[:, 0] / p.D, xy[:, 1] / p.D
        ax.cla(); ax.set_aspect("equal"); ax.set_xlim(-0.2, 1.2); ax.set_ylim(-0.62, 0.62); ax.axis("off")
        ax.plot(bx, by, color="#3a4250", lw=2); ax.plot(bx, -by, color="#3a4250", lw=2)
        ax.plot(x, y, color="#ff9e40", lw=4); ax.plot(x, -y, color="#ff9e40", lw=4)
        ax.axhline(0, color="#5a6270", lw=1, ls="--")
        ax.text(0.5, 0.56, "one parameter table draws every shape  (grey: the Apollo baseline)", ha="center", fontsize=26, color="#eceef2")
        ax.text(0.5, -0.58, lab, ha="center", fontsize=28, color="#ff9e40")
        frames.append(fig_to_image(fig))
    plt.close(fig)
    return frames


def carbuncle_frames(n):
    """wall pressure and heat flux of S08: the carbuncle branch against the physical branch"""
    runs = [("carbuncle branch (first mesh family)", os.path.join(ROOT, "cases", "sweep", "S08"), "#ff6b6b"),
            ("physical branch (cells stretched along the shock)", os.path.join(ROOT, "cases", "variant", "S08_t15"), "#5ad17a")]
    data = []
    for lab, d, col in runs:
        w = pd.read_csv(os.path.join(d, "wall_profile.csv")); meta = json.load(open(os.path.join(d, "case.json")))
        R = meta["params"]["D"] / 2; pt2 = float(meta["freestream"]["p_t2"])
        data.append((lab, col, w["s"].to_numpy() / R, w["Pressure"].to_numpy() / pt2, w["Heat_Flux"].to_numpy() / 1e3))
    frames = []
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(W / 100, H / 100), dpi=100)
    fig.subplots_adjust(left=0.07, right=0.98, top=0.86, bottom=0.12, wspace=0.22)
    for i in range(n):
        t = i / (n - 1)
        for ax in (a1, a2):
            ax.cla(); ax.grid(True, alpha=0.4); ax.set_xlim(0, 1.2); ax.set_xlabel("distance from the stagnation point  S / R")
        a1.set_ylim(0, 1.2); a1.set_ylabel("wall pressure / pitot pressure"); a1.axhline(1.0, color="#c8ccd4", lw=1, ls="--")
        a1.text(1.18, 1.02, "Rayleigh pitot limit", ha="right", fontsize=16, color="#c8ccd4")
        a2.set_ylim(0, 720); a2.set_ylabel("wall heat flux  [kW/m$^2$]")
        fig.suptitle("Same shape, same solver, both runs converged: only one of them is physical", x=0.07, ha="left", fontsize=24)
        for k, (lab, col, s, pp, q) in enumerate(data):
            prog = ease((t - 0.25 * k) / 0.5)
            if prog <= 0:
                continue
            m = s <= 1.2 * prog
            a1.plot(s[m], pp[m], color=col, lw=3.2, label=lab); a2.plot(s[m], q[m], color=col, lw=3.2, label=lab)
        if t > 0.05:
            a1.legend(loc="lower left", fontsize=17); a2.legend(loc="upper right", fontsize=17)
        frames.append(fig_to_image(fig))
    plt.close(fig)
    return frames


def wall_frames(n):
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
        ax.cla(); ax.set_xlim(0, 0.75); ax.set_ylim(0, 125)
        ax.set_xlabel("distance along the wall  s / D"); ax.set_ylabel("wall heat flux  [kW/m$^2$]")
        ax.set_title("Heat flux along the heat shield: a plateau set by the nose radius, a peak at the shoulder", loc="left")
        ax.grid(True, alpha=0.4)
        for k, (lab, col, s, q, s2) in enumerate(data):
            prog = ease((t - 0.12 * k) / 0.62)
            if prog <= 0:
                continue
            m = s <= 0.75 * prog
            ax.plot(s[m], q[m], color=col, lw=3.2, label=lab)
            if prog >= 1:
                ax.axvline(s2, color=col, lw=1, ls=":", alpha=0.7)
        if t > 0.05:
            ax.legend(loc="upper right", fontsize=20)
        frames.append(fig_to_image(fig))
    plt.close(fig)
    return frames


def pareto_frames(n):
    ts = pd.read_csv(os.path.join(ROOT, "results", "tradespace.csv"))
    pa = json.load(open(os.path.join(ROOT, "results", "pareto_analysis.json")))
    unc = pa["uncertainty"]; sel = pa["selections"]["lowest_q_at_98pct_drag"]["case_id"]
    groups = {"baseline": ("#eceef2", "baseline (Apollo)"), "nose": ("#4c9be8", "nose radius"), "cone": ("#5ad17a", "cone angle"),
              "shoulder": ("#ff9e40", "shoulder radius"), "combo": ("#c48bf0", "combinations"), "extreme": ("#9a8578", "off-range")}
    nd = ts[ts["nondominated"]].sort_values("cd")
    frames = []
    fig, ax = plt.subplots(figsize=(W / 100, H / 100), dpi=100)
    fig.subplots_adjust(left=0.08, right=0.97, top=0.88, bottom=0.12)
    for i in range(n):
        t = i / (n - 1)
        ax.cla(); ax.set_xlim(0.9, 1.54); ax.set_ylim(99, 129)
        ax.set_xlabel(r"drag coefficient  $C_D$   (more is better)  $\rightarrow$")
        ax.set_ylabel(r"peak heat flux on the shield  [kW/m$^2$]   $\leftarrow$ (less is better)")
        ax.set_title("Drag versus peak heating, Mach 10.18: twenty shapes, one condition", loc="left"); ax.grid(True, alpha=0.4)
        for k, g in enumerate(["baseline", "nose", "cone", "shoulder", "combo", "extreme"]):
            col, lab = groups[g]
            sub = ts[ts["case_id"] == "B00"] if g == "baseline" else ts[ts["group"] == g]
            a = ease((t - 0.08 * k) / 0.10)
            if a <= 0 or sub.empty:
                continue
            ax.errorbar(sub["cd"], sub["q_max_shield"] / 1e3, xerr=unc["u_cd"] * sub["cd"], yerr=unc["u_q"] * sub["q_max_shield"] / 1e3,
                        fmt="o", color=col, ms=11 if g == "baseline" else 9, capsize=3, alpha=a, label=lab)
            for _, r in sub.iterrows():
                ax.annotate(r["case_id"], (r["cd"], r["q_max_shield"] / 1e3), textcoords="offset points", xytext=(8, 6), fontsize=15, alpha=a, color=col)
        lp = ease((t - 0.56) / 0.16)
        if lp > 0:
            x = nd["cd"].to_numpy(); y = nd["q_max_shield"].to_numpy() / 1e3
            total = np.cumsum(np.r_[0, np.hypot(np.diff(x) / 0.64, np.diff(y) / 30)]); L = total[-1] * lp
            xs, ys = [x[0]], [y[0]]
            for j in range(1, len(x)):
                if total[j] <= L:
                    xs.append(x[j]); ys.append(y[j])
                else:
                    f = (L - total[j - 1]) / (total[j] - total[j - 1]); xs.append(x[j - 1] + f * (x[j] - x[j - 1])); ys.append(y[j - 1] + f * (y[j] - y[j - 1])); break
            ax.plot(xs, ys, "-", color="#f2545b", lw=3, label="nondominated set" if lp >= 1 else None)
        sp = ease((t - 0.74) / 0.10)
        if sp > 0:
            r = ts[ts["case_id"] == sel].iloc[0]; cdb, qb = pa["baseline"]["cd"], pa["baseline"]["q_max_shield"]
            ax.plot(r["cd"], r["q_max_shield"] / 1e3, "*", color="#f2545b", ms=28 + 10 * (1 - sp), mfc="none", mew=3, alpha=sp, label="selected: 98 % drag rule")
            ax.annotate(f"{sel}: {100*(r['cd']/cdb-1):+.1f} % drag, {100*(r['q_max_shield']/qb-1):+.1f} % peak heating", (r["cd"], r["q_max_shield"] / 1e3),
                        textcoords="data", xytext=(1.30, 100.4), fontsize=22, color="#f2545b", alpha=sp)
        if t > 0.02:
            ax.legend(loc="upper right", fontsize=16)
        frames.append(fig_to_image(fig))
    plt.close(fig)
    return frames


# ----------------------------------------------------------------------------- scenes
rot = sorted(os.path.join(WORK, "frames3d", f) for f in os.listdir(os.path.join(WORK, "frames3d")) if f.endswith(".png"))
body = sorted(os.path.join(WORK, "body", f) for f in os.listdir(os.path.join(WORK, "body")) if f.endswith(".png"))
still = lambda name: load(os.path.join(WORK, "stills", name))
NOSE = [("N06_t15", "0.60"), ("N08_t15", "0.80"), ("N10_t15", "1.00"), ("B00_t15", "1.20"), ("N14_t15", "1.40"), ("N16_t15", "1.60")]
SHOULDER = [("S03_t20", "0.030"), ("B00_t15", "0.051"), ("S08_t15", "0.080"), ("S12_t15", "0.120"), ("S18_t15", "0.180"), ("X02_t15", "0.450")]


class Scene:
    def __init__(self, name, dur, seg_id):
        self.name, self.dur, self.seg = name, dur, seg_id


scenes = [Scene("f1", DUR["s1"] + LEAD + GAP, "s1"), Scene("isro", DUR["s2"] + LEAD + GAP, "s2"),
          Scene("design", DUR["s3"] + LEAD + GAP, "s3"), Scene("build", DUR["s4"] + LEAD + GAP, "s4"),
          Scene("broke", DUR["s5"] + LEAD + GAP, "s5"), Scene("results", DUR["s6"] + LEAD + GAP, "s6"),
          Scene("learn", DUR["s7"] + LEAD + 1.8, "s7")]
total = sum(s.dur for s in scenes)
print(f"scenes: {[(s.name, round(s.dur, 1)) for s in scenes]} total {total:.1f} s")

morph_fr = morph_frames(int(0.62 * scenes[2].dur * FPS) + 1)
carb_fr = carbuncle_frames(int(0.6 * scenes[4].dur * FPS) + 1)
wall_fr = wall_frames(int(0.45 * scenes[5].dur * FPS) + 1)
pareto_fr = pareto_frames(int(0.55 * scenes[5].dur * FPS) + 1)
mach_bg = still("B00_t15_Mach.png"); temp_bg = still("B00_t15_Temperature.png")
from PIL import ImageOps  # noqa: E402
mesh_im = Image.open(os.path.join(ROOT, "cases", "variant", "B00_t15", "mesh_zoom.png")).convert("RGB")
mesh_im = mesh_im.crop((int(0.125 * mesh_im.width), int(0.085 * mesh_im.height), int(0.985 * mesh_im.width), int(0.90 * mesh_im.height)))
mesh_im = ImageOps.invert(mesh_im)                       # dark background, light grid lines
mh = int(H * 0.70); mw = int(mh * mesh_im.width / mesh_im.height)
mesh_card = Image.new("RGB", (W, H), BG); mesh_card.paste(mesh_im.resize((mw, mh), Image.LANCZOS), ((W - mw) // 2, int(H * 0.05)))


def sweep(items, field, t, dur, label, key):
    n = len(items); per = dur / n
    k = min(int(t / per), n - 1); u = (t - k * per) / per
    cur = still(f"{items[k][0]}_{field}.png")
    if k + 1 < n and u > 0.75:
        cur = blend(cur, still(f"{items[k + 1][0]}_{field}.png"), (u - 0.75) / 0.25)
    cd, q = vals(items[k][0])
    cur = ken_burns(cur, (k + u) / n, 1.0, 1.05, 0.45, 0.55)
    return lower_third(cur, f"{label}  {key} = {items[k][1]}", f"C_D = {cd:.3f}      peak heat flux = {q:.1f} kW/m²      {items[k][0].split('_')[0]}")


def frame_of(sc, t):
    d = sc.dur
    if sc.name == "f1":
        bg = dim(vignette(ken_burns(mach_bg, t / d, 1.2, 1.05, 0.4, 0.5), 0.3), 0.6)
        im = text(bg, (W / 2, H * 0.36), "PROJECT AETHER", F_TITLE, anchor="mm", alpha=ease((t - 0.3) / 1.0))
        im = text(im, (W / 2, H * 0.46), "a first-person account", F_SUB, fill=MUTED, anchor="mm", alpha=ease((t - 1.0) / 1.0))
        im = text(im, (W / 2, H * 0.66), "Two years ago: a model Formula One car.", F_QUOTE, anchor="mm", alpha=ease((t - 3.2) / 0.8))
        im = text(im, (W / 2, H * 0.75), "Shape it.  Simulate it.  Race it.  Measure.", F_QUOTE, fill=ACCENT, anchor="mm", alpha=ease((t - 5.6) / 0.8))
        im = text(im, (W / 2, H * 0.86), "change one thing at a time", F_SUB, fill=MUTED, anchor="mm", alpha=ease((t - 9.0) / 0.8))
        return fade(im, min(1, t / 1.0))
    if sc.name == "isro":
        k = min(int(t / d * len(body)), len(body) - 1)
        im = load(body[k])
        hold = (1 - ease((t - d + 8.5) / 1.0))
        im = lower_third(im, "A re-entry capsule, seen up close at ISRO", "blunt on purpose: the face pushes the shock away from the shield", alpha=ease((t - 1.0) / 1.0) * hold)
        u = t - (d - 8.0)
        if u > 0:
            im = text(im, (W / 2, H * 0.16), "If the shape makes both the drag and the heating,", F_QUOTE, anchor="mm", alpha=ease(u / 0.8))
            im = text(im, (W / 2, H * 0.25), "how do you choose it?", F_QUOTE, fill=ACCENT, anchor="mm", alpha=ease((u - 1.2) / 0.8))
        return im
    if sc.name == "design":
        if t < d * 0.62:
            return morph_fr[min(int(t * FPS), len(morph_fr) - 1)]
        u = t - d * 0.62
        im = dim(vignette(ken_burns(temp_bg, u / (d * 0.38), 1.0, 1.06)), 0.45)
        return statements(im, [("One condition: Apollo at Mach 10.18, NASA TM X-1243 (1966)", F_QUOTE, INK), ("Two objectives: maximise drag, minimise peak heat flux", F_QUOTE, INK),
                               ("One rule, written first: lowest heating at 98 % of baseline drag", F_QUOTE, ACCENT)], u, 0.2, 1.6)
    if sc.name == "build":
        if t < d * 0.5:
            im = ken_burns(mesh_card, t / (d * 0.5), 1.0, 1.08, 0.5, 0.45)
            return lower_third(im, "Structured mesh from the same parameter table", "first cell 2 µm at the wall  ·  cells elongated along the bow shock  ·  three nested levels", alpha=ease(t / 0.8))
        u = t - d * 0.5
        k = min(int(u / (d * 0.5) * len(rot) * 0.45), len(rot) - 1)
        im = load(rot[k])
        return lower_third(im, "Twenty shapes  ·  59 solver cases  ·  three mesh levels  ·  two benchmarks", "SU2 v8.5.0, laminar Navier–Stokes, axisymmetric; every case kept in its own directory", alpha=ease(u / 0.8))
    if sc.name == "broke":
        if t < d * 0.6:
            return carb_fr[min(int(t * FPS), len(carb_fr) - 1)]
        u = t - d * 0.6
        bgk = min(int(u / (d * 0.4) * len(rot) * 0.3) + int(len(rot) * 0.5), len(rot) - 1)
        im = dim(vignette(load(rot[bgk])), 0.4)
        return statements(im, [("The monitors said done.", F_QUOTE, INK), ("The pitot pressure said no.", F_QUOTE, ACCENT),
                               ("The fix was the mesh: stretch the cells along the shock.", F_QUOTE, INK),
                               ("Fourteen shapes on two mesh families: agreement within a percent.", F_SUB, MUTED)], u, 0.2, 1.5, 0.32, 0.11)
    if sc.name == "results":
        if t < d * 0.45:
            return wall_fr[min(int(t * FPS), len(wall_fr) - 1)]
        return pareto_fr[min(int((t - d * 0.45) * FPS), len(pareto_fr) - 1)]
    if sc.name == "learn":
        k = min(int(t / d * len(rot)), len(rot) - 1)
        im = dim(load(rot[k]), 0.4)
        im = statements(im, [("Write the rule before the result.", F_QUOTE, INK), ("A converged solution is not a correct one until the physics agrees.", F_QUOTE, INK),
                             ("Keep the failures. They are the evidence.", F_QUOTE, ACCENT)], t, 0.4, 2.6, 0.30, 0.12, fade_out_at=d - 5.0)
        u = t - (d - 4.4)
        if u > 0:
            im = text(im, (W / 2, H * 0.42), "PROJECT AETHER", F_TITLE, anchor="mm", alpha=ease(u / 0.8))
            im = text(im, (W / 2, H * 0.54), "Adithya Kesan Jayakanth", F_SUB, anchor="mm", alpha=ease((u - 0.4) / 0.8))
            im = text(im, (W / 2, H * 0.62), "every number traceable to its case directory", F_SMALL, fill=MUTED, anchor="mm", alpha=ease((u - 0.8) / 0.8))
        return fade(im, 1 - ease((t - d + 0.9) / 0.9))
    raise ValueError(sc.name)


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
XF = 0.6
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
