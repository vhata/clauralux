import math

from clauralux.engine.types import Position


def test_distance_to_same_point() -> None:
    p = Position(5.0, 5.0)
    assert p.distance_to(p) == 0.0


def test_distance_to_horizontal() -> None:
    a = Position(0.0, 0.0)
    b = Position(3.0, 0.0)
    assert a.distance_to(b) == 3.0


def test_distance_to_diagonal() -> None:
    a = Position(0.0, 0.0)
    b = Position(3.0, 4.0)
    assert a.distance_to(b) == 5.0


def test_direction_to() -> None:
    a = Position(0.0, 0.0)
    b = Position(10.0, 0.0)
    dx, dy = a.direction_to(b)
    assert dx == 1.0
    assert dy == 0.0


def test_direction_to_diagonal() -> None:
    a = Position(0.0, 0.0)
    b = Position(1.0, 1.0)
    dx, dy = a.direction_to(b)
    assert abs(dx - 1 / math.sqrt(2)) < 1e-9
    assert abs(dy - 1 / math.sqrt(2)) < 1e-9


def test_direction_to_same_point() -> None:
    p = Position(5.0, 5.0)
    assert p.direction_to(p) == (0.0, 0.0)
