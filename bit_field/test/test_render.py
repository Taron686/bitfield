import pytest
import json
from .. import render
from ..jsonml_stringify import jsonml_stringify
from ..render import Renderer
from pathlib import Path
from subprocess import run, CalledProcessError
from .render_report import render_report


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
    renderer = Renderer(bits=8, types={"gray": {"color": "#D9D9D9", "label": "test"}})
    jsonml = renderer.render(reg)

    fills = []

    def collect_rect_fills(node):
        if isinstance(node, list):
            if node and node[0] == 'rect':
                fills.append(node[1].get('fill'))
            for child in node[1:]:
                collect_rect_fills(child)

    collect_rect_fills(jsonml)
    assert '#D9D9D9' in fills


def test_types_config_requires_mapping():
    with pytest.raises(TypeError):
        Renderer(types=["not", "a", "mapping"])
