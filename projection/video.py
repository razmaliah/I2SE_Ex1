"""Building the output video (FR-11, FR-19, FR-21, FR-22)."""

import numpy as np
import imageio_ffmpeg


def frame_shape(shapes):
    """The frame size: the largest height and width, rounded up to even numbers.

    MP4 (H.264, yuv420p) needs an even width and height; the extra row or column is black.
    """
    rows = max(shape[0] for shape in shapes)
    cols = max(shape[1] for shape in shapes)
    return rows + rows % 2, cols + cols % 2


def place(image, shape):
    """Center ``image`` in a black frame of ``shape`` (FR-19)."""
    frame = np.zeros(shape, dtype=np.uint8)
    top = (shape[0] - image.shape[0]) // 2
    left = (shape[1] - image.shape[1]) // 2
    frame[top:top + image.shape[0], left:left + image.shape[1]] = image
    return frame


class VideoWriter:
    """Writes grayscale frames of one size to an MP4 file. Use as a context manager."""

    def __init__(self, path, shape, fps):
        self.path = str(path)
        self.shape = shape
        self.fps = fps
        self._frames = None
        self.count = 0

    def __enter__(self):
        rows, cols = self.shape
        self._frames = imageio_ffmpeg.write_frames(
            self.path,
            size=(cols, rows),
            pix_fmt_in="gray",
            fps=self.fps,
            codec="libx264",
            quality=8,
            macro_block_size=1,          # never resize: the size is already even
            ffmpeg_log_level="error",
        )
        self._frames.send(None)          # start ffmpeg
        return self

    def write(self, frame):
        if frame.shape != self.shape or frame.dtype != np.uint8:
            raise ValueError(f"frame must be uint8 of shape {self.shape}")
        self._frames.send(np.ascontiguousarray(frame).tobytes())
        self.count += 1

    def __exit__(self, *exc):
        self._frames.close()
        return False
