import math
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1] / 'app'))
from main import Point3D, bezier_surface, rotate_point, bernstein


def close(a, b, eps=1e-9):
    assert abs(a-b) < eps


def test_bernstein_partition():
    for t in [0.0, 0.2, 0.5, 0.9, 1.0]:
        close(sum(bernstein(5, i, t) for i in range(6)), 1.0)


def test_surface_hits_corners():
    p = [
        [Point3D(0,0,0), Point3D(1,0,0)],
        [Point3D(0,1,0), Point3D(1,1,1)],
    ]
    for u,v,expected in [
        (0,0,p[0][0]), (0,1,p[0][1]), (1,0,p[1][0]), (1,1,p[1][1])
    ]:
        actual = bezier_surface(p,u,v)
        close(actual.x, expected.x); close(actual.y, expected.y); close(actual.z, expected.z)


def test_center_of_planar_patch():
    p = [[Point3D(0,0,0), Point3D(2,0,0)], [Point3D(0,2,0), Point3D(2,2,0)]]
    q = bezier_surface(p, 0.5, 0.5)
    close(q.x, 1); close(q.y, 1); close(q.z, 0)


def test_rotation_x_90():
    q = rotate_point(Point3D(0,1,0), 90, 0)
    close(q.x, 0); close(q.y, 0); close(q.z, 1)
