from .tspan import tspan
import colorsys


def t(x, y):
    return 'translate({}, {})'.format(x, y)


def typeStyle(t):
    return ';fill:' + typeColor(t)


def typeColor(t):
    styles = {
        '2': 0,
        '3': 80,
        '4': 170,
        '5': 45,
        '6': 126,
        '7': 215,
    }
    
    # --- Fall 1: t ist eine Liste ---
    if isinstance(t, list):
        if len(t) == 3 and all(isinstance(x, int) and 0 <= x <= 255 for x in t):
            r, g, b = t
            return f"rgb({r}, {g}, {b})"
        else:
            # Fehlerhafte Liste -> Standardfarbe
            return "rgb(229, 229, 229)"

    # --- Fall 2: t ist ein Schlüssel im Dictionary ---
    t = str(t)
    if t in styles:
        r, g, b = colorsys.hls_to_rgb(styles[t] / 360, 0.9, 1)
        return "rgb({:.0f}, {:.0f}, {:.0f})".format(r * 255, g * 255, b * 255)
    
    # --- Standardfarbe für alles andere ---
    return "rgb(229, 229, 229)"


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
                 label_lines=None):
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
        self.label_lines = label_lines

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

    def _extract_label_lines(self, desc):
        if self.label_lines is None:
            filtered = []
            for e in desc:
                if isinstance(e, dict) and 'label_lines' in e:
                    self.label_lines = e
                else:
                    filtered.append(e)
            return filtered
        return [e for e in desc if not (isinstance(e, dict) and 'label_lines' in e)]

    def _label_lines_margins(self):
        self.cage_width = self.hspace / self.mod
        self.label_gap = self.cage_width / 2
        self.label_width = self.cage_width
        self.label_margin = self.label_gap + self.label_width
        if self.label_lines['layout'] == 'left':
            return self.label_margin, 0
        return 0, self.label_margin

    def render(self, desc):
        desc = self._extract_label_lines(desc)

        self.total_bits = self.get_total_bits(desc)
        if self.lanes is None:
            self.lanes = (self.total_bits + self.bits - 1) // self.bits
        mod = self.bits
        self.mod = mod
        lsb = 0
        msb = self.total_bits - 1
        for e in desc:
            if 'array' in e:
                length = e['array'][-1] if isinstance(e['array'], list) else e['array']
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
                         'markerHeight': 10,
                         'refX': 10,
                         'refY': 5,
                         'orient': 'auto-start-reverse',
                         'markerUnits': 'strokeWidth'
                     },
                      ['path', {
                          'd': 'M0,0 L10,5 L0,10 Z',
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
            res.append(self._label_lines_element())
        return res

    def _validate_label_lines(self):
        required = ['label_lines', 'font_size', 'start_line', 'end_line', 'layout']
        for key in required:
            if key not in self.label_lines:
                raise ValueError('label_lines missing required key: {}'.format(key))
        start = self.label_lines['start_line']
        end = self.label_lines['end_line']
        if not (isinstance(start, int) and isinstance(end, int)):
            raise ValueError('label_lines start_line and end_line must be integers')
        if start < 0 or end < 0:
            raise ValueError('label_lines start_line and end_line must be non-negative')
        if end >= self.lanes or start >= self.lanes:
            raise ValueError('label_lines start_line/end_line exceed number of lanes')
        if end - start < 2:
            raise ValueError('label_lines must cover at least 2 lines')
        layout = self.label_lines['layout']
        if layout not in ('left', 'right'):
            raise ValueError('label_lines layout must be "left" or "right"')

    def _label_lines_element(self):
        cfg = self.label_lines
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
        #width = width+ (width/2)
        if layout == 'left':
            x = -(gap + width / 2)
            left = x - width / 2
            right = x + width / 2
            angle = 0
        else:
            x = self.hspace + gap + width / 2
            left = x - width / 2
            right = x + width / 2
            angle = 0

        half_cage = (right-left)/2
        lines = text.split('\n')
        max_text_len = max((len(line) for line in lines), default=0)
        text_length = max_text_len * font_size * 0.6
        text_attrs = {
            'x': x,
            'y': mid_y,
            'font-size': font_size,
            'font-family': self.fontfamily,
            'font-weight': self.fontweight,
            'text-anchor': 'middle',
            'dominant-baseline': 'middle',
            'transform': 'rotate({},{},{})'.format(angle, x, mid_y)
        }
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
                elements.append(['tspan', {'x': x, 'y': start_y + line_height * i}, line])
            text_element = elements
        top_y2 = mid_y - text_length / 2 - 5
        bottom_y1 = mid_y + text_length / 2 + 5

        bracket = ['g', {
            'stroke': 'black',
            'stroke-width': self.stroke_width,
            'fill': 'none'
        },
            ['line', {'x1': left, 'y1': top_y, 'x2': right, 'y2': top_y}],
            ['line', {'x1': left, 'y1': bottom_y, 'x2': right, 'y2': bottom_y}],
            ['line', {
                'x1': left + half_cage,
                'y1': top_y,
                'x2': left + half_cage,
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
                'fill': typeColor(value),
                'style': 'stroke:#000; stroke-width:' + str(self.stroke_width) + ';' + typeStyle(value)
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
                width = step / 2
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
                color = typeColor(e.get('type')) if e.get('type') is not None else 'black'
                grp = ['g', {'stroke': color, 'stroke-width': self.stroke_width}]
                # fill the full gap bounds with the type color to avoid transparent edges
                if e.get('type') is not None:
                    # use raw coordinates so the background reaches the lane boundaries
                    left = x1_raw
                    right = self.hspace if (x2_raw == 0 and end > start) else x2_raw
                    rect = f"{left},{top_y} {right},{top_y} {right},{bottom_y} {left},{bottom_y}"
                    grp.append(['polygon', {
                        'points': rect,
                        'fill': typeColor(e['type']),
                        'stroke': 'none'
                    }])
                # white gap polygon on top
                grp.append(['polygon', {'points': pts, 'fill': '#fff'}])
                grp.append(['line', {'x1': x1, 'y1': top_y, 'x2': x2, 'y2': bottom_y}])
                grp.append(['line', {'x1': x1+width, 'y1': top_y, 'x2': x2_outer, 'y2': bottom_y}])
                if 'name' in e:
                    mid_x = (x1 + x2_outer) / 2
                    mid_y = (top_y + bottom_y) / 2 + self.fontsize / 2
                    grp.append(['text', {
                        'x': mid_x,
                        'y': mid_y,
                        'font-size': self.fontsize,
                        'font-family': self.fontfamily,
                        'font-weight': self.fontweight,
                        'text-anchor': 'middle'
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

        if not self.compact or self.hflip or self.lane_index == 0:
            res.append(self.hline(hlen, hpos, self.vlane))  # bottom
        if not self.compact or not self.hflip or self.lane_index == 0:
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
                res.append(self.vline((self.vlane / 8),
                                      lpos * hbit + self.stroke_width / 2))
                res.append(self.vline((self.vlane / 8),
                                      lpos * hbit + self.stroke_width / 2, self.vlane * 7 / 8))

        return res

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
                style = typeStyle(e['type'])
                blanks.append(['rect', {
                    'style': style,
                    'x': step * (lsb_pos if self.vflip else msb_pos),
                    'y': self.stroke_width / 2,
                    'width': step * (msbm - lsbm + 1),
                    'height': self.vlane - self.stroke_width / 2,
                    'fill': typeColor(e['type']),
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
