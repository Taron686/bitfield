A Python3 port of the javascript [bit-field library](https://github.com/drom/bitfield/) by [Aliaksei Chapyzhenka](https://github.com/drom).

This package is also available as an extension for Sphinx: [sphinxcontrib-bitfield](https://github.com/Arth-ur/sphinxcontrib-bitfield).

## Install

```sh
pip install bit_field
```

To install this package with JSON5 support:

```sh
pip install bit_field[JSON5]
```

## Library usage

```python
from bit_field import render, jsonml_stringify

reg = [
  {'bits': 8, 'name': 'data'}
]

jsonml = render(reg, hspace=888)
html = jsonml_stringify(jsonml)
# <svg...>
```

### Vertical lane labels

Add a rotated label spanning multiple lanes either by passing a
`label_lines` configuration or by appending an object with a
`"label_lines"` key to the descriptor list:

```python
reg = [
  {"bits": 8, "name": "data"},
  {"label_lines": "Demo", "font_size": 6, "start_line": 0, "end_line": 3, "layout": "right"},
]
render(reg, bits=8)
```

The label is drawn only if `end_line - start_line >= 3`.

## CLI Usage

```sh
bit_field [options] input > alpha.svg
```

### options

```
input        : input JSON filename - must be specified always
--input      : input JSON filename (kept for compatibility)
--compact    : compact rendering mode
--vspace     : vertical space - default 80
--hspace     : horizontal space - default 640
--lanes      : rectangle lanes (computed if omitted)
--bits       : bits per lane - default 32
--fontfamily : - default sans-serif
--fontweight : - default normal
--fontsize   : - default 14
--strokewidth: - default 1
--hflip      : horizontal flip
--vflip      : vertical flip
--trim       : horizontal space available for a single character
--uneven:    : uneven lanes
--label-lines: text for a vertical label across lanes
--label-fontsize: font size for label text
--label-start-line: starting line index for label
--label-end-line: ending line index for label
--label-layout: place label on 'left' or 'right'

--beautify   : use xml beautifier

--json5      : force json5 input format (need json5 python module)
--no-json5   : never use json5 input format
```

### alpha.json

```json
[
    { "name": "IPO",   "bits": 8, "attr": "RO" },
    {                  "bits": 7 },
    { "name": "BRK",   "bits": 5, "attr": "RW", "type": 4 },
    { "name": "CPK",   "bits": 1 },
    { "name": "Clear", "bits": 3 },
    { "bits": 8 }
]
```
### alpha.svg

![Heat Sink](https://raw.githubusercontent.com/Arth-ur/bitfield/master/bit_field/test/alpha.svg?sanitize=true)

### Licensing
This work is based on original work by [Aliaksei Chapyzhenka](https://github.com/drom) under the MIT license (see LICENSE-ORIGINAL).
