"""Field figures with ParaView's pvpython (ParaView 6.2.0).

usage: pvpython scripts/paraview_fields.py <case_dir> <out_prefix> [--revolve]

Writes <out_prefix>_<field>.png for Mach, Temperature, Pressure and a
density-gradient magnitude (numerical schlieren) of the stage-2 solution,
plus, with --revolve, a 3-D revolved view of the Mach field. The revolved
image is a visualisation of the axisymmetric solution, not a 3-D CFD result.
"""
import os
import sys

from paraview.simple import *  # noqa: F401,F403

case_dir, out = sys.argv[1], sys.argv[2]
revolve = "--revolve" in sys.argv
vtu = os.path.join(case_dir, "flow_stage2.vtu")
if not os.path.exists(vtu):
    vtu = os.path.join(case_dir, "flow_stage1.vtu")

reader = XMLUnstructuredGridReader(FileName=[vtu])
reader.UpdatePipeline()
bounds = reader.GetDataInformation().GetBounds()
grad = GradientOfUnstructuredDataSet(Input=reader) if hasattr(sys.modules[__name__], "GradientOfUnstructuredDataSet") else Gradient(Input=reader)
try:
    grad.ScalarArray = ["POINTS", "Density"]
except Exception:
    grad.SelectInputScalars = ["POINTS", "Density"]
grad.ResultArrayName = "grad_rho"
calc = Calculator(Input=grad)
calc.ResultArrayName = "schlieren"
calc.Function = "mag(grad_rho)"
calc.UpdatePipeline()

view = GetActiveViewOrCreate("RenderView")
view.ViewSize = [1400, 800]
view.InteractionMode = "2D"
view.OrientationAxesVisibility = 0
view.Background = [1, 1, 1]
try:
    view.UseColorPaletteForBackground = 0
except Exception:
    pass

fields = [("Mach", "Mach number", None, "Viridis"),
          ("Temperature", "Temperature [K]", None, "Inferno"),
          ("Pressure", "Pressure [Pa]", None, "Viridis"),
          ("schlieren", "|grad rho| [kg/m^4]", "log", "Grayscale")]
for name, title, scale, cmap in fields:
    disp = Show(calc, view)
    ColorBy(disp, ("POINTS", name))
    lut = GetColorTransferFunction(name)
    lut.ApplyPreset(cmap, True)
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
    view.ResetCamera()
    # frame the body region: x from -0.4 D to L + D, y to 1.3 D (bounds-based)
    cam = GetActiveCamera()
    D = float(os.environ.get("AETHER_D", "0.17577"))
    cx, cy = 0.35 * D, 0.65 * D            # frame the body: x in [-0.5 D, 1.2 D], y in [0, 1.3 D]
    cam.SetFocalPoint(cx, cy, 0); cam.SetPosition(cx, cy, 1.0)
    cam.SetParallelScale(0.7 * D)
    Render(view)
    SaveScreenshot(f"{out}_{name}.png", view, ImageResolution=[1400, 800])
    Hide(calc, view)

if revolve:
    surf = ExtractSurface(Input=reader)
    warp = RotationalExtrusion(Input=surf)
    warp.Resolution = 90
    warp.Angle = 270
    try:
        warp.RotationAxis = [1.0, 0.0, 0.0]
    except Exception:
        pass
    try:
        warp.Capping = 0
    except Exception:
        pass
    v3 = CreateView("RenderView")
    v3.ViewSize = [1400, 900]; v3.Background = [1, 1, 1]
    try:
        v3.UseColorPaletteForBackground = 0
    except Exception:
        pass
    d3 = Show(warp, v3)
    ColorBy(d3, ("POINTS", "Mach"))
    GetColorTransferFunction("Mach").ApplyPreset("Viridis", True)
    d3.SetScalarBarVisibility(v3, True)
    v3.ResetCamera()
    cam = v3.GetActiveCamera(); cam.Elevation(25); cam.Azimuth(-35)
    Render(v3)
    SaveScreenshot(f"{out}_Mach_revolved.png", v3, ImageResolution=[1400, 900])
print("done")
