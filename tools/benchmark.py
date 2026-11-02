"""Speed measurement for the experiment (TESTING.md, section 6).

Usage:
    python tools/benchmark.py [--repeats N] [--reference-frames N] VOLUME.nrrd:PLANES.csv ...

For each pair, the volume is loaded and mapped once, and every valid plane is projected
``--repeats`` times. Reported: load time, frames, average image size, projection FPS
(median over the repeats) and, for comparison, the reference projector's seconds per frame.
Then the same is done on a random 500³ volume with planes of known sizes.
"""

import argparse
import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from projection import FastProjector, Plane, ReferenceProjector, Volume  # noqa: E402
from projection.app import ProjectionApp  # noqa: E402
from projection.intensity import IntensityMapper  # noqa: E402
from projection.readers import PlaneReader, load_volume  # noqa: E402

RANDOM_PLANES = {
    "slice 500 x 500": [(0, 0, 250), (499, 0, 250), (0, 499, 250), (499, 499, 250)],
    "diagonal triangle": [(249.5, 0, 0), (0, 499, 499), (499, 499, 499)],
    "triangle around a full slice": [(-250, 249.5, 250), (749, -250, 250), (749, 749, 250)],
}


def fps(projector, volume, planes, repeats):
    results = []
    for _ in range(repeats):
        start = time.perf_counter()
        for plane in planes:
            projector.project(volume, plane)
        results.append(len(planes) / (time.perf_counter() - start))
    return statistics.median(results)


def reference_seconds(volume, planes, count):
    sample = planes[:count]
    if not sample:
        return float("nan")
    start = time.perf_counter()
    for plane in sample:
        ReferenceProjector().project(volume, plane)
    return (time.perf_counter() - start) / len(sample)


def mean_size(planes):
    return np.mean([r * c for r, c in (p.image_shape for p in planes)])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("pairs", nargs="*", help="VOLUME.nrrd:PLANES.csv")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--reference-frames", type=int, default=2)
    args = parser.parse_args()
    fast = FastProjector()

    print("| Volume | Planes | Load (s) | Frames | Mean image (pixels) | Projection FPS | Reference (s/frame) |")
    print("|---|---|---|---|---|---|---|")
    for pair in args.pairs:
        volume_path, planes_path = pair.split(":")
        start = time.perf_counter()
        volume = load_volume(volume_path)
        mapped = IntensityMapper().map(volume)
        mapped.padded
        load = time.perf_counter() - start
        entries = ProjectionApp.validate(PlaneReader().read(planes_path), 2 * volume.diagonal)
        planes = [e.plane for e in entries if e.valid]
        print(f"| {Path(volume_path).name} | {Path(planes_path).name} | {load:.2f} | {len(planes)} "
              f"| {mean_size(planes):,.0f} | {fps(fast, mapped, planes, args.repeats):.0f} "
              f"| {reference_seconds(mapped, planes, args.reference_frames):.2f} |", flush=True)

    print()
    print("| Random 500³ uint8 | Image (rows x cols) | Projection FPS |")
    print("|---|---|---|")
    volume = Volume(np.random.default_rng(0).integers(0, 256, (500, 500, 500), dtype=np.uint8))
    volume.padded
    for name, points in RANDOM_PLANES.items():
        plane = Plane.from_points(points)
        rows, cols = plane.image_shape
        result = fps(fast, volume, [plane] * 20, args.repeats)
        print(f"| {name} | {rows} x {cols} | {result:.0f} |", flush=True)


if __name__ == "__main__":
    main()
