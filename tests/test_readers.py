"""Readers: the NRRD volume and the CSV plane list (FR-1 – FR-8, FR-10)."""

import numpy as np
import pytest

from projection import InputError, Trapezoid, Triangle
from projection.readers import PlaneReader, load_volume

TRIANGLE = "3,0,0,0,4,-3,0,4,3,0,,,"
TRAPEZOID = "4,0,-2,0,4,-5,0,0,2,0,4,5,0"


# --- volume -----------------------------------------------------------------------------


def test_load_volume_keeps_axes_and_values(write_nrrd):
    data = np.arange(2 * 3 * 4, dtype=np.int16).reshape(2, 3, 4) - 10
    volume = load_volume(write_nrrd(data))
    assert volume.shape == (2, 3, 4)
    np.testing.assert_array_equal(volume.data, data)


def test_load_volume_missing_file(tmp_path):
    with pytest.raises(InputError, match="not found"):
        load_volume(tmp_path / "missing.nrrd")


def test_load_volume_not_nrrd(tmp_path):
    path = tmp_path / "bad.nrrd"
    path.write_text("this is not an NRRD file")
    with pytest.raises(InputError, match="cannot read"):
        load_volume(path)


def test_load_volume_2d_is_rejected(write_nrrd):
    with pytest.raises(InputError, match="3D"):
        load_volume(write_nrrd(np.zeros((4, 4), dtype=np.uint8)))


def test_load_volume_float_is_rejected(write_nrrd):
    with pytest.raises(InputError, match="not supported"):
        load_volume(write_nrrd(np.zeros((2, 2, 2), dtype=np.float32)))


# --- CSV --------------------------------------------------------------------------------


def test_reads_triangles_and_trapezoids_with_line_numbers(write_csv):
    entries = PlaneReader().read(write_csv([TRIANGLE, "", "# a comment", TRAPEZOID]))
    assert [entry.line for entry in entries] == [2, 5]
    assert isinstance(entries[0].plane, Triangle)
    assert isinstance(entries[1].plane, Trapezoid)


def test_spaces_and_scientific_notation(write_csv):
    entries = PlaneReader().read(write_csv([" 3 , 0 , 0 , 0 , 4e0 , -3 , 0 , 0.4e1 , 3 , 0 , , , "]))
    assert entries[0].valid


def test_triangle_without_empty_columns(write_csv):
    assert PlaneReader().read(write_csv(["3,0,0,0,4,-3,0,4,3,0"]))[0].valid


@pytest.mark.parametrize(
    "line, message",
    [
        ("5,0,0,0,4,-3,0,4,3,0,,,", "3 or 4"),
        ("3.5,0,0,0,4,-3,0,4,3,0,,,", "3 or 4"),
        ("x,0,0,0,4,-3,0,4,3,0,,,", "not a number"),
        ("3,0,0,0,4,-3,0,4,abc,0,,,", "'abc' is not a number"),
        ("3,0,0,0,4,-3,0,4,3,,,,", "need 9 numbers"),
        ("4,0,0,0,4,-3,0,4,3,0,,,", "need 12 numbers"),
        ("3,0,0,0,4,-3,0,4,3,0,1,2,3", "but there are more"),
        ("3,0,0,0,4,-3,0,4,3,inf,,,", "finite"),
        ("3,0,0,0,4,-3,0,4,3.1,0,,,", "not isosceles"),
    ],
)
def test_bad_line_becomes_an_error_entry(write_csv, line, message):
    entries = PlaneReader().read(write_csv([TRIANGLE, line]))
    assert entries[0].valid
    assert not entries[1].valid
    assert entries[1].line == 3
    assert message in entries[1].error


def test_missing_file(tmp_path):
    with pytest.raises(InputError, match="not found"):
        PlaneReader().read(tmp_path / "missing.csv")


def test_missing_header(write_csv):
    with pytest.raises(InputError, match="header"):
        PlaneReader().read(write_csv([TRIANGLE], header=False))


def test_empty_file(write_csv):
    with pytest.raises(InputError, match="header"):
        PlaneReader().read(write_csv([], header=False))


def test_header_only(write_csv):
    with pytest.raises(InputError, match="no planes"):
        PlaneReader().read(write_csv([]))
