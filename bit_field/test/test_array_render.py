from .. import render
from ..jsonml_stringify import jsonml_stringify


def test_array_polygon():
    reg = [
        {'name': 'length1', 'bits': 8},
        {'array': [8, 10, 12, 16]},
        {'name': 'rest', 'bits': 8},
    ]
    svg = jsonml_stringify(render(reg))
    assert '<polygon' in svg
