# /// script
# requires-python = ">=3.11"
# ///
# 由 themes.py, tools/sources/ 下的原主题与 VS Code 颜色注册表生成 VS Code 颜色主题 themes/<name>-color-theme.json.
# 用法: uv run tools/gen_vscode.py [--check]   (--check: 只比对, 产物与生成结果不一致时退出码 1)
import json, math, os, re, sys

sys.dont_write_bytecode = True  # 不在 tools/ 下留 __pycache__
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from colorlib import Rgb, blend, cr, from_oklch, h, hx, oklch, toward_bg, tune
import pool
from coverage import fill as fill_coverage
from schema import FONT_STYLE, HEX, RULE_KEYS, SEMANTIC_STYLE_KEYS, SETTINGS_KEYS, TRANSPARENT, problems
from comfort import HIGHLIGHT_KEYS, HIGHLIGHT_MAX_CR, HIGHLIGHT_TEXT_MIN, PANEL_KEYS, PANEL_MAX_CHROMA, PANEL_MAX_CR
from themes import ANSI, build

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SOURCES = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sources')
REGISTRY = os.path.join(SOURCES, 'vscode-color-registry.json')
OUT = os.path.join(ROOT, 'themes')

# 界面上的文字与其底色, 及对比度下限; metrics.py 用同一张表评级
UI_PAIRS = [
    ('editorLineNumber.foreground', 'editor.background', 2.2),
    ('sideBar.foreground', 'sideBar.background', 4.5),
    ('tab.activeForeground', 'tab.activeBackground', 4.5),
    ('tab.inactiveForeground', 'tab.inactiveBackground', 4.5),
    ('statusBar.foreground', 'statusBar.background', 4.5),
    ('activityBar.foreground', 'activityBar.background', 4.5),
    ('activityBar.inactiveForeground', 'activityBar.background', 4.5),
]
# 行号对比度上限: 常驻视野边缘, 够读即可(防疲劳理想 2.0~2.6)
LINE_NO_MAX = 2.6
# 画在代码上的界面色, 按语法色的规则调色
TEXT_ON_CODE = ('editorBracketHighlight.foreground',)
# 原主题不定义括号色时, 用原主题的 数字 / 关键字 / 转义 色补上, 而不是落到注册表的通用补色
BRACKET_FALLBACK = ['constant.numeric', 'keyword.control', 'constant.character.escape']
NEUTRAL_CHROMA = 0.035
SAME_COLOR = 0.012
COMMENT_RATIO = 1.85
COMMENT_RANGE = (3.4, 4.2)


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


def source_fg(src: dict, dark: bool) -> str:
    # 原主题的正文色: editor.foreground, foreground, 无 scope 的全局规则, 都没有时就是 VS Code 的默认正文色
    c = src['colors']
    glob = [r['settings']['foreground'] for r in src.get('tokenColors', []) if not r.get('scope') and r.get('settings', {}).get('foreground')]
    reg = json.load(open(REGISTRY, encoding='utf-8'))['colors']['editor.foreground']
    return c.get('editor.foreground') or c.get('foreground') or (glob[0] if glob else reg['dark' if dark else 'light'])


def hardcoded_keys(dark: bool) -> dict[str, str]:
    """VS Code 注册表中默认值是硬编码字面量的键 -> 该默认值; 主题不定义这些键时界面会落到与主题无关的颜色."""
    reg = json.load(open(REGISTRY, encoding='utf-8'))
    mode = 'dark' if dark else 'light'
    return {k: v[mode] for k, v in reg['colors'].items() if v.get(mode) and not v.get('deprecated')}


# 已废弃颜色键的官方替代键(VS Code deprecationMessage 所指); 其余废弃键与未注册的键直接丢弃
DEPRECATED_RENAME = {
    'editorActiveLineNumber.foreground': 'editorLineNumber.activeForeground',
    'editorIndentGuide.background': 'editorIndentGuide.background1',
    'editorIndentGuide.activeBackground': 'editorIndentGuide.activeBackground1',
}


def translucent(target: Rgb, bg: Rgb) -> str:
    # 须半透明的颜色: 取叠到编辑区底上后与 target 相同的最小透明度, 观感不变而不再遮住下面的内容
    for i in range(25, 96):
        a = i / 100
        c = [(x - (1 - a) * y) / a for x, y in zip(target, bg)]
        if all(-1e-6 <= v <= 1 + 1e-6 for v in c):
            return hx(tuple(min(1, max(0, v)) for v in c)) + '%02X' % round(a * 255)
    return hx(target) + 'F2'


def conform(colors: dict, rules: list, semantic: dict, t: dict) -> None:
    """按 vscode://schemas/color-theme 清理: VS Code 会忽略或报错的写法改成等效的合法写法, 改不了的丢弃."""
    reg = json.load(open(REGISTRY, encoding='utf-8'))
    known = reg['colors']
    for old, new in DEPRECATED_RENAME.items():
        if old in colors:
            colors.setdefault(new, colors[old])
    for k in list(colors):
        info = known.get(k)
        if info is None or info.get('deprecated') or not (isinstance(colors[k], str) and HEX.match(colors[k])):
            del colors[k]
        elif info.get('transparent') and not TRANSPARENT.match(colors[k]):
            colors[k] = translucent(opaque(colors, k, t['bg']), t['bg'])
    kept = []
    for r in rules:
        st = r.get('settings')
        if not isinstance(st, dict):
            continue
        for k in [k for k in r if k not in RULE_KEYS]:
            del r[k]
        # token 背景色已废弃且不生效; 其余不在 schema 里的字段(CSS 属性等)同样不生效
        for k in [k for k in st if k not in SETTINGS_KEYS or k == 'background']:
            del st[k]
        if 'fontStyle' in st and not FONT_STYLE.match(str(st['fontStyle'])):
            # TextMate 的 normal / regular 意为取消样式, schema 里的等效写法是空字符串
            st['fontStyle'] = '' if str(st['fontStyle']).strip().lower() in ('normal', 'regular', 'none') else None
            if st['fontStyle'] is None:
                del st['fontStyle']
        if st:
            kept.append(r)
    rules[:] = kept
    selector = re.compile(reg['semanticSelector'])
    for k in list(semantic):
        v = semantic[k]
        if not selector.match(k):
            del semantic[k]
        elif isinstance(v, dict):
            for f in [f for f in v if f not in SEMANTIC_STYLE_KEYS or f == 'background']:
                del v[f]
            if not v:
                del semantic[k]


class Mapper:
    """把原主题的颜色映射到目标主题: 语法色调对比度与彩度, 界面中性色随底色平移, 界面彩色封顶彩度."""

    def __init__(self, t: dict, src: dict):
        self.t = t
        c = src['colors']
        self.src_bg = parse(c['editor.background'])[0]
        self.src_fg = parse(source_fg(src, t['dark']))[0]
        self.dl = oklch(t['bg'])[0] - oklch(self.src_bg)[0]
        normal = [t['ansi'][n] for n in ANSI[1:7]]
        self.hues = [(oklch(c)[2], c) for c in normal]
        # 注释对比度: 'auto' 随正文联动, 正文 / COMMENT_RATIO, 限制在 COMMENT_RANGE 内
        target = t.get('comment_cr')
        if target == 'auto':
            target = min(COMMENT_RANGE[1], max(COMMENT_RANGE[0], cr(t['fg'], t['bg']) / COMMENT_RATIO))
        self.comment_cr = target

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
            if self.comment_cr is None:
                return hx(rgb) + alpha
            # 注释统一到同一对比度: 偏低的提上来, 偏高的压下去
            return hx(toward_bg(tune(hx(rgb), bg, 0.04, self.comment_cr), bg, self.comment_cr)) + alpha
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

    def tint(self, v, ref_bg: Rgb) -> str | None:
        # 背景类默认色: 色相取本主题同色相的终端色, 明度保留默认值(随底色平移), 彩度封顶; 不把暗底色换成亮色块
        p = parse(v)
        if p is None:
            return None
        rgb, alpha = p
        L, C, H = oklch(rgb)
        if C < NEUTRAL_CHROMA:
            return None
        near = min(self.hues, key=lambda x: abs(math.atan2(math.sin(x[0] - H), math.cos(x[0] - H))))
        L += oklch(self.t['bg'])[0] - oklch(ref_bg)[0]
        return hx(from_oklch(L, min(C, self.t['cap']), oklch(near[1])[2])) + alpha


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
        if k.startswith(TEXT_ON_CODE):
            out = m.token(default)
        elif k.lower().endswith('background'):
            out = m.tint(default, vs_bg)
        else:
            out = m.accent(default)
        colors[k] = out or m.ui(default, vs_bg)


def calm(colors: dict, t: dict) -> None:
    # 面板底色不成亮块, 高亮底色不刺眼且压在上面的正文可读; 口径与 comfort.py 的防疲劳规则一致
    bg, fg = t['bg'], t['fg']
    for k in PANEL_KEYS + HIGHLIGHT_KEYS:
        p = parse(colors.get(k))
        if p is None:
            continue
        rgb, alpha = p
        if k in PANEL_KEYS and oklch(blend(rgb, bg, int(alpha, 16) / 255 if alpha else 1.0))[1] > PANEL_MAX_CHROMA:
            L, C, H = oklch(rgb)
            rgb = from_oklch(L, PANEL_MAX_CHROMA * (1 if not alpha else 255 / max(1, int(alpha, 16))), H)
            colors[k] = hx(rgb) + alpha
        a = int(alpha, 16) / 255 if alpha else 1.0
        limit = PANEL_MAX_CR if k in PANEL_KEYS else HIGHLIGHT_MAX_CR
        # 留 0.03 余量, 避免 hex 取整后又越过门禁边界
        bad = lambda c, a: cr(blend(c, bg, a), bg) > limit - 0.03 or (
            k in HIGHLIGHT_KEYS and cr(fg, blend(c, bg, a)) < HIGHLIGHT_TEXT_MIN + 0.03)
        if not bad(rgb, a):
            continue
        if alpha:
            while a > 0.05 and bad(rgb, a):
                a -= 0.02
            colors[k] = hx(rgb) + '%02X' % round(a * 255)
        else:
            L, C, H = oklch(rgb)
            step = 0.004 if oklch(bg)[0] > L else -0.004
            while bad(rgb, 1.0) and 0 < L < 1:
                L += step
                rgb = from_oklch(L, C, H)
            colors[k] = hx(rgb)


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
    line_no = opaque(colors, 'editorLineNumber.foreground', t['bg'])
    if line_no is not None and cr(line_no, t['bg']) > LINE_NO_MAX:
        colors['editorLineNumber.foreground'] = hx(toward_bg(line_no, t['bg'], LINE_NO_MAX))
    calm(colors, t)

    rules = pool_rules(src, m, t)
    # 语义着色交给 VS Code 内置的语义 token -> TextMate scope 映射, 与规则池一致; 原主题自带的语义色不再沿用
    semantic = {}
    # 统一着色覆盖: 原主题没定义的常用 scope 从本主题的相近角色取色补上(见 coverage.py)
    rules[:0] = fill_coverage(rules, hx(t['fg']))
    conform(colors, rules, semantic, t)
    return dict(colors=dict(sorted(colors.items())), tokenColors=rules, semanticTokenColors=semantic)


_POOL = None
VARIABLE_CHROMA = 0.09


def derive_variable(colors: dict, t: dict) -> str | None:
    """普通变量的派生专用色: 明度贴近参数色, 彩度 VARIABLE_CHROMA, 对比度在语法色下限与正文之间,
    在色环上取与周围角色色(pool.DERIVE_CONTEXT)最小色差最大的色相; 现成角色色都会与某个角色撞色, 所以单独派生."""
    from colorlib import de2000
    bg = t['bg']
    hi = cr(t['fg'], bg) * (t.get('syntax_max') or 1.0)
    ctx = [parse(colors[r])[0] for r in pool.DERIVE_CONTEXT if colors.get(r)]
    L0 = oklch(parse(colors['parameter'])[0])[0] if colors.get('parameter') else oklch(t['fg'])[0]
    best, pick = -1.0, None
    for dl in (0, -0.04, 0.04, -0.08, 0.08):
        for deg in range(0, 360, 3):
            c = from_oklch(L0 + dl, VARIABLE_CHROMA, math.radians(deg))
            # 留 0.05 余量, 避免 hex 取整后越过对比度边界
            if not (t['token_min'] + 0.05 <= cr(c, bg) <= hi - 0.05):
                continue
            score = min(de2000(c, x) for x in ctx)
            if score > best:
                best, pick = score, c
    return hx(pick) if pick else None


def pool_rules(src: dict, m: 'Mapper', t: dict) -> list[dict]:
    """由规则池生成 tokenColors: 每个选择器按裁决出的角色取本主题的角色色(原主题的颜色经同样的调色), 设置相同的合为一条."""
    global _POOL
    if _POOL is None:
        _POOL = pool.build(build())
    src_rules = src.get('tokenColors', [])
    fg = source_fg(src, t['dark'])
    colors = {r: m.token(pool.role_value(src_rules, r, fg), comment=r == 'comment') for r in pool.ROLES}
    colors['variable'] = derive_variable(colors, t) or colors['variable']
    groups: dict[str, list[str]] = {}
    styles: dict[str, dict] = {}
    for sel, p in _POOL.items():
        role = p['role']
        if role == pool.INHERIT:
            continue
        if role not in styles:
            settings = {}
            if colors.get(role):
                settings['foreground'] = colors[role]
            style = pool.role_value(src_rules, role, None, 'fontStyle')
            if style is not None:
                settings['fontStyle'] = style
            styles[role] = settings
        if styles[role]:
            groups.setdefault(role, []).append(sel)
    return [{'name': f'Comfort {role}', 'scope': sels, 'settings': styles[role]} for role, sels in groups.items()]


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
        theme = render(t)
        bad = problems(theme)
        if bad:
            print(f"{t['name']}: 生成结果不符合 vscode://schemas/color-theme:", *bad[:10], sep='\n  ')
            return 1
        text = json.dumps(theme, indent='\t', ensure_ascii=False) + '\n'
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
