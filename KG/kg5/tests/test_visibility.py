import math

from app.main import (Point3D, Face, Polyhedron, build_face_records,
                      create_box, create_pyramid, create_scene, to_camera)


def test_rotation_x_90():
    p = Point3D(0, 1, 0).rotate(3.141592653589793 / 2, 0)
    assert abs(p.x) < 1e-9
    assert abs(p.y) < 1e-9
    assert abs(p.z - 1) < 1e-9


def test_face_sort_is_far_to_near():
    a = create_box("A", 0, 0, 0, 2, 2, 2, "#aaa")
    b = create_box("B", 0, 0, 5, 2, 2, 2, "#bbb")
    records = build_face_records([a, b], 0, 0)
    z = [r.z_avg for r in records]
    assert z == sorted(z)


def test_each_box_has_six_faces():
    box = create_box("A", 0, 0, 0, 2, 2, 2, "#aaa")
    assert len(box.vertices) == 8
    assert len(box.faces) == 6


def test_records_contain_depth_range():
    box = create_box("A", 0, 0, 0, 2, 2, 2, "#aaa")
    records = build_face_records([box], 0, 0)
    assert all(r.z_min <= r.z_avg <= r.z_max for r in records)


# --- тесты, фиксирующие исправленное определение видимости (kg5_fixed) ---------

def test_visibility_flag_matches_camera_normal():
    box = create_box("A", 0, 0, 0, 2, 2, 2, "#aaa")
    for r in build_face_records([box], 0.3, -0.5):
        assert r.visible == (r.normal_z > 0)


def test_visible_faces_face_the_observer():
    """В исходном положении к наблюдателю обращены верхняя, задняя и правая грани."""
    box = create_box("A", 0, 0, 0, 2, 2, 2, "#aaa")
    records = build_face_records([box], 0, 0)
    assert {r.face_name for r in records if r.visible} == {"верхняя", "задняя", "правая"}


def test_each_box_has_exactly_three_visible_faces():
    box = create_box("A", 0, 0, 0, 2, 2, 2, "#aaa")
    for rx, ry in [(0, 0), (0.4, 0.9), (-1.1, 2.2), (math.pi, -0.7)]:
        records = build_face_records([box], rx, ry)
        assert sum(1 for r in records if r.visible) == 3


def test_near_box_is_drawn_last():
    far = create_box("Дальний", 0, 0, 0, 2, 2, 2, "#aaa")
    near = create_box("Ближний", 0, 0, 5, 2, 2, 2, "#bbb")
    records = build_face_records([far, near], 0, 0)
    z_far = max(r.z_avg for r in records if r.poly_name == "Дальний")
    z_near = min(r.z_avg for r in records if r.poly_name == "Ближний")
    assert z_far < z_near


def test_depth_order_is_camera_depth_order():
    """Zср грани равна глубине её центроида в системе наблюдателя."""
    scene = create_scene()
    rx, ry = 0.5, -0.8
    records = build_face_records(scene, rx, ry)
    z = [r.z_avg for r in records]
    assert z == sorted(z)                       # дальние -> ближние
    by_name = {p.name: p for p in scene}
    for r in records:
        poly = by_name[r.poly_name]
        world = [poly.vertices[i].rotate(rx, ry) for i in r.indices]
        n = len(world)
        centroid = Point3D(sum(v.x for v in world) / n,
                           sum(v.y for v in world) / n,
                           sum(v.z for v in world) / n)
        assert math.isclose(r.z_avg, to_camera(centroid).z, abs_tol=1e-9)


def test_pyramid_has_front_faces():
    pyr = create_pyramid("P", 0, 0, 0, 2, 3, "#7fc28b")
    records = build_face_records([pyr], 0.3, 0.6)
    visible = [r.face_name for r in records if r.visible]
    assert 1 <= len(visible) < len(pyr.faces)
