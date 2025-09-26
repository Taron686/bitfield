import pytest
from ..jsonml_stringify import jsonml_stringify
from ..render import typeColor, Renderer


def extract_text_content(node):
    if isinstance(node, str):
        return node
    if isinstance(node, list):
        return ''.join(extract_text_content(child) for child in node[2:])
    return ''


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


def test_array_gap_fill_used_for_background_when_no_type():
    reg = [
        {'name': 'length1', 'bits': 8},
        {'array': 8, 'gap_fill': '#abc', 'name': 'gap'},
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

    background = [
        p for p in polygons
        if p.get('fill') == '#abc' and p.get('stroke') == 'none'
    ]
    assert background, 'expected background polygon to use gap_fill colour'


def test_array_gap_fill_covers_full_lanes_for_partial_multiples():
    reg = [
        {'name': 'Lorem ipsum dolor', 'bits': 32, 'type': 'gray'},
        {'name': 'consetetur sadipsci', 'bits': 32, 'type': 1},
        {'name': 'ipsum dolor', 'bits': 32, 'type': 1},
        {'array': 48, 'name': 't dolore', 'gap_fill': '#B0BEC5'},
        {'name': 'dolores', 'bits': 16, 'type': 1},
    ]
    renderer = Renderer(bits=32)
    jsonml = renderer.render(reg)

    def collect_polygons(node, polys):
        if isinstance(node, list):
            if node and node[0] == 'polygon':
                polys.append(node[1])
            for child in node[1:]:
                collect_polygons(child, polys)

    polygons = []
    collect_polygons(jsonml, polygons)

    backgrounds = [
        p for p in polygons
        if p.get('fill') == '#B0BEC5' and p.get('stroke') == 'none'
    ]
    assert len(backgrounds) == 2

    base_y = renderer.fontsize * 1.2
    step = renderer.hspace / renderer.mod

    lane3_coords = None
    lane4_coords = None
    for poly in backgrounds:
        coords = [tuple(map(float, point.split(','))) for point in poly['points'].split()]
        top = coords[0][1]
        if top == pytest.approx(base_y + renderer.vlane * 3):
            lane3_coords = coords
        elif top == pytest.approx(base_y + renderer.vlane * 4):
            lane4_coords = coords

    assert lane3_coords is not None
    assert lane4_coords is not None

    assert lane3_coords[0][0] == pytest.approx(0)
    assert lane3_coords[1][0] == pytest.approx(renderer.hspace)
    assert lane3_coords[2][0] == pytest.approx(renderer.hspace)
    assert lane3_coords[3][0] == pytest.approx(0)

    assert lane4_coords[0][0] == pytest.approx(0)
    assert lane4_coords[1][0] == pytest.approx(step * 16)
    assert lane4_coords[2][0] == pytest.approx(step * 16)
    assert lane4_coords[3][0] == pytest.approx(0)


def test_array_text_aligns_to_first_lane_when_partial():
    reg = [
        {'name': 'Lorem ipsum dolor', 'bits': 32, 'type': 'gray'},
        {'name': 'consetetur sadipsci', 'bits': 32, 'type': 1},
        {'name': 'ipsum dolor', 'bits': 32, 'type': 1},
        {'array': 48, 'name': 't dolore'},
        {'name': 'dolores', 'bits': 16, 'type': 1},
    ]
    renderer = Renderer(bits=32)
    jsonml = renderer.render(reg)

    def collect_texts(node, texts):
        if isinstance(node, list):
            if node and node[0] == 'text':
                texts.append((node[1], extract_text_content(node)))
            for child in node[1:]:
                collect_texts(child, texts)

    texts = []
    collect_texts(jsonml, texts)
    gap_text = next(attrs for attrs, content in texts if content == 't dolore')

    base_y = renderer.fontsize * 1.2
    start_lane = 96 // renderer.mod
    first_lane_center = base_y + renderer.vlane * start_lane + renderer.vlane / 2
    expected_y = first_lane_center + renderer.fontsize / 2
    assert float(gap_text['y']) == pytest.approx(expected_y)

    step = renderer.hspace / renderer.mod
    start_offset = 96 % renderer.mod
    if start_offset:
        first_lane_bits = min(48, renderer.mod - start_offset)
    else:
        first_lane_bits = min(48, renderer.mod)
    lane_left = start_offset * step
    lane_right = lane_left + first_lane_bits * step
    expected_x = (lane_left + lane_right) / 2
    assert float(gap_text['x']) == pytest.approx(expected_x)


def test_array_text_stays_centered_for_full_lane_multiples():
    reg = [
        {'name': 'Lorem ipsum dolor', 'bits': 32, 'type': 'gray'},
        {'name': 'consetetur sadipsci', 'bits': 32, 'type': 1},
        {'name': 'ipsum dolor', 'bits': 32, 'type': 1},
        {'array': 64, 'name': 'centered'},
        {'name': 'dolores', 'bits': 16, 'type': 1},
    ]
    renderer = Renderer(bits=32)
    jsonml = renderer.render(reg)

    def collect_texts(node, texts):
        if isinstance(node, list):
            if node and node[0] == 'text':
                texts.append((node[1], extract_text_content(node)))
            for child in node[1:]:
                collect_texts(child, texts)

    texts = []
    collect_texts(jsonml, texts)
    gap_text = next(attrs for attrs, content in texts if content == 'centered')

    base_y = renderer.fontsize * 1.2
    start_lane = 96 // renderer.mod
    lane_span = 64 // renderer.mod
    center_y = base_y + renderer.vlane * start_lane + renderer.vlane * lane_span / 2
    expected_y = center_y + renderer.fontsize / 2
    assert float(gap_text['y']) == pytest.approx(expected_y)


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
                texts.append((node[1], extract_text_content(node)))
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
                texts.append((node[1], extract_text_content(node)))
            for child in node[1:]:
                collect_texts(child, texts)

    texts = []
    collect_texts(jsonml, texts)
    gap_text = next(attrs for attrs, content in texts if content == 'gap')
    assert gap_text.get('fill') == '#0f0'
    assert gap_text.get('stroke') == 'none'


def test_array_text_allows_newline():
    reg = [
        {'name': 'length1', 'bits': 8},
        {'array': 8, 'name': 'first line\nsecond line'},
        {'name': 'rest', 'bits': 8},
    ]
    renderer = Renderer(bits=16)
    jsonml = renderer.render(reg)

    text_nodes = []

    def collect_text_nodes(node):
        if isinstance(node, list):
            if node and node[0] == 'text':
                text_nodes.append(node)
            for child in node[1:]:
                collect_text_nodes(child)

    collect_text_nodes(jsonml)
    gap_node = next(
        node for node in text_nodes
        if any(isinstance(child, list) and child[0] == 'tspan' and child[2] == 'first line'
               for child in node[2:])
    )
    spans = [child for child in gap_node[2:] if isinstance(child, list) and child[0] == 'tspan']
    assert [span[2] for span in spans] == ['first line', 'second line']
    assert all('x' in span[1] for span in spans)
    assert all('y' in span[1] for span in spans)
    x_values = [float(span[1]['x']) for span in spans]
    assert x_values[0] == pytest.approx(x_values[1])
    y_values = [float(span[1]['y']) for span in spans]
    assert y_values[1] > y_values[0]


def test_array_hide_lines_skips_grid_and_horizontal():
    reg = [
        {'array': 128, 'hide_lines': True},
    ]
    renderer = Renderer(bits=32, grid_draw=True)
    jsonml = renderer.render(reg)

    lines = []

    def collect_lines(node):
        if isinstance(node, list):
            if node and node[0] == 'line':
                lines.append(node[1])
            for child in node[1:]:
                collect_lines(child)

    collect_lines(jsonml)

    horizontals = [
        attrs for attrs in lines
        if attrs.get('y1', 0) == attrs.get('y2', 0)
    ]
    tiny_verticals = [attrs for attrs in lines if attrs.get('y2') == 7.9]

    assert len(horizontals) == 2
    assert tiny_verticals == []
