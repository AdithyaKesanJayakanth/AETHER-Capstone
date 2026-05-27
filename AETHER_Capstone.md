# Project AETHER

**Aerodynamic Evaluation of Thermal Hazards in Entry Regimes**
## Multi-Objective Shape Optimization of a Hypersonic Re-entry Capsule Heat Shield

**Focus:** Computational fluid dynamics and aerodynamics  
**Author:** Adithya Kesan Jayakanth  
**Status:** Project plan and intended schedule  
**Work started:** April 2026  
**Planned technical completion:** May 2026  
**Planned final paper and reviews:** June 2026  
**Core tools:** Onshape Education, Gmsh, SU2, ParaView and Python  
**Scope:** Capsule shape at fixed flow conditions

---

## Motivation: From STEM F1 Racing to AETHER

My interest in this project grows out of my work in STEM F1 Racing, where I used CAD, aerodynamic simulation and iterative design to explore how geometry changes performance. That experience made me interested in understanding why a shape works and using simulation results to guide the next design decision.

My visit to ISRO inspired me to take that interest further into aerospace engineering. I became interested in applying the same process of modeling, simulation and design comparison to a capsule entering the atmosphere. AETHER is a natural extension of my STEM F1 Racing work: it builds on the tools and engineering approach I have used while introducing a new physical challenge—surface heating in high-speed flow.

The change in the role of drag is particularly interesting to me. In STEM F1 Racing, reducing aerodynamic resistance supports speed. For a re-entry capsule, drag helps slow the vehicle, while surface heating introduces another design consideration. This leads to my central question: how can I shape a capsule to produce useful aerodynamic drag while limiting peak heat flux?

| Connection | STEM F1 Racing | Project AETHER |
|---|---|---|
| Geometric design | Model and refine a race-car shape | Parameterize the capsule nose, shoulder and rear-body angle |
| Simulation | Examine airflow and aerodynamic performance | Examine compressible flow, the bow shock and surface heating |
| Iteration | Compare designs and use results to guide changes | Compare capsule profiles using drag and heat-flux results |
| Engineering judgment | Relate geometry changes to racing objectives and constraints | Assess drag–heating trade-offs within a defined flow condition |
| Communication | Explain the reasoning behind design choices | Present a reproducible study and defend its conclusions |

The continuity is in my engineering method. Hypersonic capsule flow introduces shock waves and thermal effects that require new physical models and validation. I want AETHER to show how I can build on my existing design experience while learning to test the assumptions behind a more demanding simulation.

## 1. Research Question

**How do nose radius, rear-body cone angle and shoulder radius affect aerodynamic drag and peak surface heat flux on a blunt capsule at a specified hypersonic flow condition?**

I want to understand how capsule shape influences two important features of atmospheric entry: aerodynamic drag and surface heating. My plan is to compare a bounded family of capsule profiles and identify shapes that offer favorable performance. I will investigate whether a trade-off exists; some geometric changes may improve both objectives.

I am focusing on the external shape of the heat shield at a fixed flow condition. Heat-shield thickness, internal temperature, ablation and complete re-entry trajectories are outside this study.

## 2. Core Objective

My objective is to identify nondominated feasible shapes that:

- maximize drag coefficient, using the same reference area for every candidate;
- minimize the maximum local convective heat flux over the defined heat-shield surface.

At fixed freestream conditions and reference area:

\[
D = \tfrac12\rho_\infty V_\infty^2 A_{ref} C_D
\]

Thus, maximizing drag coefficient also maximizes drag force for this comparison. Greater drag at this condition does not establish lower heating or acceptable deceleration over a complete flight.

\[
\min_X [-C_D(X),\;q''_{max}(X)]
\]

I will report the best trade-offs I find within the sampled geometry bounds and the limitations of that search.

## 3. Geometry: One Capsule Family

I will use a smooth, axisymmetric blunt capsule profile with three design parameters:

| Parameter | Definition | Purpose |
|---|---|---|
| Nose radius | Radius of curvature of the rounded nose | Explore bluntness |
| Rear-body cone angle | Angle between the straight rear-body sidewall and the capsule axis, defined in a labeled sketch | Explore aft-body shape and its effect on total drag |
| Shoulder radius | Radius of the rounded forebody-to-aft-body transition | Explore local curvature and heating |

My capsule family will use an Apollo/Orion-inspired rounded forebody and tapered rear body, with its own explicitly defined geometry. I will fix maximum capsule diameter D, reference area A_ref = pi D²/4, nominal mass m and the rear closure radius. I will construct the forebody and shoulder using smooth tangent joins. I will vary the rear-body angle and derive the corresponding aft length from the fixed closure radius; I will record total length and enclosed volume and reject invalid or impractical shapes.

I will express the radius variables as R_n/D and R_s/D; I will express the rear-body cone angle in degrees. The angle is not a radius ratio. A larger nose curvature radius means a flatter local nose.

Mass is a fixed bookkeeping assumption for the instantaneous drag deceleration D_drag/m. It does not enter the steady external-flow solution, and this study does not establish how structure or ballast would preserve mass as geometry changes. Using D_drag for force avoids confusing drag with capsule diameter D.

Changing the rear-body angle may affect total drag more than front-shield heating. I will measure that sensitivity to determine how strongly each variable influences the two objectives. I will integrate drag over the complete modeled capsule, while extracting the heat-flux objective over the consistently defined front shield and shoulder.

I will start by varying nose radius and rear-body cone angle with shoulder radius fixed. I will add shoulder-radius variation once the baseline and mesh workflow work reliably.

I will create the parameterized meridional sketch in Onshape and revolve it for a 3-D inspection model. I will export suitable geometry to Gmsh and preserve a labeled 2-D section for the axisymmetric CFD mesh. I will check the geometry-transfer route with the baseline before generating a family of shapes.

I may use Python to generate the equivalent parametric profile for automated meshing using the same parameter table. I will verify that the scripted profile matches the Onshape definition. I will automate CAD operations only if they simplify the workflow.

I will reject shapes with intersecting surfaces, negative dimensions, sharp unintended corners or invalid tangent connections. Every change in nose radius will be represented in the actual CFD geometry.

## 4. Simulation Scope

I will use **SU2** as my CFD solver and pin a tested version. I will confirm its compressible axisymmetric formulation and thermal outputs with the baseline before launching the shape sweep.

| Tool | Assigned role |
|---|---|
| Onshape Education | Parameterized capsule CAD and geometry inspection; use the eligible education plan for educational work |
| Gmsh | Main mesh generator; script repeatable meshes and export a supported SU2 mesh |
| Salome | Alternative only if the Gmsh workflow proves unsuitable; learning both is unnecessary |
| SU2 | Compressible viscous-flow and surface-heating calculations |
| ParaView | Pressure, Mach, temperature, heat-flux and shock visualizations |
| Python | Parameter tables, case execution, result extraction and Pareto plots |

I will choose a mesh topology that provides good cell quality with suitable near-wall layers, shock resolution and smooth cell-size transitions. A revolved ParaView visualization of an axisymmetric result is a visualization of that solution, not a full 3-D CFD calculation.

My simulations will use:

- steady, compressible, viscous flow with the energy equation;
- an axisymmetric formulation at zero angle of attack;
- one documented freestream condition shared by all shapes;
- one common prescribed wall temperature;
- a consistent gas, viscosity and thermal-conductivity model;
- a laminar assumption only where supported by the selected reference condition.

A planar 2-D solution is not interchangeable with an axisymmetric capsule solution. I will verify the chosen solver's axisymmetric implementation and force normalization before using it.

**I will select one Mach-5-or-higher flow condition from an accessible published blunt-body benchmark.** Mach 5 is a conventional hypersonic classification, not a unique re-entry velocity or a threshold at which shocks first appear. Standard atmosphere tables can supply ambient properties at a chosen altitude, but they do not select the Mach number, wall temperature or a validated case.

I will calculate velocity from the selected Mach number and speed of sound using the chosen gas model. If I use an atmospheric condition, I will document the atmosphere model and its altitude range. For my first study, I will match a benchmark condition. I will record Mach number, static pressure, static temperature, Reynolds number or its inputs, body size, wall temperature and gas properties. Mach number alone does not define the heating problem.

I will select a benchmark whose physical regime is compatible with a manageable gas model. If high-temperature chemistry or thermal nonequilibrium is essential to a candidate benchmark, I will select a condition compatible with the intended scope. I will limit any perfect-gas conclusions to the regime where that approximation is defensible.

### How I will calculate surface heating

To predict local wall heat flux, I will solve viscous flow and energy with a suitable thermal wall boundary condition. I will use a prescribed wall temperature and extract the resulting conductive heat flux at the wall, documenting the solver's sign convention.

An optional Euler calculation may help debug the initial shock and pressure solution, but it cannot supply the required viscous boundary-layer heat transfer. Only the viscous energy-equation results enter the heating comparison. An adiabatic wall imposes zero heat transfer; a prescribed heat-flux wall imposes the quantity this project seeks to predict. Neither is the intended boundary condition for the main shape comparison.

## 5. My Workflow

1. **Baseline:** I will set up one documented blunt-body case before automating anything.
2. **Numerical checks:** I will inspect forces, wall heat flux, residuals and physical fields; refine the mesh.
3. **Geometry:** I will generate valid profiles from a small configuration file.
4. **Initial sweep:** I will compare approximately 5–10 cases varying nose radius and rear-body cone angle.
5. **Selective expansion:** I will include shoulder radius and refine promising regions, aiming for a small, converged set in Phase 1; expand toward approximately 20–40 valid designs only in a later study if runtime permits.
6. **Automation:** I will write Python scripts to generate inputs, launch cases, collect metrics and record failures.
7. **Comparison:** I will plot drag coefficient against peak surface heat flux and identify nondominated cases.
8. **Final checks:** I will refine the baseline and two or three selected shapes before drawing conclusions.

The case counts are planning targets, not scientific completion requirements. A conventional parameter sweep with targeted refinement is sufficient; an advanced optimization algorithm is optional.

## 6. Measurements

| Output | What I will learn |
|---|---|
| Drag coefficient and drag force | Aerodynamic resistance at the chosen condition |
| Peak surface heat flux and its location | Worst local heating on the defined shield surface |
| Surface heat-flux distribution | Whether heating moves from nose to shoulder or another location |
| Surface pressure distribution | How geometry changes pressure loading |
| Bow-shock stand-off distance | Distance from nose to detached shock along the axis |
| Mach and temperature fields | Flow structure around selected shapes |
| Boundary-layer profiles at selected stations | Near-wall velocity and thermal gradients |

I will examine the bow shock and boundary layer as distinct flow features, investigating changes in shock position, the region between shock and body, and near-wall gradients. I will identify any shock–boundary-layer interaction from the computed flow rather than assume it occurs.

I will use the same heat-shield surface definition in every case. I will inspect any isolated numerical peak, especially at a geometry or boundary junction, and resolve it through mesh and geometry checks rather than silently excluding it.

## 7. Verification and Validation

### Reference comparison

I will compare the baseline with independent published data at matching conditions. I will seek both aerodynamic and heat-transfer evidence. If one benchmark does not supply both, I will use a separate appropriate heat-transfer benchmark and state what each comparison supports.

Reproducing a software tutorial is useful for setup but is not, by itself, independent experimental validation.

### Mesh and convergence checks

- I will use at least three systematically refined meshes for the baseline.
- I will assess drag and peak heat flux separately; convergence of drag does not establish convergence of heating.
- I will refine the near-wall region and shock region consistently.
- I will check that the outer boundary location does not materially affect the baseline.
- I will monitor integrated forces and heating as well as residuals.
- I will refine selected finalists enough to determine whether their ranking survives numerical changes.

I will set justified acceptance tolerances before selecting a preferred design. If apparent improvements are comparable to numerical uncertainty, I will report the designs as unresolved rather than claiming a meaningful advantage.

## 8. Planned Analysis

The main figure is a scatter plot of **drag coefficient versus peak heat flux**, with the baseline and nondominated shapes highlighted.

I will explain why selected shapes perform differently using their pressure, heat-flux and flow-field plots. I will select a preferred compromise using an explicit rule, such as the lowest peak heat flux among designs meeting a stated drag target. I will show sensitivity to that selection rule where useful.

| Metric | Baseline | Highest-drag case | Lowest-heating case | Selected compromise |
|---|---:|---:|---:|---:|
| Nose radius | | | | |
| Rear-body cone angle | | | | |
| Shoulder radius | | | | |
| Drag coefficient | | | | |
| Peak heat flux | | | | |
| Peak-heating location | | | | |
| Shock stand-off distance | | | | |
| Mesh/convergence checks passed? | | | | |

A useful conclusion could show a favorable compromise, one shape improving both objectives, or no reliable improvement over the baseline. I will base my conclusions on simulation results supported by the numerical checks.

## 9. Planned Deliverables

1. A parameterized capsule model and labeled geometry sketch.
2. One reproducible CFD baseline and its reference comparison.
3. Python scripts for case generation, execution and data extraction.
4. A results table retaining both successful and failed cases.
5. A drag–heating trade-space plot and selected flow-field visualizations.
6. A concise technical report explaining methods, evidence, findings and limitations.
7. A reproducible repository with exact software versions and run instructions.
8. A short presentation explaining my methods, findings and engineering decisions.

I will keep the results in a simple CSV table with links to the corresponding configurations and output files.

## 10. Project Timeline: April–June 2026

I began work on AETHER in April 2026. My plan was to complete the technical investigation by the end of May 2026, then finalize the paper and complete technical reviews in June 2026. These dates record my intended schedule; completed results and reviews will be documented separately.

| Period | Planned focus | Intended milestone |
|---|---|---|
| April 2026 | Geometry definition, mesh generation, SU2 baseline and initial shape comparisons | A working CFD workflow and preliminary drag–heating results |
| May 2026 | Complete the shape study, refine selected cases, finish validation and interpret the trade-offs | Technical investigation and principal figures complete by the end of May |
| June 2026 | Prepare and finalize the paper, obtain technical reviews and address feedback | Final paper, review record and reproducible supporting materials |

### April 2026 — Initial Four-Week Roadmap

My initial four-week goal was to establish one credible CFD workflow and a preliminary shape comparison. The following steps describe that plan; they do not imply that each milestone has already been achieved.

| Week | Focus | Concrete output |
|---|---|---|
| 1 | Geometry and physics | Onshape baseline, labeled parameter definitions, one selected benchmark and a freestream/wall-condition table |
| 2 | Mesh and boundary conditions | Gmsh mesh, correct axis and wall markers, near-wall layers, shock-region refinement and three baseline mesh levels |
| 3 | SU2 baseline and variations | Stable viscous baseline, reference and mesh checks, then a small set of geometric variations |
| 4 | Analysis and plots | ParaView fields, drag and heat-flux distributions, preliminary nondominated set and a short limitations report |

#### Week 1 — Geometry and math

I will fix diameter, reference area and nominal mass. I will parameterize R_n/D, R_s/D and the rear-body cone angle. I will confirm smooth joints and a reproducible closure rule. I will define the fluid-domain boundaries and choose a documented Mach-5+ condition compatible with the intended gas model.

#### Week 2 — Mesh and boundary layers

I will import the baseline section into Gmsh. I will refine near the wall and where the detached bow shock is expected, with gradual transitions between cell sizes. I will establish coarse, medium and fine baseline meshes. I will check cell quality, markers, axis treatment and SU2 import before creating variants.

#### Week 3 — CFD solving

I will run compressible Navier–Stokes with energy and a common prescribed wall temperature. I will check drag and heat-flux stability alongside residuals. I will complete the baseline reference comparison and mesh checks before interpreting shape changes. I will aim for approximately 5–10 valid cases in the initial sprint if resources permit; I will use one-variable perturbations first to make effects interpretable.

#### Week 4 — Trade-space analysis

I will visualize shock location, pressure, Mach and wall heating. I will extract total capsule drag coefficient and front-shield peak heat flux. I will plot the feasible cases, mark the nondominated set and recheck the baseline plus selected promising cases. I will label the frontier preliminary when sampling or numerical uncertainty is unresolved.

### Review at the End of April

If baseline heating or mesh convergence is unresolved at the end of Week 3, I will use Week 4 to fix and document it. I will carry any unresolved checks into the May work period and use the checks in Section 7 to decide when the analysis is ready for conclusions. Any change to the original schedule will be recorded rather than treating a target date as evidence of completion.

### May 2026 — Planned Technical Completion

My May target was to complete the geometry comparisons, repeat selected cases with refined meshes, finish the reference comparisons and prepare the main figures. The technical study would be ready for the paper once I could explain the observed drag–heating relationships and support them with the validation evidence.

### June 2026 — Planned Final Paper and Technical Reviews

My June plan was to bring the methods, results and limitations into a final paper and seek technical review of the geometry, CFD assumptions, mesh convergence and conclusions. I would record the feedback, my responses and any resulting revisions before finalizing the paper and supporting repository. Reviewer names, affiliations and review dates will be recorded only when confirmed.

---

## 11. Scope Boundary

I am keeping the scope focused by excluding trajectory integration, transient internal TPS model, ablation, material optimization, reacting-flow development, AI-agent competition, adaptive-fidelity system, surrogate-method comparison, custom thermal index or full robust optimization.

If time permits, I may check a few selected shapes at a second compatible flow condition. This tests whether the ranking changes without adding a new subsystem.

## 12. Questions I Want to Answer

By the end of the project, I want to explain:

- why base diameter and reference area are fixed;
- how the three shape parameters change the actual geometry;
- the difference between a bow shock and a boundary layer;
- why wall temperature and gas properties affect predicted heat flux;
- why an adiabatic wall cannot answer the heating objective;
- why peak heat flux needs its own mesh-convergence check;
- what a nondominated design means and why it is not an absolute sweet spot;
- where the gas model and fixed-condition study cease to apply;
- which result changed my original expectation.

I will document any AI assistance in code or writing and check its outputs. I will explain my own design choices, numerical checks and interpretation of the results.

## 13. Technical Starting References

I will use official documentation for solver setup and a primary research source for the selected physical benchmark. A general project-ideas article is inspiration, not validation evidence.

- [SU2: Markers and Boundary Conditions](https://su2code.github.io/docs_v7/Markers-and-BC/) — viscous wall and thermal boundary definitions.
- [SU2: Laminar Flat Plate](https://su2code.github.io/tutorials/Laminar_Flat_Plate/) — introductory viscous-flow workflow; not a substitute for a blunt-body heating benchmark.
- [Onshape Education](https://www.onshape.com/en/education/plans) — eligible education access and plan details.
- [Gmsh](https://gmsh.info/) — mesh generation and documentation.
- [SU2 configuration template](https://github.com/su2code/SU2/blob/master/config_template.cfg) — inspect the matching pinned release for axisymmetric and solver settings.
- [ParaView](https://www.paraview.org/) — visualization software.
- [Ansys Fluent: Modeling Hypersonic Flow](https://ansyshelp.ansys.com/public/Views/Secured/corp/v252/en/flu_tg/flu_tg_reentry_capsule.html) — context for high-temperature model limitations; advanced models are not required here.

**My first technical decision:** select a reproducible blunt-body benchmark with usable surface-heating data and a compatible flow regime. I will freeze the operating condition and SU2 version after that baseline works.
