from app.main import Point3D, Face, Polyhedron, build_face_records, create_box


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
