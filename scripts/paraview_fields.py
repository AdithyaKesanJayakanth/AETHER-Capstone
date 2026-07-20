"""Field figures with ParaView's pvpython (ParaView 6.2.0).

usage: pvpython scripts/paraview_fields.py <case_dir> <out_prefix> [--revolve]

Writes <out_prefix>_<field>.png for Mach, Temperature, Pressure and a
density-gradient magnitude (numerical schlieren) of the stage-2 solution in
the meridional plane, clipped to the body region, plus, with --revolve, a
3-D view: the wall revolved about the axis (270 degrees, coloured by the
wall heat flux of wall_profile.csv) together with the meridional Mach field.
The revolved image is a visualisation of the axisymmetric solution, not a
3-D CFD result.
"""
import csv
import json
import os
import sys

from paraview.simple import *  # noqa: F401,F403
from paraview import servermanager
from vtkmodules.vtkCommonCore import vtkFloatArray, vtkPoints
from vtkmodules.vtkCommonDataModel import vtkCellArray, vtkPolyData

case_dir, out = sys.argv[1], sys.argv[2]
revolve = "--revolve" in sys.argv
vtu = os.path.join(case_dir, "flow_stage2.vtu")
if not os.path.exists(vtu):
    vtu = os.path.join(case_dir, "flow_stage1.vtu")
with open(os.path.join(case_dir, "case.json")) as fh:
    meta = json.load(fh)
D = float(meta["params"]["D"])
L = float(meta["geometry"]["length_m"])

reader = XMLUnstructuredGridReader(FileName=[vtu])
reader.UpdatePipeline()
grad = Gradient(Input=reader)
try:
    grad.ScalarArray = ["POINTS", "Density"]
except Exception:
    grad.SelectInputScalars = ["POINTS", "Density"]
grad.ResultArrayName = "grad_rho"
calc = Calculator(Input=grad)
calc.ResultArrayName = "schlieren"
calc.Function = "mag(grad_rho)"
# body region only: the far field is uniform free stream
box = Clip(Input=calc)
box.ClipType = "Box"
x0, x1, y1 = -0.45 * D, L + 0.15 * D, 0.95 * D
box.ClipType.Position = [x0, -0.01 * D, -0.01 * D]
box.ClipType.Length = [x1 - x0, y1 + 0.01 * D, 0.02 * D]
try:
    box.Invert = 1          # keep the inside of the box
except Exception:
    pass
box.UpdatePipeline()

view = GetActiveViewOrCreate("RenderView")
view.ViewSize = [1400, 800]
view.InteractionMode = "2D"
view.OrientationAxesVisibility = 0
view.Background = [1, 1, 1]
try:
    view.UseColorPaletteForBackground = 0
except Exception:
    pass


def frame_2d(v, scale):
    v.CameraParallelProjection = 1
    cx, cy = 0.5 * (x0 + x1), 0.5 * y1
    v.CameraFocalPoint = [cx, cy, 0.0]
    v.CameraPosition = [cx, cy, 1.0]
    v.CameraViewUp = [0.0, 1.0, 0.0]
    v.CameraParallelScale = scale


fields = [("Mach", "Mach number", None, "Viridis"),
          ("Temperature", "Temperature [K]", None, "Inferno"),
          ("Pressure", "Pressure [Pa]", None, "Viridis"),
          ("schlieren", "|grad rho| [kg/m^4]", "log", "Grayscale")]


def preset(lut, name):
    for cand in (name, name + " (matplotlib)"):
        try:
            lut.ApplyPreset(cand, True)
            return
        except Exception:
            continue
for name, title, scale, cmap in fields:
    disp = Show(box, view)
    ColorBy(disp, ("POINTS", name))
    lut = GetColorTransferFunction(name)
    preset(lut, cmap)
    if scale == "log":
        try:
            lut.MapControlPointsToLogSpace(); lut.UseLogScale = 1
        except Exception:
            pass
    disp.RescaleTransferFunctionToDataRange(True, False)
    disp.SetScalarBarVisibility(view, True)
    bar = GetScalarBar(lut, view)
    bar.Title = title; bar.ComponentTitle = ""
    bar.TitleColor = [0, 0, 0]; bar.LabelColor = [0, 0, 0]
    frame_2d(view, 0.52 * y1)
    Render(view)
    SaveScreenshot(f"{out}_{name}.png", view, ImageResolution=[1400, 800])
    Hide(box, view)

if revolve:
    # wall polyline with the wall heat flux from the post-processed profile
    pts = vtkPoints(); lines = vtkCellArray(); hf = vtkFloatArray(); hf.SetName("Heat flux [kW/m^2]")
    with open(os.path.join(case_dir, "wall_profile.csv")) as fh:
        rows = list(csv.DictReader(fh))
    n = 0
    for r in rows:
        pts.InsertNextPoint(float(r["x"]), float(r["y"]), 0.0); hf.InsertNextValue(1e-3 * float(r["Heat_Flux"])); n += 1
    lines.InsertNextCell(n)
    for i in range(n):
        lines.InsertCellPoint(i)
    poly = vtkPolyData(); poly.SetPoints(pts); poly.SetLines(lines); poly.GetPointData().AddArray(hf)
    poly.GetPointData().SetActiveScalars("Heat flux [kW/m^2]")
    wall = TrivialProducer()
    wall.GetClientSideObject().SetOutput(poly)
    body = RotationalExtrusion(Input=wall)
    body.Resolution = 120; body.Angle = 270
    try:
        body.RotationAxis = [1.0, 0.0, 0.0]
    except Exception:
        pass
    v3 = CreateView("RenderView")
    v3.ViewSize = [1400, 900]; v3.Background = [1, 1, 1]
    try:
        v3.UseColorPaletteForBackground = 0
    except Exception:
        pass
    v3.OrientationAxesVisibility = 0
    plane = Show(box, v3)
    ColorBy(plane, ("POINTS", "Mach"))
    lutM = GetColorTransferFunction("Mach")
    plane.RescaleTransferFunctionToDataRange(True, False)
    plane.SetScalarBarVisibility(v3, True)
    bM = GetScalarBar(lutM, v3); bM.Title = "Mach number (meridional plane)"; bM.ComponentTitle = ""
    bM.TitleColor = [0, 0, 0]; bM.LabelColor = [0, 0, 0]; bM.WindowLocation = "Lower Right Corner"
    d3 = Show(body, v3)
    ColorBy(d3, ("POINTS", "Heat flux [kW/m^2]"))
    lutQ = GetColorTransferFunction("Heat flux [kW/m^2]")
    preset(lutQ, "Inferno")
    d3.RescaleTransferFunctionToDataRange(True, False)
    d3.SetScalarBarVisibility(v3, True)
    bQ = GetScalarBar(lutQ, v3); bQ.Title = "Wall heat flux [kW/m^2] (revolved wall)"; bQ.ComponentTitle = ""
    bQ.TitleColor = [0, 0, 0]; bQ.LabelColor = [0, 0, 0]; bQ.WindowLocation = "Upper Right Corner"
    try:
        d3.Ambient = 0.25; d3.Diffuse = 0.85
    except Exception:
        pass
    v3.CameraPosition = [-1.7 * D, 1.2 * D, 1.9 * D]
    v3.CameraFocalPoint = [0.45 * D, 0.25 * D, 0.0]
    v3.CameraViewUp = [0.0, 1.0, 0.0]
    v3.CameraViewAngle = 30
    Render(v3)
    SaveScreenshot(f"{out}_Mach_revolved.png", v3, ImageResolution=[1400, 900])
print("done")
