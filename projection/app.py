"""The whole run: from an NRRD file and a CSV file to an MP4 video (ALGORITHM.md, section 6)."""

import time
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np

from .errors import InputError, InvalidPlaneError
from .intensity import IntensityMapper
from .projector import FastProjector
from .readers import PlaneReader, load_volume
from .video import VideoWriter, frame_shape, place

DEFAULT_FPS = 10  # playback rate of the video (FR-22a)


@dataclass(frozen=True)
class Report:
    """What the run did and how fast (FR-23)."""

    frames: int
    invalid: int
    frame_shape: tuple
    load_seconds: float
    projection_fps: float
    end_to_end_fps: float


class ProjectionApp:
    """Connects the parts. The projector and the mapper can be replaced (Strategy pattern)."""

    def __init__(self, projector=None, mapper=None, fps=DEFAULT_FPS, strict=False, log=print):
        self.projector = projector or FastProjector()
        self.mapper = mapper or IntensityMapper()
        self.fps = fps
        self.strict = strict
        self.log = log

    def run(self, volume_path, planes_path, video_path):
        video_path = _check_output(video_path)

        # 1. Load and map the volume once (FR-20). Counted as load time, not as projection.
        start = time.perf_counter()
        volume = load_volume(volume_path)
        mapped = self.mapper.map(volume)
        mapped.padded                                   # build the zero border now
        load_seconds = time.perf_counter() - start

        # 2. Read and validate all planes before projecting any (FR-10).
        entries = self.validate(PlaneReader().read(planes_path), max_side=2 * volume.diagonal)
        invalid = [entry for entry in entries if not entry.valid]
        if invalid:
            summary = error_summary(entries)
            if self.strict:
                raise InputError(summary + "\nstrict mode: no video was written")   # FR-12
            if len(invalid) == len(entries):
                raise InputError(summary + "\nno valid plane: no video was written")  # FR-8
            self.log("Warning: " + summary)                                         # FR-11

        # 3. Project every plane into frames of one size and write the video.
        shape = frame_shape([entry.plane.image_shape for entry in entries if entry.valid])
        black = np.zeros(shape, dtype=np.uint8)
        buffer = np.zeros(shape, dtype=np.uint8)       # reused for every frame
        projection_seconds = 0.0
        start = time.perf_counter()
        with VideoWriter(video_path, shape, self.fps) as writer:
            for entry in entries:
                frame_start = time.perf_counter()
                if entry.valid:
                    frame = place(self.projector.project(mapped, entry.plane), shape, buffer)
                else:
                    frame = black
                projection_seconds += time.perf_counter() - frame_start
                writer.write(frame)
        total_seconds = time.perf_counter() - start

        return Report(
            frames=len(entries),
            invalid=len(invalid),
            frame_shape=shape,
            load_seconds=load_seconds,
            projection_fps=len(entries) / max(projection_seconds, 1e-9),
            end_to_end_fps=len(entries) / max(total_seconds, 1e-9),
        )

    @staticmethod
    def validate(entries, max_side):
        """Add the size check of FR-19a, which needs the volume, to the CSV entries."""
        checked = []
        for entry in entries:
            if entry.valid:
                try:
                    entry.plane.check_size(max_side)
                except InvalidPlaneError as error:
                    entry = replace(entry, plane=None, error=str(error))
            checked.append(entry)
        return checked


def error_summary(entries):
    """All plane errors in one message, with CSV line numbers (FR-10)."""
    invalid = [entry for entry in entries if not entry.valid]
    lines = [f"  line {entry.line}: {entry.error}" for entry in invalid]
    return f"{len(invalid)} of {len(entries)} planes are invalid:\n" + "\n".join(lines)


def _check_output(path):
    path = Path(path)
    if path.suffix.lower() != ".mp4":
        raise InputError(f"the output file must end with .mp4: {path}")
    if not path.parent.resolve().is_dir():
        raise InputError(f"output folder not found: {path.parent}")
    return path
