"""Модульные тесты математического ядра лабораторной работы №2.

Тесты оформлены в стиле pytest (функции с проверками assert) и запускаются
интерпретатором pytest либо прямым вызовом функций.
"""
import math

from app.main import (CLAMPED, UNIFORM, Point2D, all_basis, basis_value,
                      bspline_point, curve_length, default_points, find_span,
                      knot_domain, make_knots, max_degree, sample_curve)

PTS = default_points()
N = len(PTS) - 1


def bernstein(n, i, t):
    return math.comb(n, i) * t ** i * (1 - t) ** (n - i)


def test_knot_vector_length_and_clamping():
    """Длина вектора n+p+2, крайние узлы кратности p+1, вектор неубывающий."""
    for p in range(1, 7):
        knots = make_knots(N, p, CLAMPED)
        assert len(knots) == N + p + 2
        assert all(k == 0.0 for k in knots[:p + 1])
        assert all(k == N - p + 1 for k in knots[N + 1:])
        assert all(knots[i] <= knots[i + 1] for i in range(len(knots) - 1))


def test_uniform_knot_vector_is_arithmetic():
    """Равномерный вектор — последовательность с шагом 1, область [p, n+1]."""
    for p in range(1, 7):
        knots = make_knots(N, p, UNIFORM)
        assert len(knots) == N + p + 2
        assert all(abs(knots[i] - i) < 1e-12 for i in range(len(knots)))
        a, b = knot_domain(N, p, knots)
        assert abs(a - p) < 1e-12 and abs(b - (N + 1)) < 1e-12


def test_partition_of_unity():
    """Сумма базисных функций равна единице на всей области определения."""
    for p in range(1, 7):
        for kind in (CLAMPED, UNIFORM):
            knots = make_knots(N, p, kind)
            a, b = knot_domain(N, p, knots)
            worst = 0.0
            for s in range(0, 41):
                u = a + (b - a) * s / 40
                worst = max(worst, abs(sum(all_basis(u, N, p, knots)) - 1.0))
            assert worst < 1e-10, (p, kind, worst)


def test_number_of_nonzero_basis_functions():
    """Внутри пролёта (вне узлов) ненулевых базисных функций ровно p+1."""
    for p in range(1, 7):
        knots = make_knots(N, p, CLAMPED)
        a, b = knot_domain(N, p, knots)
        for s in range(1, 40):
            u = a + (b - a) * s / 40
            if any(abs(u - k) < 1e-9 for k in knots):
                continue                    # в самом узле функций меньше
            nonzero = sum(1 for v in all_basis(u, N, p, knots) if v > 1e-12)
            assert nonzero == p + 1, (p, u, nonzero)


def test_degree_one_is_polyline():
    """При p = 1 кривая совпадает с задающей ломаной."""
    knots = make_knots(N, 1, CLAMPED)
    for i in range(N):
        for t in (0.25, 0.5, 0.75):
            q = bspline_point(PTS, 1, knots, i + t)
            expected = Point2D(PTS[i].x + t * (PTS[i + 1].x - PTS[i].x),
                               PTS[i].y + t * (PTS[i + 1].y - PTS[i].y))
            assert math.dist((q.x, q.y), (expected.x, expected.y)) < 1e-9


def test_clamped_curve_passes_through_end_points():
    """Зажатый вектор: кривая начинается и заканчивается в крайних точках."""
    for p in range(1, 7):
        knots = make_knots(N, p, CLAMPED)
        a, b = knot_domain(N, p, knots)
        first = bspline_point(PTS, p, knots, a)
        last = bspline_point(PTS, p, knots, b)
        assert math.dist((first.x, first.y), (PTS[0].x, PTS[0].y)) < 1e-9
        assert math.dist((last.x, last.y), (PTS[N].x, PTS[N].y)) < 1e-9


def test_degree_equal_to_n_matches_bezier():
    """При p = n зажатый B-сплайн совпадает с кривой Безье степени n."""
    p = N
    knots = make_knots(N, p, CLAMPED)
    for s in range(0, 21):
        t = s / 20
        q = bspline_point(PTS, p, knots, t)
        bx = sum(bernstein(N, i, t) * PTS[i].x for i in range(N + 1))
        by = sum(bernstein(N, i, t) * PTS[i].y for i in range(N + 1))
        assert math.dist((q.x, q.y), (bx, by)) < 1e-9


def test_deboor_matches_cox_de_boor_sum():
    """Алгоритм де Бура совпадает с прямой суммой по базисным функциям."""
    for p in (2, 3, 4, 6):
        for kind in (CLAMPED, UNIFORM):
            knots = make_knots(N, p, kind)
            a, b = knot_domain(N, p, knots)
            for s in range(1, 40):
                u = a + (b - a) * s / 40
                q = bspline_point(PTS, p, knots, u)
                w = all_basis(u, N, p, knots)
                x = sum(w[i] * PTS[i].x for i in range(N + 1))
                y = sum(w[i] * PTS[i].y for i in range(N + 1))
                assert math.dist((q.x, q.y), (x, y)) < 1e-9


def test_basis_local_support():
    """N(i,p) отлична от нуля только на интервале (u_i, u_{i+p+1})."""
    p = 3
    knots = make_knots(N, p, CLAMPED)
    i = 2
    assert basis_value(i, p, knots[i] - 1e-6, knots) == 0.0
    assert basis_value(i, p, knots[i + p + 1] + 1e-6, knots) == 0.0
    assert basis_value(i, p, 0.5 * (knots[i] + knots[i + p + 1]), knots) > 0.0


def test_moving_point_changes_curve_locally():
    """Смещение одной точки меняет кривую лишь на участке её локального влияния."""
    p = 3
    knots = make_knots(N, p, CLAMPED)
    moved = list(PTS)
    moved[2] = Point2D(PTS[2].x + 3.0, PTS[2].y + 3.0)
    a, b = knot_domain(N, p, knots)
    left, right = knots[2], knots[2 + p + 1]
    for s in range(0, 81):
        u = a + (b - a) * s / 80
        q1 = bspline_point(PTS, p, knots, u)
        q2 = bspline_point(moved, p, knots, u)
        delta = math.dist((q1.x, q1.y), (q2.x, q2.y))
        if u < left - 1e-9 or u > right + 1e-9:
            assert delta < 1e-9, (u, delta)
        elif left + 0.2 < u < right - 0.2:
            assert delta > 1e-6


def test_convex_hull_property():
    """Кривая целиком лежит в габаритном прямоугольнике задающих точек."""
    xmin = min(p.x for p in PTS)
    xmax = max(p.x for p in PTS)
    ymin = min(p.y for p in PTS)
    ymax = max(p.y for p in PTS)
    for p in range(1, 7):
        for kind in (CLAMPED, UNIFORM):
            knots = make_knots(N, p, kind)
            for q in sample_curve(PTS, p, knots, per_span=12):
                assert xmin - 1e-9 <= q.x <= xmax + 1e-9
                assert ymin - 1e-9 <= q.y <= ymax + 1e-9


def test_continuity_at_interior_knots():
    """Кубический сплайн непрерывен вместе с первой производной на стыках."""
    p = 3
    knots = make_knots(N, p, CLAMPED)
    a, b = knot_domain(N, p, knots)
    eps = 1e-6
    for u in sorted({k for k in knots if a + 1e-9 < k < b - 1e-9}):
        left = bspline_point(PTS, p, knots, u - eps)
        right = bspline_point(PTS, p, knots, u + eps)
        assert math.dist((left.x, left.y), (right.x, right.y)) < 1e-5
        d_left = ((right.x - left.x) / (2 * eps), (right.y - left.y) / (2 * eps))
        far_left = bspline_point(PTS, p, knots, u - 1e-3)
        far_right = bspline_point(PTS, p, knots, u + 1e-3)
        dx = (right.x - left.x) / (2 * eps)
        dy = (right.y - left.y) / (2 * eps)
        d2x = (far_right.x - far_left.x) / 2e-3
        d2y = (far_right.y - far_left.y) / 2e-3
        assert math.dist((dx, dy), (d2x, d2y)) < 1e-2


def test_find_span_returns_valid_interval():
    """Индекс пролёта лежит в допустимых границах и накрывает параметр."""
    for p in range(1, 7):
        knots = make_knots(N, p, CLAMPED)
        a, b = knot_domain(N, p, knots)
        for s in range(0, 41):
            u = a + (b - a) * s / 40
            span = find_span(N, p, u, knots)
            assert p <= span <= N
            assert knots[span] - 1e-12 <= u <= knots[span + 1] + 1e-12


def test_straight_polyline_length():
    """Для коллинеарных точек при p = 1 длина кривой равна длине ломаной."""
    pts = [Point2D(float(i), 0.0) for i in range(7)]
    knots = make_knots(6, 1, CLAMPED)
    length = curve_length(pts, 1, knots, samples=1200)
    assert abs(length - 6.0) < 1e-6


def test_max_degree_limit():
    """Степень ограничена числом точек и значением 6."""
    assert max_degree(6) == 6
    assert max_degree(3) == 3
    assert max_degree(9) == 6
