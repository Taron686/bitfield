import pytest
from .. import render


def _make_reg(bits=8, lanes=8):
    return [{"bits": bits}] * (bits * lanes // bits)


def _find_text(node, text):
    if isinstance(node, list):
        if node and node[0] == "text" and text in node[2:]:
            return node
        for child in node[1:]:
            res = _find_text(child, text)
            if res:
                return res
    return None


def test_label_lines_draws_text():
    reg = _make_reg()
    cfg = {"label_lines": "Demo", "font_size": 6, "start_line": 0, "end_line": 3, "layout": "right"}
    res = render(reg, bits=8, label_lines=cfg)
    node = _find_text(res, "Demo")
    assert node is not None
    attrs = node[1]
    assert attrs["font-size"] == 6
    assert "rotate(90" in attrs.get("transform", "")


def test_label_lines_invalid_range():
    reg = _make_reg()
    cfg = {"label_lines": "X", "font_size": 6, "start_line": 0, "end_line": 8, "layout": "left"}
    with pytest.raises(ValueError):
        render(reg, bits=8, label_lines=cfg)


def test_label_lines_too_short():
    reg = _make_reg()
    cfg = {"label_lines": "X", "font_size": 6, "start_line": 0, "end_line": 2, "layout": "left"}
    with pytest.raises(ValueError):
        render(reg, bits=8, label_lines=cfg)


def test_label_lines_from_desc():
    reg = _make_reg()
    reg.append({"label_lines": "Demo", "font_size": 6, "start_line": 0, "end_line": 3, "layout": "left"})
    res = render(reg, bits=8)
    node = _find_text(res, "Demo")
    assert node is not None


def test_label_lines_from_desc_invalid():
    reg = _make_reg()
    reg.append({"label_lines": "X", "font_size": 6, "start_line": 0, "end_line": 2, "layout": "right"})
    with pytest.raises(ValueError):
        render(reg, bits=8)
