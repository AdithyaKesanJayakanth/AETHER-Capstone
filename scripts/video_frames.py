"""Render the ParaView frames of the AETHER video (pvpython).

usage: pvpython scripts/video_frames.py <out_dir>

Writes
  <out_dir>/frames3d/rot_%04d.png   rotating revolved view of the baseline (wall coloured by
                                    heat flux, Mach field in the meridional plane)
  <out_dir>/stills/<case>_<field>.png  meridional-plane fields of sweep shapes, identical framing
"""
import csv
import json
import math
import os
import sys

from paraview.simple import *  # noqa: F401,F403
from vtkmodules.vtkCommonCore import vtkFloatArray, vtkPoints
from vtkmodules.vtkCommonDataModel import vtkCellArray, vtkPolyData

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = sys.argv[1]
W, H = 1920, 1080
BG = [0.055, 0.075, 0.10]
os.makedirs(os.path.join(OUT, "frames3d"), exist_ok=True)
os.makedirs(os.path.join(OUT, "stills"), exist_ok=True)


def preset(lut, name):
    for cand in (name, name + " (matplotlib)"):
        try:
            lut.ApplyPreset(cand, True); return
        except Exception:
            continue


def load_case(case_dir):
    with open(os.path.join(case_dir, "case.json")) as fh:
        meta = json.load(fh)
    D = float(meta["params"]["D"]); L = float(meta["geometry"]["length_m"])
    reader = XMLUnstructuredGridReader(FileName=[os.path.join(case_dir, "flow_stage2.vtu")])
    reader.UpdatePipeline()
    return reader, D, L


def clip_box(src, x0, x1, y1, D):
    box = Clip(Input=src); box.ClipType = "Box"
    box.ClipType.Position = [x0, -0.01 * D, -0.01 * D]
    box.ClipType.Length = [x1 - x0, y1 + 0.01 * D, 0.02 * D]
    try:
        box.Invert = 1
    except Exception:
        pass
    box.UpdatePipeline()
    return box


def dark_view(size):
    v = CreateView("RenderView")
    v.ViewSize = size; v.Background = BG
    try:
        v.UseColorPaletteForBackground = 0
    except Exception:
        pass
    v.OrientationAxesVisibility = 0
    return v


def bar(lut, view, title, loc):
    b = GetScalarBar(lut, view); b.Title = title; b.ComponentTitle = ""
    b.TitleColor = [0.92, 0.92, 0.92]; b.LabelColor = [0.85, 0.85, 0.85]
    b.TitleFontSize = 22; b.LabelFontSize = 18; b.ScalarBarLength = 0.33
    b.WindowLocation = loc
    return b


# ----------------------------------------------------------------- 3-D rotating baseline
case = os.path.join(ROOT, "cases", "variant", "B00_t15")
reader, D, L = load_case(case)
x0, x1, y1 = -0.45 * D, L + 0.15 * D, 0.95 * D
plane_src = clip_box(reader, x0, x1, y1, D)

pts = vtkPoints(); lines = vtkCellArray(); hf = vtkFloatArray(); hf.SetName("Heat flux [kW/m^2]")
with open(os.path.join(case, "wall_profile.csv")) as fh:
    rows = list(csv.DictReader(fh))
for r in rows:
    pts.InsertNextPoint(float(r["x"]), float(r["y"]), 0.0); hf.InsertNextValue(1e-3 * float(r["Heat_Flux"]))
lines.InsertNextCell(len(rows))
for i in range(len(rows)):
    lines.InsertCellPoint(i)
poly = vtkPolyData(); poly.SetPoints(pts); poly.SetLines(lines); poly.GetPointData().AddArray(hf)
poly.GetPointData().SetActiveScalars("Heat flux [kW/m^2]")
wall = TrivialProducer(); wall.GetClientSideObject().SetOutput(poly)
body = RotationalExtrusion(Input=wall); body.Resolution = 160; body.Angle = 270
try:
    body.RotationAxis = [1.0, 0.0, 0.0]
except Exception:
    pass

v3 = dark_view([W, H])
plane = Show(plane_src, v3); ColorBy(plane, ("POINTS", "Mach"))
lutM = GetColorTransferFunction("Mach"); preset(lutM, "Viridis"); lutM.RescaleTransferFunction(0.0, 10.2)
plane.SetScalarBarVisibility(v3, True); bar(lutM, v3, "Mach number", "Lower Right Corner")
d3 = Show(body, v3); ColorBy(d3, ("POINTS", "Heat flux [kW/m^2]"))
lutQ = GetColorTransferFunction("Heat flux [kW/m^2]"); preset(lutQ, "Inferno"); lutQ.RescaleTransferFunction(0.0, 115.0)
d3.SetScalarBarVisibility(v3, True); bar(lutQ, v3, "Wall heat flux [kW/m^2]", "Upper Right Corner")
try:
    d3.Ambient = 0.25; d3.Diffuse = 0.85
except Exception:
    pass
v3.CameraViewUp = [0.0, 1.0, 0.0]; v3.CameraViewAngle = 28
focal = [0.42 * D, 0.2 * D, 0.0]
N3 = 0 if "--extra" in sys.argv else 240
for i in range(N3):
    t = i / (N3 - 1)
    az = math.radians(172 - 62 * t)         # from nearly head-on upstream to the open quadrant (+z side)
    el = math.radians(18 + 14 * t)
    rad = 3.2 * D - 0.6 * D * t
    v3.CameraFocalPoint = focal
    v3.CameraPosition = [focal[0] + rad * math.cos(el) * math.cos(az), focal[1] + rad * math.sin(el), focal[2] + rad * math.cos(el) * math.sin(az)]
    Render(v3)
    SaveScreenshot(os.path.join(OUT, "frames3d", f"rot_{i:04d}.png"), v3, ImageResolution=[W, H])
print("3d frames done")
if "--3d-only" in sys.argv:
    sys.exit(0)
if "--extra" in sys.argv:
    STILLS = []

# ----------------------------------------------------------------- 2-D stills of sweep shapes
STILLS = [("N06_t15", "Mach"), ("N08_t15", "Mach"), ("N10_t15", "Mach"), ("B00_t15", "Mach"), ("N14_t15", "Mach"), ("N16_t15", "Mach"),
          ("S03_t20", "Temperature"), ("S08_t15", "Temperature"), ("B00_t15", "Temperature"), ("S12_t15", "Temperature"), ("S18_t15", "Temperature"), ("X02_t15", "Temperature")]
v2 = dark_view([W, H]); v2.InteractionMode = "2D"
for cid, field in STILLS:
    rd, D, L = load_case(os.path.join(ROOT, "cases", "variant", cid))
    bx = clip_box(rd, -0.45 * D, 1.15 * D, 0.9 * D, D)
    disp = Show(bx, v2); ColorBy(disp, ("POINTS", field))
    lut = GetColorTransferFunction(field)
    if field == "Mach":
        preset(lut, "Viridis"); lut.RescaleTransferFunction(0.0, 10.2); title = "Mach number"
    else:
        preset(lut, "Inferno"); lut.RescaleTransferFunction(48.0, 1080.0); title = "Temperature [K]"
    disp.SetScalarBarVisibility(v2, True); bar(lut, v2, title, "Lower Right Corner")
    v2.CameraParallelProjection = 1
    cx, cy = 0.35 * D, 0.45 * D
    v2.CameraFocalPoint = [cx, cy, 0.0]; v2.CameraPosition = [cx, cy, 1.0]; v2.CameraViewUp = [0, 1, 0]
    v2.CameraParallelScale = 0.45 * D
    Render(v2)
    SaveScreenshot(os.path.join(OUT, "stills", f"{cid}_{field}.png"), v2, ImageResolution=[W, H])
    Hide(bx, v2); Delete(bx); Delete(rd)
print("stills done")

# ----------------------------------------------------------------- extra: body-only rotation and the carbuncle comparison
if "--extra" in sys.argv:
    os.makedirs(os.path.join(OUT, "body"), exist_ok=True)
    vb = dark_view([W, H])
    full = RotationalExtrusion(Input=wall); full.Resolution = 180; full.Angle = 360
    try:
        full.RotationAxis = [1.0, 0.0, 0.0]
    except Exception:
        pass
    db = Show(full, vb); ColorBy(db, None); db.DiffuseColor = [0.72, 0.74, 0.78]; db.AmbientColor = [0.72, 0.74, 0.78]
    try:
        db.Specular = 0.5; db.SpecularPower = 40; db.Ambient = 0.15; db.Diffuse = 0.9
    except Exception:
        pass
    vb.CameraViewUp = [0, 1, 0]; vb.CameraViewAngle = 26
    NB = 180
    for i in range(NB):
        t = i / (NB - 1)
        az = math.radians(200 - 140 * t); el = math.radians(12 + 8 * math.sin(math.pi * t)); rad = 2.6 * D
        vb.CameraFocalPoint = [0.3 * D, 0.0, 0.0]
        vb.CameraPosition = [0.3 * D + rad * math.cos(el) * math.cos(az), rad * math.sin(el), rad * math.cos(el) * math.sin(az)]
        Render(vb)
        SaveScreenshot(os.path.join(OUT, "body", f"body_{i:04d}.png"), vb, ImageResolution=[W, H])
    print("body frames done")
    # carbuncle branch (family A, S08 after the sequencing restart) against the physical branch (family B)
    vc = dark_view([W, H]); vc.InteractionMode = "2D"
    for tag, cdir in (("carbuncle", os.path.join(ROOT, "cases", "sweep", "S08")), ("physical", os.path.join(ROOT, "cases", "variant", "S08_t15"))):
        rd, D2, L2 = load_case(cdir)
        bx = clip_box(rd, -0.35 * D2, 0.45 * D2, 0.55 * D2, D2)
        disp = Show(bx, vc); ColorBy(disp, ("POINTS", "Pressure"))
        lut = GetColorTransferFunction("Pressure"); preset(lut, "Inferno"); lut.RescaleTransferFunction(0.0, 29000.0)
        disp.SetScalarBarVisibility(vc, True); bar(lut, vc, "Pressure [Pa]", "Lower Right Corner")
        vc.CameraParallelProjection = 1
        vc.CameraFocalPoint = [0.05 * D2, 0.275 * D2, 0.0]; vc.CameraPosition = [0.05 * D2, 0.275 * D2, 1.0]; vc.CameraViewUp = [0, 1, 0]
        vc.CameraParallelScale = 0.275 * D2
        Render(vc)
        SaveScreenshot(os.path.join(OUT, "stills", f"S08_{tag}_Pressure.png"), vc, ImageResolution=[W, H])
        Hide(bx, vc); Delete(bx); Delete(rd)
    print("carbuncle stills done")
