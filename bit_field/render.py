from .tspan import tspan
import colorsys
import math
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
    ARROW_JUMP_HEAD_LENGTH = 10

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
                 arrow_jumps=None,
                 grid_draw=True,
                 number_draw=True,
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
        arrow_jumps = extra_kwargs.pop('arrow_jumps', arrow_jumps)
        if arrow_jumps is not None and not isinstance(arrow_jumps, list):
            self.arrow_jumps = [arrow_jumps]
        else:
            self.arrow_jumps = arrow_jumps
        types = extra_kwargs.pop('types', types)
        if extra_kwargs:
            unexpected = ', '.join(sorted(extra_kwargs))
            raise TypeError(f'Renderer.__init__() got unexpected keyword argument(s): {unexpected}')

        self.grid_draw = grid_draw
        self.number_draw = number_draw
        self.bit_label_height = self.fontsize * 1.2 if self.number_draw else 0
        self.type_overrides = _parse_type_overrides(types)
        self.attr_padding = 0
        self.lane_spacing = self.vspace

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

    def _extract_arrow_jumps(self, desc):
        collected = []
        filtered = []
        for e in desc:
            if isinstance(e, dict) and 'arrow_jump' in e:
                collected.append(e)
            else:
                filtered.append(e)
        if collected:
            if self.arrow_jumps is None:
                self.arrow_jumps = collected
            else:
                self.arrow_jumps.extend(collected)
        return filtered

    def _label_lines_margins(self):
        self.cage_width = self.hspace / self.mod
        self.label_gap = self.cage_width / 2
        self.label_width = self.cage_width
        left_margin = right_margin = 0

        label_items = self.label_lines or []
        arrow_items = self.arrow_jumps or []

        for side in ('left', 'right'):
            active = []
            side_items = []
            side_items.extend(('label', cfg) for cfg in label_items if cfg['layout'] == side)
            side_items.extend(('arrow', cfg) for cfg in arrow_items if cfg['layout'] == side)
            for kind, cfg in side_items:
                if kind == 'label':
                    font_size = cfg.get('font_size', self.fontsize)
                    lines = cfg['label_lines'].split('\n')
                    max_text_len = max((len(line) for line in lines), default=0)
                    text_length = max_text_len * font_size * 0.6
                    angle = cfg.get('angle', 0) or 0
                    normalized = angle % 360
                    is_vertical = math.isclose(normalized % 180, 90, abs_tol=1e-6)
                    text_gap = 20 if is_vertical else self.label_gap
                    angle_rad = math.radians(angle)
                    horizontal_extent = (
                        abs(text_length * math.cos(angle_rad))
                        + font_size * abs(math.sin(angle_rad))
                    )
                    margin = (
                        self.label_width / 2
                        + self.label_gap
                        + text_gap
                        + horizontal_extent
                    )
                    cfg_start = cfg['start_line']
                    cfg_end = cfg['end_line']
                    cfg['_margin'] = margin
                    active = [a for a in active if a['end'] >= cfg_start]
                    offset = 0
                    for a in active:
                        offset = max(offset, a['offset'] + a['margin'])
                    cfg['_offset'] = offset
                    active.append({'end': cfg_end, 'offset': offset, 'margin': margin})
                    if side == 'left':
                        left_margin = max(left_margin, offset + margin)
                    else:
                        right_margin = max(right_margin, offset + margin)
                else:
                    stroke_width = cfg.get('stroke_width', 3)
                    base_outer = cfg.get('outer_distance', 10)
                    outer_distance = min(base_outer, 10)
                    arrow_head_length = self._arrow_jump_head_extent(stroke_width)

                    if cfg['layout'] == 'left':
                        end_x = self._bit_column_x(cfg['end_bit'])
                        final_x = end_x - arrow_head_length
                        if final_x <= -outer_distance:
                            max_outer = max(outer_distance, cfg.get('max_outer_distance', 25))
                            required = arrow_head_length - end_x + stroke_width
                            outer_distance = min(max_outer, max(outer_distance, required))
                    else:
                        end_x = self._bit_column_x(cfg['end_bit'])
                        final_x = end_x + arrow_head_length
                        limit = self.hspace + outer_distance
                        if final_x >= limit:
                            max_outer = max(outer_distance, cfg.get('max_outer_distance', 25))
                            required = final_x - self.hspace + stroke_width
                            outer_distance = min(max_outer, max(outer_distance, required))

                    margin = outer_distance + stroke_width / 2
                    cfg['_outer_distance'] = outer_distance
                    cfg['_margin'] = margin
                    cfg['_offset'] = 0
                    if side == 'left':
                        left_margin = max(left_margin, margin)
                    else:
                        right_margin = max(right_margin, margin)

        self.label_margin = max(left_margin, right_margin)
        return left_margin, right_margin

    def render(self, desc):
        desc = self._extract_label_lines(desc)
        desc = self._extract_arrow_jumps(desc)

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
        if self.arrow_jumps is not None:
            self._validate_arrow_jumps()

        self.attr_padding = 0
        max_attr_height = 0
        for e in desc:
            attr_entries = self._prepare_attr_entries(e.get('attr'))
            if attr_entries:
                e['_attr_entries'] = attr_entries
                total_height = sum(entry['spacing'] for entry in attr_entries)
                max_attr_height = max(max_attr_height, total_height)
            else:
                e['_attr_entries'] = []

        if not self.compact:
            self.vlane = self.vspace - self.bit_label_height
            self.attr_padding = max_attr_height
            self.lane_spacing = self.vspace + self.attr_padding
            height = self.lane_spacing * self.lanes + self.stroke_width / 2
        else:
            self.vlane = self.vspace - self.bit_label_height
            self.attr_padding = 0
            self.lane_spacing = self.vspace
            height = self.vlane * (self.lanes - 1) + self.vspace + self.stroke_width / 2
        if self.legend:
            height += self.fontsize * 1.2

        left_margin = right_margin = 0
        self.label_margin = 0
        self.label_gap = 0
        self.label_width = 0
        self.cage_width = 0 
        if self.label_lines is not None or self.arrow_jumps is not None:
            left_margin, right_margin = self._label_lines_margins()

            has_left = any(
                cfg.get('layout') == 'left'
                for cfg in (self.label_lines or [])
            ) or any(
                cfg.get('layout') == 'left'
                for cfg in (self.arrow_jumps or [])
            )
            has_right = any(
                cfg.get('layout') == 'right'
                for cfg in (self.label_lines or [])
            ) or any(
                cfg.get('layout') == 'right'
                for cfg in (self.arrow_jumps or [])
            )

            if has_left:
                left_margin += 5
            if has_right:
                right_margin += 5

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
                     ],
                     ['marker', {
                         'id': 'arrow-jump-head',
                         'markerWidth': 10,
                         'markerHeight': 6,
                         'refX': 0,
                         'refY': 3,
                         'orient': 'auto',
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
        if self.arrow_jumps:
            arrow_group = self._arrow_jump_elements()
            if arrow_group is not None:
                res.append(arrow_group)
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
            if end - start <= 1:
                raise ValueError('label_lines must cover at least 2 lines')
            layout = cfg['layout']
            if layout not in ('left', 'right'):
                raise ValueError('label_lines layout must be "left" or "right"')
            if 'angle' in cfg and not isinstance(cfg['angle'], (int, float)):
                raise ValueError('label_lines angle must be a number')
            if 'Reserved' in cfg and not isinstance(cfg['Reserved'], bool):
                raise ValueError('label_lines Reserved must be a boolean')

    def _validate_arrow_jumps(self):
        required = ['arrow_jump', 'start_line', 'jump_to_first', 'jump_to_second', 'end_bit', 'layout']
        for cfg in self.arrow_jumps:
            for key in required:
                if key not in cfg:
                    raise ValueError('arrow_jump missing required key: {}'.format(key))
            start = cfg['start_line']
            jump_first = cfg['jump_to_first']
            jump_second = cfg['jump_to_second']
            for value_name, value in (
                ('start_line', start),
                ('jump_to_first', jump_first),
                ('jump_to_second', jump_second),
            ):
                if not isinstance(value, int):
                    raise ValueError(f'arrow_jump {value_name} must be an integer')
                if value < 0:
                    raise ValueError(f'arrow_jump {value_name} must be non-negative')
                if value >= self.lanes:
                    raise ValueError('arrow_jump {} exceeds number of lanes'.format(value_name))
            for bit_name in ('arrow_jump', 'end_bit'):
                bit_value = cfg[bit_name]
                if not isinstance(bit_value, int):
                    raise ValueError(f'arrow_jump {bit_name} must be an integer')
                if bit_value < 0 or bit_value >= self.mod:
                    raise ValueError(f'arrow_jump {bit_name} must be between 0 and {self.mod - 1}')
            layout = cfg['layout']
            if layout not in ('left', 'right'):
                raise ValueError('arrow_jump layout must be "left" or "right"')
            if 'stroke_width' in cfg:
                stroke_width = cfg['stroke_width']
                if not isinstance(stroke_width, (int, float)):
                    raise ValueError('arrow_jump stroke_width must be a number')
                if stroke_width <= 0:
                    raise ValueError('arrow_jump stroke_width must be positive')

    def _label_lines_element(self, cfg):
        text = cfg['label_lines']
        font_size = cfg.get('font_size', self.fontsize)
        start = cfg['start_line']
        end = cfg['end_line']
        layout = cfg['layout']
        base_y = self.bit_label_height
        if self.legend:
            base_y += self.fontsize * 1.2
        top_y = base_y + self.vlane * start + self.attr_padding * start
        bottom_y = base_y + self.vlane * (end + 1) + self.attr_padding * (end + 1)
        mid_y = (top_y + bottom_y) / 2
        gap = self.label_gap
        width = self.label_width
        offset = cfg.get('_offset', 0)
        if layout == 'left':
            x = -(gap + width / 2 + offset)
            left = x - width / 2
            right = x + width / 2
            anchor = 'end'
        else:
            x = self.hspace + gap + width / 2 + offset
            left = x - width / 2
            right = x + width / 2
            anchor = 'start'

        lines = text.split('\n')
        max_text_len = max((len(line) for line in lines), default=0)
        text_length = max_text_len * font_size * 0.6
        angle = cfg.get('angle', 0) or 0
        normalized = angle % 360
        is_vertical = math.isclose(normalized % 180, 90, abs_tol=1e-6)
        text_gap = 20 if is_vertical else gap
        arrow_x = left + self.cage_width / 2
        if layout == 'left':
            text_x = arrow_x - text_gap
        else:
            text_x = arrow_x + text_gap
        if angle:
            anchor = 'middle'
            if not is_vertical:
                text_x += (-text_length / 2) if layout == 'left' else (text_length / 2)
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

    def _bit_column_x(self, bit):
        step = self.hspace / self.mod
        if self.vflip:
            position = bit + 0.5
        else:
            position = self.mod - bit - 0.5
        return step * position

    def _line_center_y(self, line, base_y):
        return base_y + self.vlane * line + self.attr_padding * line + self.vlane / 2

    def _arrow_jump_head_extent(self, stroke_width):
        return self.ARROW_JUMP_HEAD_LENGTH * stroke_width

    def _arrow_jump_elements(self):
        if not self.arrow_jumps:
            return None

        base_y = self.bit_label_height
        if self.legend:
            base_y += self.fontsize * 1.2

        group = ['g', {'class': 'arrow-jumps'}]

        for cfg in self.arrow_jumps:
            stroke_width = cfg.get('stroke_width', 3)
            outer_distance = cfg.get('_outer_distance', 10)
            if cfg['layout'] == 'left':
                outer_x = -outer_distance
            else:
                outer_x = self.hspace + outer_distance

            start_x = self._bit_column_x(cfg['arrow_jump'])
            end_x = self._bit_column_x(cfg['end_bit'])

            start_y = self._line_center_y(cfg['start_line'], base_y)
            first_y = self._line_center_y(cfg['jump_to_first'], base_y)
            second_y = self._line_center_y(cfg['jump_to_second'], base_y)

            arrow_head_length = self._arrow_jump_head_extent(stroke_width)
            if cfg['layout'] == 'left':
                final_x = end_x - arrow_head_length
            else:
                final_x = end_x + arrow_head_length

            points = [
                (start_x, start_y),
                (start_x, first_y),
                (outer_x, first_y),
                (outer_x, second_y),
                (final_x, second_y),
            ]

            commands = [f"M{points[0][0]},{points[0][1]}"]
            commands.extend(f"L{x},{y}" for x, y in points[1:])
            path = ['path', {
                'd': ' '.join(commands),
                'stroke': 'black',
                'stroke-width': stroke_width,
                'fill': 'none',
                'marker-end': 'url(#arrow-jump-head)'
            }]
            group.append(path)

        return group

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
        base_y = self.bit_label_height
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
                top_y = base_y + self.vlane * start_lane + self.attr_padding * start_lane
                bottom_y = base_y + self.vlane * (end_lane + 1) + self.attr_padding * (end_lane + 1)
                if x2_raw == 0 and end > start:
                    x2_outer = self.hspace - margin
                else:
                    x2_outer = x2_raw - margin
                x1 = x1_raw + margin
                x2 = x2_outer - width
                pts = f"{x1},{top_y} {x1+width},{top_y} {x2_outer},{bottom_y} {x2},{bottom_y}"
                color = self.type_color(e.get('type')) if e.get('type') is not None else 'black'
                show_lines = not e.get('hide_lines')
                grp_attrs = {'stroke-width': self.stroke_width}
                if show_lines:
                    grp_attrs['stroke'] = color
                grp = ['g', grp_attrs]
                # fill the full gap bounds to avoid transparent edges
                background_fill = None
                if e.get('type') is not None:
                    background_fill = self.type_color(e['type'])
                else:
                    if e.get('fill') is not None:
                        background_fill = e.get('fill')
                    elif e.get('gap_fill') is not None:
                        background_fill = e.get('gap_fill')
                if background_fill is not None:
                    # use raw coordinates so the background reaches the lane boundaries
                    overlap = 0.0
                    if end_lane > start_lane:
                        overlap = min(self.vlane * 0.05, 0.5)
                    for lane_idx in range(start_lane, end_lane + 1):
                        lane_top = base_y + self.vlane * lane_idx + self.attr_padding * lane_idx
                        lane_bottom = lane_top + self.vlane
                        if overlap:
                            if lane_idx > start_lane:
                                lane_top -= overlap
                            if lane_idx < end_lane:
                                lane_bottom += overlap
                        left = x1_raw if lane_idx == start_lane else 0
                        if lane_idx == end_lane:
                            right = x2_raw
                            if right == 0 and end > start:
                                right = self.hspace
                        else:
                            right = self.hspace
                        rect = f"{left},{lane_top} {right},{lane_top} {right},{lane_bottom} {left},{lane_bottom}"
                        grp.append(['polygon', {
                            'points': rect,
                            'fill': background_fill,
                            'stroke': 'none'
                        }])
                # gap polygon on top, optionally with custom fill
                gap_fill = e.get('gap_fill', e.get('fill', '#fff'))
                polygon_attrs = {'points': pts, 'fill': gap_fill}
                if show_lines:
                    polygon_attrs['stroke'] = color
                else:
                    polygon_attrs['stroke'] = 'none'
                grp.append(['polygon', polygon_attrs])
                if not show_lines:
                    trailing_offset = end % self.mod
                    if trailing_offset:
                        lane_idx = end_lane
                        skip_count = 0
                        if self.uneven and self.lanes > 1 and lane_idx == self.lanes - 1:
                            skip_count = self.mod - self.total_bits % self.mod
                            if skip_count == self.mod:
                                skip_count = 0
                        lane_start_bit = lane_idx * self.mod
                        lane_width_bits = self.mod - skip_count
                        boundary_segments = self._boundary_segments(
                            lane_start_bit,
                            lane_width_bits,
                            lane_start_bit,
                        )
                        if boundary_segments:
                            hpos = 0 if self.vflip else step * skip_count
                            lane_top = base_y + self.vlane * lane_idx + self.attr_padding * lane_idx
                            for seg_start, seg_end in boundary_segments:
                                if seg_end <= trailing_offset:
                                    continue
                                seg_start = max(seg_start, trailing_offset)
                                if seg_start >= seg_end:
                                    continue
                                x_start = hpos + seg_start * step
                                x_end = hpos + seg_end * step
                                grp.append(['line', {
                                    'x1': x_start,
                                    'y1': lane_top,
                                    'x2': x_end,
                                    'y2': lane_top,
                                    'stroke': 'black',
                                    'stroke-width': self.stroke_width,
                                    'stroke-linecap': 'butt',
                                }])
                if show_lines:
                    grp.append(['line', {
                        'x1': x1,
                        'y1': top_y,
                        'x2': x2,
                        'y2': bottom_y,
                        'stroke': color,
                    }])
                    grp.append(['line', {
                        'x1': x1 + width,
                        'y1': top_y,
                        'x2': x2_outer,
                        'y2': bottom_y,
                        'stroke': color,
                    }])
                if 'name' in e:
                    name = str(e['name'])
                    lines = name.split('\n')
                    mid_x = (x1 + x2_outer) / 2
                    center_y = (top_y + bottom_y) / 2
                    first_lane_center = top_y + self.vlane / 2
                    align_first_lane = (length % self.mod) != 0
                    label_x = mid_x
                    if align_first_lane:
                        start_offset = start % self.mod
                        if start_offset:
                            first_lane_bits = min(length, self.mod - start_offset)
                        else:
                            first_lane_bits = min(length, self.mod)
                        lane_left = x1_raw
                        lane_right = lane_left + first_lane_bits * step
                        label_x = (lane_left + lane_right) / 2
                    base_center = first_lane_center if align_first_lane else center_y
                    text_color = e.get('font_color', 'black')
                    text_attrs = {
                        'x': label_x,
                        'font-size': self.fontsize,
                        'font-family': self.fontfamily,
                        'font-weight': self.fontweight,
                        'text-anchor': 'middle',
                        'fill': text_color,
                        'stroke': 'none'
                    }
                    if len(lines) == 1:
                        text_attrs['y'] = base_center + self.fontsize / 2
                        grp.append(['text', text_attrs] + tspan(lines[0]))
                    else:
                        line_height = self.fontsize * 1.2
                        if align_first_lane:
                            first_line_y = first_lane_center + self.fontsize / 2
                        else:
                            first_line_y = center_y + self.fontsize / 2 - line_height * (len(lines) - 1) / 2
                        text_element = ['text', text_attrs]
                        for i, line in enumerate(lines):
                            spans = tspan(line)
                            if not spans:
                                spans = [['tspan', {}, '']]
                            for j, span in enumerate(spans):
                                span_attrs = dict(span[1])
                                if j == 0:
                                    span_attrs['x'] = label_x
                                    span_attrs['y'] = first_line_y + line_height * i
                                text_element.append(['tspan', span_attrs, span[2]])
                        grp.append(text_element)
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
            dy = self.index * self.lane_spacing
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
            dy = self.bit_label_height
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

        lane_start_bit = self.lane_index * self.mod
        lane_width_bits = self.mod - skip_count
        step = self.hspace / self.mod
        hpos = 0 if self.vflip else step * skip_count

        bottom_boundary = lane_start_bit + lane_width_bits
        if not self.compact or self.hflip or self.lane_index == 0:
            segments = self._boundary_segments(lane_start_bit, lane_width_bits, bottom_boundary)
            for start_bits, end_bits in segments:
                length_bits = end_bits - start_bits
                if length_bits <= 0:
                    continue
                x = hpos + start_bits * step
                res.append(self.hline(length_bits * step, x, self.vlane))  # bottom

        top_boundary = lane_start_bit
        if not self.compact or not self.hflip or self.lane_index == 0:
            segments = self._boundary_segments(lane_start_bit, lane_width_bits, top_boundary)
            for start_bits, end_bits in segments:
                length_bits = end_bits - start_bits
                if length_bits <= 0:
                    continue
                x = hpos + start_bits * step
                res.append(self.hline(length_bits * step, x))  # top

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

    def _boundary_segments(self, lane_start_bit, lane_width_bits, boundary_bit):
        if lane_width_bits <= 0:
            return []

        lane_end_bit = lane_start_bit + lane_width_bits
        overlaps = []
        for start, end in getattr(self, 'hidden_array_ranges', []):
            if start < boundary_bit < end:
                overlap_start = max(start, lane_start_bit)
                overlap_end = min(end, lane_end_bit)
                if overlap_start < overlap_end:
                    overlaps.append((overlap_start, overlap_end))

        if not overlaps:
            return [(0, lane_width_bits)]

        overlaps.sort()
        merged = []
        for start, end in overlaps:
            if not merged or start > merged[-1][1]:
                merged.append([start, end])
            else:
                merged[-1][1] = max(merged[-1][1], end)

        segments = []
        cursor = lane_start_bit
        for start, end in merged:
            if start > cursor:
                segments.append((cursor - lane_start_bit, start - lane_start_bit))
            cursor = max(cursor, end)

        if cursor < lane_end_bit:
            segments.append((cursor - lane_start_bit, lane_end_bit - lane_start_bit))

        return segments

    def _bit_hidden(self, bit_pos):
        for start, end in getattr(self, 'hidden_array_ranges', []):
            if start < bit_pos < end:
                return True
        return False

    @staticmethod
    def _is_numeric_angle(value):
        return isinstance(value, (int, float)) and not isinstance(value, bool)

    def _is_rotated_attr_entry(self, value):
        return (
            isinstance(value, (list, tuple))
            and len(value) == 2
            and isinstance(value[0], str)
            and self._is_numeric_angle(value[1])
        )

    def _estimate_text_width(self, text):
        text = str(text)
        if not text:
            return 0
        char_width = self.trim_char_width if self.trim_char_width is not None else self.fontsize * 0.6
        lines = text.split('\n')
        max_length = max((len(line) for line in lines), default=0)
        return max_length * char_width

    def _prepare_attr_entries(self, attr_value):
        if attr_value is None:
            return []

        if self._is_rotated_attr_entry(attr_value):
            items = [attr_value]
        elif isinstance(attr_value, list):
            items = list(attr_value)
        else:
            items = [attr_value]

        entries = []
        for item in items:
            if self._is_rotated_attr_entry(item):
                text, angle = item
                text = str(text)
                angle = float(angle)
                text_width = self._estimate_text_width(text)
                base_height = self.fontsize
                angle_rad = math.radians(angle)
                rotated_height = abs(text_width * math.sin(angle_rad)) + abs(base_height * math.cos(angle_rad))
                spacing = max(rotated_height, base_height)
                entries.append({
                    'kind': 'rotated_text',
                    'text': text,
                    'angle': angle,
                    'spacing': spacing,
                    'y': spacing / 2,
                })
            elif isinstance(item, int):
                entries.append({
                    'kind': 'bits',
                    'value': item,
                    'spacing': self.fontsize,
                    'y': self.fontsize,
                })
            else:
                entries.append({
                    'kind': 'text',
                    'text': str(item),
                    'spacing': self.fontsize,
                    'y': self.fontsize,
                })

        return entries

    def _render_attr_entry(self, entry, step, lsb_pos, msb_pos, lsb, msb, element):
        kind = entry.get('kind')

        if kind == 'bits':
            attribute = entry['value']
            nodes = []
            for biti in range(0, msb - lsb + 1):
                bit_index = biti + lsb - element['lsb']
                if (1 << bit_index) & attribute == 0:
                    bit_text = "0"
                else:
                    bit_text = "1"
                bit_pos = lsb_pos + biti if self.vflip else (lsb_pos - biti)
                text_attrs = {
                    'x': step * bit_pos,
                    'y': entry['y'],
                    'font-size': self.fontsize,
                    'font-family': self.fontfamily,
                    'font-weight': self.fontweight,
                }
                nodes.append(['text', text_attrs] + tspan(bit_text))
            return nodes

        if kind == 'rotated_text':
            text = entry['text']
            angle = entry['angle']
            center_x = step * (msb_pos + lsb_pos) / 2
            center_y = entry['y']
            text_attrs = {
                'x': center_x,
                'y': center_y,
                'font-size': self.fontsize,
                'font-family': self.fontfamily,
                'font-weight': self.fontweight,
                'text-anchor': 'middle',
                'dominant-baseline': 'middle',
                'transform': 'rotate({},{},{})'.format(angle, center_x, center_y),
            }
            return [['text', text_attrs] + tspan(text)]

        if kind == 'text':
            text_attrs = {
                'x': step * (msb_pos + lsb_pos) / 2,
                'y': entry['y'],
                'font-size': self.fontsize,
                'font-family': self.fontfamily,
                'font-weight': self.fontweight,
            }
            return [['text', text_attrs] + tspan(entry['text'])]

        return []

    def labels(self, desc):
        return ['g', {'text-anchor': 'middle'}, self.labelArr(desc)]

    def labelArr(self, desc):  # noqa: C901
        step = self.hspace / self.mod
        bits = None
        if self.number_draw:
            bits = ['g', {'transform': t(step / 2, self.fontsize)}]
        names = ['g', {'transform': t(step / 2, self.vlane / 2 + self.fontsize / 2)}]
        attrs = ['g', {'transform': t(step / 2, self.vlane)}]
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
            if self.number_draw and not self.compact:
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
                trimmed_name = self.trim_text(e['name'], available_space)
                lines = str(trimmed_name).split('\n')
                text_group = ['text']
                if len(lines) == 1:
                    text_group.append(ltextattrs)
                    text_group.extend(tspan(lines[0]))
                else:
                    line_height = self.fontsize * 1.2
                    first_line_y = ltextattrs['y'] - line_height * (len(lines) - 1) / 2
                    multiline_attrs = dict(ltextattrs)
                    multiline_attrs['y'] = first_line_y
                    text_group.append(multiline_attrs)
                    for i, line in enumerate(lines):
                        spans = tspan(line)
                        if not spans:
                            spans = [['tspan', {}, '']]
                        for j, span in enumerate(spans):
                            span_attrs = dict(span[1])
                            if j == 0:
                                span_attrs['x'] = 0
                                if i > 0:
                                    span_attrs['dy'] = line_height
                            text_group.append(['tspan', span_attrs, span[2]])
                ltext = ['g', {
                    'transform': t(step * (msb_pos + lsb_pos) / 2, -6),
                }, text_group]
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
            if not self.compact:
                attr_entries = e.get('_attr_entries', [])
                if attr_entries:
                    attr_offset = 0
                    for entry in attr_entries:
                        rendered = self._render_attr_entry(entry, step, lsb_pos, msb_pos, lsb, msb, e)
                        if rendered:
                            attrs.append(['g', {
                                'transform': t(0, attr_offset)
                            }, *rendered])
                        attr_offset += entry['spacing']
        if not self.compact or (self.index == 0):
            lane_children = []
            if self.number_draw:
                if self.compact:
                    for i in range(self.mod):
                        bits.append(['text', {
                            'x': step * i,
                            'font-size': self.fontsize,
                            'font-family': self.fontfamily,
                            'font-weight': self.fontweight,
                        }, str(i if self.vflip else self.mod - i - 1)])
                lane_children.append(bits)
            content_attrs = {}
            if self.bit_label_height:
                content_attrs['transform'] = t(0, self.bit_label_height)
            lane_children.append(['g', content_attrs, blanks, names, attrs])
            res = ['g', {}, *lane_children]
        else:
            res = ['g', {}, blanks, names, attrs]
        return res

    def hline(self, length, x=0, y=0, padding=0):
        res = ['line']
        if padding != 0:
            length -= padding
            x += padding / 2

        end_x = x + length
        att = {
            'x1': x,
            'x2': end_x,
            'y1': y,
            'y2': y,
        }
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
        text = str(text)
        if self.trim_char_width is None:
            return text

        def _trim_line(line):
            text_width = len(line) * self.trim_char_width
            if text_width <= available_space:
                return line
            end = len(line) - int((text_width - available_space) / self.trim_char_width) - 3
            if end > 0:
                return line[:end] + '...'
            return line[:1] + '...'

        lines = text.split('\n')
        trimmed_lines = [_trim_line(line) for line in lines]
        return '\n'.join(trimmed_lines)


def render(desc, **kwargs):
    renderer = Renderer(**kwargs)
    return renderer.render(desc)
