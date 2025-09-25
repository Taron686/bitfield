import pytest
from .. import render
from ..render import Renderer


def _make_reg(bits=8, lanes=8):
    return [{"bits": bits}] * (bits * lanes // bits)


def _find_text(node, text):
    if isinstance(node, list):
        if node and node[0] in ("text", "tspan") and text in node[2:]:
            return node
        for child in node[1:]:
            res = _find_text(child, text)
            if res:
                return res
    return None


def _find_line(node, x1, x2, y1, y2, tol=1e-6):
    if isinstance(node, list):
        if node and node[0] == "line":
            attrs = node[1]
            if all(k in attrs for k in ("x1", "x2", "y1", "y2")):
                if (
                    abs(float(attrs["x1"]) - x1) < tol
                    and abs(float(attrs["x2"]) - x2) < tol
                    and abs(float(attrs["y1"]) - y1) < tol
                    and abs(float(attrs["y2"]) - y2) < tol
                ):
                    return node
        for child in node[1:]:
            res = _find_line(child, x1, x2, y1, y2, tol)
            if res:
                return res
    return None


def _find_path(node, predicate):
    if isinstance(node, list):
        if node and node[0] == "path":
            attrs = node[1]
            if predicate(attrs):
                return node
        for child in node[1:]:
            res = _find_path(child, predicate)
            if res:
                return res
    return None


def test_label_lines_draws_text_outside_right():
    reg = _make_reg()
    cfg = {"label_lines": "Demo", "font_size": 6, "start_line": 0, "end_line": 3, "layout": "right"}
    res = render(reg, bits=8, label_lines=cfg)
    node = _find_text(res, "Demo")
    assert node is not None
    attrs = node[1]
    assert attrs["font-size"] == 6
    assert attrs["text-anchor"] == "start"
    assert attrs["x"] == pytest.approx(760)
    expected_len = len("Demo") * 6 * 0.6
    assert attrs["textLength"] == pytest.approx(expected_len)
    top_y = 14 * 1.2
    vlane = 80 - 14 * 1.2
    bottom_y = top_y + vlane * 4
    assert _find_line(res, 680, 760, top_y, top_y) is not None
    assert _find_line(res, 680, 760, bottom_y, bottom_y) is not None
    assert _find_line(res, 720, 720, top_y, bottom_y) is not None


def test_label_lines_draws_text_outside_left():
    reg = _make_reg()
    cfg = {"label_lines": "Demo", "font_size": 6, "start_line": 0, "end_line": 3, "layout": "left"}
    res = render(reg, bits=8, label_lines=cfg)
    node = _find_text(res, "Demo")
    assert node is not None
    attrs = node[1]
    assert attrs["x"] == pytest.approx(-120)
    assert attrs["text-anchor"] == "end"
    root = res
    root_attrs = root[1]
    view_min_x = float(root_attrs["viewBox"].split()[0])
    assert view_min_x == pytest.approx(-139.4)
    top_y = 14 * 1.2
    vlane = 80 - 14 * 1.2
    bottom_y = top_y + vlane * 4
    assert _find_line(res, -120, -40, top_y, top_y) is not None
    assert _find_line(res, -120, -40, bottom_y, bottom_y) is not None
    assert _find_line(res, -80, -80, top_y, bottom_y) is not None


def test_label_lines_multiline():
    reg = _make_reg()
    cfg = {"label_lines": "Line1\nLine2", "font_size": 6, "start_line": 0, "end_line": 3, "layout": "right"}
    res = render(reg, bits=8, label_lines=cfg)
    node1 = _find_text(res, "Line1")
    node2 = _find_text(res, "Line2")
    assert node1 is not None
    assert node2 is not None
    top_y = 14 * 1.2
    vlane = 80 - 14 * 1.2
    bottom_y = top_y + vlane * 4
    assert node1[1]["x"] == pytest.approx(760)
    assert node2[1]["x"] == pytest.approx(760)
    assert _find_line(res, 720, 720, top_y, bottom_y) is not None


def test_label_lines_angle():
    reg = _make_reg()
    cfg = {"label_lines": "Demo", "font_size": 6, "start_line": 0, "end_line": 3, "layout": "right", "angle": 45}
    res = render(reg, bits=8, label_lines=cfg)
    node = _find_text(res, "Demo")
    assert node is not None
    attrs = node[1]
    assert "transform" in attrs
    assert attrs["text-anchor"] == "middle"
    expected_len = len("Demo") * 6 * 0.6
    assert attrs["x"] == pytest.approx(760 + expected_len / 2)
    angle, x, y = attrs["transform"][7:-1].split(",")
    assert float(angle) == pytest.approx(45)
    assert float(x) == pytest.approx(attrs["x"])
    assert float(y) == pytest.approx(attrs["y"])


def test_label_lines_angle_vertical_spacing():
    reg = _make_reg()
    cfg = {"label_lines": "Demo", "font_size": 6, "start_line": 0, "end_line": 3, "layout": "right", "angle": -90}
    res = render(reg, bits=8, label_lines=cfg)
    node = _find_text(res, "Demo")
    assert node is not None
    attrs = node[1]
    assert attrs["text-anchor"] == "middle"
    assert attrs["x"] == pytest.approx(740)
    angle, x, y = attrs["transform"][7:-1].split(",")
    assert float(angle) == pytest.approx(-90)
    assert float(x) == pytest.approx(attrs["x"])
    assert float(y) == pytest.approx(attrs["y"])


def test_label_lines_angle_left():
    reg = _make_reg()
    cfg = {"label_lines": "Demo", "font_size": 6, "start_line": 0, "end_line": 3, "layout": "left", "angle": -30}
    res = render(reg, bits=8, label_lines=cfg)
    node = _find_text(res, "Demo")
    assert node is not None
    attrs = node[1]
    assert attrs["text-anchor"] == "middle"
    expected_len = len("Demo") * 6 * 0.6
    assert attrs["x"] == pytest.approx(-120 - expected_len / 2)
    angle, x, y = attrs["transform"][7:-1].split(",")
    assert float(angle) == pytest.approx(-30)
    assert float(x) == pytest.approx(attrs["x"])
    assert float(y) == pytest.approx(attrs["y"])


def test_multiple_label_lines():
    reg = _make_reg()
    cfgs = [
        {"label_lines": "Demo1", "font_size": 6, "start_line": 0, "end_line": 3, "layout": "right"},
        {"label_lines": "Demo2", "font_size": 6, "start_line": 4, "end_line": 7, "layout": "right"},
    ]
    res = render(reg, bits=8, label_lines=cfgs)
    node1 = _find_text(res, "Demo1")
    node2 = _find_text(res, "Demo2")
    assert node1 is not None
    assert node2 is not None
    top_y = 14 * 1.2
    vlane = 80 - 14 * 1.2
    top_y2 = top_y + vlane * 4
    bottom_y2 = top_y + vlane * 8
    assert _find_line(res, 720, 720, top_y, top_y + vlane * 4) is not None
    assert _find_line(res, 720, 720, top_y2, bottom_y2) is not None


def test_overlapping_label_lines_shift_right():
    reg = _make_reg(lanes=9)
    cfgs = [
        {"label_lines": "Demo1", "font_size": 6, "start_line": 0, "end_line": 3, "layout": "right"},
        {"label_lines": "Demo2", "font_size": 6, "start_line": 2, "end_line": 5, "layout": "right"},
        {"label_lines": "Demo3", "font_size": 6, "start_line": 6, "end_line": 8, "layout": "right"},
    ]
    res = render(reg, bits=8, label_lines=cfgs)
    node1 = _find_text(res, "Demo1")
    node2 = _find_text(res, "Demo2")
    node3 = _find_text(res, "Demo3")
    assert node1 is not None and node2 is not None and node3 is not None
    # first and third labels are in the default position
    assert node1[1]["x"] == pytest.approx(760)
    assert node3[1]["x"] == pytest.approx(760)
    # second label overlaps with the first and should be shifted right
    expected = 760 + (40 + 80 + len("Demo1") * 6 * 0.6)
    assert node2[1]["x"] == pytest.approx(expected)


def test_label_lines_reserved_shifts_arrow():
    reg = _make_reg()
    cfg = {
        "label_lines": "Demo",
        "font_size": 6,
        "start_line": 1,
        "end_line": 3,
        "layout": "right",
        "Reserved": True,
    }
    res = render(reg, bits=8, label_lines=cfg)
    top_y = 14 * 1.2 + (80 - 14 * 1.2)
    vlane = 80 - 14 * 1.2
    bottom_y = 14 * 1.2 + vlane * 4
    reserved_offset = vlane * 0.2
    assert _find_line(res, 680, 760, top_y - reserved_offset, top_y - reserved_offset) is not None
    assert _find_line(res, 720, 720, top_y - reserved_offset, bottom_y) is not None


def test_label_lines_invalid_range():
    reg = _make_reg()
    cfg = {"label_lines": "X", "font_size": 6, "start_line": 0, "end_line": 8, "layout": "left"}
    with pytest.raises(ValueError):
        render(reg, bits=8, label_lines=cfg)


def test_label_lines_too_short():
    reg = _make_reg()
    cfg = {"label_lines": "X", "font_size": 6, "start_line": 0, "end_line": 1, "layout": "left"}
    with pytest.raises(ValueError):
        render(reg, bits=8, label_lines=cfg)


def test_label_lines_from_desc():
    reg = _make_reg()
    reg.append({"label_lines": "Demo", "font_size": 6, "start_line": 0, "end_line": 2, "layout": "left"})
    res = render(reg, bits=8)
    node = _find_text(res, "Demo")
    assert node is not None


def test_label_lines_from_desc_invalid():
    reg = _make_reg()
    reg.append({"label_lines": "X", "font_size": 6, "start_line": 0, "end_line": 1, "layout": "right"})
    with pytest.raises(ValueError):
        render(reg, bits=8)


def test_arrow_jump_draws_path_left():
    reg = _make_reg(lanes=6)
    cfg = {
        "arrow_jump": 5,
        "start_line": 2,
        "jump_to_first": 3,
        "layout": "left",
        "jump_to_second": 5,
        "end_bit": 5,
    }
    renderer = Renderer(bits=8, arrow_jumps=cfg)
    res = renderer.render(reg)

    path_node = _find_path(res, lambda attrs: attrs.get("marker-end") == "url(#arrow)")
    assert path_node is not None
    attrs = path_node[1]
    assert attrs["stroke-width"] == 3

    step = renderer.hspace / renderer.mod
    base_y = renderer.fontsize * 1.2
    line_center = lambda line: base_y + renderer.vlane * line + renderer.vlane / 2
    bit_x = lambda bit: step * (renderer.mod - bit - 0.5)
    outer_distance = renderer.arrow_jumps[0]["_outer_distance"]
    assert outer_distance == pytest.approx(10)
    assert renderer.arrow_jumps[0]["_offset"] == 0
    outer_x = -outer_distance

    expected_points = [
        (bit_x(cfg["arrow_jump"]), line_center(cfg["start_line"])),
        (bit_x(cfg["arrow_jump"]), line_center(cfg["jump_to_first"])),
        (outer_x, line_center(cfg["jump_to_first"])),
        (outer_x, line_center(cfg["jump_to_second"])),
        (bit_x(cfg["end_bit"]), line_center(cfg["jump_to_second"])),
    ]

    commands = attrs["d"].split()
    actual_points = [tuple(map(float, commands[0][1:].split(",")))]
    actual_points.extend(tuple(map(float, cmd[1:].split(","))) for cmd in commands[1:])

    for actual, expected in zip(actual_points, expected_points):
        assert actual[0] == pytest.approx(expected[0])
        assert actual[1] == pytest.approx(expected[1])


def test_arrow_jump_updates_viewbox_left_margin():
    reg = _make_reg(lanes=3)
    cfg = {
        "arrow_jump": 2,
        "start_line": 0,
        "jump_to_first": 1,
        "layout": "left",
        "jump_to_second": 2,
        "end_bit": 1,
    }
    res = render(reg, bits=8, arrow_jumps=cfg)
    view_min_x = float(res[1]["viewBox"].split()[0])
    assert view_min_x == pytest.approx(-16.5)


def test_arrow_jump_from_desc():
    reg = _make_reg(lanes=4)
    reg.append({
        "arrow_jump": 1,
        "start_line": 0,
        "jump_to_first": 1,
        "layout": "right",
        "jump_to_second": 3,
        "end_bit": 2,
    })
    res = render(reg, bits=8)
    path_node = _find_path(res, lambda attrs: attrs.get("marker-end") == "url(#arrow)")
    assert path_node is not None
