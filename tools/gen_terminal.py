# /// script
# requires-python = ">=3.11"
# dependencies = ["pyobjc-framework-Cocoa; sys_platform == 'darwin'"]
# ///
# 由 themes.py 生成 macOS Terminal.app 主题 terminal/<name>.terminal(颜色以 sRGB 存储).
# 用法: uv run tools/gen_terminal.py [--font MapleMono-NF-CN-Regular] [--size 12]
import argparse, os, plistlib, sys

sys.dont_write_bytecode = True  # 不在 tools/ 下留 __pycache__
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from AppKit import NSColor, NSFont, NSKeyedArchiver
from themes import ANSI, build

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OUT = os.path.join(ROOT, 'terminal')

BASE = {
    'type': 'Window Settings', 'ProfileCurrentVersion': 2.09,
    'columnCount': 200, 'rowCount': 50,
    'CursorBlink': True, 'CursorType': 2,
    'EnableSmoothResizing': True, 'FontAntialias': True,
    # 粗体不借用亮色; 开启时 bold 文字会变色, Solarized 一类亮色为灰阶的配色尤其明显
    'UseBrightBold': False,
    'useOptionAsMetaKey': True,
    'shellExitAction': 1, 'warnOnShellCloseAction': 0,
    'ShowActiveProcessArgumentsInTabTitle': False, 'ShowActiveProcessArgumentsInTitle': False,
    'ShowActiveProcessInTabTitle': False, 'ShowActiveProcessInTitle': False,
    'ShowActivityIndicatorInTab': False, 'ShowDimensionsInTitle': False,
    'ShowRepresentedURLPathInTabTitle': False,
}


def archive(obj) -> bytes:
    d, err = NSKeyedArchiver.archivedDataWithRootObject_requiringSecureCoding_error_(obj, False, None)
    if d is None:
        raise SystemExit(f'归档失败: {err}')
    return bytes(d)


def color(rgb, alpha: float = 1.0) -> bytes:
    return archive(NSColor.colorWithSRGBRed_green_blue_alpha_(*rgb, alpha))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--font', default='MapleMono-NF-CN-Regular')
    ap.add_argument('--size', type=float, default=12)
    args = ap.parse_args()
    font = NSFont.fontWithName_size_(args.font, args.size)
    if font is None:
        print(f'字体 {args.font} 未安装, 改用 Menlo', file=sys.stderr)
        font = NSFont.fontWithName_size_('Menlo-Regular', args.size)
    os.makedirs(OUT, exist_ok=True)
    for t in build():
        if not t['terminal']:
            continue
        p = dict(BASE, name=t['name'], WindowTitle=t['name'], Font=archive(font))
        p.update(BackgroundColor=color(t['bg']), TextColor=color(t['fg']), TextBoldColor=color(t['bold']),
                 CursorColor=color(t['cursor']), SelectionColor=color(t['sel']))
        for n in ANSI:
            p[f'ANSI{n}Color'] = color(t['ansi'][n])
            p[f'ANSIBright{n}Color'] = color(t['ansi']['Bright' + n])
        path = os.path.join(OUT, t['name'] + '.terminal')
        with open(path, 'wb') as f:
            plistlib.dump(p, f, fmt=plistlib.FMT_XML)
        print('wrote', os.path.relpath(path, ROOT))
    return 0


if __name__ == '__main__':
    sys.exit(main())
