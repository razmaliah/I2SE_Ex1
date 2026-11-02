# I2SE Ex1 – Plane Projection of a 3D Volume

Course: Introduction to Software Engineering (OOP, OOD), Ariel University.

## The problem

A 3D medical or scientific scan is stored as a volume: a 3D matrix `M` of size `sx × sy × sz`
whose entries are unsigned integers (8, 16 or 32 bit). Viewers such as 3D Slicer show the volume
as three fixed slices (X, Y, Z). We want to see the volume along **any** plane.

Given a volume `M` and a plane `p`, compute the 2D image of `p` inside `M`. The plane is given by
3 points (an isosceles triangle) or by 4 points (an isosceles trapezoid). For a list of planes,
produce a video with one frame per plane.

As the assignment states, the problem is not well defined for implementation. The decisions
that make it well defined are in the [SRS](docs/SRS.md).

## Scope

In scope:

- Reading a volume from an NRRD file.
- Reading a list of planes from a CSV file (3 or 4 points per plane).
- Validating the input and reporting errors clearly.
- Projecting each plane to a 2D image, fast enough for real-time use (target: 100+ FPS on a
  500³ volume).
- Writing the images as an MP4 video, one frame per plane, in the CSV order.
- A design document, a test strategy and an experiment on real data.

Out of scope:

- Physical (millimeter) coordinates and non-cubic voxel correction. Points are voxel indices.
- Interpolation between voxels. The nearest voxel is used.
- A graphical user interface or interactive plane selection.

## Usage

```
python Ex0.py <file.nrrd> <file.csv> <file.mp4> [--strict]
```

- `file.nrrd` – the input volume.
- `file.csv` – the list of planes.
- `file.mp4` – the output video.
- `--strict` – stop without writing a video if any plane is invalid.

## Repository layout (planned)

| Path | Content |
|---|---|
| `Ex0.py` | Demo entry point |
| `projection/` | Source code |
| `tests/` | Automated tests |
| `docs/` | SRS, algorithm, data set, test strategy, experiment |
| `demo/` | Demo CSV files and output videos |
| `data/` | NRRD files (not committed, see `docs/DATASET.md`) |

## Documents

- [Software Requirements Specification](docs/SRS.md)
- Algorithm – in progress
- Data set – in progress
- Test strategy – in progress
- Experiment and results – in progress

## Status

Planning. An early loop-based prototype (`sample_line.py`, `projection.py`) is kept as the
reference implementation for testing.
