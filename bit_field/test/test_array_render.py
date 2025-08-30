import pytest
from ..jsonml_stringify import jsonml_stringify
from ..render import typeColor, Renderer


def test_array_polygon_type():
    reg = [
        {'name': 'length1', 'bits': 8},
        {'array': 8, 'type': 4, 'name': 'gap'},
        {'name': 'rest', 'bits': 8},
    ]
    renderer = Renderer(bits=16)
    jsonml = renderer.render(reg)
    svg = jsonml_stringify(jsonml)
    assert '<polygon' in svg
    assert 'fill="#fff"' in svg
    assert f'stroke="{typeColor(4)}"' in svg
    assert 'gap' in svg
    assert renderer.lanes == 2

    def find_polygon(node):
        if isinstance(node, list):
            if node and node[0] == 'polygon':
                return node[1]['points']
            for child in node[1:]:
                pts = find_polygon(child)
                if pts:
                    return pts
        return None

    pts = find_polygon(jsonml)
    coords = [tuple(map(float, p.split(','))) for p in pts.split()]
    top_y = coords[0][1]
    bottom_y = coords[2][1]
    base_y = renderer.fontsize * 1.2
    margin = renderer.vlane * 0.1
    assert top_y == pytest.approx(base_y + margin)
    assert bottom_y == pytest.approx(base_y + renderer.vlane - margin)


def test_array_full_lane_wedge():
    reg = [
        {'name': 'head', 'bits': 8},
        {'array': 32, 'type': 4},
        {'name': 'tail', 'bits': 8},
    ]
    renderer = Renderer(bits=16)
    svg = jsonml_stringify(renderer.render(reg))
    assert f"{renderer.hspace}" in svg
