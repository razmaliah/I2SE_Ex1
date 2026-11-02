"""Exceptions of the projection package.

Two kinds of errors, as in the SRS:

- ``InputError``: the input as a whole cannot be used (FR-8). The program stops.
- ``InvalidPlaneError``: one plane is invalid (FR-9). The program shows a black frame
  for it and continues, unless it runs in strict mode (FR-11, FR-12).
"""


class InputError(Exception):
    """A file-level error: missing file, bad volume, empty plane list."""


class InvalidPlaneError(ValueError):
    """A single plane breaks one of the rules of FR-9."""
