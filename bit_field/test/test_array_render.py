import copy
import math

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
    assert f'stroke="{typeColor(4)}"' in svg
    assert 'gap' in svg
    assert renderer.lanes == 2

    def collect_polygons(node, polys):
        if isinstance(node, list):
            if node and node[0] == 'polygon':
                polys.append(node[1])
            for child in node[1:]:
                collect_polygons(child, polys)

    polygons = []
    collect_polygons(jsonml, polygons)
    fills = [p.get('fill') for p in polygons]
    assert '#fff' in fills
    assert typeColor(4) in fills

    white_poly = next(p for p in polygons if p.get('fill') == '#fff')
    coords = [tuple(map(float, p.split(','))) for p in white_poly['points'].split()]
    top_y = coords[0][1]
    bottom_y = coords[2][1]
    base_y = renderer.fontsize * 1.2
    assert top_y == pytest.approx(base_y)
    assert bottom_y == pytest.approx(base_y + renderer.vlane)
    step = renderer.hspace / renderer.mod
    margin = step * 0.1
    x1 = coords[0][0]
    x2 = coords[2][0]
    assert x1 == pytest.approx(step * 8 + margin)
    assert x2 == pytest.approx(renderer.hspace - margin)

    color_poly = next(p for p in polygons if p.get('fill') == typeColor(4))
    c_coords = [tuple(map(float, p.split(','))) for p in color_poly['points'].split()]
    c_top = c_coords[0][1]
    c_bottom = c_coords[2][1]
    assert c_top == pytest.approx(base_y)
    assert c_bottom == pytest.approx(base_y + renderer.vlane)
    c_x1 = c_coords[0][0]
    c_x2 = c_coords[2][0]
    assert c_x1 == pytest.approx(step * 8)
    assert c_x2 == pytest.approx(renderer.hspace)


def test_array_gap_width():
    reg = [
        {'name': 'length1', 'bits': 8},
        {'array': 8, 'gap_width': 1.0, 'name': 'gap'},
        {'name': 'rest', 'bits': 8},
    ]
    renderer = Renderer(bits=16)
    jsonml = renderer.render(reg)

    def collect_polygons(node, polys):
        if isinstance(node, list):
            if node and node[0] == 'polygon':
                polys.append(node[1])
            for child in node[1:]:
                collect_polygons(child, polys)

    polygons = []
    collect_polygons(jsonml, polygons)
    white_poly = next(p for p in polygons if p.get('fill') == '#fff')
    coords = [tuple(map(float, p.split(','))) for p in white_poly['points'].split()]
    step = renderer.hspace / renderer.mod
    width = step * 1.0
    assert coords[1][0] == pytest.approx(coords[0][0] + width)
    assert coords[3][0] == pytest.approx(coords[2][0] - width)

def test_array_full_lane_wedge():
    reg = [
        {'name': 'head', 'bits': 8},
        {'array': 32, 'type': 4},
        {'name': 'tail', 'bits': 8},
    ]
    renderer = Renderer(bits=16)
    svg = jsonml_stringify(renderer.render(reg))
    assert f"{renderer.hspace}" in svg


def test_array_text_default_black():
    reg = [
        {'name': 'length1', 'bits': 8},
        {'array': 8, 'type': 4, 'name': 'gap'},
        {'name': 'rest', 'bits': 8},
    ]
    renderer = Renderer(bits=16)
    jsonml = renderer.render(reg)

    def collect_texts(node, texts):
        if isinstance(node, list):
            if node and node[0] == 'text':
                content = node[2] if len(node) > 2 else ''
                texts.append((node[1], content))
            for child in node[1:]:
                collect_texts(child, texts)

    texts = []
    collect_texts(jsonml, texts)
    gap_text = next(attrs for attrs, content in texts if content == 'gap')
    assert gap_text.get('fill') == 'black'
    assert gap_text.get('stroke') == 'none'


def test_array_text_custom_color():
    reg = [
        {'name': 'length1', 'bits': 8},
        {'array': 8, 'type': 4, 'name': 'gap', 'font_color': '#0f0'},
        {'name': 'rest', 'bits': 8},
    ]
    renderer = Renderer(bits=16)
    jsonml = renderer.render(reg)

    def collect_texts(node, texts):
        if isinstance(node, list):
            if node and node[0] == 'text':
                content = node[2] if len(node) > 2 else ''
                texts.append((node[1], content))
            for child in node[1:]:
                collect_texts(child, texts)

    texts = []
    collect_texts(jsonml, texts)
    gap_text = next(attrs for attrs, content in texts if content == 'gap')
    assert gap_text.get('fill') == '#0f0'
    assert gap_text.get('stroke') == 'none'


def test_array_hide_lines_suppresses_internal_ticks():
    base_reg = [
        {'name': 'start', 'bits': 8},
        {'array': 128, 'type': 4, 'name': 'gap'},
        {'name': 'end', 'bits': 8},
    ]

    def collect_lines(node, lines):
        if isinstance(node, list):
            if node and node[0] == 'line':
                lines.append(node[1])
            for child in node[1:]:
                collect_lines(child, lines)

    def top_tick_positions(renderer, jsonml):
        lines = []
        collect_lines(jsonml, lines)
        top_tick_y = renderer.vlane / 8
        ticks = []
        for attrs in lines:
            if attrs.get('x1') == attrs.get('x2') and 'y1' not in attrs and 'y2' in attrs:
                if math.isclose(attrs['y2'], top_tick_y, abs_tol=1e-6):
                    ticks.append(attrs['x1'])
        return ticks

    def horizontal_lines(renderer, jsonml):
        lines = []
        collect_lines(jsonml, lines)
        tops = []
        bottoms = []
        for attrs in lines:
            if attrs.get('y1') == renderer.vlane and attrs.get('y2') == renderer.vlane:
                bottoms.append(attrs)
            elif 'y1' not in attrs and 'y2' not in attrs and 'x2' in attrs:
                tops.append(attrs)
        return tops, bottoms

    regular_reg = copy.deepcopy(base_reg)
    renderer_regular = Renderer(bits=32)
    jsonml_regular = renderer_regular.render(regular_reg)
    start = regular_reg[1]['_array_start']
    end = regular_reg[1]['_array_end']
    regular_ticks = top_tick_positions(renderer_regular, jsonml_regular)

    hidden_reg = copy.deepcopy(base_reg)
    hidden_reg[1]['hide_lines'] = True
    renderer_hidden = Renderer(bits=32)
    jsonml_hidden = renderer_hidden.render(hidden_reg)
    hidden_ticks = top_tick_positions(renderer_hidden, jsonml_hidden)
    hidden_tops, hidden_bottoms = horizontal_lines(renderer_hidden, jsonml_hidden)

    field_starts = {e['lsb'] for e in regular_reg if 'lsb' in e}
    expected_removed_ticks = 0
    for span_start, span_end in [(e['_array_start'], e['_array_end'])
                                 for e in hidden_reg if e.get('hide_lines')]:
        for bit in range(span_start + 1, span_end):
            if bit >= renderer_regular.total_bits:
                continue
            if bit % renderer_regular.mod == 0:
                continue
            if bit in field_starts:
                continue
            expected_removed_ticks += 1

    assert expected_removed_ticks > 0
    assert len(hidden_ticks) < len(regular_ticks)
    assert len(regular_ticks) - len(hidden_ticks) == expected_removed_ticks

    regular_tops, regular_bottoms = horizontal_lines(renderer_regular, jsonml_regular)

    lane_boundaries = [renderer_regular.mod * lane
                       for lane in range(1, renderer_regular.lanes)]
    hidden_boundaries = 0
    for span_start, span_end in [(e['_array_start'], e['_array_end'])
                                 for e in hidden_reg if e.get('hide_lines')]:
        hidden_boundaries += sum(1 for boundary in lane_boundaries
                                 if span_start < boundary < span_end)

    assert hidden_boundaries > 0
    assert len(regular_bottoms) - len(hidden_bottoms) == hidden_boundaries
    assert len(regular_tops) - len(hidden_tops) == hidden_boundaries
