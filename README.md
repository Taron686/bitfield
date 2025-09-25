# bit_field

A Python 3 port of the JavaScript [bit-field library](https://github.com/drom/bitfield/) by [Aliaksei Chapyzhenka](https://github.com/drom)
and a Fork of [Arth-ur](https://github.com/Arth-ur/bitfield). 
The renderer produces SVG diagrams from a simple JSON description and is also
available as a Sphinx extension: [sphinxcontrib-bitfield](https://github.com/Arth-ur/sphinxcontrib-bitfield).

## Features

* Render register/bit‑field layouts to SVG
* Optional [JSON5](https://json5.org/) input support
* Per-field types with predefined colours or explicit RGB values
* Unknown-length gaps using `array` descriptors
* Legends explaining field types
* Per-bit attribute display and automatic name trimming
* Vertical lane labels for grouping fields across lanes
* Horizontal/vertical flipping, compact layout, and uneven lane widths

## Installation

```sh
currently not on pip
```

To install with JSON5 support:

```sh
currently not on pip
```

## Library usage

### Basic rendering

```python
from bit_field import render, jsonml_stringify

reg = [
    {"name": "IPO",   "bits": 8, "attr": "RO"},
    {"bits": 7},
    {"name": "BRK",   "bits": 5, "attr": [0b1011, "RW"], "type": 4},
    {"name": "CPK",   "bits": 1, "type": [120, 180, 255]},  # custom colour
    {"name": "Clear", "bits": 3},
    {"array": 8, "type": 4, "name": "gap"},                  # unknown-length field
    {"bits": 8},
]

jsonml = render(reg, bits=16, legend={"Status": 2, "Control": 4})
svg = jsonml_stringify(jsonml)
# <svg...>
```

### Vertical lane labels

Add horizontal labels spanning multiple lanes by including objects with a
`"label_lines"` key in your descriptor list. Newline characters (`\n`) create
multiple lines. The optional `angle` parameter rotates the text around its
centre. Set `"Reserved": true` to draw the connecting arrow a little above the
start line when you need to indicate a reserved region:

```json
[
  {"bits": 8, "name": "data"},
  {"label_lines": "Line1\nLine2", "font_size": 6, "start_line": 0, "end_line": 3, "layout": "right", "angle": 30},
  {"label_lines": "Reserved", "font_size": 6, "start_line": 4, "end_line": 7, "layout": "right", "Reserved": true},
  {"label_lines": "Other", "font_size": 6, "start_line": 4, "end_line": 7, "layout": "right"}
]
```

Each label is drawn outside the bitfield on the requested side. Labels are
rendered only if `end_line - start_line >= 2`.

### Array gaps

Use an `{"array": length}` descriptor to draw a wedge representing an
unknown-length field or gap. The optional `type` and `name` keys colour and
label the gap, and `gap_width` adjusts the wedge width as a fraction of a
single bit (default `0.5`):

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
    { "array": 64, "type": 4, "name": " accu","font_size": 12},

    {"label_lines": "Line Cover1", "font_size": 12, "start_line": 0, "end_line": 3, "layout": "left"},
    {"label_lines": "Line Cover2", "font_size": 12, "start_line": 4, "end_line": 4, "layout": "left"},
    {"label_lines": "Length", "font_size": 12, "start_line": 5, "end_line": 8, "layout": "right"},
    {"label_lines": "Length", "font_size": 12, "start_line": 2, "end_line": 4, "layout": "right"}
    
]
```

Add a `types` mapping inside `config` to override the colours associated with
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
![Json Example](example/example.svg)

Rendering with the CLI:

```sh
bit_field alpha.json > alpha.svg
```

## Licensing

This work is based on original work by [Aliaksei Chapyzhenka](https://github.com/drom) under the MIT license (see LICENSE-ORIGINAL).
