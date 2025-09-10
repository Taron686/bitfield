from .render import render
from .jsonml_stringify import jsonml_stringify
import argparse


def beautify(res):
    import xml.dom.minidom
    xml = xml.dom.minidom.parseString(res)
    res = xml.toprettyxml()
    return res


def bit_field_cli():
    parser = argparse.ArgumentParser('bitfield')

    parser.add_argument(
        'input', help='input JSON filename - must be specified always')
    parser.add_argument(
        '--input', help='(compatibility option)', action='store_true')
    parser.add_argument('--vspace', help='vertical space', default=80, type=int)
    parser.add_argument('--hspace', help='horizontal space', default=800, type=int)
    parser.add_argument('--lanes', help='rectangle lanes', default=None, type=int)
    parser.add_argument('--bits', help='bits per lane', default=32, type=int)
    parser.add_argument('--fontfamily', default='sans-serif')
    parser.add_argument('--fontweight', default='normal')
    parser.add_argument('--fontsize', default=14, type=int)
    parser.add_argument('--strokewidth', help='stroke width', default=1, type=float)
    parser.add_argument('--beautify', action='store_true')
    parser.add_argument('--json5', action='store_true')
    parser.add_argument('--no-json5', action='store_true')
    parser.add_argument('--compact', action='store_true')
    parser.add_argument('--hflip', help='horizontal flip', action='store_true')
    parser.add_argument('--vflip', help='vertical flip', action='store_true')
    parser.add_argument('--trim', help='trim long bitfield names', type=float)
    parser.add_argument('--uneven', help='uneven lanes', action='store_true')
    parser.add_argument('--legend', help='legend item', action='append', nargs=2, metavar=('NAME', 'TYPE'))
    parser.add_argument('--label-lines', help='vertical label text')
    parser.add_argument('--label-fontsize', type=int)
    parser.add_argument('--label-start-line', type=int)
    parser.add_argument('--label-end-line', type=int)
    parser.add_argument('--label-layout', choices=['left', 'right'], default='left')
    parser.add_argument('--label-angle', type=float)
    args = parser.parse_args()

    # default is json5, unless forced with --(no-)json5
    if args.json5:
        import json5 as json
    elif args.no_json5:
        import json
    else:
        try:
            import json5 as json
        except ModuleNotFoundError:
            import json

    with open(args.input, 'r') as f:
        data = json.load(f)
        label_cfg = None
        if args.label_lines is not None:
            label_cfg = {
                'label_lines': args.label_lines,
                'font_size': args.label_fontsize if args.label_fontsize is not None else args.fontsize,
                'start_line': args.label_start_line,
                'end_line': args.label_end_line,
                'layout': args.label_layout,
            }
            if args.label_angle is not None:
                label_cfg['angle'] = args.label_angle
        res = render(data,
                     hspace=args.hspace,
                     vspace=args.vspace,
                     lanes=args.lanes,
                     bits=args.bits,
                     fontfamily=args.fontfamily,
                     fontweight=args.fontweight,
                     fontsize=args.fontsize,
                     compact=args.compact,
                     hflip=args.hflip,
                     vflip=args.vflip,
                     strokewidth=args.strokewidth,
                     trim=args.trim,
                     uneven=args.uneven,
                     legend={key: value for key, value in args.legend} if args.legend else None,
                     label_lines=label_cfg)

    res = jsonml_stringify(res)
    if args.beautify:
        res = beautify(res)
    print(res)
