from .tspan import tspan
import colorsys
import string


DEFAULT_TYPE_COLOR = "rgb(229, 229, 229)"


def t(x, y):
    return 'translate({}, {})'.format(x, y)


def typeStyle(t):
    return ';fill:' + typeColor(t)


def _normalize_color(color):
    if not isinstance(color, str):
        return None
    text = color.strip()
    if not text:
        return None
    if text.startswith('#'):
        if len(text) == 7 and all(c in string.hexdigits for c in text[1:]):
            return text
        return text
    if len(text) == 6 and all(c in string.hexdigits for c in text):
        return '#' + text
    return text


def _parse_type_overrides(types):
    if types is None:
        return {}
    if not isinstance(types, dict):
        raise TypeError('types configuration must be a mapping')

    overrides = {}
    for key, value in types.items():
        aliases = [key]
        color = None

        if isinstance(value, dict):
            color = _normalize_color(value.get('color'))
            label = value.get('label')
            if label is not None:
                aliases.append(label)
            value_alias = value.get('value')
            if value_alias is not None:
                aliases.append(value_alias)
            aliases_config = value.get('aliases')
            if isinstance(aliases_config, (list, tuple, set)):
                aliases.extend(aliases_config)
            elif aliases_config is not None:
                aliases.append(aliases_config)
        else:
            color = _normalize_color(value)

        if not isinstance(color, str):
            continue

        for alias in aliases:
            if alias is None:
                continue
            overrides[str(alias)] = color

    return overrides


def _type_color_value(t, overrides=None):
    styles = {
        '2': 0,
        '3': 80,
        '4': 170,
        '5': 45,
        '6': 126,
        '7': 215,
    }

    if isinstance(t, list):
        if len(t) == 3 and all(isinstance(x, int) and 0 <= x <= 255 for x in t):
            r, g, b = t
            return f"rgb({r}, {g}, {b})"
        return DEFAULT_TYPE_COLOR

    if overrides:
        key = str(t)
        if key in overrides:
            return overrides[key]

    t = str(t)
    if t in styles:
        r, g, b = colorsys.hls_to_rgb(styles[t] / 360, 0.9, 1)
        return "rgb({:.0f}, {:.0f}, {:.0f})".format(r * 255, g * 255, b * 255)
    if "#" in t and len(t) == 7:
        return t
    return DEFAULT_TYPE_COLOR


def typeColor(t):
    return _type_color_value(t)


class Renderer(object):
    def __init__(self,
                 vspace=80,
                 hspace=640,
                 bits=32,
                 lanes=None,
                 fontsize=14,
                 fontfamily='sans-serif',
                 fontweight='normal',
                 compact=False,
                 hflip=False,
                 vflip=False,
                 strokewidth=1,
                 trim=None,
                 uneven=False,
                 legend=None,
                 label_lines=None,
                 grid_draw=True,
                 types=None,
                 **extra_kwargs):
        if vspace <= 19:
            raise ValueError(
                'vspace must be greater than 19, got {}.'.format(vspace))
        if hspace <= 39:
            raise ValueError(
                'hspace must be greater than 39, got {}.'.format(hspace))
        if lanes is not None and lanes <= 0:
            raise ValueError(
                'lanes must be greater than 0, got {}.'.format(lanes))
        if bits <= 4:
            raise ValueError(
                'bits must be greater than 4, got {}.'.format(bits))
        if fontsize <= 5:
            raise ValueError(
                'fontsize must be greater than 5, got {}.'.format(fontsize))
        self.vspace = vspace
        self.hspace = hspace
        self.bits = bits  # bits per lane
        self.lanes = lanes  # computed in render if None
        self.total_bits = None
        self.fontsize = fontsize
        self.fontfamily = fontfamily
        self.fontweight = fontweight
        self.compact = compact
        self.hflip = hflip
        self.vflip = vflip
        self.stroke_width = strokewidth
        self.trim_char_width = trim
        self.uneven = uneven
        self.legend = legend
        if label_lines is not None and not isinstance(label_lines, list):
            self.label_lines = [label_lines]
        else:
            self.label_lines = label_lines
        types = extra_kwargs.pop('types', types)
        if extra_kwargs:
            unexpected = ', '.join(sorted(extra_kwargs))
            raise TypeError(f'Renderer.__init__() got unexpected keyword argument(s): {unexpected}')

        self.grid_draw = grid_draw
        self.type_overrides = _parse_type_overrides(types)

    def get_total_bits(self, desc):
        lsb = 0
        for e in desc:
            if 'array' in e:
                # numeric array descriptors specify a gap length
                length = e['array'][-1] if isinstance(e['array'], list) else e['array']
                lsb += length
            elif 'bits' in e:
                lsb += e['bits']
        return lsb

    def type_color(self, value):
        return _type_color_value(value, self.type_overrides)

    def type_style(self, value):
        return ';fill:' + self.type_color(value)

    def _extract_label_lines(self, desc):
        collected = []
        filtered = []
        for e in desc:
            if isinstance(e, dict) and 'label_lines' in e:
                collected.append(e)
            else:
                filtered.append(e)
        if collected:
            if self.label_lines is None:
                self.label_lines = collected
            else:
                self.label_lines.extend(collected)
        return filtered

    def _label_lines_margins(self):
        self.cage_width = self.hspace / self.mod
        self.label_gap = self.cage_width / 2
        self.label_width = self.cage_width
        left_margin = right_margin = 0

        for side in ('left', 'right'):
            active = []
            for cfg in [c for c in self.label_lines if c['layout'] == side]:
                font_size = cfg.get('font_size', self.fontsize)
                lines = cfg['label_lines'].split('\n')
                max_text_len = max((len(line) for line in lines), default=0)
                text_length = max_text_len * font_size * 0.6
                margin = self.label_width / 2 + 2 * self.label_gap + text_length
                cfg['_margin'] = margin
                active = [a for a in active if a['end'] >= cfg['start_line']]
                offset = 0
                for a in active:
                    offset = max(offset, a['offset'] + a['margin'])
                cfg['_offset'] = offset
                active.append({'end': cfg['end_line'], 'offset': offset, 'margin': margin})
                if side == 'left':
                    left_margin = max(left_margin, offset + margin)
                else:
                    right_margin = max(right_margin, offset + margin)

        self.label_margin = max(left_margin, right_margin)
        return left_margin, right_margin

    def render(self, desc):
        desc = self._extract_label_lines(desc)

        self.total_bits = self.get_total_bits(desc)
        if self.lanes is None:
            self.lanes = (self.total_bits + self.bits - 1) // self.bits
        mod = self.bits
        self.mod = mod
        lsb = 0
        msb = self.total_bits - 1
        self.hidden_array_ranges = []
        for e in desc:
            if 'array' in e:
                length = e['array'][-1] if isinstance(e['array'], list) else e['array']
                if isinstance(e, dict) and e.get('hide_lines'):
                    self.hidden_array_ranges.append((lsb, lsb + length))
                lsb += length
                continue
            if 'bits' not in e:
                continue
            e['lsb'] = lsb
            lsb += e['bits']
            e['msb'] = lsb - 1
            e['lsbm'] = e['lsb'] % mod
            e['msbm'] = e['msb'] % mod
            if 'type' not in e:
                e['type'] = None

        if self.label_lines is not None:
            self._validate_label_lines()

        max_attr_count = 0
        for e in desc:
            if 'attr' in e:
                if isinstance(e['attr'], list):
                    max_attr_count = max(max_attr_count, len(e['attr']))
                else:
                    max_attr_count = max(max_attr_count, 1)

        if not self.compact:
            self.vlane = self.vspace - self.fontsize * (1.2 + max_attr_count)
            height = self.vspace * self.lanes  + self.stroke_width / 2
        else:
            self.vlane = self.vspace - self.fontsize * 1.2
            height = self.vlane * (self.lanes - 1) + self.vspace + self.stroke_width / 2
        if self.legend:
            height += self.fontsize * 1.2

        left_margin = right_margin = 0
        self.label_margin = 0
        self.label_gap = 0
        self.label_width = 0
        self.cage_width = 0 
        if self.label_lines is not None:
            left_margin, right_margin = self._label_lines_margins()

        canvas_width = self.hspace + left_margin + right_margin
        view_min_x = -left_margin

        res = ['svg', {
            'xmlns': 'http://www.w3.org/2000/svg',
            'width': canvas_width,
            'height': height,
            'viewBox': ' '.join(str(x) for x in [view_min_x, 0, canvas_width, height])
        }]

        arrow_def = ['defs', {},
                     ['marker', {
                         'id': 'arrow',
                         'markerWidth': 10,
                         'markerHeight': 6,
                         'refX': 10,
                         'refY': 3,
                         'orient': 'auto-start-reverse',
                         'markerUnits': 'strokeWidth'
                     },
                      ['path', {
                          'd': 'M0,0 L10,3 L0,6 Z',
                          'fill': 'black'
                      }]
                     ]]

        res.append(arrow_def)

        if self.legend:
            res.append(self.legend_items())

        # draw array gaps (unknown length fields)
        res.append(self.array_gaps(desc))

        for i in range(0, self.lanes):
            if self.hflip:
                self.lane_index = i
            else:
                self.lane_index = self.lanes - i - 1
            self.index = i
            res.append(self.lane(desc))
        if self.label_lines is not None:
            for cfg in self.label_lines:
                res.append(self._label_lines_element(cfg))
        return res

    def _validate_label_lines(self):
        required = ['label_lines', 'font_size', 'start_line', 'end_line', 'layout']
        for cfg in self.label_lines:
            for key in required:
                if key not in cfg:
                    raise ValueError('label_lines missing required key: {}'.format(key))
            start = cfg['start_line']
            end = cfg['end_line']
            if not (isinstance(start, int) and isinstance(end, int)):
                raise ValueError('label_lines start_line and end_line must be integers')
            if start < 0 or end < 0:
                raise ValueError('label_lines start_line and end_line must be non-negative')
            if end >= self.lanes or start >= self.lanes:
                raise ValueError('label_lines start_line/end_line exceed number of lanes')
            if end - start < 2:
                raise ValueError('label_lines must cover at least 2 lines')
            layout = cfg['layout']
            if layout not in ('left', 'right'):
                raise ValueError('label_lines layout must be "left" or "right"')
            if 'angle' in cfg and not isinstance(cfg['angle'], (int, float)):
                raise ValueError('label_lines angle must be a number')
            if 'Reserved' in cfg and not isinstance(cfg['Reserved'], bool):
                raise ValueError('label_lines Reserved must be a boolean')

    def _label_lines_element(self, cfg):
        text = cfg['label_lines']
        font_size = cfg.get('font_size', self.fontsize)
        start = cfg['start_line']
        end = cfg['end_line']
        layout = cfg['layout']
        base_y = self.fontsize * 1.2
        if self.legend:
            base_y += self.fontsize * 1.2
        top_y = base_y + self.vlane * start
        bottom_y = base_y + self.vlane * (end + 1)
        mid_y = (top_y + bottom_y) / 2
        gap = self.label_gap
        width = self.label_width
        offset = cfg.get('_offset', 0)
        if layout == 'left':
            x = -(gap + width / 2 + offset)
            left = x - width / 2
            right = x + width / 2
            text_x = x - gap
            anchor = 'end'
        else:
            x = self.hspace + gap + width / 2 + offset
            left = x - width / 2
            right = x + width / 2
            text_x = x + gap
            anchor = 'start'

        lines = text.split('\n')
        max_text_len = max((len(line) for line in lines), default=0)
        text_length = max_text_len * font_size * 0.6
        angle = cfg.get('angle', 0)
        if angle:
            text_x += (-text_length / 2) if layout == 'left' else (text_length / 2)
            anchor = 'middle'
        reserved_offset = self.vlane * 0.2 if cfg.get('Reserved') else 0
        text_attrs = {
            'x': text_x,
            'y': mid_y,
            'font-size': font_size,
            'font-family': self.fontfamily,
            'font-weight': self.fontweight,
            'text-anchor': anchor,
            'dominant-baseline': 'middle'
        }
        if angle:
            text_attrs['transform'] = 'rotate({},{},{})'.format(angle, text_x, mid_y)
        if len(lines) == 1:
            text_attrs['textLength'] = text_length
            text_attrs['lengthAdjust'] = 'spacingAndGlyphs'
            text_element = ['text', text_attrs, text]
        else:
            line_height = font_size * 1.2
            start_y = mid_y - line_height * (len(lines) - 1) / 2
            attrs = text_attrs.copy()
            del attrs['x']
            del attrs['y']
            elements = ['text', attrs]
            for i, line in enumerate(lines):
                elements.append(['tspan', {'x': text_x, 'y': start_y + line_height * i}, line])
            text_element = elements

        top_line_y = top_y - reserved_offset
        bracket = ['g', {
            'stroke': 'black',
            'stroke-width': self.stroke_width,
            'fill': 'none'
        },
            ['line', {'x1': left, 'y1': top_line_y, 'x2': right, 'y2': top_line_y}],
            ['line', {'x1': left, 'y1': bottom_y, 'x2': right, 'y2': bottom_y}],
            ['line', {
                'x1': left + self.cage_width/2,
                'y1': top_line_y,
                'x2': left + self.cage_width/2,
                'y2': bottom_y,
                'marker-start': 'url(#arrow)',
                'marker-end': 'url(#arrow)'
            }],
        ]

        return ['g', {}, bracket, text_element]

    def legend_items(self):
        items = ['g', {'transform': t(0, self.stroke_width / 2)}]
        name_padding = 64
        square_padding = 20
        x = self.hspace / 2 - len(self.legend) / 2 * (square_padding + name_padding)
        for key, value in self.legend.items():
            items.append(['rect', {
                'x': x,
                'width': 12,
                'height': 12,
                'fill': self.type_color(value),
                'style': 'stroke:#000; stroke-width:' + str(self.stroke_width) + ';' + self.type_style(value)
            }])
            x += square_padding
            items.append(['text', {
                'x': x,
                'font-size': self.fontsize,
                'font-family': self.fontfamily,
                'font-weight': self.fontweight,
                'y': self.fontsize / 1.2,
            }, key])
            x += name_padding
        return items

    def array_gaps(self, desc):
        step = self.hspace / self.mod
        base_y = self.fontsize * 1.2
        res = ['g', {}]
        bit_pos = 0
        for e in desc:
            if 'bits' in e:
                bit_pos += e['bits']
                continue
            if isinstance(e, dict) and 'array' in e:
                start = bit_pos
                length = e['array'][-1] if isinstance(e['array'], list) else e['array']
                end = start + length
                start_lane = start // self.mod
                end_lane = (end - 1) // self.mod if end > 0 else 0
                x1_raw = (start % self.mod) * step
                x2_raw = (end % self.mod) * step
                width = step * e.get('gap_width', 0.5)
                margin = step * 0.1
                top_y = base_y + self.vlane * start_lane
                bottom_y = base_y + self.vlane * (end_lane + 1)
                if x2_raw == 0 and end > start:
                    x2_outer = self.hspace - margin
                else:
                    x2_outer = x2_raw - margin
                x1 = x1_raw + margin
                x2 = x2_outer - width
                pts = f"{x1},{top_y} {x1+width},{top_y} {x2_outer},{bottom_y} {x2},{bottom_y}"
                color = self.type_color(e.get('type')) if e.get('type') is not None else 'black'
                grp = ['g', {'stroke': color, 'stroke-width': self.stroke_width}]
                # fill the full gap bounds with the type color to avoid transparent edges
                if e.get('type') is not None:
                    # use raw coordinates so the background reaches the lane boundaries
                    left = x1_raw
                    right = self.hspace if (x2_raw == 0 and end > start) else x2_raw
                    rect = f"{left},{top_y} {right},{top_y} {right},{bottom_y} {left},{bottom_y}"
                    grp.append(['polygon', {
                        'points': rect,
                        'fill': self.type_color(e['type']),
                        'stroke': 'none'
                    }])
                # gap polygon on top, optionally with custom fill
                gap_fill = e.get('gap_fill', e.get('fill', '#fff'))
                grp.append(['polygon', {'points': pts, 'fill': gap_fill}])
                grp.append(['line', {'x1': x1, 'y1': top_y, 'x2': x2, 'y2': bottom_y}])
                grp.append(['line', {'x1': x1+width, 'y1': top_y, 'x2': x2_outer, 'y2': bottom_y}])
                if 'name' in e:
                    mid_x = (x1 + x2_outer) / 2
                    mid_y = (top_y + bottom_y) / 2 + self.fontsize / 2
                    text_color = e.get('font_color', 'black')
                    grp.append(['text', {
                        'x': mid_x,
                        'y': mid_y,
                        'font-size': self.fontsize,
                        'font-family': self.fontfamily,
                        'font-weight': self.fontweight,
                        'text-anchor': 'middle',
                        'fill': text_color,
                        'stroke': 'none'
                    }, e['name']])
                res.append(grp)
                bit_pos = end
        return res

    def lane(self, desc):
        if self.compact:
            if self.index > 0:
                dy = (self.index - 1) * self.vlane + self.vspace
            else:
                dy = 0
        else:
            dy = self.index * self.vspace
        if self.legend:
            dy += self.fontsize * 1.2
        res = ['g', {
            'transform': t(0, dy)
        }]
        res.append(self.labels(desc))
        res.append(self.cage(desc))
        return res

    def cage(self, desc):
        if not self.compact or self.index == 0:
            dy = self.fontsize * 1.2
        else:
            dy = 0
        res = ['g', {
            'stroke': 'black',
            'stroke-width': self.stroke_width,
            'stroke-linecap': 'butt',
            'transform': t(0, dy)
        }]

        skip_count = 0
        if self.uneven and self.lanes > 1 and self.lane_index == self.lanes - 1:
            skip_count = self.mod - self.total_bits % self.mod
            if skip_count == self.mod:
                skip_count = 0

        hlen = (self.hspace / self.mod) * (self.mod - skip_count)
        hpos = 0 if self.vflip else (self.hspace / self.mod) * (skip_count)

        bottom_boundary = (self.lane_index + 1) * self.mod
        if (not self.compact or self.hflip or self.lane_index == 0) and not self._boundary_hidden(bottom_boundary):
            res.append(self.hline(hlen, hpos, self.vlane))  # bottom
        top_boundary = self.lane_index * self.mod
        if (not self.compact or not self.hflip or self.lane_index == 0) and not self._boundary_hidden(top_boundary):
            res.append(self.hline(hlen, hpos))  # top

        hbit = (self.hspace - self.stroke_width) / self.mod
        for bit_pos in range(self.mod):
            bitm = (bit_pos if self.vflip else self.mod - bit_pos - 1)
            bit = self.lane_index * self.mod + bitm
            if bit >= self.total_bits:
                continue
            rpos = bit_pos + 1 if self.vflip else bit_pos
            lpos = bit_pos if self.vflip else bit_pos + 1
            if bitm + 1 == self.mod - skip_count:
                res.append(self.vline(self.vlane, rpos * hbit + self.stroke_width / 2))
            if bitm == 0:
                res.append(self.vline(self.vlane, lpos * hbit + self.stroke_width / 2))
            elif any('lsb' in e and e['lsb'] == bit for e in desc):
                res.append(self.vline(self.vlane, lpos * hbit + self.stroke_width / 2))
            else:
                if self.grid_draw and not self._bit_hidden(bit):
                    res.append(self.vline((self.vlane / 8),
                                          lpos * hbit + self.stroke_width / 2))
                    res.append(self.vline((self.vlane / 8),
                                          lpos * hbit + self.stroke_width / 2, self.vlane * 7 / 8))

        return res

    def _boundary_hidden(self, bit_pos):
        for start, end in getattr(self, 'hidden_array_ranges', []):
            if start < bit_pos < end:
                return True
        return False

    def _bit_hidden(self, bit_pos):
        for start, end in getattr(self, 'hidden_array_ranges', []):
            if start < bit_pos < end:
                return True
        return False

    def labels(self, desc):
        return ['g', {'text-anchor': 'middle'}, self.labelArr(desc)]

    def labelArr(self, desc):  # noqa: C901
        step = self.hspace / self.mod
        bits = ['g', {'transform': t(step / 2, self.fontsize)}]
        names = ['g', {'transform': t(step / 2, self.vlane / 2 + self.fontsize / 2)}]
        attrs = ['g', {'transform': t(step / 2, self.vlane + self.fontsize)}]
        blanks = ['g', {'transform': t(0, 0)}]

        for e in desc:
            if 'bits' not in e:
                continue
            lsbm = 0
            msbm = self.mod - 1
            lsb = self.lane_index * self.mod
            msb = (self.lane_index + 1) * self.mod - 1
            if e['lsb'] // self.mod == self.lane_index:
                lsbm = e['lsbm']
                lsb = e['lsb']
                if e['msb'] // self.mod == self.lane_index:
                    msb = e['msb']
                    msbm = e['msbm']
            else:
                if e['msb'] // self.mod == self.lane_index:
                    msb = e['msb']
                    msbm = e['msbm']
                elif not (lsb > e['lsb'] and msb < e['msb']):
                    continue
            msb_pos = msbm if self.vflip else (self.mod - msbm - 1)
            lsb_pos = lsbm if self.vflip else (self.mod - lsbm - 1)
            if not self.compact:
                bits.append(['text', {
                    'x': step * lsb_pos,
                    'font-size': self.fontsize,
                    'font-family': self.fontfamily,
                    'font-weight': self.fontweight
                }, str(lsb)])
                if lsbm != msbm:
                    bits.append(['text', {
                        'x': step * msb_pos,
                        'font-size': self.fontsize,
                        'font-family': self.fontfamily,
                        'font-weight': self.fontweight
                    }, str(msb)])
            if 'name' in e:
                ltextattrs = {
                    'font-size': self.fontsize,
                    'font-family': self.fontfamily,
                    'font-weight': self.fontweight,
                    'text-anchor': 'middle',
                    'y': 6
                }
                if 'rotate' in e:
                    ltextattrs['transform'] = ' rotate({})'.format(e['rotate'])
                if 'overline' in e and e['overline']:
                    ltextattrs['text-decoration'] = 'overline'
                available_space = step * (msbm - lsbm + 1)
                ltext = ['g', {
                    'transform': t(step * (msb_pos + lsb_pos) / 2, -6),
                }, ['text', ltextattrs] + tspan(self.trim_text(e['name'], available_space))]
                names.append(ltext)
            if 'name' not in e or e['type'] is not None:
                style = self.type_style(e['type'])
                blanks.append(['rect', {
                    'style': style,
                    'x': step * (lsb_pos if self.vflip else msb_pos),
                    'y': self.stroke_width / 2,
                    'width': step * (msbm - lsbm + 1),
                    'height': self.vlane - self.stroke_width / 2,
                    'fill': self.type_color(e['type']),
                }])
            if 'attr' in e and not self.compact:
                if isinstance(e['attr'], list):
                    e_attr = e['attr']
                else:
                    e_attr = [e['attr']]
                for i, attribute in enumerate(e_attr):
                    if isinstance(attribute, int):
                        atext = []
                        for biti in range(0, msb - lsb + 1):
                            if (1 << (biti + lsb - e['lsb'])) & attribute == 0:
                                bit_text = "0"
                            else:
                                bit_text = "1"
                            bit_pos = lsb_pos + biti if self.vflip else (lsb_pos - biti)
                            atext += [['text', {
                                'x': step * bit_pos,
                                'font-size': self.fontsize,
                                'font-family': self.fontfamily,
                                'font-weight': self.fontweight,
                            }] + tspan(bit_text)]
                    else:
                        atext = [['text', {
                            'x': step * (msb_pos + lsb_pos) / 2,
                            'font-size': self.fontsize,
                            'font-family': self.fontfamily,
                            'font-weight': self.fontweight
                        }] + tspan(attribute)]
                    attrs.append(['g', {
                        'transform': t(0, i*self.fontsize)
                    }, *atext])
        if not self.compact or (self.index == 0):
            if self.compact:
                for i in range(self.mod):
                    bits.append(['text', {
                        'x': step * i,
                        'font-size': self.fontsize,
                        'font-family': self.fontfamily,
                        'font-weight': self.fontweight,
                    }, str(i if self.vflip else self.mod - i - 1)])
            res = ['g', {}, bits, ['g', {
                'transform': t(0, self.fontsize*1.2)
            }, blanks, names, attrs]]
        else:
            res = ['g', {}, blanks, names, attrs]
        return res

    def hline(self, len, x=0, y=0, padding=0):
        res = ['line']
        att = {}
        if padding != 0:
            len -= padding
            x += padding/2
        if x != 0:
            att['x1'] = x
        if len != 0:
            att['x2'] = x + len
        if y != 0:
            att['y1'] = y
            att['y2'] = y
        res.append(att)
        return res

    def vline(self, len, x=None, y=None, stroke=None):
        res = ['line']
        att = {}
        if x is not None:
            att['x1'] = x
            att['x2'] = x
        if y is not None:
            att['y1'] = y
            att['y2'] = y + len
        else:
            att['y2'] = len
        if stroke:
            att['stroke'] = stroke
        res.append(att)
        return res

    def trim_text(self, text, available_space):
        if self.trim_char_width is None:
            return text
        text_width = len(text) * self.trim_char_width
        if text_width <= available_space:
            return text
        end = len(text) - int((text_width - available_space) / self.trim_char_width) - 3
        if end > 0:
            return text[:end] + '...'
        return text[:1] + '...'


def render(desc, **kwargs):
    renderer = Renderer(**kwargs)
    return renderer.render(desc)
