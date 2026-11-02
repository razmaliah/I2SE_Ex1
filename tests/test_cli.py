"""End-to-end: run Ex0.py as a user would (TESTING.md, section 5)."""

import subprocess
import sys
from pathlib import Path

import imageio.v3 as iio
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
TRIANGLE = "3,2,10,10,14,4,10,14,16,10,,,"          # inside the box volume
RECTANGLE = "4,0,0,10,19,0,10,0,19,10,19,19,10"     # the full slice z = 10
NOT_ISOSCELES = "3,2,10,10,14,4,10,14,17,10,,,"


def run(*args):
    return subprocess.run(
        [sys.executable, str(ROOT / "Ex0.py"), *map(str, args)],
        capture_output=True, text=True, cwd=ROOT,
    )


def frames_of(path):
    return iio.imread(path)[..., 0]


def test_success(tmp_path, write_nrrd, write_csv, box_volume):
    video = tmp_path / "out.mp4"
    result = run(write_nrrd(box_volume), write_csv([TRIANGLE, RECTANGLE]), video)
    assert result.returncode == 0, result.stderr
    assert "Wrote 2 frames" in result.stdout
    assert "Projection FPS" in result.stdout and "End-to-end FPS" in result.stdout
    frames = frames_of(video)
    assert frames.shape == (2, 20, 20)                     # largest plane: 20 x 20
    assert frames[1, 7:13, 7:13].min() > 200               # the box is white in the slice
    assert frames[1, :3, :3].max() < 20                    # around it is black


def test_invalid_plane_gives_black_frame_and_warning(tmp_path, write_nrrd, write_csv, box_volume):
    video = tmp_path / "out.mp4"
    result = run(write_nrrd(box_volume), write_csv([RECTANGLE, NOT_ISOSCELES, RECTANGLE]), video)
    assert result.returncode == 0, result.stderr
    assert "1 of 3 planes are invalid" in result.stderr
    assert "line 3: triangle is not isosceles" in result.stderr
    frames = frames_of(video)
    assert len(frames) == 3                                # frame N = plane N
    assert frames[1].max() < 20                            # black
    assert frames[0].max() > 200 and frames[2].max() > 200


def test_strict_mode_stops_without_video(tmp_path, write_nrrd, write_csv, box_volume):
    video = tmp_path / "out.mp4"
    result = run(write_nrrd(box_volume), write_csv([RECTANGLE, NOT_ISOSCELES]), video, "--strict")
    assert result.returncode == 1
    assert "line 3" in result.stderr and "strict mode" in result.stderr
    assert not video.exists()


def test_all_planes_invalid_stops(tmp_path, write_nrrd, write_csv, box_volume):
    video = tmp_path / "out.mp4"
    result = run(write_nrrd(box_volume), write_csv([NOT_ISOSCELES, "3,a,b,c"]), video)
    assert result.returncode == 1
    assert "no valid plane" in result.stderr
    assert not video.exists()


def test_plane_larger_than_twice_the_diagonal(tmp_path, write_nrrd, write_csv, box_volume):
    # the volume's diagonal is about 34.6, so a base of 100 is too wide
    huge = "3,0,50,10,60,0,10,60,100,10,,,"
    result = run(write_nrrd(box_volume), write_csv([RECTANGLE, huge]), tmp_path / "out.mp4")
    assert result.returncode == 0
    assert "larger than the maximum" in result.stderr


def test_missing_files(tmp_path, write_nrrd, write_csv, box_volume):
    csv = write_csv([RECTANGLE])
    nrrd_path = write_nrrd(box_volume)
    assert "volume file not found" in run(tmp_path / "x.nrrd", csv, tmp_path / "o.mp4").stderr
    assert "plane file not found" in run(nrrd_path, tmp_path / "x.csv", tmp_path / "o.mp4").stderr
    assert run(nrrd_path, csv, tmp_path / "no" / "o.mp4").returncode == 1
    assert run(nrrd_path, csv, tmp_path / "o.avi").returncode == 1


def test_bad_arguments():
    assert run().returncode == 2
    assert run("a.nrrd", "b.csv", "c.mp4", "--fps", "0").returncode == 2


def test_signed_volume_outside_is_black(tmp_path, write_nrrd, write_csv):
    # range -500 .. 500, so the raw value 0 inside the volume is mid gray (FR-13)
    data = np.zeros((10, 10, 10), dtype=np.int16)
    data[0, 0, 0], data[0, 0, 1] = -500, 500
    plane = "4,-5,0,5,14,0,5,-5,9,5,14,9,5"                # rows 0..4 and 15..19 are outside
    video = tmp_path / "out.mp4"
    assert run(write_nrrd(data), write_csv([plane]), video).returncode == 0
    frame = frames_of(video)[0]
    assert frame[:4].max() < 20 and frame[16:].max() < 20  # outside: black
    assert 110 < frame[8:12].mean() < 145                  # inside: gray
