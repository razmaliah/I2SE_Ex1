"""Shared helpers: small input files written into pytest's temporary folder."""

import nrrd
import numpy as np
import pytest

HEADER = "Number of Points (3 or 4),x1,y1,z1,x2,y2,z2,x3,y3,z3,x4,y4,z4"


@pytest.fixture
def write_csv(tmp_path):
    """Write a CSV file from a list of lines (the header is added unless ``header=False``)."""

    def write(lines, name="planes.csv", header=True):
        path = tmp_path / name
        path.write_text("\n".join(([HEADER] if header else []) + list(lines)) + "\n")
        return path

    return write


@pytest.fixture
def write_nrrd(tmp_path):
    """Write an NRRD file from an array."""

    def write(data, name="volume.nrrd"):
        path = tmp_path / name
        nrrd.write(str(path), np.asarray(data))
        return path

    return write


@pytest.fixture
def box_volume():
    """A 20 x 20 x 20 volume: value 100 inside the box 5..14, 0 elsewhere."""
    data = np.zeros((20, 20, 20), dtype=np.uint16)
    data[5:15, 5:15, 5:15] = 100
    return data
