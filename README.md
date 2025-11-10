# bit_field

A Python 3 port of the JavaScript [bit-field library](https://github.com/drom/bitfield/) by [Aliaksei Chapyzhenka](https://github.com/drom)
and a Fork of [Arth-ur](https://github.com/Arth-ur/bitfield). 
The renderer produces SVG diagrams from a simple JSON description and is also
available as a Sphinx extension: [sphinxcontrib-bitfield](https://github.com/Arth-ur/sphinxcontrib-bitfield).

## Features

* Render register/bit-field layouts to SVG from simple `bits`/`name` dictionaries
* Optional `[JSON5]` input support via the `json5` extra
* Per-field `type` descriptors with predefined colours or explicit RGB values
* Unknown-length gaps using `array` descriptors
* Cross-lane connector support through `arrow_jumps`
* Legends driven by the `legend` mapping or `config.types` overrides
* Per-bit attribute display with the `attr` list, only usable when `compact` = false is
* Vertical lane labels defined via `label_lines`, `start_line`/`end_line`, `layout`, and `angle`
* Layout controls through `compact`, `uneven`, `hflip`, `vflip`, `lanes`, and `bits`

## Installation

```sh
pip install bitfield-extended
```

To install with JSON5 support:

```sh
pip install bitfield-extended[JSON5]
```

## Library usage

### Basic rendering

```python
from bit_field import render, jsonml_stringify

reg = [
    {"name": "IPO",   "bits": 8, "attr": "RO"},
    {"bits": 7},
    {"name": "BRK",   "bits": 5, "attr": ["0b1011", "RW"], "type": 4},
    {"name": "CPK",   "bits": 5, "type": [120, 180, 255]},  # custom colour
    {"name": "Clear", "bits": 7},
    {"array": 64, "type": 4, "name": "gap", "gap_width":2 , "gap_fill": "black"}, # unknown-length field
    {"bits": 8},
]

jsonml = render(reg, bits=16, legend={"Status": 2, "Control": 4})
svg = jsonml_stringify(jsonml)
# <svg...>
```
### attr using
Example
```json
{ "attr": "RW" }
{ "name": "IPO",   "bits": 4, "attr": ["0b1011", "RW"] }    // bit labels for each bit     
{ "attr": [["Ctrl", 90], "RW"] } // rotated text plus normal text
```

### Vertical lane labels

Add horizontal labels spanning multiple lanes by including objects with a
`"label_lines"` key in your descriptor list. Newline characters (`\n`) create
multiple lines. The optional `angle` parameter rotates the text around its
centre. Set `"reserved": true` to draw the connecting arrow a little above the
start line when you need to indicate a reserved region:

**Supported keys for a label entry**

- `label_lines` *(required)* – string or list of strings to show; `\n` makes multiple lines.
- `font_size` *(required)* – text size in px; defaults to renderer `fontsize` when labels are provided globally.
- `start_line`, `end_line` *(required)* – zero-based lane indices defining the vertical span; `end_line` must be ≥ `start_line + 1`.
- `layout` *(required)* – `left` or `right`, defining which side of the diagram hosts the label.
- `angle` – rotate the text in degrees; vertical text automatically uses extra spacing.
- `reserved` – boolean; if `true` the arrow sits slightly above the bracket to highlight reserved blocks.
- Internal `_offset` and `_margin` are assigned automatically when labels overlap; no need to set them manually.

```json
[
  {"bits": 8, "name": "data"},
  {"label_lines": "Line1\nLine2", "font_size": 6, "start_line": 0, "end_line": 3, "layout": "right", "angle": 30},
  {"label_lines": "reserved", "font_size": 6, "start_line": 4, "end_line": 7, "layout": "right", "reserved": true},
  {"label_lines": "Other", "font_size": 6, "start_line": 4, "end_line": 7, "layout": "right"}
]
```

Each label is drawn outside the bitfield on the requested side. Labels are
rendered only if `end_line - start_line < 0`.

### Arrow-head jumps

Route cross-lane references with dedicated arrow-head jump descriptors.
They run vertically from a `start_line`, step through two intermediate
lanes, then end on the requested bit column with an arrow head pointing to
the destination field. Arrow-head length automatically scales with the
`stroke_width`, so thicker lines give a more pronounced head without any
additional parameters.

You can supply arrow jumps either via the `arrow_jumps` argument to
`render()` or by embedding objects that contain an `"arrow_jump"` key inside
your descriptor list (they are stripped out before field rendering).

**Supported keys for an arrow-head descriptor**

- `arrow_jump` *(required)* – bit index in the source lane that the arrow leaves from.
- `start_line` *(required)* – zero-based lane where the arrow starts.
- `jump_to_first`, `jump_to_second` *(required)* – intermediate lanes that the two vertical legs run through before the final horizontal segment.
- `end_bit` *(required)* – bit index in the target lane that the arrow head points to.
- `layout` *(required)* – `left` or `right`, deciding on which side of the diagram the detour is routed.
- `stroke_width` – thickness of the path; also scales the arrow head length.
- `outer_distance` – minimum spacing, in SVG units, between the diagram edge and the outer vertical run (default `10`).
- `max_outer_distance` – hard cap for automatic margin adjustments when the arrow head would overlap the target bit (default `25`).

```python
reg = [
  {"name": "CTRL", "bits": 8},
  {"name": "DATA", "bits": 8},
  {"name": "STATUS", "bits": 8},
]

arrow = {
  "arrow_jump": 2,
  "start_line": 0,
  "jump_to_first": 1,
  "jump_to_second": 2,
  "end_bit": 6,
  "layout": "right",
  "stroke_width": 4,
}

svg = jsonml_stringify(render(reg, bits=8, arrow_jumps=arrow, compact=True))
```

### Array gaps

Use an `{"array": length}` descriptor to draw a wedge representing an
unknown-length field or gap. The optional `type` and `name` keys colour and
label the gap, and `gap_width` adjusts the wedge width as a fraction of a
single bit (default `0.5`):

**Supported keys for an array descriptor**

- `array` *(required)* – number of bits covered by the gap; can also be a list where the last entry is interpreted as the length.
- `name` – label shown inside the wedge.
- `type` – numeric ID or RGB triplet used to colour both the wedge border and its background fill; overrides `fill`/`gap_fill`.
- `gap_width` – width multiplier relative to a single bit cell; controls the wedge thickness (default `0.5`).
- `gap_fill` – colour of the wedge polygon; defaults to `fill` or white if omitted.
- `fill` – legacy alias for `gap_fill`; used only when `gap_fill` is absent.
- `hide_lines` – boolean; if `true`, suppresses the outline so the gap blends with adjacent fields. Hidden gaps still keep the final lane boundary for following fields.
- `font_size` – allows matching text height to neighbouring fields when a `name` is provided.

```python
reg = [
  {"name": "start", "bits": 8},
  {"array": 8, "type": 4, "name": "gap", "gap_width": 0.75},
  {"name": "end", "bits": 8},
]
render(reg, bits=16)
```

### Legends

Pass a mapping of legend names to field types to add a legend above the
bitfield:

```python
legend = {"Status": 2, "Control": 4}
render(reg, legend=legend)
```

The numbers refer to the `type` values used in the field descriptors and can
also be RGB triplets `[r, g, b]`.

## CLI usage

```sh
bit_field [options] input > out.svg
```

### Options

```
input                           input JSON filename (required)
--input                         compatibility option
--vspace VSPACE                 vertical space (default 80)
--hspace HSPACE                 horizontal space (default 800)
--lanes LANES                   rectangle lanes (computed if omitted)
--bits BITS                     bits per lane (default 32)
--fontfamily FONTFAMILY         font family (default sans-serif)
--fontweight FONTWEIGHT         font weight (default normal)
--fontsize FONTSIZE             font size (default 14)
--strokewidth STROKEWIDTH       stroke width (default 1)
--hflip                         horizontal flip
--vflip                         vertical flip
--compact                       compact rendering mode
--trim TRIM                     trim long bitfield names
--uneven                        uneven lanes
--legend NAME TYPE              add legend item (repeatable)
--beautify                      pretty-print SVG
--json5                         force JSON5 input
--no-json5                      disable JSON5 input
```

### Example JSON

```json
[
    { "name": "Lorem ipsum dolor", "bits": 32 , "type": 1},
    { "name": "consetetur sadipsci", "bits": 32 , "type": 1},
    { "name": "ipsum dolor ", "bits": 32 , "type": 1},
    { "name": "t dolore ", "bits": 8 , "type": 1},
    { "name": "dolores ", "bits": 8, "type": 1},
    { "name": "ea takima", "bits": 8 , "type": 1},
    { "name": "s est Lorem", "bits": 8 , "type": [125,36,200]},
    { "array": 64, "name": "et accusa","type": 3},

    { "name": "et accusa", "bits": 32 , "type": 4},
    { "array": 64, "type": 4, "name": " accu","font_size": 12, "gap_width": 3,"gap_fill":"red", "hide_lines": true},

    {"label_lines": "Line Cover1", "font_size": 12, "start_line": 0, "end_line": 3, "layout": "left"},
    {"label_lines": "Line Cover2", "font_size": 12, "start_line": 4, "end_line": 4, "layout": "left"},
    {"label_lines": "Length", "font_size": 12, "start_line": 5, "end_line": 8, "layout": "right", "reserved": true, "angle":-90},
    {"label_lines": "Length", "font_size": 12, "start_line": 2, "end_line": 4, "layout": "right", "angle":90},
    {"arrow_jump": 2,"start_line": 0,"jump_to_first": 1,"jump_to_second": 2,"end_bit": 6,"layout": "left","stroke_width": 1}
    
]
```

Add a `types` mapping inside `config` to override the colors associated with
field types and to use human-readable labels in your payload:

```json
{
  "config": {
    "bits": 32,
    "types": {
      "gray": {
        "color": "#D9D9D9",
        "label": "test"
      }
    }
  },
  "payload": [
    { "name": "Lorem ipsum dolor", "bits": 32, "type": "test" }
  ]
}
```

Disable the bit number labels drawn above each field by setting
`"number_draw": false` in your configuration:

```json
{
  "config": {
    "number_draw": false
  },
  "payload": [
    { "name": "Lorem ipsum dolor", "bits": 32 }
  ]
}
```
![Json Example](example/example.svg)

Rendering with the CLI:

```sh
bit_field alpha.json > alpha.svg
```

## Licensing

This work is based on original work by [Aliaksei Chapyzhenka](https://github.com/drom) under the MIT license (see LICENSE-ORIGINAL).
