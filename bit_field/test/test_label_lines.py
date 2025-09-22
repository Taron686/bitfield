import pytest
from .. import render


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
    assert view_min_x == pytest.approx(-134.4)
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
