"""Demo: project a list of planes through a volume into a video.

Usage:
    python Ex0.py <file.nrrd> <file.csv> <file.mp4> [--strict] [--fps N] [--percentiles LOW HIGH]

Exit codes: 0 success (possibly with warnings), 1 the run stopped on an error, 2 bad arguments.
"""

import argparse
import sys

from projection import InputError
from projection.app import DEFAULT_FPS, ProjectionApp
from projection.intensity import IntensityMapper


def parse_arguments(argv):
    parser = argparse.ArgumentParser(description="Project planes of a 3D volume into a video.")
    parser.add_argument("volume", help="input volume, NRRD file")
    parser.add_argument("planes", help="input plane list, CSV file")
    parser.add_argument("video", help="output video, MP4 file")
    parser.add_argument(
        "--strict", action="store_true",
        help="stop without a video if any plane is invalid",
    )
    parser.add_argument(
        "--fps", type=float, default=DEFAULT_FPS,
        help=f"playback rate of the video (default {DEFAULT_FPS})",
    )
    parser.add_argument(
        "--percentiles", type=float, nargs=2, metavar=("LOW", "HIGH"),
        help="map gray levels by these percentiles of the volume instead of min/max, e.g. 1 99",
    )
    arguments = parser.parse_args(argv)
    if arguments.fps <= 0:
        parser.error("--fps must be positive")
    return arguments


def main(argv=None):
    arguments = parse_arguments(argv)
    try:
        percentiles = arguments.percentiles or (None, None)
        app = ProjectionApp(
            mapper=IntensityMapper(*percentiles),
            fps=arguments.fps,
            strict=arguments.strict,
            log=lambda message: print(message, file=sys.stderr),
        )
        report = app.run(arguments.volume, arguments.planes, arguments.video)
    except (InputError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    rows, cols = report.frame_shape
    print(f"Wrote {report.frames} frames of {cols} x {rows} to {arguments.video}"
          + (f" ({report.invalid} black for invalid planes)" if report.invalid else ""))
    print(f"Load time (read + intensity mapping): {report.load_seconds:.2f} s")
    print(f"Projection FPS: {report.projection_fps:.1f}")
    print(f"End-to-end FPS (including video writing): {report.end_to_end_fps:.1f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
