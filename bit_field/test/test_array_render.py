from .. import render
from ..jsonml_stringify import jsonml_stringify
from ..render import typeColor


def test_array_polygon_type():
    reg = [
        {'name': 'length1', 'bits': 8},
        {'array': 16, 'type': 4, 'name': 'gap'},
        {'name': 'rest', 'bits': 8},
    ]
    svg = jsonml_stringify(render(reg))
    assert '<polygon' in svg
    assert 'fill="#fff"' in svg
    assert f'stroke="{typeColor(4)}"' in svg
    assert 'gap' in svg
