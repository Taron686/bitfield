import pytest

from .. import render


def _make_reg(bits=8, lanes=8):
    return [{"bits": bits}] * (bits * lanes // bits)


def _find_arrow(node):
    if isinstance(node, list):
        if node and node[0] == "polyline":
            attrs = node[1]
            if attrs.get("marker-end") == "url(#arrow)":
                return node
        for child in node[1:]:
            res = _find_arrow(child)
            if res:
                return res
    return None


def _parse_points(node):
    attrs = node[1]
    pts = []
    for pair in attrs["points"].split():
        x_str, y_str = pair.split(",")
        pts.append((float(x_str), float(y_str)))
    return pts


def _line_center(line):
    base_y = 14 * 1.2
    vlane = 80 - 14 * 1.2
    return base_y + vlane * (line + 0.5)


def test_arrow_jump_from_descriptor():
    reg = _make_reg()
    reg.append(
        {
            "arrow_jump": 18,
            "start_line": 1,
            "jump_to_first": 2,
            "jump_to_second": 3,
            "layout": "left",
            "end_bit": 25,
        }
    )

    res = render(reg, bits=8)
    arrow = _find_arrow(res)
    assert arrow is not None

    attrs = arrow[1]
    assert attrs["stroke-width"] == 3
    assert attrs["stroke"] == "black"

    points = _parse_points(arrow)
    assert points[0][0] == pytest.approx(0)
    assert points[0][1] == pytest.approx(_line_center(1))
    assert points[1][1] == pytest.approx(_line_center(2))
    assert points[2][1] == pytest.approx(_line_center(3))
    assert points[3][0] == pytest.approx(0)
    target_x = 640 - ((25 % 8) + 0.5) * (640 / 8)
    assert points[-1][0] == pytest.approx(target_x)
    assert points[-1][1] == pytest.approx(_line_center(3))


def test_arrow_jump_custom_stroke_right_layout():
    reg = _make_reg()
    cfg = {
        "arrow_jump": 5,
        "start_line": 0,
        "layout": "right",
        "stroke_width": 5,
        "end_bit": 5,
    }

    res = render(reg, bits=8, arrow_jumps=cfg)
    arrow = _find_arrow(res)
    assert arrow is not None

    attrs = arrow[1]
    assert attrs["stroke-width"] == 5
    assert attrs["marker-end"] == "url(#arrow)"

    points = _parse_points(arrow)
    assert points[0][0] == pytest.approx(640)
    assert points[-2][0] == pytest.approx(640)
    target_x = 640 - ((5 % 8) + 0.5) * (640 / 8)
    assert points[-1][0] == pytest.approx(target_x)


def test_arrow_jump_relative_bit_uses_last_jump_lane():
    reg = _make_reg()
    cfg = {
        "arrow_jump": 3,
        "start_line": 1,
        "jump_to_first": 4,
        "layout": "left",
        "jump_to_second": 5,
        "end_bit": 3,
    }

    res = render(reg, bits=8, arrow_jumps=cfg)
    arrow = _find_arrow(res)
    assert arrow is not None

    points = _parse_points(arrow)
    assert points[-1][1] == pytest.approx(_line_center(5))


def test_arrow_jump_invalid_layout():
    reg = _make_reg()
    cfg = {"arrow_jump": 1, "start_line": 0, "layout": "up"}

    with pytest.raises(ValueError):
        render(reg, bits=8, arrow_jumps=cfg)


def test_arrow_jump_respects_vflip_orientation():
    reg = _make_reg()
    cfg = {
        "arrow_jump": 5,
        "start_line": 0,
        "layout": "left",
        "end_bit": 5,
    }

    res = render(reg, bits=8, vflip=True, arrow_jumps=cfg)
    arrow = _find_arrow(res)
    assert arrow is not None

    points = _parse_points(arrow)
    expected_x = ((5 % 8) + 0.5) * (640 / 8)
    assert points[-1][0] == pytest.approx(expected_x)


def test_arrow_jump_absolute_target_respects_hflip():
    reg = _make_reg()
    cfg = {
        "arrow_jump": 9,
        "start_line": 0,
        "layout": "left",
        "end_bit": 9,
    }

    res = render(reg, bits=8, hflip=True, arrow_jumps=cfg)
    arrow = _find_arrow(res)
    assert arrow is not None

    points = _parse_points(arrow)
    assert points[-1][1] == pytest.approx(_line_center(1))
