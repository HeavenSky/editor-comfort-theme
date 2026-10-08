# /// script
# requires-python = ">=3.11"
# ///
# 由 themes.py, tools/sources/ 下的原主题与 VS Code 颜色注册表生成 VS Code 颜色主题 themes/<name>-color-theme.json.
# 用法: uv run tools/gen_vscode.py [--check]   (--check: 只比对, 产物与生成结果不一致时退出码 1)
import json, math, os, re, sys

sys.dont_write_bytecode = True  # 不在 tools/ 下留 __pycache__
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from colorlib import Rgb, blend, cr, from_oklch, h, hx, oklch, toward_bg, tune
from themes import ANSI, build

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SOURCES = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sources')
REGISTRY = os.path.join(SOURCES, 'vscode-color-registry.json')
OUT = os.path.join(ROOT, 'themes')

# 界面上的文字与其底色, 及对比度下限; metrics.py 用同一张表评级
UI_PAIRS = [
    ('editorLineNumber.foreground', 'editor.background', 3.0),
    ('sideBar.foreground', 'sideBar.background', 4.5),
    ('tab.activeForeground', 'tab.activeBackground', 4.5),
    ('tab.inactiveForeground', 'tab.inactiveBackground', 4.5),
    ('statusBar.foreground', 'statusBar.background', 4.5),
    ('activityBar.foreground', 'activityBar.background', 4.5),
    ('activityBar.inactiveForeground', 'activityBar.background', 4.5),
]
# 画在代码上的界面色, 按语法色的规则调色
TEXT_ON_CODE = ('editorBracketHighlight.foreground',)
# 原主题不定义括号色时, 用原主题的 数字 / 关键字 / 转义 色补上, 而不是落到注册表的通用补色
BRACKET_FALLBACK = ['constant.numeric', 'keyword.control', 'constant.character.escape']
NEUTRAL_CHROMA = 0.035
SAME_COLOR = 0.012


def load(path: str) -> dict:
    s = open(path, encoding='utf-8').read()
    s = re.sub(r'^\s*//.*$', '', s, flags=re.M)
    s = re.sub(r',(\s*[}\]])', r'\1', s)
    return json.loads(s)


def parse(v) -> tuple[Rgb, str] | None:
    if not isinstance(v, str):
        return None
    v = {'white': '#FFFFFF', 'black': '#000000'}.get(v.lower(), v)
    m = re.fullmatch(r'#([0-9A-Fa-f]{3,8})', v)
    if not m:
        return None
    s = m.group(1)
    if len(s) in (3, 4):
        s = ''.join(c * 2 for c in s)
    return h(s[:6]), s[6:8].upper()


def dist(a: Rgb, b: Rgb) -> float:
    (L1, C1, H1), (L2, C2, H2) = oklch(a), oklch(b)
    return math.dist((L1, C1 * math.cos(H1), C1 * math.sin(H1)), (L2, C2 * math.cos(H2), C2 * math.sin(H2)))


def scopes_of(rule: dict) -> list[str]:
    sc = rule.get('scope') or []
    return [x.strip() for x in (sc.split(',') if isinstance(sc, str) else sc)]


def resolve(rules: list, scope: str) -> str | None:
    # 选择器是 scope 的点分前缀即命中, 最长者胜; 只用于补括号色, 不处理后代选择器
    best, color = -1, None
    for r in rules:
        fg = r.get('settings', {}).get('foreground')
        for sel in scopes_of(r):
            if fg and ' ' not in sel and (scope == sel or scope.startswith(sel + '.')) and len(sel) > best:
                best, color = len(sel), fg
    return color


def hardcoded_keys(dark: bool) -> dict[str, str]:
    """VS Code 注册表中默认值是硬编码字面量的键 -> 该默认值; 主题不定义这些键时界面会落到与主题无关的颜色."""
    reg = json.load(open(REGISTRY, encoding='utf-8'))
    mode = 'dark' if dark else 'light'
    return {k: v[mode] for k, v in reg['colors'].items() if v.get(mode)}


class Mapper:
    """把原主题的颜色映射到目标主题: 语法色调对比度与彩度, 界面中性色随底色平移, 界面彩色封顶彩度."""

    def __init__(self, t: dict, src: dict):
        self.t = t
        c = src['colors']
        self.src_bg = parse(c['editor.background'])[0]
        self.src_fg = parse(c.get('editor.foreground') or c['foreground'])[0]
        self.dl = oklch(t['bg'])[0] - oklch(self.src_bg)[0]
        normal = [t['ansi'][n] for n in ANSI[1:7]]
        self.hues = [(oklch(c)[2], c) for c in normal]

    def token(self, v, comment: bool = False) -> str | None:
        p = parse(v)
        if p is None:
            return None
        rgb, alpha = p
        if dist(rgb, self.src_fg) < SAME_COLOR and not alpha:
            return hx(self.t['fg'])
        if alpha:
            # 半透明语法色(原主题用来弱化标点)按叠到底色上的实际颜色调对比度, 输出不透明色
            base = self.t['fg'] if dist(rgb, self.src_fg) < SAME_COLOR else rgb
            rgb, alpha = blend(base, self.t['bg'], int(alpha, 16) / 255), ''
        bg = self.t['bg']
        if comment:
            if self.t.get('comment_cr') is None:
                return hx(rgb) + alpha
            # 注释统一到同一对比度: 偏低的提上来, 偏高的压下去
            return hx(toward_bg(tune(hx(rgb), bg, 0.04, self.t['comment_cr']), bg, self.t['comment_cr'])) + alpha
        out = tune(hx(rgb), bg, self.t['cap'], self.t['token_min'])
        if self.t.get('syntax_max'):
            # 语法色不亮过正文太多, 避免满屏最抢眼的是字符串一类的彩色
            out = toward_bg(out, bg, cr(self.t['fg'], bg) * self.t['syntax_max'])
        return hx(out) + alpha

    def ui(self, v, ref_bg: Rgb | None = None) -> str | None:
        # ref_bg: 该颜色所在体系的编辑区底; 原主题的颜色用原主题底, VS Code 默认色用 VS Code 默认主题的底
        p = parse(v)
        if p is None:
            return None
        rgb, alpha = p
        ref_bg = ref_bg or self.src_bg
        if dist(rgb, ref_bg) < SAME_COLOR:
            return hx(self.t['bg']) + alpha
        if ref_bg is self.src_bg and dist(rgb, self.src_fg) < SAME_COLOR:
            return hx(self.t['fg']) + alpha
        L, C, H = oklch(rgb)
        if C < NEUTRAL_CHROMA:
            return hx(from_oklch(L + oklch(self.t['bg'])[0] - oklch(ref_bg)[0], C, H)) + alpha
        return hx(from_oklch(L, min(C, self.t['cap']), H)) + alpha

    def accent(self, v) -> str | None:
        # VS Code 默认的彩色映射到本主题同色相的终端色, 保留原透明度
        p = parse(v)
        if p is None:
            return None
        rgb, alpha = p
        L, C, H = oklch(rgb)
        if C < NEUTRAL_CHROMA:
            return None
        near = min(self.hues, key=lambda x: abs(math.atan2(math.sin(x[0] - H), math.cos(x[0] - H))))
        return hx(near[1]) + alpha


def opaque(colors: dict, key: str, under: Rgb) -> Rgb | None:
    p = parse(colors.get(key))
    if p is None:
        return None
    rgb, alpha = p
    return blend(rgb, under, int(alpha, 16) / 255) if alpha else rgb


def fill_hardcoded(colors: dict, t: dict, m: Mapper) -> None:
    # 注册表里默认值硬编码的键, 主题没定义的一律按本主题色板补齐, 不让任何界面落到与主题无关的颜色
    hard = hardcoded_keys(t['dark'])
    vs_bg = parse(hard['editor.background'])[0]
    for k, default in hard.items():
        if k in colors:
            continue
        out = m.accent(default) if not k.startswith(TEXT_ON_CODE) else m.token(default)
        colors[k] = out or m.ui(default, vs_bg)


def transform(t: dict, src: dict) -> dict:
    m = Mapper(t, src)
    colors = {}
    for k, v in src['colors'].items():
        out = m.token(v) if k.startswith(TEXT_ON_CODE) else m.ui(v)
        if out is not None:
            colors[k] = out
    if 'editorBracketHighlight.foreground1' not in colors:
        for i, scope in enumerate(BRACKET_FALLBACK, 1):
            colors[f'editorBracketHighlight.foreground{i}'] = m.token(resolve(src['tokenColors'], scope) or hx(m.src_fg))
    colors.update({
        'editor.background': hx(t['bg']), 'editor.foreground': hx(t['fg']), 'editorCursor.foreground': hx(t['cursor']),
        'terminal.background': hx(t['bg']), 'terminal.foreground': hx(t['fg']), 'terminalCursor.foreground': hx(t['cursor']),
    })
    for n in ANSI:
        colors['terminal.ansi' + n] = hx(t['ansi'][n])
        colors['terminal.ansiBright' + n] = hx(t['ansi']['Bright' + n])

    fill_hardcoded(colors, t, m)

    # 映射后仍可能有界面文字对比度不足(底色变了, 或原主题本身就偏淡), 逐对推到下限
    for fg_key, bg_key, need in UI_PAIRS:
        under = opaque(colors, bg_key, t['bg']) or t['bg']
        fg = opaque(colors, fg_key, under)
        if fg is not None and cr(fg, under) < need:
            colors[fg_key] = hx(tune(hx(fg), under, 1.0, need))

    rules = []
    for r in src['tokenColors']:
        r = json.loads(json.dumps(r))
        st = r.get('settings', {})
        comment = any('comment' in s for s in scopes_of(r))
        for field, fn in (('foreground', lambda v: m.token(v, comment)), ('background', m.ui)):
            if field in st:
                out = fn(st[field])
                if out is None:
                    del st[field]
                else:
                    st[field] = out
        rules.append(r)

    semantic = {}
    for k, v in (src.get('semanticTokenColors') or {}).items():
        if isinstance(v, str):
            out = m.token(v)
            if out is not None:
                semantic[k] = out
            continue
        v = dict(v)
        if 'foreground' in v:
            out = m.token(v['foreground'])
            if out is None:
                del v['foreground']
            else:
                v['foreground'] = out
        semantic[k] = v
    return dict(colors=dict(sorted(colors.items())), tokenColors=rules, semanticTokenColors=semantic)


def render(t: dict) -> dict:
    src = load(os.path.join(SOURCES, t['source']))
    body = transform(t, src)
    return {
        '$schema': 'vscode://schemas/color-theme',
        'name': t['label'],
        'type': 'dark' if t['dark'] else 'light',
        'semanticHighlighting': src.get('semanticHighlighting', True),
        'colors': body['colors'],
        'tokenColors': body['tokenColors'],
        'semanticTokenColors': body.get('semanticTokenColors') or {},
    }


def main() -> int:
    check = '--check' in sys.argv
    os.makedirs(OUT, exist_ok=True)
    stale = []
    for t in build():
        path = os.path.join(OUT, f"{t['name']}-color-theme.json")
        text = json.dumps(render(t), indent='\t', ensure_ascii=False) + '\n'
        old = open(path, encoding='utf-8').read() if os.path.exists(path) else None
        if check:
            if old != text:
                stale.append(os.path.relpath(path, ROOT))
        elif old != text:
            open(path, 'w', encoding='utf-8').write(text)
            print('wrote', os.path.relpath(path, ROOT))
    if stale:
        print('与 tools/themes.py 不一致, 先运行 uv run tools/gen_vscode.py:', *stale, sep='\n  ')
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
