# Software Requirements Specification – Plane Projection

## 1. Introduction

### 1.1 Purpose

This document defines what the program must do. The assignment leaves many details open; each
such detail is decided here, with the reason for the decision.

### 1.2 Definitions

| Term | Meaning |
|---|---|
| Volume | The 3D matrix `M[x][y][z]` read from the NRRD file |
| Voxel | One entry of the volume |
| Plane | One CSV row: a triangle (3 points) or a trapezoid (4 points) |
| Frame | The 2D image of one plane, one frame of the output video |
| EPS | Tolerance for geometric checks, `0.001` |

## 2. Input

### 2.1 Volume (NRRD)

- **FR-1** The program reads a 3D volume from an NRRD file.
- **FR-2** Supported voxel types: unsigned 8, 16 and 32 bit integers.
- **FR-3** Supported sizes: `1 ≤ sx, sy, sz < 1024`.

### 2.2 Planes (CSV)

- **FR-4** The first line is a header: `Number of Points (3 or 4),x1,y1,z1,x2,y2,z2,x3,y3,z3,x4,y4,z4`.
- **FR-5** Each following line is one plane. It starts with the number of points, 3 or 4,
  followed by the coordinates. For a triangle the last three columns are empty.
- **FR-6** Point order:
  - Triangle: `a, b, c`, where `a` is the apex and `b→c` is the base.
  - Trapezoid: `a1, b, a2, c`, where the legs are `a1→b` and `a2→c`, `a1→a2` is the top and
    `b→c` is the base.
  - *Reason:* the order `a1, a2, b, c` written in the assignment's Q&A does not fit the
    lecturer's own example (`lecturer_example.csv`, row 4): with it the legs are 300 and 400.
    With `a1, b, a2, c` both legs are 502.49. Row 2 fits both orders.
- **FR-7** Coordinates are voxel indices, as real numbers. They may be outside the volume.
  - *Reason:* this is what the assignment's algorithm assumes, and it is simpler.
  - *Limitation:* NRRD voxels are not always cubes (e.g. 1 × 1 × 1.3 mm). For such volumes the
    image is stretched along the longer voxel axis. Conversion to millimeters is a possible
    extension.

## 3. Validation

### 3.1 File-level errors – the program stops

- **FR-8** The program stops with a clear message and a non-zero exit code, and writes no
  video, if:
  - an input file does not exist or cannot be read;
  - the NRRD file is not a valid 3D volume of a supported type (FR-2, FR-3);
  - the CSV file has no header or no planes;
  - all planes are invalid.

### 3.2 Plane-level errors

- **FR-9** A plane is invalid if any of the following holds:
  1. The number of points is not 3 or 4, or the number of values does not match it.
  2. A value is not a finite number.
  3. Triangle: `|dist(a,b) − dist(a,c)| ≥ EPS` (not isosceles).
  4. Triangle: the points are on one line, or two of them are the same point.
  5. Trapezoid: `|dist(a1,b) − dist(a2,c)| ≥ EPS` (legs not equal).
  6. Trapezoid: `dist(a1,a2) > dist(b,c)` (top longer than base).
  7. Trapezoid: the four points are not on one plane (distance of `a2` from the plane of
     `a1, b, c` is `≥ EPS`).
  8. Trapezoid: the legs cross (the top and the base point in opposite directions).
- **FR-10** All planes are validated **before** any projection, and all errors are reported
  together, with their CSV line numbers. Example:
  `2 of 30 planes are invalid: line 4: triangle is not isosceles (|ab|=497.39, |ac|=476.86); line 8: value 'abc' is not a number`.
- **FR-11** Default mode: an invalid plane produces a **black frame**, the warning is printed and
  the run continues.
  - *Reason:* frame N in the video always matches plane N in the CSV. Skipping a plane would
    shift all following frames.
  - *Reason for rejecting non-isosceles triangles instead of drawing them:* the algorithm steps
    the same number of times on both legs. With unequal legs one side does not reach its end
    point or passes it, and the rows are not parallel to the base, so the image does not show
    the requested plane.
- **FR-12** Strict mode (`--strict`): if any plane is invalid, the program prints all errors and
  stops before projecting. No video is written.

### 3.3 Not an error

- **FR-13** A valid plane that is partly or completely outside the volume is not an error. The
  parts outside the volume are black. No warning is printed.

## 4. Projection

- **FR-14** Each valid plane is projected using the assignment's algorithm: rows run from the
  apex (`a`, or the top `a1→a2`) to the base, in steps of length 1; each row runs between the two
  legs in steps of length 1.
- **FR-15** Both end points of every row are included (`x1 ≤ d12`), so a row of length `d` has
  `floor(d) + 1` samples.
- **FR-16** The point on row `y` of each leg is computed directly (`a1 = a + y·v_ab`), not by
  adding steps, so rounding errors do not accumulate.
- **FR-17** Sampling uses the **nearest voxel** (rounding each coordinate).
  - *Reason:* speed, and the image shows only values that were actually measured.
    Interpolation creates values that were never measured.
- **FR-18** Each row is centered horizontally. When it cannot be centered exactly, it is shifted
  half a pixel to the left.

## 5. Output

### 5.1 Frame size

- **FR-19** All frames have the same size: the largest height and width over all valid planes.
  A smaller image is centered in the frame, with black margins.

### 5.2 Intensity mapping

- **FR-20** Voxel values are mapped linearly to `0..255`, using one range for the whole video.
  - Default: the minimum and maximum of the whole volume.
  - Option: percentiles of the volume (e.g. 1% and 99%), so a few extreme voxels do not make
    the image dark.
  - *Rejected:* a range per frame. The same value would look different in different frames.

### 5.3 Video

- **FR-21** The video has one frame per CSV plane, in the CSV order.
- **FR-22** The video is grayscale, in MP4 format.

### 5.4 Report

- **FR-23** After the run the program prints:
  - the time to load the volume, in seconds;
  - **projection FPS**: frames per second for projection and intensity mapping;
  - **end-to-end FPS**: frames per second including writing the video.

## 6. Non-functional requirements

- **NFR-1 Performance:** on a 500³ volume of 8-bit voxels, projection FPS of at least **100**.
  The assignment's minimum is 30.
- **NFR-2 Correctness:** the fast implementation must give the same images as the simple
  loop-based reference implementation.
- **NFR-3 Robustness:** no input may crash the program with an unhandled exception.
- **NFR-4 Code quality:** object-oriented design, PEP 8, docstrings, automated tests.
- **NFR-5 Environment:** Python 3.10+, with NumPy and common libraries for NRRD and MP4.

## 7. Open questions

- The playback rate of the output video (frames per second of the MP4 file).
- A maximum frame size, for planes that extend far outside the volume (a valid plane can be
  thousands of pixels wide).
