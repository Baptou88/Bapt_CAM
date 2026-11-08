# Bapt's CAM Workbench

A FreeCAD workbench for CNC programming — from machining geometry to G-code generation.

## About

I'm Bapt — programmer/machinist for 10+ years on various CNC machines (DMG, Huron…) with Heidenhain and Siemens controllers. I built this workbench to bridge my manufacturing and software skills, using FreeCAD as a foundation.

**Version:** 0.2.0  
**License:** LGPL-2.1-or-later

![Bapt's CAM Workbench Screenshot v0.0.1](/resources/image.bmp)

![Bapt's CAM Workbench Screenshot v0.0.3](/resources/Animation.gif)

![Bapt's CAM Workbench Screenshot v0.1.2](/resources/image3.png)

## Philosophy

After years of CNC programming, I found it's best to correctly define machining geometries *before* defining machining cycles. This is why the workflow starts with creating geometry objects (DrillGeometry, ContourGeometry, etc.) and then associating operations to them.

## Features

### Operations

| Operation | Description |
|-----------|-------------|
| **Contournage** | Contouring with approach/retract types (tangential, perpendicular, helical), climb/conventional milling, cutter compensation (G41/G42, computer-side), multi-pass |
| **Perçage (Drill)** | 6 cycle types: simple, peck (deep hole), tapping, boring, reaming, contournage. Configurable peck depth, dwell, thread pitch |
| **Surfaçage** | Surface facing with configurable overlap, parallel passes at set feed rates |
| **Poche (Pocket)** | Pocket milling with 4 fill modes (offset, zigzag, spiral), plunge types (direct, helical, ramp), multi-pass depth |
| **Fraisage adaptatif** | adaptive milling with controlled radial engagement (ae), concentric peel passes |
| **Path** | Custom G-code path with direct input, variables, labels, repeat blocks, parsing and animation |

### Key Capabilities

- **Tool Management** — SQLite-based tool database, multiple tool types (endmill, drill, tap, torus endmill…) with speed/feed, geometry parameters
- **Hole Recognition** — Automatic detection of cylindrical holes perpendicular to workplane, grouped by diameter/depth
- **G-code Visualization** — Real-time 3D path display with color coding (rapid = red, feed = green)
- **Path Animation** — Multi-operation playback with speed control
- **Cutter Compensation** — G41/G42 support (machine or computer-side)
- **Collision Detection** — Volume intersection highlighting between objects
- **Probe Surface** — Automatic surface probing for workpiece measurement
- **MPF Import** — Heidenhain MPF file parser (RL→G41, RR→G42, L→G0/G1…)
- **Contour Geometry** — Basic geometry selection or editable sketcher-based geometry
- **Multi-pass Machining** — Step-down control, axial/radial allowance across all operations
- **Inter-operation Transitions** — Automatic retract/rapid/plunge between operations (same tool or tool change)
- **Post-processing Dialog** — Drag & drop operation reordering, per-operation enable/disable, G-code preview

### Post-Processors

| Post-Processor | Target |
|----------------|--------|
| **ITnc530** | Heidenhain iTNC 530 |
| **Siemens828** | Siemens 828D |

## Installation

1. Copy the `Bapt_CAM` folder into the `Mod` folder of your FreeCAD installation.
2. Restart FreeCAD.

## Usage

1. Select the **Bapt** workbench from the workbenches dropdown.
2. Create a CAM project, define your stock and origin.
3. Create machining geometries (contour, drill, etc.).
4. Create operations associated to those geometries.
5. Post-process to generate G-code.

## Commands

| Icon | Command | Description |
|------|---------|-------------|
| ![](/resources/icons/BaptWorkbench.svg) | `Bapt_CreateCamProject` | Create a new CAM project |
| ![](/resources/icons/Origin.svg) | `Bapt_CreateOrigin` | Create a machining origin (G54, G55…) |
| ![](/resources/icons/Tree_Contour.svg) | `Bapt_CreateContourGeometry` | Create a contour geometry |
| ![](/resources/icons/Tree_Contour.svg) | `Bapt_CreateContourEditableGeometry` | Create an editable contour geometry |
| ![](/resources/icons/Tree_Drilling.svg) | `Bapt_CreateDrillGeometry` | Create a drill geometry |
| ![](/resources/icons/Tree_HoleRecognition.svg) | `Bapt_HoleRecognition` | Auto-detect cylindrical holes |
| ![](/resources/icons/Contournage.svg) | `Bapt_CreateMachiningCycle` | Create a contouring operation |
| ![](/resources/icons/Tree_Drilling.svg) | `Bapt_CreateDrillOperation` | Create a drill operation |
| ![](/resources/icons/Pocket.svg) | `Bapt_CreatePocketOperation` | Create a pocket operation |
| ![](/resources/icons/AdaptativeOp.svg) | `Bapt_CreateAdaptativeOperation` | Create an adaptive/trochoidal operation |
| ![](/resources/icons/Surfacage.svg) | `Bapt_CreateSurfacage` | Create a surfacing operation |
| ![](/resources/icons/ProbeSurface.svg) | `Bapt_CreateProbeFace` | Generate a surface probe |
| ![](/resources/icons/PostProcess.svg) | `Bapt_PostProcessGCode` | Post-process and generate G-code |
| ![](/resources/icons/tool.svg) | `Bapt_ToolsManager` | Open the tool manager |
| ![](/resources/icons/ImportMpf.svg) | `ImportMpf` | Import a Heidenhain MPF file |
| ![](/resources/icons/hotreload.svg) | `Bapt_CreateHotReload` | Hot reload modules (development) |

## TODO

- [ ] 3D toolpath generation
- [ ] 3+2 axis (XY + C) toolpath
- [ ] M90/M91 commands support
- [ ] Additional post-processors (Fanuc, Mazak…)
- [ ] G17/18 in Simulation

## License

This workbench is released under the LGPL-2.1-or-later license.
