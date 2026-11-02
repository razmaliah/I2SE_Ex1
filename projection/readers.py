"""Reading the input files: the volume (NRRD) and the plane list (CSV)."""

import csv
from dataclasses import dataclass
from pathlib import Path

import nrrd

from .errors import InputError, InvalidPlaneError
from .plane import Plane
from .volume import Volume

HEADER_START = "number of points"


def load_volume(path):
    """Read an NRRD file into a ``Volume`` (FR-1 – FR-3). Problems raise ``InputError``."""
    path = Path(path)
    if not path.is_file():
        raise InputError(f"volume file not found: {path}")
    try:
        data, _header = nrrd.read(str(path))     # data[x, y, z], in the order of 'sizes'
    except Exception as error:                   # the library raises many kinds of errors
        raise InputError(f"cannot read NRRD file {path}: {error}") from error
    return Volume(data)


@dataclass(frozen=True)
class PlaneEntry:
    """One plane of the CSV file: its line number and either a plane or an error."""

    line: int
    plane: Plane = None
    error: str = None

    @property
    def valid(self):
        return self.plane is not None


class PlaneReader:
    """Reads the plane list (FR-4 – FR-7).

    The first line is the header. Every other line is one plane: the number of points
    (3 or 4) and then their coordinates. Empty lines and lines starting with ``#`` are
    ignored. A bad line does not stop the reading: it becomes an entry with an error, so
    all errors can be reported together (FR-10).
    """

    def read(self, path):
        path = Path(path)
        if not path.is_file():
            raise InputError(f"plane file not found: {path}")
        try:
            with path.open(newline="", encoding="utf-8-sig") as file:
                rows = list(csv.reader(file))
        except (OSError, UnicodeDecodeError, csv.Error) as error:
            raise InputError(f"cannot read CSV file {path}: {error}") from error

        lines = [
            (number, row)
            for number, row in enumerate(rows, start=1)
            if any(cell.strip() for cell in row) and not row[0].lstrip().startswith("#")
        ]
        if not lines or not lines[0][1][0].strip().lower().startswith(HEADER_START):
            raise InputError(
                f"{path}: the first line must be the header "
                "'Number of Points (3 or 4),x1,y1,z1,...'"
            )
        entries = [self._entry(number, row) for number, row in lines[1:]]
        if not entries:
            raise InputError(f"{path}: the file has no planes")
        return entries

    @staticmethod
    def _entry(number, row):
        try:
            return PlaneEntry(number, plane=Plane.from_points(parse_points(row)))
        except InvalidPlaneError as error:
            return PlaneEntry(number, error=str(error))


def parse_points(row):
    """Turn one CSV row into a list of 3 or 4 points; raises ``InvalidPlaneError``."""
    cells = [cell.strip() for cell in row]
    try:
        count = int(float(cells[0]))
    except ValueError:
        raise InvalidPlaneError(f"number of points '{cells[0]}' is not a number") from None
    if count not in (3, 4) or float(cells[0]) != count:
        raise InvalidPlaneError(f"number of points must be 3 or 4, not '{cells[0]}'")

    needed = 3 * count
    values = cells[1:1 + needed]
    extra = [cell for cell in cells[1 + needed:] if cell]
    if len(values) < needed or not all(values):
        raise InvalidPlaneError(f"{count} points need {needed} numbers")
    if extra:
        raise InvalidPlaneError(f"{count} points need {needed} numbers, but there are more")

    numbers = []
    for value in values:
        try:
            numbers.append(float(value))
        except ValueError:
            raise InvalidPlaneError(f"value '{value}' is not a number") from None
    return [numbers[i:i + 3] for i in range(0, needed, 3)]
