# /// script
# requires-python = ">=3.11"
# ///
# 调色链: 补全段的中间主题 tools/sources/<name>-full.json(complete.py)经 tools/steps.py 登记的调色步骤生成 VS Code 颜色主题 themes/<name>.json.
# 一切改色都必须是登记过的步骤: COMFORT_STEPS=none 时产物与 full 逐键相等(--identity 校验).
# 用法: uv run tools/gen_vscode.py [--check] [--out <目录>]   (--check: 只比对, 产物与生成结果不一致时退出码 1;
#       --out: 写到别的目录, 不动 themes/, 供 compare-steps.mjs 按不同 COMFORT_STEPS 生成对比用)
#       COMFORT_STEPS=none uv run tools/gen_vscode.py --identity   全关产物与 full 的 colors / tokenColors / semanticTokenColors 不等时退出码 1
# themes/*.json 是生成物: 手改会在下次生成时被覆盖, 要改颜色改 themes.py 或 tools/sources/ 的输入.
import json, math, os, re, sys

sys.dont_write_bytecode = True  # 不在 tools/ 下留 __pycache__
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from colorlib import (Rgb, amber, blend, cr, de2000, deneon, fit, from_oklch, h, hx, lum, neon, oklch, sat, soften, toward_bg, tune,
                      unextreme, with_sat)
import levels, pool
from schema import FONT_STYLE, HEX, RULE_KEYS, SEMANTIC_STYLE_KEYS, SETTINGS_KEYS, TRANSPARENT, problems
from comfort import (BADGE_MAX_CR, BRIGHT_TINT_L, BRIGHT_TINT_SAT, BADGE_PAIRS, BADGE_TEXT_MIN, BORDER_KEYS, BORDER_MAX_CR, CONTROL_BORDER_KEYS, CONTROL_BORDER_MAX_CR,
                     CONTROL_TEXT_MIN, CONTROL_TEXT_PAIRS, FOCUS_KEYS, FOCUS_MAX, FOCUS_MIN_CR, GRAY_CHROMA, TINT_KEYS, TINTED_BG_CHROMA, PLACEHOLDER_CR, PLACEHOLDER_KEY, PLACEHOLDER_MAX_CHROMA,
                     HIGHLIGHT_KEYS, HIGHLIGHT_MAX_CR, INPUT_SELECTION_TEXT, SELECTION_VISIBLE, input_selection,
                     HIGHLIGHT_TEXT_MIN, LIGHT_PANEL_MAX, PANEL_KEYS,
                     PANEL_MAX_CHROMA, PANEL_MAX_CR, STATUS_GROUPS, UI_TEXT_MAX, UI_TEXT_SKIP, own_background)
from themes import ANSI, LEGIBLE, NEON_TARGET, TERM_MARGIN, SYN_FLOOR, SYN_KNEE, UI_FLOOR, UI_KNEE, build
from steps import on

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SOURCES = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sources')
REGISTRY = os.path.join(SOURCES, 'vscode-color-registry.json')
OUT = os.path.join(ROOT, 'themes')

# 界面上的文字与其底色, 及对比度下限(非活动的图标 / 标签本就该淡一档, 下限 3.0); metrics.py 用同一张表评级
UI_PAIRS = [
    ('editorLineNumber.foreground', 'editor.background', 2.2),
    ('sideBar.foreground', 'sideBar.background', 4.5),
    ('tab.activeForeground', 'tab.activeBackground', 4.5),
    ('tab.inactiveForeground', 'tab.inactiveBackground', 3.0),
    ('statusBar.foreground', 'statusBar.background', 4.5),
    ('activityBar.foreground', 'activityBar.background', 4.5),
    ('activityBar.inactiveForeground', 'activityBar.background', 3.0),
    ('sideBarTitle.foreground', 'sideBar.background', 4.5),
    ('sideBarSectionHeader.foreground', 'sideBarSectionHeader.background', 4.5),
    ('titleBar.activeForeground', 'titleBar.activeBackground', 4.5),
    # 没有定义 sideBar.foreground 的主题(如 Ayu)文件树用通用前景色
    ('foreground', 'sideBar.background', 4.5),
]
# 按钮(如源代码管理的 Commit): 低彩度, 与编辑区底拉开到 BUTTON_CR(悬停再高一点), 不做饱和的实心色块, 也不至于看不出是按钮
BUTTON_PAIRS = [('button.background', 1.75), ('button.hoverBackground', 2.0)]
BUTTON_CHROMA = 0.06
# 列表选中 / 悬停 / 聚焦行上的字: 用正文色, 不用彩色(彩色像报错或链接)
LIST_TEXT_KEYS = ['list.activeSelectionForeground', 'list.inactiveSelectionForeground', 'list.focusForeground', 'list.hoverForeground',
                  'list.focusHighlightForeground']
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
# 注释的饱和度区间: 保留原主题注释的色调(纯灰的取底色色相), 退后但不是死灰
COMMENT_SAT = (0.12, 0.35)


def is_area(key: str) -> bool:
    """画成一片的颜色(底色, 边框, 阴影): 仍按 cap(彩度)与对比度安静处理; 其余(文字, 图标)按饱和度平滑压缩."""
    return key.lower().endswith(('background', 'border', 'shadow'))


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
    """把原主题的颜色映射到目标主题: 语法色按原顺序映射对比度, 饱和度平滑压缩; 界面中性色随底色平移并带底色色调;
    界面文字与图标的彩色按饱和度压缩, 大面积的底色与边框封顶彩度."""

    def __init__(self, t: dict, src: dict):
        self.t = t
        c = src['colors']
        self.src_bg = parse(c['editor.background'])[0]
        self.src_fg = parse(source_fg(src, t['dark']))[0]
        self.dl = oklch(t['bg'])[0] - oklch(self.src_bg)[0]
        normal = [t.get('ui_ansi', t['ansi'])[n] for n in ANSI[1:7]]
        self.hues = [(oklch(c)[2], c) for c in normal]
        # 注释对比度: 'auto' 随正文联动, 正文 / COMMENT_RATIO, 限制在 COMMENT_RANGE 内
        target = t.get('comment_cr')
        if target == 'auto':
            target = min(COMMENT_RANGE[1], max(COMMENT_RANGE[0], cr(t['fg'], t['bg']) / COMMENT_RATIO))
        self.comment_cr = target
        # 原主题彩色语法色对其底色的对比度范围: 语法色按原来的明暗顺序平滑映射进 [token_min, 上限], 不全部贴到同一个边界
        fg = source_fg(src, t['dark'])
        crs = []
        for r in pool.ROLES:
            p = parse(pool.role_value(src.get('tokenColors', []), r, fg) or '') if r not in ('comment', 'text') else None
            if p and oklch(p[0])[1] > NEUTRAL_CHROMA:
                crs.append(cr(p[0], self.src_bg))
        self.src_cr = (min(crs), max(crs)) if crs else None
        text = self.text = cr(t['fg'], t['bg'])
        # 底色 / 正文没变时不做吸附与平移, 未调整的颜色原样输出(全关时与补全段产物逐键相等)
        self.bg_same, self.fg_same = hx(t['bg']) == hx(self.src_bg), hx(t['fg']) == hx(self.src_fg)
        self.band = (t['token_min'], text * (t.get('syntax_max') or 1.0))

    def target_cr(self, c: float) -> float:
        """原主题对比度 c 在 [min(原下限, lo), max(原上限, hi)] 中的位置(对数), 映射到 [lo, hi]; 原范围在区间内时不变.
        只开 syntax_floor 时只抬低于 lo 的颜色(抬到 lo), 本来够读的不动.
        只开 syntax_cap 时对称地只压高端. 两者都关时原样返回."""
        lo, hi = self.band
        floor, cap = on('syntax_floor'), on('syntax_cap')
        if not (floor and cap):
            if not (floor or cap):
                return c
            a, b = self.src_cr or (c, c)
            la, lb, lx = math.log(a), math.log(b), math.log(c)
            if floor:
                return max(lo, c)
            if a >= hi:
                return min(hi, c * hi / b)
            r = (math.log(min(b, hi)) - la) / (lb - la) if lb > la else 1.0
            return min(hi, c if c <= a else math.exp(la + (lx - la) * r))
        a, b = self.src_cr or (lo, hi)
        a, b = min(a, lo), max(b, hi)
        if b <= a or hi <= lo:
            return lo
        x = min(1.0, max(0.0, (math.log(c) - math.log(a)) / (math.log(b) - math.log(a))))
        return math.exp(math.log(lo) + x * (math.log(hi) - math.log(lo)))

    def token(self, v, comment: bool = False) -> str | None:
        # 全透明(如括号色 4~6 的 #00000000)表示不着色, VS Code 跳过它只循环前 3 色; 按语法色抬到可读会变成不透明的灰括号
        if (q := parse(v)) and q[1] == '00':
            return v
        out, p = self._token(v, comment), parse(v)
        # 半透明色没被调整(叠到底上的实际颜色不变)时保留原写法, 不改成不透明
        if out is None or p is None or not p[1] or not self.bg_same:
            return out
        q = parse(out)
        return hx(p[0]) + p[1] if q and not q[1] and hx(q[0]) == hx(blend(p[0], self.src_bg, int(p[1], 16) / 255)) else out

    def _token(self, v, comment: bool = False) -> str | None:
        p = parse(v)
        if p is None:
            return None
        rgb, alpha = p
        near_fg = dist(rgb, self.src_fg) < SAME_COLOR and not self.fg_same
        if near_fg and not alpha:
            return hx(self.t['fg'])
        src_c = rgb
        if alpha:
            # 半透明语法色(原主题用来弱化标点)按叠到底色上的实际颜色调对比度, 输出不透明色
            a = int(alpha, 16) / 255
            base = self.t['fg'] if near_fg else rgb
            src_c = blend(self.src_fg if base is self.t['fg'] else rgb, self.src_bg, a)
            rgb, alpha = blend(base, self.t['bg'], a), ''
        bg, dark = self.t['bg'], self.t['dark']
        L, C, H = oklch(rgb)
        if comment:
            if self.comment_cr is None:
                return hx(rgb) + alpha
            if not on('comment_fit'):
                if on('comment_floor') and cr(rgb, bg) < COMMENT_RANGE[0]:
                    return hx(fit(rgb, bg, lo=COMMENT_RANGE[0] + 0.02)) + alpha
                return hx(rgb) + alpha
            # 注释统一到同一对比度(偏低的提上来, 偏高的压下去), 饱和度落进 COMMENT_SAT: 带原主题注释的色调, 不是死灰
            s = min(max(sat(rgb), COMMENT_SAT[0]), COMMENT_SAT[1])
            if C < 0.01:
                H = oklch(bg)[2]
            return hx(fit(with_sat(L, s, H), bg, lo=self.comment_cr, hi=self.comment_cr, s=s)) + alpha
        # 饱和度平滑压缩(不封顶), 对比度按原顺序映射; 浅色主题压深的黄朝琥珀偏; 最后去荧光感
        soft = on('syntax_soften')
        s = soften(sat(rgb), SYN_KNEE, SYN_FLOOR if C > NEUTRAL_CHROMA else 0.0) if soft else sat(rgb)
        target = self.target_cr(cr(src_c, self.src_bg))
        # 饱和度不压且对比度已在目标上时原样保留, 不经 OKLCH 往返
        if soft or abs(cr(rgb, bg) - target) > 0.01:
            out = fit(with_sat(L, s, H), bg, lo=target, hi=target, s=s)
        else:
            out = rgb
        H2 = amber(H, oklch(out)[0], dark) if on('amber') else H
        if H2 != H:
            out = fit(with_sat(oklch(out)[0], s, H2), bg, lo=target, hi=target, s=s)
        return hx(deneon(out, NEON_TARGET, bg, self.t['token_min']) if on('neon') else out) + alpha

    def ui(self, v, ref_bg: Rgb | None = None, area: bool = False) -> str | None:
        # ref_bg: 该颜色所在体系的编辑区底; 原主题的颜色用原主题底, VS Code 默认色用 VS Code 默认主题的底
        # area: 画成一片的颜色(见 is_area), 彩色封顶 cap; 否则按饱和度平滑压缩
        p = parse(v)
        if p is None:
            return None
        rgb, alpha = p
        own = ref_bg is None
        ref_bg = ref_bg or self.src_bg
        if dist(rgb, ref_bg) < SAME_COLOR and not (own and self.bg_same):
            return hx(self.t['bg']) + alpha
        if own and dist(rgb, self.src_fg) < SAME_COLOR and not self.fg_same:
            return hx(self.t['fg']) + alpha
        L, C, H = oklch(rgb)
        Lb, Cb, Hb = oklch(self.t['bg'])
        if C < NEUTRAL_CHROMA:
            # 中性色随底色平移明度, 并带上底色的色调(不超过面板彩度上限): 不出现与底色不搭的纯灰
            Ct = min(Cb, PANEL_MAX_CHROMA - 0.005)
            if Ct > C and on('ui_neutral_tint'):
                C, H = Ct, Hb
            elif own and self.bg_same:
                return hx(rgb) + alpha
            return hx(from_oklch(L + Lb - oklch(ref_bg)[0], C, H)) + alpha
        if area:
            return hx(from_oklch(L, min(C, self.t['cap']), H) if on('area_cap') else rgb) + alpha
        out = with_sat(L, soften(sat(rgb), UI_KNEE, UI_FLOOR), H) if on('ui_soften') else rgb
        return hx(deneon(out, NEON_TARGET) if on('neon') else out) + alpha

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
        # 界面图标与文字: 终端色的饱和度按界面口径(UI_KNEE)再压一档, 去荧光感
        nL, nC, nH = oklch(near[1])
        out = with_sat(nL, soften(sat(near[1]), UI_KNEE, UI_FLOOR), nH) if on('ui_soften') else near[1]
        return hx(deneon(out, NEON_TARGET) if on('neon') else out) + alpha

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
        return hx(from_oklch(L, min(C, self.t['cap']) if on('area_cap') else C, oklch(near[1])[2])) + alpha


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
        # 默认值全透明的(如括号色 4~6 的 #00000000, 表示不着色)原样保留; 混到底色上会变成与底同色的不透明色, 字就看不见了
        p = parse(default)
        if p and p[1] == '00':
            colors[k] = default
            continue
        if k.startswith(TEXT_ON_CODE):
            out = m.token(default)
        elif k.lower().endswith('background'):
            out = m.tint(default, vs_bg)
        else:
            out = m.accent(default)
            out = out and (out if is_area(k) else default_cr(out, default, t['bg'], vs_bg))
        colors[k] = out or m.ui(default, vs_bg, is_area(k))


# 补出的界面文字色对底色的对比度要求上限: 与看不清类步骤的正文 / 语法 / 终端可读下限一致
FILL_TEXT_CR = 4.5


def default_cr(v: str, default: str, bg: Rgb, vs_bg: Rgb) -> str:
    """补出的界面文字 / 图标色(色相取终端色)对本主题底色的对比度不低于 VS Code 默认色对默认底色的对比度, 但最多要求到 FILL_TEXT_CR:
    明度往远离底色的方向调, 色相与饱和度不变, 保留透明度. 浅色主题的终端黄(如 Owl Light #E0AF02)直接拿来当 git 修改标记会比默认棕色浅;
    VS Code 深色默认色对比度多在 9~10, 不封顶会把深色主题本来够读的终端色都提成浅色, 偏离原主题."""
    (rgb, alpha), (drgb, dalpha) = parse(v), parse(default)
    a = int(alpha, 16) / 255 if alpha else 1.0
    goal = min(FILL_TEXT_CR, cr(blend(drgb, vs_bg, int(dalpha, 16) / 255) if dalpha else drgb, vs_bg))
    L, _, H = oklch(rgb)
    s, step, out = sat(rgb), (0.004 if lum(rgb) >= lum(bg) else -0.004), rgb
    while cr(blend(out, bg, a), bg) < goal and 0 < L + step < 1:
        L += step
        out = with_sat(L, s, H)
    return hx(out) + alpha


# 状态色组内两两色差目标(门禁清晰理想 15): 原主题没定义而由 fill_hardcoded 补出的状态色, 撞上同组颜色时改取另一个终端色
STATUS_DE = 15.0


def status_apart(colors: dict, src_colors: dict, t: dict, m: 'Mapper') -> None:
    from colorlib import de2000
    bg = t['bg']
    for group in STATUS_GROUPS:
        for k in group:
            if k in src_colors or k not in colors:
                continue
            others = [opaque(colors, o, bg) for o in group if o != k and o in colors]
            cur = opaque(colors, k, bg)
            if not others or min(de2000(cur, o) for o in others) >= STATUS_DE:
                continue
            hard = hardcoded_keys(t['dark'])
            vs_bg = parse(hard['editor.background'])[0]
            cands = [default_cr(v, hard[k], bg, vs_bg) if k in hard and not is_area(k) else v for _, c in m.hues if (v := m.accent(hx(c)))]
            colors[k] = max(cands, key=lambda v: min(de2000(parse(v)[0], o) for o in others))


# 亮高亮底压饱和度后与编辑区底的色差(CIEDE2000)最多补回到这里: 约 12 已一眼可辨, 再大就又成色块;
# 查找当前要比其他匹配深一档(原来靠更高的饱和度区分, 压完只能靠明度), 放宽到 18
HIGHLIGHT_MIN_DE = 12
HIGHLIGHT_MIN_DE_KEY = {'editor.findMatchBackground': 18}


def selections(colors: dict, t: dict) -> None:
    """编辑区选区与输入框里选中文字的底(搜索框, 筛选框等): 与各自底色的对比度到 选区可见 理想下限加余量, 不超过高亮上限,
    压在上面的字不低于口径(编辑区按 高亮上的字, 输入框按 输入框选中的字). 已达标的不动; selection.background 原主题未定义时
    沿用编辑区选区的色相. 先按惯常方向(浅色主题往深, 深色主题往亮)找, 字读不清时改往反方向(远离字色, 字反而更清楚)."""
    bg, fg = t['bg'], t['fg']
    if 'editor.selectionBackground' not in colors:
        return
    colors.setdefault('selection.background', colors['editor.selectionBackground'])
    inp, _, itext = input_selection(colors, bg)
    vis_lo, vis_hi = SELECTION_VISIBLE[0] + 0.08, HIGHLIGHT_MAX_CR - 0.05 if on('highlight_cap') else math.inf
    # 选区上的字按高亮底上的字的可读口径(3.5)判: 原选区上的字只要读得清就保留原选区, 不为凑 4.5 把选区压成近黑(如 Sunlit Dark)
    for k, under, text, tmin in (('editor.selectionBackground', bg, fg, HIGHLIGHT_TEXT_MIN + 0.05),
                                 ('selection.background', inp, itext, INPUT_SELECTION_TEXT[1] + 0.05)):
        rgb, alpha = parse(colors[k])
        cur = blend(rgb, under, int(alpha, 16) / 255 if alpha else 1.0)
        if vis_lo - 0.08 <= cr(cur, under) <= vis_hi and cr(text, cur) >= tmin - 0.05:
            continue
        # 先从原选区色出发只动必要的一侧: 看不出就远离底色, 字读不清就远离字色; 两者兼顾不了再按下面从底色重算
        if cr(text, cur) >= tmin - 0.05:
            c = away(cur, under, vis_lo)
            if cr(text, c) >= tmin - 0.05 and cr(c, under) <= vis_hi:
                colors[k] = hx(c)
                continue
        elif cr(cur, under) >= vis_lo - 0.08:
            c = away(cur, text, tmin)
            if vis_lo - 0.08 <= cr(c, under) <= vis_hi:
                colors[k] = hx(c)
                continue
        _, C, H = oklch(cur)
        Lu = oklch(under)[0]
        # best: 看得出且字可读; most: 字可读的前提下最看得出的一档(正文本身偏淡, 如 Sunlit Light 4.56, 两者兼顾不了时退而用它)
        best, most = None, cur
        for sign in ((-1, 1) if lum(under) > 0.2 else (1, -1)):
            for i in range(1, 120):
                L = Lu + sign * i * 0.004
                if not 0 < L < 1:
                    break
                c = from_oklch(L, C, H)
                if on('bright_tint') and L > BRIGHT_TINT_L and sat(c) > BRIGHT_TINT_SAT[0] - 0.02:
                    c = from_oklch(L, C * (BRIGHT_TINT_SAT[0] - 0.02) / max(sat(c), 1e-6), H)
                if cr(text, c) < tmin or cr(c, under) > vis_hi:
                    break
                if cr(c, under) > cr(most, under) or cr(text, most) < tmin - 0.05:
                    most = c
                if cr(c, under) >= vis_lo:
                    best = c
                    break
            if best is not None:
                break
        if best is not None:
            colors[k] = hx(best)
        elif hx(most) != hx(cur):
            colors[k] = hx(most)


# 列表(文件树, 问题面板等)选中 / 聚焦 / 悬停行上的字与其行底; 字未定义时 VS Code 用 foreground
LIST_TEXT_PAIRS = [('list.activeSelectionForeground', 'list.activeSelectionBackground'),
                   ('list.inactiveSelectionForeground', 'list.inactiveSelectionBackground'),
                   ('list.focusForeground', 'list.focusBackground'), ('list.hoverForeground', 'list.hoverBackground')]


def list_selection_text(colors: dict, t: dict) -> None:
    """列表选中行上的字不低于 4.5: 字不换边, 先往原方向推(白字更白), 不够再微调行底(见 nudge); 都不行才换字色."""
    bg = t['bg']
    for fk, bk in LIST_TEXT_PAIRS:
        under = opaque(colors, bk, bg)
        text = opaque(colors, fk, under) if under is not None and fk in colors else None
        if under is None:
            continue
        text = text or opaque(colors, 'foreground', under) or t['fg']
        if cr(text, under) >= 4.5:
            continue
        n = nudge(under, text, 4.5)
        if n is not None:
            if n[0] != under:
                colors[bk] = hx(n[0])
            colors[fk] = hx(n[1])
        else:
            side = max((t['fg'], bg), key=lambda x: cr(x, under))
            colors[fk] = hx(tune(hx(side), under, 1.0, 4.55))


def calm(colors: dict, t: dict) -> None:
    # 面板底色不成亮块, 高亮底色不刺眼且压在上面的正文可读; 口径与 comfort.py 的防疲劳规则一致
    bg, fg = t['bg'], t['fg']
    for k in PANEL_KEYS + HIGHLIGHT_KEYS:
        p = parse(colors.get(k))
        if p is None:
            continue
        rgb, alpha = p
        a = int(alpha, 16) / 255 if alpha else 1.0
        limit = PANEL_MAX_CR if k in PANEL_KEYS else HIGHLIGHT_MAX_CR
        capped = on('panel_glare') if k in PANEL_KEYS else on('highlight_cap')
        # 留 0.03 余量, 避免 hex 取整后又越过门禁边界
        # 浅色主题的大面积底色另有亮度上限(LIGHT_PANEL_MAX): 比编辑区底更亮的输入框, 弹窗等像一块块白纸
        bright = lambda c, a: on('light_panel') and not t['dark'] and k in PANEL_KEYS and lum(blend(c, bg, a)) > LIGHT_PANEL_MAX - 0.01
        bad = lambda c, a: (capped and cr(blend(c, bg, a), bg) > limit - 0.03) or bright(c, a) or (
            on('highlight_text') and k in HIGHLIGHT_KEYS and cr(fg, blend(c, bg, a)) < HIGHLIGHT_TEXT_MIN + 0.03)
        if bad(rgb, a):
            if alpha:
                while a > 0.05 and bad(rgb, a):
                    a -= 0.02
                alpha = '%02X' % round(a * 255)
            else:
                L, C, H = oklch(rgb)
                step = 0.004 if oklch(bg)[0] > L else -0.004
                while bad(rgb, 1.0) and 0 < L < 1:
                    L += step
                    rgb = from_oklch(L, C, H)
            colors[k] = hx(rgb) + alpha
        # 亮的高亮底(浅色主题的选区, 查找等)饱和度压到理想上限内, 近白处同样的彩度已是糖果色; 二分自身彩度, 留余量防 hex 取整越界
        vivid = lambda c: on('bright_tint') and k in HIGHLIGHT_KEYS and oklch(blend(c, bg, a))[0] > BRIGHT_TINT_L and \
            sat(blend(c, bg, a)) > BRIGHT_TINT_SAT[0] - 0.02
        if vivid(rgb):
            de0 = de2000(blend(rgb, bg, a), bg)
            L, C, H = oklch(rgb)

            def desat(L):
                lo, hi = 0.0, C
                for _ in range(30):
                    mid = (lo + hi) / 2
                    lo, hi = (lo, mid) if vivid(from_oklch(L, mid, H)) else (mid, hi)
                return from_oklch(L, lo, H)
            rgb = desat(L)
            # 改彩度会带动亮度, 再沿底色方向收明度, 不让高亮底因此越过对比度口径
            step = 0.004 if oklch(bg)[0] > L else -0.004
            while bad(rgb, a) and 0 < L < 1:
                L += step
                rgb = desat(L)
            # 与底色亮度相近的高亮(如 Ayu Light 的查找)原本只靠饱和度区分, 压完会认不出; 往远离底色的方向挪明度,
            # 把与底色的色差补回压之前的水平(最多 HIGHLIGHT_MIN_DE), 不越过对比度口径
            target = min(de0, HIGHLIGHT_MIN_DE_KEY.get(k, HIGHLIGHT_MIN_DE))
            while de2000(blend(rgb, bg, a), bg) < target and 0 < L < 1:
                nxt = desat(L - step)
                if bad(nxt, a):
                    break
                L, rgb = L - step, nxt
            colors[k] = hx(rgb) + alpha
        # 彩度在对比度之后压: 降透明度会让底色占比变大, 底色自身的彩度随之透出来
        chroma = lambda c: oklch(blend(c, bg, a))[1]
        if on('panel_chroma') and k in PANEL_KEYS and chroma(rgb) > PANEL_MAX_CHROMA:
            # 半透明色叠到底色上后的彩度与自身彩度不成比例, 二分自身彩度, 让叠色结果落在上限内(留余量防 hex 取整越界)
            L, C, H = oklch(rgb)
            lo, hi = 0.0, C
            for _ in range(30):
                mid = (lo + hi) / 2
                lo, hi = (mid, hi) if chroma(from_oklch(L, mid, H)) <= PANEL_MAX_CHROMA - 0.002 else (lo, mid)
            rgb = from_oklch(L, lo, H)
            # 中性灰半透明叠在带色底上, sRGB 混色后仍可能带出底色的彩度; 此时往底色的反色相补一点彩度抵消
            if chroma(rgb) > PANEL_MAX_CHROMA - 0.002:
                rgb = min((from_oklch(L, i / 500, oklch(bg)[2] + math.pi) for i in range(51)), key=chroma)
            # 改彩度会带动亮度, 再沿底色方向收明度, 不让面板因此越过亮块上限
            L, C, H = oklch(rgb)
            step = 0.004 if oklch(bg)[0] > L else -0.004
            while bad(rgb, a) and 0 < L < 1:
                L += step
                rgb = from_oklch(L, C, H)
            colors[k] = hx(rgb) + alpha


# 查找当前要比其他匹配醒目: 与编辑区底的色差至少大 FIND_GAP_DE(Owl Light 原先两者同色, Pale 的当前反而更淡);
# 不足时先把当前往远离底色挪明度, 到高亮口径边界仍不够再把其他匹配往底色收, 但其他匹配的色差不低于 FIND_OTHER_MIN_DE
FIND_GAP_DE, FIND_OTHER_MIN_DE = 5, 5


def find_order(colors: dict, t: dict) -> None:
    bg, fg = t['bg'], t['fg']
    keys = 'editor.findMatchBackground', 'editor.findMatchHighlightBackground'
    ps = [parse(colors.get(k)) for k in keys]
    if None in ps:
        return
    (c, calpha), (o, oalpha) = ps
    ca, oa = (int(x, 16) / 255 if x else 1.0 for x in (calpha, oalpha))
    de = lambda x, a: de2000(blend(x, bg, a), bg)
    short = lambda: de(c, ca) < de(o, oa) + FIND_GAP_DE
    vivid = lambda x, a: on('bright_tint') and oklch(blend(x, bg, a))[0] > BRIGHT_TINT_L and sat(blend(x, bg, a)) > BRIGHT_TINT_SAT[0] - 0.02
    ok = lambda x, a: ((not on('highlight_cap') or cr(blend(x, bg, a), bg) <= HIGHLIGHT_MAX_CR - 0.03)
                       and (not on('highlight_text') or cr(fg, blend(x, bg, a)) >= HIGHLIGHT_TEXT_MIN + 0.03) and not vivid(x, a))
    if not short():
        return
    L, C, H = oklch(c)
    away = -0.004 if oklch(bg)[0] > 0.5 else 0.004
    while short() and 0 < L + away < 1:
        lo, hi = 0.0, C
        if vivid(from_oklch(L + away, C, H), ca):
            for _ in range(30):
                mid = (lo + hi) / 2
                lo, hi = (lo, mid) if vivid(from_oklch(L + away, mid, H), ca) else (mid, hi)
        else:
            lo = C
        nxt = from_oklch(L + away, lo, H)
        if not ok(nxt, ca):
            break
        L, c = L + away, nxt
    colors[keys[0]] = hx(c) + calpha
    if oalpha:
        while short() and oa > 0.06 and de(o, oa - 0.02) >= FIND_OTHER_MIN_DE:
            oa -= 0.02
        colors[keys[1]] = hx(o) + '%02X' % round(oa * 255)
    else:
        L, C, H = oklch(o)
        while short() and de(from_oklch(L - away, C, H), 1.0) >= FIND_OTHER_MIN_DE:
            L -= away
            o = from_oklch(L, C, H)
        colors[keys[1]] = hx(o)


# 徽标的生成目标比门禁(BADGE_MAX_CR 2.2, 字 >= 3.5)更安静: 低彩度的色点, 与编辑区底对比度 BADGE_SOFT_CR 以内, 字推到 BADGE_TEXT_GOAL;
# 贴着门禁上限时浅色主题是一片粉彩色块, 上面的深色字只有 3.7, 深色主题的字只有 3.6
BADGE_CHROMA, BADGE_SOFT_CR, BADGE_TEXT_GOAL = 0.07, 1.7, 4.5
# 小块(按钮, 徽标)上的字不够读时先保留原样式: 字不换边(白字仍是白字), 先沿原方向推到更白 / 更黑, 不够再把底色沿远离字色的方向
# 调明度(色相与饱和度不变), 如 One Light 蓝底白字 3.8 只把蓝色加深一点(ΔE 5); 底色要变 NUDGE_MAX_DE 以上才够时(一眼已是另一种颜色),
# 多半是原主题配错了字色(如 Moka Light 蓝底红字 1.1, 要变 38), 才换字色. 15 以内的有各主题白字橙底的 Warning 徽标(12~14)
NUDGE_MAX_DE = 15


def away(c: Rgb, ref: Rgb, goal: float) -> Rgb:
    """c 沿远离 ref 的方向调明度(比 ref 亮就更亮, 暗就更暗), 色相与饱和度不变, 直到对比度 >= goal 或到头;
    与 fit 不同, 方向按两者的相对明暗定, 不按 ref 是不是暗色(中等亮度的彩色底上的白字也往白推)."""
    L, _, H = oklch(c)
    s, step, out = sat(c), (0.004 if lum(c) >= lum(ref) else -0.004), c
    while cr(out, ref) < goal and 0 < L + step < 1:
        L += step
        out = with_sat(L, s, H)
    return out


def nudge(block: Rgb, text: Rgb, goal: float) -> tuple[Rgb, Rgb] | None:
    """(底色, 字色): 字沿远离 block 的方向推(不换边), 仍不够时 block 沿远离字的方向调明度, 直到对比度 >= goal;
    调到头仍不够, 或底色变化超过 NUDGE_MAX_DE 时返回 None."""
    t = away(text, block, goal + 0.05)
    c = away(block, t, goal + 0.05)
    return (c, t) if cr(t, c) >= goal and de2000(block, c) <= NUDGE_MAX_DE else None


def quiet_badges(colors: dict, t: dict) -> None:
    # 徽标: 压到 BADGE_SOFT_CR 以内, 深色主题不成亮块, 浅色主题不成暗斑; 字取与徽标反差大的一侧(暗徽标配浅字, 亮徽标配深字), 推到可读
    bg, dark = t['bg'], t['dark']
    quiet, need_text = on('badge_quiet'), on('badge_text')
    if not (quiet or need_text):
        return
    for bk, fk in BADGE_PAIRS:
        badge = opaque(colors, bk, bg)
        if badge is None:
            continue
        if quiet:
            L, C, H = oklch(badge)
            if C > BADGE_CHROMA:
                badge = from_oklch(L, BADGE_CHROMA, H)
            if cr(badge, bg) > BADGE_SOFT_CR:
                badge = toward_bg(badge, bg, BADGE_SOFT_CR)
        else:
            # 只管字可读: 原来的字已可读(或没定义字色)就不动
            cur = opaque(colors, fk, badge)
            if cur is None or cr(cur, badge) >= BADGE_TEXT_GOAL:
                continue
        if not need_text:
            colors[bk] = hx(badge)
            continue
        if not quiet and (n := nudge(badge, cur, BADGE_TEXT_GOAL)) is not None:
            colors[bk] = hx(n[0])
            if n[1] != cur:
                colors[fk] = hx(n[1])
            continue
        # 亮度 0.18 附近白字与黑字对徽标的对比度相等; 字从正文(深色主题浅字)或底色一侧起步, 不额外提亮或加黑
        light = lum(badge) < 0.18
        text = (t['fg'] if dark else t['bg']) if light else (t['bg'] if dark else t['fg'])
        step = 0.004 if light else -0.004
        # 先把徽标往远离字的方向调(深色主题即再压暗); 靠近编辑区底时最多到面板上限, 免得徽标看不出来
        L, C, H = oklch(badge)
        toward = (-step > 0) == (oklch(bg)[0] > L)
        while cr(text, badge) < BADGE_TEXT_GOAL + 0.03 and 0 < L - step < 1 and not (toward and cr(badge, bg) < PANEL_MAX_CR + 0.1):
            L -= step
            badge = from_oklch(L, C, H)
        L, C, H = oklch(text)
        while cr(text, badge) < BADGE_TEXT_GOAL + 0.03 and 0 < L + step < 1:
            L += step
            text = from_oklch(L, C, H)
        colors[bk], colors[fk] = hx(badge), hx(text)


def quiet_buttons(colors: dict, t: dict) -> None:
    """按钮底: 彩度封顶 BUTTON_CHROMA, 明度从编辑区底向外推到 BUTTON_PAIRS 给的对比度(色相不变); 字从正文起步推到 4.5."""
    bg, fg = t['bg'], t['fg']
    for key, target in BUTTON_PAIRS if on('button_quiet') else []:
        c = opaque(colors, key, bg)
        if c is None:
            continue
        L, C, H = oklch(c)
        C = min(C, BUTTON_CHROMA)
        L = oklch(bg)[0]
        step = 0.004 if t['dark'] else -0.004
        b = from_oklch(L, C, H)
        while cr(b, bg) < target and 0 < L < 1:
            L += step
            b = from_oklch(L, C, H)
        colors[key] = hx(b)
    # 半透明的按钮底按叠到编辑区底上的实际颜色算
    under = opaque(colors, 'button.background', bg)
    cur = under and opaque(colors, 'button.foreground', under)
    if under and on('button_text') and not on('button_quiet') and cur is not None and cr(cur, under) < 4.5:
        # 只管字可读时保留原按钮的样式(见 NUDGE_MAX_DE): 只调按钮底(连同悬停底)够用就不动字; 不够的换字色,
        # 在正文与编辑区底两侧取对按钮底反差大的一侧(Pale Light 深紫底上原为深色字 2.6, 换浅色字)
        if (n := nudge(under, cur, 4.5)) is not None:
            colors['button.background'] = hx(n[0])
            if n[1] != cur:
                colors['button.foreground'] = hx(n[1])
            hover = opaque(colors, 'button.hoverBackground', bg)
            if hover is not None and cr(n[1], hover) < 4.5:
                colors['button.hoverBackground'] = hx((nudge(hover, n[1], 4.5) or (hover,))[0])
            return
        side = max((fg, bg), key=lambda x: cr(x, under))
        text = tune(hx(side), under, 1.0, 4.55)
        colors['button.foreground'] = hx(text)
        # 字推到纯白 / 纯黑仍不够时, 按钮底再往反方向挪一点补足
        if cr(text, under) < 4.5:
            colors['button.background'] = hx(fit(under, text, lo=4.55))
        return
    if under and on('button_text') and (on('button_quiet') or cur is None or cr(cur, under) < 4.5):
        colors['button.foreground'] = hx(tune(hx(fg), under, 1.0, 4.55))


IGNORED_MIN = 3.0


def quiet_lists_and_borders(colors: dict, t: dict, m: 'Mapper') -> None:
    """列表选中行的字用正文色; 布局边框去掉彩度; 被忽略文件(.gitignore 命中)按注释的对比度显示: 看得出变淡, 也仍然读得清."""
    bg, fg = t['bg'], t['fg']
    for k in LIST_TEXT_KEYS if on('list_text_fg') else []:
        p = parse(colors.get(k))
        if p and oklch(p[0])[1] > NEUTRAL_CHROMA:
            colors[k] = hx(fg) + p[1]
    for k in BORDER_KEYS if on('border_quiet') else []:
        p = parse(colors.get(k))
        if p and oklch(p[0])[1] > PANEL_MAX_CHROMA:
            L, C, H = oklch(p[0])
            colors[k] = hx(from_oklch(L, PANEL_MAX_CHROMA, H)) + p[1]
        # 只需看得出分界: 与编辑区底的对比度压到 BORDER_MAX_CR(如 Dracula 的拆分线原本 6.5, 一道亮线贯穿屏幕)
        p = parse(colors.get(k))
        if p is None:
            continue
        rgb, alpha = p
        a = int(alpha, 16) / 255 if alpha else 1.0
        if cr(blend(rgb, bg, a), bg) > BORDER_MAX_CR:
            if alpha:
                while a > 0.05 and cr(blend(rgb, bg, a), bg) > BORDER_MAX_CR - 0.02:
                    a -= 0.02
                colors[k] = hx(rgb) + '%02X' % round(a * 255)
            else:
                colors[k] = hx(toward_bg(rgb, bg, BORDER_MAX_CR - 0.02))
    k = 'gitDecoration.ignoredResourceForeground'
    p = parse(colors.get(k))
    if p and on('ignored_floor') and not on('ignored_dim'):
        # 只在读不清(低于 IGNORED_MIN)时提上来, 色相与饱和度不变
        under = opaque(colors, 'sideBar.background', bg) or bg
        c = blend(p[0], under, int(p[1], 16) / 255) if p[1] else p[0]
        if cr(c, under) < IGNORED_MIN:
            colors[k] = hx(fit(c, under, lo=IGNORED_MIN + 0.02))
    if p and m.comment_cr and on('ignored_dim'):
        under = opaque(colors, 'sideBar.background', bg) or bg
        c = blend(p[0], under, int(p[1], 16) / 255) if p[1] else p[0]
        # 比普通文件名(侧边栏前景)至少暗一档, 否则看不出被忽略
        normal = opaque(colors, 'sideBar.foreground', under) or opaque(colors, 'foreground', under)
        target = min(m.comment_cr, cr(normal, under) * 0.75) if normal else m.comment_cr
        colors[k] = hx(toward_bg(tune(hx(c), under, 0.04, target), under, target))


def quiet_ui_text(colors: dict, t: dict) -> None:
    # 界面文字与图标不比正文更刺眼(口径见 comfort.ui_text_glare); 彩色小块(按钮, 徽标)上的字不在此列
    bg = t['bg']
    limit = cr(t['fg'], bg) * UI_TEXT_MAX
    for k in list(colors) if on('ui_text_cap') else []:
        if not k.lower().endswith('foreground') or k.startswith(UI_TEXT_SKIP):
            continue
        under, colored = own_background(colors, k, bg)
        p = parse(colors[k])
        if colored or p is None:
            continue
        rgb, alpha = p
        a = int(alpha, 16) / 255 if alpha else 1.0
        if cr(blend(rgb, under, a), under) <= limit:
            continue
        if alpha:
            while a > 0.05 and cr(blend(rgb, under, a), under) > limit - 0.02:
                a -= 0.02
            colors[k] = hx(rgb) + '%02X' % round(a * 255)
        else:
            colors[k] = hx(toward_bg(rgb, under, limit - 0.02))


def cap_cr(colors: dict, k: str, under: Rgb, limit: float) -> None:
    """k 的颜色与 under 的对比度压到 limit 以内: 半透明色降透明度, 不透明色朝底色收明度, 色相不变."""
    p = parse(colors.get(k))
    if p is None:
        return
    rgb, alpha = p
    a = int(alpha, 16) / 255 if alpha else 1.0
    if cr(blend(rgb, under, a), under) <= limit:
        return
    if alpha:
        while a > 0.05 and cr(blend(rgb, under, a), under) > limit - 0.02:
            a -= 0.02
        colors[k] = hx(rgb) + '%02X' % round(a * 255)
    else:
        colors[k] = hx(toward_bg(rgb, under, limit - 0.02))


def tint_grays(colors: dict, t: dict) -> None:
    # 底色带色调的主题里, 中间灰的底色块(多为 VS Code 默认色补出, 如活动栏 / 工具栏选中图标的底, 列表失焦选中行)换成底色的色调:
    # 色相取编辑区底, 彩度取底色彩度(封顶 PANEL_MAX_CHROMA), 明度与透明度不变; 口径见 comfort.gray_patches
    L0, C0, H0 = oklch(t['bg'])
    if C0 <= TINTED_BG_CHROMA or not on('tint_grays'):
        return
    for k in TINT_KEYS:
        p = parse(colors.get(k))
        if p is None:
            continue
        rgb, alpha = p
        L, C, H = oklch(rgb)
        a = int(alpha, 16) / 255 if alpha else 1.0
        if C < GRAY_CHROMA and 0.12 < L < 0.92 and a >= 0.2:
            colors[k] = hx(from_oklch(L, min(C0, PANEL_MAX_CHROMA - 0.002), H0)) + alpha


def quiet_controls(colors: dict, t: dict) -> None:
    # 输入框 / 下拉框(问题面板与输出面板的筛选框, 输出通道下拉框等): 描边去彩度并压到 CONTROL_BORDER_MAX_CR, 焦点描边不超过 正文 x FOCUS_MAX;
    # 占位提示字落到 PLACEHOLDER_CR(注释口径, 比输入的字淡), 输入的字至少 CONTROL_TEXT_MIN; 口径见 comfort.control_issues
    bg, fg = t['bg'], t['fg']
    inp = opaque(colors, 'input.background', bg) or bg
    quiet = on('control_quiet')
    for k in CONTROL_BORDER_KEYS if quiet else []:
        p = parse(colors.get(k))
        if p and oklch(p[0])[1] > PANEL_MAX_CHROMA:
            L, C, H = oklch(p[0])
            colors[k] = hx(from_oklch(L, PANEL_MAX_CHROMA, H)) + p[1]
        cap_cr(colors, k, bg, CONTROL_BORDER_MAX_CR)
    for k in FOCUS_KEYS:
        if quiet:
            cap_cr(colors, k, bg, cr(fg, bg) * FOCUS_MAX)
        if not on('focus_floor'):
            continue
        # 太淡时提到 FOCUS_MIN_CR(半透明色先叠成不透明), 色相不变: 否则聚焦的输入框反而比未聚焦的描边更暗(如 Owl / Pale 的焦点描边 1.0)
        c = opaque(colors, k, bg)
        if c is not None and cr(c, bg) < FOCUS_MIN_CR:
            rgb, alpha = parse(colors[k])
            a = int(alpha, 16) / 255 if alpha else 1.0
            while a < 1 and cr(blend(rgb, bg, a), bg) < FOCUS_MIN_CR:
                a = min(1.0, a + 0.02)
            ok = cr(blend(rgb, bg, a), bg) >= FOCUS_MIN_CR
            colors[k] = hx(rgb) + '%02X' % round(a * 255) if alpha and ok else hx(fit(c, bg, lo=FOCUS_MIN_CR + 0.02))
    ph = opaque(colors, PLACEHOLDER_KEY, inp)
    if ph is not None:
        lo, hi = PLACEHOLDER_CR
        L, C, H = oklch(ph)
        if on('placeholder_quiet') and C > PLACEHOLDER_MAX_CHROMA:
            ph = from_oklch(L, PLACEHOLDER_MAX_CHROMA - 0.002, H)
            colors[PLACEHOLDER_KEY] = hx(ph)
        if on('placeholder_quiet') and cr(ph, inp) > hi:
            colors[PLACEHOLDER_KEY] = hx(toward_bg(ph, inp, hi - 0.02))
        elif on('placeholder_floor') and cr(ph, inp) < lo:
            colors[PLACEHOLDER_KEY] = hx(tune(hx(ph), inp, 1.0, lo + 0.02))
    for fk, bk in CONTROL_TEXT_PAIRS if on('control_text') else []:
        under = opaque(colors, bk, bg) or bg
        c = opaque(colors, fk, under)
        if c is not None and cr(c, under) < CONTROL_TEXT_MIN:
            colors[fk] = hx(tune(hx(c), under, 1.0, CONTROL_TEXT_MIN + 0.02))


# 源代码管理 Graph 视图的分支标签: 字是 historyItemHoverLabelForeground(默认取面板底), 底是各 ref 色(默认取 charts.blue / charts.purple)
GRAPH_LABEL_TEXT = 'scmGraph.historyItemHoverLabelForeground'
GRAPH_REF_KEYS = [('scmGraph.historyItemRefColor', 'charts.blue', 'editorInfo.foreground'),
                  ('scmGraph.historyItemRemoteRefColor', 'charts.purple'), ('scmGraph.historyItemBaseRefColor',)]
GRAPH_LABEL_MIN = 4.5


def graph_labels(colors: dict, t: dict) -> None:
    # 标签字回到 VS Code 的默认取色(面板底); 原主题沿用的浅灰字落在 ref 色块上几乎看不清, 如 One Dark Pro 的 #B1B1B1 字压在蓝底上.
    # ref 色与字不够 GRAPH_LABEL_MIN 时沿远离字色的方向推明度, 色相不变
    if not on('graph_labels'):
        return
    colors.pop(GRAPH_LABEL_TEXT, None)
    bg = opaque(colors, 'panel.background', t['bg']) or t['bg']
    for chain in GRAPH_REF_KEYS:
        ref = next((opaque(colors, k, bg) for k in chain if colors.get(k)), None)
        if ref is not None and cr(ref, bg) < GRAPH_LABEL_MIN:
            colors[chain[0]] = hx(fit(ref, bg, lo=GRAPH_LABEL_MIN))


def comfortable(colors: dict, t: dict) -> None:
    """最后一遍(口径见 comfort 的护眼与鲜艳柔和维度): 不透明色收回极端黑白(阴影类不动);
    荧光感过强的颜色(按叠到底色上的实际颜色算)降彩度, 明度与透明度不变."""
    bg = t['bg']
    ux, nn = on('unextreme'), on('neon')
    for k, v in list(colors.items()) if ux or nn else []:
        p = parse(v)
        if p is None or 'shadow' in k.lower():
            continue
        rgb, alpha = p
        a = int(alpha, 16) / 255 if alpha else 1.0
        new = unextreme(rgb) if ux and a >= 0.9 else rgb
        L, C, H = oklch(new)
        while nn and neon(blend(new, bg, a)) > NEON_TARGET and C > 0.01:
            C *= 0.95
            new = from_oklch(L, C, H)
        if new != rgb:
            colors[k] = hx(new) + alpha


def transform(t: dict, src: dict) -> dict:
    m = Mapper(t, src)
    colors = {}
    for k, v in src['colors'].items():
        out = m.token(v) if k.startswith(TEXT_ON_CODE) else m.ui(v, area=is_area(k))
        if out is not None:
            colors[k] = out
    # 编辑区底色 / 正文 / 光标, 终端选区与 16 色按 themes.py 的结果写回; 与补全段产物相同的不动(保留原写法)
    put = lambda k, c: colors.__setitem__(k, hx(c)) if parse(colors.get(k)) is None or hx(opaque(colors, k, t['bg'])) != hx(c) else None
    for k, c in (('editor.background', t['bg']), ('editor.foreground', t['fg']), ('editorCursor.foreground', t['cursor'])):
        put(k, c)
    if t.get('sel_changed'):
        colors['terminal.selectionBackground'], colors['terminal.inactiveSelectionBackground'] = hx(t['sel']), hx(t['sel_inactive'])
    for n in ANSI:
        put('terminal.ansi' + n, t['ansi'][n])
        put('terminal.ansiBright' + n, t['ansi']['Bright' + n])
    # themes.py 按编辑区底提终端彩色; VS Code 终端画在 terminal.background 上(如 Ayu / Owl Light 比编辑区底深一档), 按它再补一次
    tbg = opaque(colors, 'terminal.background', t['bg'])
    if on('term_floor') and tbg is not None and hx(tbg) != hx(t['bg']):
        for k in [p + n for p in ('terminal.ansi', 'terminal.ansiBright') for n in ANSI[1:7]]:
            c = opaque(colors, k, tbg)
            if c is not None and cr(c, tbg) < LEGIBLE + TERM_MARGIN:
                colors[k] = hx(fit(c, tbg, lo=LEGIBLE + TERM_MARGIN))

    # 映射后仍可能有界面文字对比度不足(底色变了, 或原主题本身就偏淡), 逐对推到下限
    for fg_key, bg_key, need in UI_PAIRS if on('ui_text_floor') else []:
        under = opaque(colors, bg_key, t['bg']) or t['bg']
        fg = opaque(colors, fg_key, under)
        if fg is not None and cr(fg, under) < need:
            # 半透明的字先加不透明度, 够了就保留原色与透明度写法
            rgb, alpha = parse(colors[fg_key])
            a = int(alpha, 16) / 255 if alpha else 1.0
            while a < 1 and cr(blend(rgb, under, a), under) < need:
                a = min(1.0, a + 0.02)
            if alpha and cr(blend(rgb, under, a), under) >= need:
                colors[fg_key] = hx(rgb) + '%02X' % round(a * 255)
            else:
                colors[fg_key] = hx(tune(hx(fg), under, 1.0, need))
    line_no = opaque(colors, 'editorLineNumber.foreground', t['bg'])
    if on('line_no_cap') and line_no is not None and cr(line_no, t['bg']) > LINE_NO_MAX:
        colors['editorLineNumber.foreground'] = hx(toward_bg(line_no, t['bg'], LINE_NO_MAX))
    calm(colors, t)
    if on('find_order'):
        find_order(colors, t)
    quiet_badges(colors, t)
    quiet_buttons(colors, t)
    quiet_lists_and_borders(colors, t, m)
    quiet_ui_text(colors, t)
    quiet_controls(colors, t)
    tint_grays(colors, t)
    graph_labels(colors, t)
    # 分层门槛: 取代 ui_text_floor / badge_text / button_text 等旧的逐对下限; 放在选区之前, 选区按调整后的输入框字色求
    if on('level_floor'):
        levels.fix(colors, t)
    # 输入框底色与文字在前面几步还会调整, 选区放到它们之后求
    if on('list_selection_text'):
        list_selection_text(colors, t)
    if on('selections'):
        selections(colors, t)
    comfortable(colors, t)

    # 语法规则与语义色: 补全段已按规则池补齐, 这里只调色
    rules = source_rules(src, m)
    semantic = {}
    for k, v in (src.get('semanticTokenColors') or {}).items():
        if isinstance(v, str):
            v = m.token(v)
        elif isinstance(v, dict) and v.get('foreground'):
            v = dict(v, foreground=m.token(v['foreground']))
        if v:
            semantic[k] = v
    conform(colors, rules, semantic, t)
    return dict(colors=dict(sorted(colors.items())), tokenColors=rules, semanticTokenColors=semantic)


def is_comment_rule(rule: dict) -> bool:
    """规则按注释口径处理. 补全段按角色成组的规则(name 为 'Pool <角色>')看角色: 组里混有 comment.block.documentation variable
    这类选择器, 按选择器判会让整组变量色只抬到 3.4(如 Sunlit 的 Pool variable #268BD2 停在 3.41); 原主题自己的规则仍按选择器里
    出现 comment 判(含 punctuation.definition.comment 与 comment markup.link 这类注释里的片段, 原主题给的就是注释色)."""
    name = rule.get('name') or ''
    if name.startswith('Pool '):
        return name == 'Pool comment'
    return any('comment' in x for x in scopes_of(rule))


def source_rules(src: dict, m: 'Mapper') -> list[dict]:
    """沿用原主题的 tokenColors(选择器, 字体样式不变), 只把各条的前景色经 Mapper.token 调色(注释走注释口径)."""
    out = []
    for r in json.loads(json.dumps(src.get('tokenColors', []))):
        st = r.get('settings')
        if isinstance(st, dict) and st.get('foreground'):
            v = m.token(st['foreground'], comment=is_comment_rule(r))
            # 非 hex 的写法(如 inherit)VS Code 不认, 按 schema 丢掉
            if v:
                st['foreground'] = v
            else:
                del st['foreground']
        out.append(r)
    return out


def render(t: dict) -> dict:
    # 输入是补全段的中间主题 <name>-full.json(complete.py), 不是原主题
    src = load(os.path.join(SOURCES, t['full']))
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


def identity() -> int:
    if os.environ.get('COMFORT_STEPS') != 'none':
        print('--identity 要在 COMFORT_STEPS=none 下运行')
        return 2
    bad = []
    for t in build():
        full, out = load(os.path.join(SOURCES, t['full'])), render(t)
        for k in ('colors', 'tokenColors', 'semanticTokenColors'):
            a, b = full.get(k) or {}, out[k] or {}
            if a != b:
                diff = [x for x in set(a) | set(b) if a.get(x) != b.get(x)] if isinstance(a, dict) else [f'{len(a)} 条 vs {len(b)} 条']
                bad.append(f"{t['name']} {k}: {len(diff)} 处不同, 例 {sorted(map(str, diff))[:3]}")
    print('全关产物与 full 逐键相等' if not bad else '全关产物与 full 不等(有未登记的改色):\n  ' + '\n  '.join(bad))
    return 1 if bad else 0


def main() -> int:
    if '--identity' in sys.argv:
        return identity()
    check = '--check' in sys.argv
    out = sys.argv[sys.argv.index('--out') + 1] if '--out' in sys.argv else OUT
    os.makedirs(out, exist_ok=True)
    stale = []
    for t in build():
        path = os.path.join(out, f"{t['name']}.json")
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
