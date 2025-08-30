from ..jsonml_stringify import jsonml_stringify
from ..render import typeColor, Renderer


def test_array_polygon_type():
    reg = [
        {'name': 'length1', 'bits': 8},
        {'array': 8, 'type': 4, 'name': 'gap'},
        {'name': 'rest', 'bits': 8},
    ]
    renderer = Renderer(bits=16)
    svg = jsonml_stringify(renderer.render(reg))
    assert '<polygon' in svg
    assert 'fill="#fff"' in svg
    assert f'stroke="{typeColor(4)}"' in svg
    assert 'gap' in svg
    assert renderer.lanes == 2


def test_array_full_lane_wedge():
    reg = [
        {'name': 'head', 'bits': 8},
        {'array': 32, 'type': 4},
        {'name': 'tail', 'bits': 8},
    ]
    renderer = Renderer(bits=16)
    svg = jsonml_stringify(renderer.render(reg))
    assert f"{renderer.hspace}" in svg
