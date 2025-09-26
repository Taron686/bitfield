import pytest
import json
from .. import render
from ..render import Renderer
from ..jsonml_stringify import jsonml_stringify
from pathlib import Path
from subprocess import run, CalledProcessError
from .render_report import render_report


def _walk(node):
    if isinstance(node, list):
        yield node
        for child in node[2:]:
            if isinstance(child, list):
                yield from _walk(child)


def _contains_text(node, text):
    if not isinstance(node, list):
        return False
    if node and node[0] == 'tspan' and len(node) >= 3 and node[2] == text:
        return True
    for child in node[2:]:
        if _contains_text(child, text):
            return True
    return False


@pytest.mark.parametrize('bits', [31, 16, 8])
@pytest.mark.parametrize('compact', [True, False])
@pytest.mark.parametrize('hflip', [True, False])
@pytest.mark.parametrize('vflip', [True, False])
@pytest.mark.parametrize('strokewidth', [1, 4])
@pytest.mark.parametrize('trim', [None, 8])
@pytest.mark.parametrize('uneven', [True])
def test_render(request,
                output_dir,
                input_data,
                bits,
                compact,
                hflip,
                vflip,
                strokewidth,
                trim,
                uneven):
    res = render(input_data,
                 bits=bits,
                 compact=compact,
                 hflip=hflip,
                 vflip=vflip,
                 strokewidth=strokewidth,
                 trim=trim,
                 uneven=uneven)
    total_bits = 31
    res[1]['data-bits'] = bits
    res[1]['data-lanes'] = (total_bits + bits - 1) // bits
    res[1]['data-compact'] = compact
    res[1]['data-hflip'] = hflip
    res[1]['data-vflip'] = vflip
    res[1]['data-strokewidth'] = strokewidth
    res[1]['data-trim'] = trim
    res[1]['data-uneven'] = uneven
    res = jsonml_stringify(res)

    output_filename = request.node.name
    output_filename += '.svg'

    (output_dir / output_filename).write_text(res)


@pytest.fixture
def input_data():
    return json.loads("""
[
  { "name": "IPO",   "bits": 8, "attr": "RO" },
  {                  "bits": 7 },
  { "name": "BRK",   "bits": 5, "attr": [ 11, "RO"], "type": 4 },
  { "name": "CPK",   "bits": 1 },
  { "name": "Clear", "bits": 3 },
  { "bits": 7 }
]
    """)


@pytest.fixture
def output_dir():
    try:
        git_describe = run(
            ['git', 'describe', '--tags', '--match', 'v*'],
            capture_output=True,
            check=True,
            text=True,
        ).stdout.strip()
    except CalledProcessError:
        git_describe = run(
            ['git', 'rev-parse', '--short', 'HEAD'],
            capture_output=True,
            check=True,
            text=True,
        ).stdout.strip()
    output_dir = Path(__file__).parent / f'output-{git_describe}'
    output_dir.mkdir(exist_ok=True)
    return output_dir

@pytest.fixture(scope='module', autouse=True)
def fixture_render_report():
    yield
    render_report()


def test_types_config_color_override_by_label():
    reg = [
        {"name": "field", "bits": 8, "type": "test"},
    ]
    jsonml = render(
        reg,
        bits=8,
        types={"gray": {"color": "#D9D9D9", "label": "test"}},
    )

    fills = []

    def collect_rect_fills(node):
        if isinstance(node, list):
            if node and node[0] == 'rect':
                fills.append(node[1].get('fill'))
            for child in node[1:]:
                collect_rect_fills(child)

    collect_rect_fills(jsonml)
    assert '#D9D9D9' in fills


def test_types_config_color_override_allows_hex_without_hash():
    reg = [
        {"name": "field", "bits": 8, "type": "test"},
    ]
    jsonml = render(
        reg,
        bits=8,
        types={"gray": {"color": "EBF1DE", "label": "test"}},
    )

    fills = []

    def collect_rect_fills(node):
        if isinstance(node, list):
            if node and node[0] == 'rect':
                fills.append(node[1].get('fill'))
            for child in node[1:]:
                collect_rect_fills(child)

    collect_rect_fills(jsonml)
    assert '#EBF1DE' in fills


def test_types_config_requires_mapping():
    with pytest.raises(TypeError):
        render([], types=["not", "a", "mapping"])


def test_attr_allows_single_text_rotation():
    reg = [
        {"name": "field", "bits": 4, "type": "gray", "attr": ["rotated", -90]},
    ]

    jsonml = render(reg, bits=8)

    rotated_node = None
    for node in _walk(jsonml):
        if node and node[0] == 'text':
            attrs = node[1]
            for child in node[2:]:
                if (
                    isinstance(child, list)
                    and len(child) >= 3
                    and child[0] == 'tspan'
                    and child[2] == 'rotated'
                ):
                    rotated_node = node
                    break
            if rotated_node is not None:
                break

    assert rotated_node is not None, "rotated attribute text not found"

    attrs = rotated_node[1]
    assert attrs.get('text-anchor') == 'middle'
    assert attrs.get('dominant-baseline') == 'hanging'

    rect_attrs = None
    for node in _walk(jsonml):
        if node and node[0] == 'rect':
            rect_attrs = node[1]
            break

    assert rect_attrs is not None, "field rectangle not found"

    font_size = attrs['font-size']
    renderer = Renderer(bits=8, fontsize=font_size)
    upward, _ = renderer._rotated_text_extents('rotated', -90)
    margin = font_size * 0.2
    expected_y = rect_attrs['y'] + margin + upward
    assert attrs.get('y') == pytest.approx(expected_y)
    transform = attrs.get('transform')
    assert transform is not None

    assert transform.startswith('rotate(')
    angle, pivot_x, pivot_y = transform[7:-1].split(',')
    assert float(angle) == pytest.approx(-90)
    assert float(pivot_x) == pytest.approx(attrs['x'])
    assert float(pivot_y) == pytest.approx(attrs['y'])


def test_attr_rotated_text_offsets_below_field_for_positive_angles():
    reg = [
        {"name": "field", "bits": 4, "type": "gray", "attr": ["rotated", 90]},
    ]

    jsonml = render(reg, bits=8)

    rotated_node = None
    for node in _walk(jsonml):
        if node and node[0] == 'text':
            attrs = node[1]
            for child in node[2:]:
                if (
                    isinstance(child, list)
                    and len(child) >= 3
                    and child[0] == 'tspan'
                    and child[2] == 'rotated'
                ):
                    rotated_node = node
                    break
            if rotated_node is not None:
                break

    assert rotated_node is not None, "rotated attribute text not found"

    attrs = rotated_node[1]
    rect_attrs = None
    for node in _walk(jsonml):
        if node and node[0] == 'rect':
            rect_attrs = node[1]
            break

    assert rect_attrs is not None, "field rectangle not found"

    font_size = attrs['font-size']
    renderer = Renderer(bits=8, fontsize=font_size)
    upward, _ = renderer._rotated_text_extents('rotated', 90)
    margin = font_size * 0.2
    expected_y = rect_attrs['y'] + margin + upward

    assert attrs.get('y') == pytest.approx(expected_y)
    transform = attrs.get('transform')
    assert transform is not None and transform.startswith('rotate(')

    angle, pivot_x, pivot_y = transform[7:-1].split(',')
    assert float(angle) == pytest.approx(90)
    assert float(pivot_x) == pytest.approx(attrs['x'])
    assert float(pivot_y) == pytest.approx(attrs['y'])


def test_rotated_attr_increases_attribute_height():
    reg = [
        {"name": "field", "bits": 4, "attr": [["vertical", -90], "RO"]},
    ]

    jsonml = render(reg, bits=8)

    vertical_group = None
    ro_group = None
    for node in _walk(jsonml):
        if node and node[0] == 'g':
            transform = node[1].get('transform')
            if not isinstance(transform, str) or not transform.startswith('translate(0'):
                continue
            if _contains_text(node, 'vertical'):
                vertical_group = node
            if _contains_text(node, 'RO'):
                ro_group = node

    assert vertical_group is not None, "rotated attribute group not found"
    assert ro_group is not None, "secondary attribute group not found"

    def extract_offset(group):
        transform = group[1]['transform']
        prefix = 'translate(0,'
        assert transform.startswith(prefix)
        value = transform[len(prefix):-1]
        return float(value.strip())

    first_offset = extract_offset(vertical_group)
    second_offset = extract_offset(ro_group)

    assert first_offset == pytest.approx(0)

    renderer = Renderer(bits=8)
    expected_offset = renderer._attribute_line_height(["vertical", -90])
    assert second_offset == pytest.approx(expected_offset)
    assert second_offset > renderer.fontsize


def test_field_name_supports_newlines():
    reg = [
        {"name": "Lorem ipsum\ndolor", "bits": 32, "type": "gray"},
    ]

    jsonml = render(reg, bits=32)

    matching_spans = []

    def collect_multiline_spans(node):
        if isinstance(node, list):
            if node and node[0] == 'text':
                spans = [child for child in node[2:] if isinstance(child, list) and child and child[0] == 'tspan']
                texts = [span[2] for span in spans]
                if 'Lorem ipsum' in texts and 'dolor' in texts:
                    matching_spans.extend(spans)
            for child in node[1:]:
                collect_multiline_spans(child)

    collect_multiline_spans(jsonml)

    assert any(span[2] == 'Lorem ipsum' for span in matching_spans)
    dolor_span = next(span for span in matching_spans if span[2] == 'dolor')
    assert 'dy' in dolor_span[1]
